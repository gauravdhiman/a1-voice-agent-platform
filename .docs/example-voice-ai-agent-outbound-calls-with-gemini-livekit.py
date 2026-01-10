from __future__ import annotations

import asyncio
import json
import logging
import os

# Get the project root directory (parent of backend_motia)
import pathlib
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from livekit import api, rtc
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    WorkerType,
    cli,
    llm,
    utils,
)
from livekit.plugins.google.beta.realtime import RealtimeModel
from utils.database import CallStatus, DatabaseClient

# Load environment variables with priority order
# 1. .env.local (development)
# 2. .env (fallback)
# 3. System environment variables (production)


project_root = pathlib.Path(__file__).parent.parent

load_dotenv(dotenv_path=project_root / ".env.local", override=False)
load_dotenv(dotenv_path=project_root / ".env", override=False)
logger = logging.getLogger("outbound-caller")
logger.setLevel(logging.INFO)

outbound_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")

# Remove the initial chat context as it's not needed for RealtimeModel


@dataclass
class CallSessionConfig:
    """Configuration for the Gemini live API session"""

    gemini_api_key: str
    instructions: str
    voice: str
    temperature: float
    max_response_output_tokens: str | int
    call_id: str
    contact_name: str
    business_name: str
    phone_number: str

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if k != "gemini_api_key"}

    def __eq__(self, other) -> bool:
        return self.to_dict() == other.to_dict()


class OutboundCallAssistant(Agent):
    """LiveKit Agent for outbound calls using Google Gemini Live API"""

    def __init__(self, config: CallSessionConfig):
        self.config = config
        super().__init__(instructions=self.create_instructions())

    def create_instructions(self) -> str:
        """Create dynamic instructions based on call context"""
        return f"""
        You are a professional outbound calling assistant making a call on behalf of a business.

        CALL CONTEXT:
        - You are calling {self.config.contact_name} from {self.config.business_name}
        - Contact's phone number: {self.config.phone_number}
        - Call ID: {self.config.call_id} (for internal tracking)

        BEHAVIOR GUIDELINES:
        - Be polite, professional, and respectful at all times
        - Introduce yourself and the purpose of your call clearly
        - Listen actively and respond appropriately to the contact's needs
        - If the contact asks to be transferred to a human, confirm and use the transfer function
        - If you detect voicemail, acknowledge it briefly and hang up
        - Allow the contact to end the conversation naturally
        - Keep the conversation focused and productive

        IMPORTANT:
        - This is a real phone call, so speak naturally and conversationally
        - Be prepared for various responses including hang-ups, voicemail, or engaged conversations
        - Maintain professionalism even if the contact is uninterested or hostile
        """


class OutboundCallManager:
    """Manages outbound call sessions using Gemini live API"""

    def __init__(self, config: CallSessionConfig):
        self.config = config
        self.call_start_time = None
        self.db_client = DatabaseClient()
        self.agent_session: AgentSession | None = None
        self.participant: rtc.RemoteParticipant | None = None

    def create_realtime_model(self):
        """Create LiveKit Google RealtimeModel"""
        try:
            logger.info("Creating LiveKit Google RealtimeModel...")
            model = RealtimeModel(
                model="gemini-2.5-flash-preview-native-audio-dialog",
                voice="Puck",  # Use Puck voice as in the example
                temperature=0.8,
                api_key=self.config.gemini_api_key,
            )
            logger.info("RealtimeModel created successfully")
            return model
        except Exception as e:
            logger.error(f"Error creating RealtimeModel: {e}")
            raise

    async def setup_session(self, ctx: JobContext, participant: rtc.RemoteParticipant):
        """Setup the LiveKit AgentSession with Google RealtimeModel"""
        try:
            self.participant = participant

            # Create RealtimeModel
            realtime_model = self.create_realtime_model()

            # Create AgentSession with RealtimeModel (following new pattern)
            self.agent_session = AgentSession(
                llm=realtime_model,  # Use RealtimeModel instead of pipeline
                # No STT/TTS needed since RealtimeModel handles audio directly
            )

            # Create the Assistant agent
            assistant = OutboundCallAssistant(self.config)

            # Start the session with the agent
            await self.agent_session.start(agent=assistant, room=ctx.room)

            # Register call event handlers
            self._register_event_handlers(ctx)

            # Mark call as started
            await self.on_call_started()

            logger.info(
                f"LiveKit AgentSession with Google RealtimeModel started for call {self.config.call_id}"
            )

        except Exception as e:
            logger.error(f"Error setting up session: {e}")
            await self.on_call_failed(str(e))
            raise

    # Function handlers removed for now - can be added back when function calling is properly supported

    def _register_event_handlers(self, ctx: JobContext):
        """Register event handlers for call lifecycle"""

        @ctx.room.on("participant_disconnected")
        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            if participant.identity == self.participant.identity:
                logger.info(f"Participant {participant.identity} disconnected")
                asyncio.create_task(self.on_call_ended("participant_disconnected"))

    async def hangup(self):
        """Helper function to hang up the call by deleting the room"""
        try:
            # Calculate call duration if we have start time
            duration = None
            if self.call_start_time:
                duration = int(
                    (datetime.utcnow() - self.call_start_time).total_seconds()
                )

            # Update call status to completed
            await self.db_client.update_call_status(
                self.config.call_id, CallStatus.COMPLETED, duration=duration
            )

            # Create call event
            await self.db_client.create_call_event(
                self.config.call_id,
                "call_ended",
                {
                    "end_time": datetime.utcnow().isoformat(),
                    "duration": duration,
                    "ended_by": "agent",
                },
            )

            logger.info(f"Call {self.config.call_id} completed, duration: {duration}s")

        except Exception as e:
            logger.error(f"Error updating call status on hangup: {e}")

        # Clean up session
        await self.end_session()

        # Delete the room
        from livekit.agents import get_job_context

        job_ctx = get_job_context()
        await job_ctx.api.room.delete_room(
            api.DeleteRoomRequest(
                room=job_ctx.room.name,
            )
        )

    @utils.log_exceptions(logger=logger)
    async def end_session(self):
        """End the current AgentSession"""
        try:
            logger.info("Ending AgentSession")
            if hasattr(self, "agent_session") and self.agent_session:
                await self.agent_session.aclose()
            logger.info("AgentSession ended")
        except Exception as e:
            logger.warning(f"Error ending AgentSession: {e}")

    async def on_call_started(self):
        """Called when call begins - update database"""
        try:
            self.call_start_time = datetime.utcnow()

            # Update call status to in_progress
            await self.db_client.update_call_status(
                self.config.call_id,
                CallStatus.IN_PROGRESS,
                start_time=self.call_start_time,
            )

            # Create call event
            await self.db_client.create_call_event(
                self.config.call_id,
                "call_started",
                {
                    "start_time": self.call_start_time.isoformat(),
                    "contact_name": self.config.contact_name,
                    "business_name": self.config.business_name,
                },
            )

            logger.info(f"Call {self.config.call_id} started at {self.call_start_time}")

        except Exception as e:
            logger.error(f"Error updating call status on start: {e}")

    async def on_call_ended(self, reason: str = "natural_completion"):
        """Called when call ends - update database"""
        try:
            # Calculate duration
            duration = None
            if self.call_start_time:
                duration = int(
                    (datetime.utcnow() - self.call_start_time).total_seconds()
                )

            # Create a simple summary
            summary = f"Call completed. Duration: {duration}s. Reason: {reason}"

            # Update call status with summary
            await self.db_client.update_call_status(
                self.config.call_id,
                CallStatus.COMPLETED,
                summary=summary,
                duration=duration,
            )

            # Create call event
            await self.db_client.create_call_event(
                self.config.call_id,
                "call_ended",
                {
                    "end_time": datetime.utcnow().isoformat(),
                    "duration": duration,
                    "summary": summary,
                    "ended_by": reason,
                },
            )

            logger.info(
                f"Call {self.config.call_id} ended: {reason}, duration: {duration}s"
            )

        except Exception as e:
            logger.error(f"Error updating call status on end: {e}")

    async def on_call_failed(self, error_message: str):
        """Called when call fails - update database"""
        try:
            # Update call status to failed
            await self.db_client.update_call_status(
                self.config.call_id, CallStatus.FAILED, failure_reason=error_message
            )

            # Create call event
            await self.db_client.create_call_event(
                self.config.call_id,
                "call_failed",
                {
                    "failure_time": datetime.utcnow().isoformat(),
                    "failure_reason": error_message,
                },
            )

            logger.error(f"Call {self.config.call_id} failed: {error_message}")

        except Exception as e:
            logger.error(f"Error updating call status on failure: {e}")

    async def on_voicemail_detected(self):
        """Called when voicemail is detected"""
        try:
            # Update call status to voicemail
            await self.db_client.update_call_status(
                self.config.call_id, CallStatus.VOICEMAIL
            )

            # Create call event
            await self.db_client.create_call_event(
                self.config.call_id,
                "voicemail_detected",
                {
                    "detection_time": datetime.utcnow().isoformat(),
                    "participant_identity": (
                        self.participant.identity if self.participant else None
                    ),
                },
            )

            logger.info(f"Call {self.config.call_id} marked as voicemail")

        except Exception as e:
            logger.error(f"Error updating call status for voicemail: {e}")

        # End the call
        await self.hangup()


def parse_call_metadata(metadata: dict) -> CallSessionConfig:
    """Parse call metadata into session configuration"""
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")

    config = CallSessionConfig(
        gemini_api_key=gemini_api_key,
        instructions="",  # Will be generated dynamically
        voice="Puck",  # Use Puck voice as recommended in LiveKit example
        temperature=0.8,
        max_response_output_tokens=2048,
        call_id=metadata["call_id"],
        contact_name=metadata.get("contact_name", "Unknown"),
        business_name=metadata.get("business_name", "Unknown"),
        phone_number=metadata["phone_number"],
    )
    return config


async def entrypoint(ctx: JobContext):
    logger.info(f"Agent worker starting for room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Parse call metadata from room metadata
    try:
        # Get room metadata
        room_metadata = None
        if hasattr(ctx.room, "metadata") and ctx.room.metadata:
            room_metadata = ctx.room.metadata
        elif hasattr(ctx, "job") and ctx.job and ctx.job.metadata:
            room_metadata = ctx.job.metadata

        if room_metadata:
            metadata = json.loads(room_metadata)
            logger.info(f"Parsed room metadata: {metadata}")
        else:
            # Extract call_id from room name and get call info from database
            call_id = ctx.room.name.replace("call-", "")
            logger.info(f"No metadata found, using call_id from room name: {call_id}")

            # Get call info from database
            db_client = DatabaseClient()
            call = await db_client.get_call(call_id)

            if call:
                # Get contact info
                contact = (
                    await db_client.get_contact(call.contact_id)
                    if call.contact_id
                    else None
                )

                metadata = {
                    "call_id": call_id,
                    "phone_number": call.phone_number,
                    "contact_name": contact.name if contact else "Unknown",
                    "business_name": contact.business_name if contact else "Unknown",
                }
                logger.info(f"Retrieved metadata from database: {metadata}")
            else:
                logger.error(f"Could not find call {call_id} in database")
                ctx.shutdown()
                return

    except Exception as e:
        logger.error(f"Error parsing metadata: {e}")
        ctx.shutdown()
        return

    config = parse_call_metadata(metadata)
    participant_identity = phone_number = metadata["phone_number"]

    logger.info(f"Starting outbound call to {phone_number} for {config.contact_name}")

    # Create call manager
    call_manager = OutboundCallManager(config)

    # Update call status to show agent is processing
    try:
        await call_manager.db_client.update_call_status(
            config.call_id, CallStatus.RINGING
        )
        await call_manager.db_client.create_call_event(
            config.call_id,
            "agent_started",
            {
                "room_name": ctx.room.name,
                "phone_number": phone_number,
                "note": "Agent worker started processing the call",
            },
        )
    except Exception as e:
        logger.error(f"Error updating call status: {e}")

    # `create_sip_participant` starts dialing the user
    try:
        logger.info(f"Creating SIP participant for {phone_number}")
        logger.info(f"Using SIP trunk: {outbound_trunk_id}")
        logger.info(f"Room name: {ctx.room.name}")
        logger.info(f"Participant identity: {participant_identity}")

        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=outbound_trunk_id,
                sip_call_to=phone_number,
                participant_identity=participant_identity,
                # function blocks until user answers the call, or if the call fails
                wait_until_answered=True,
            )
        )

        # Wait for participant to join
        participant = await ctx.wait_for_participant(identity=participant_identity)
        logger.info(f"participant joined: {participant.identity}")

        # Setup Gemini live API session
        await call_manager.setup_session(ctx, participant)

        logger.info("Outbound call session established with Gemini live API")

    except api.TwirpError as e:
        sip_status_code = e.metadata.get("sip_status_code", "unknown")
        sip_status = e.metadata.get("sip_status", "unknown")

        logger.error(
            f"SIP call failed - error creating SIP participant: {e.message}, "
            f"SIP status: {sip_status_code} ({sip_status})"
        )

        # Log detailed debugging information
        logger.error(
            f"Call details - Phone: {phone_number}, Trunk: {outbound_trunk_id}, Room: {ctx.room.name}"
        )
        logger.error(f"Full error metadata: {e.metadata}")

        # Provide specific error messages for common SIP errors
        if sip_status_code == "400":
            error_msg = f"SIP 400 BAD_REQUEST - Invalid phone number format or trunk configuration. Check: 1) Phone number format (+1234567890), 2) SIP trunk outbound permissions, 3) Caller ID verification. Phone: {phone_number}, Trunk: {outbound_trunk_id}"
        elif sip_status_code == "403":
            error_msg = f"SIP 403 FORBIDDEN - Check trunk permissions and phone number verification. Trunk: {outbound_trunk_id}, Number: {phone_number}"
        elif sip_status_code == "404":
            error_msg = f"SIP 404 NOT FOUND - Invalid phone number or trunk configuration. Number: {phone_number}"
        elif sip_status_code == "486":
            error_msg = (
                f"SIP 486 BUSY HERE - Phone number is busy. Number: {phone_number}"
            )
        else:
            error_msg = f"SIP error {sip_status_code} ({sip_status}): {e.message}"

        await call_manager.on_call_failed(error_msg)
        ctx.shutdown()
    except Exception as e:
        logger.error(f"Unexpected error in call setup: {e}")
        await call_manager.on_call_failed(f"Setup error: {str(e)}")
        ctx.shutdown()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            worker_type=WorkerType.ROOM,
        )
    )
