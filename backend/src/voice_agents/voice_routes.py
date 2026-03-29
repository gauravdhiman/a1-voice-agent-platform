import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response
from twilio.twiml.voice_response import VoiceResponse

from shared.voice_agents.service import voice_agent_service

logger = logging.getLogger(__name__)
voice_router = APIRouter(prefix="/api/v1/voice", tags=["Voice Webhooks"])


@voice_router.post("/twilio/incoming")
async def handle_twilio_incoming(request: Request):
    """
    Handle incoming calls from Twilio.
    This endpoint should be configured as the "A Call Comes In" webhook in Twilio.
    """
    from src.call_logs.models import CallLogCreate
    from src.call_logs.service import call_log_service

    form_data = await request.form()
    to_number = form_data.get("To")
    from_number = form_data.get("From")
    call_sid = form_data.get("CallSid")

    logger.info(
        f"Incoming call from {from_number} to {to_number} (CallSid: {call_sid})"
    )

    # 1. Find the agent associated with this phone number
    agent, error = await voice_agent_service.get_agent_by_phone(to_number)

    if error or not agent:
        logger.warning(f"No agent found for phone number {to_number}")
        # Cannot log call without an organization — skip logging
        response = VoiceResponse()
        response.say("I'm sorry, this number is not assigned to an active agent.")
        return Response(content=str(response), media_type="application/xml")

    # Log the incoming call
    if call_sid:
        try:
            await call_log_service.create_call_log(
                CallLogCreate(
                    call_sid=call_sid,
                    organization_id=agent.organization_id,
                    agent_id=agent.id,
                    caller_number=from_number,
                    called_number=to_number,
                    status="initiated",
                    started_at=datetime.now(timezone.utc),
                )
            )
        except Exception as log_err:
            logger.warning(f"Failed to create call log for {call_sid}: {log_err}")

    # 2. Use LiveKit SIP to bridge the call
    sip_domain = os.getenv("LIVEKIT_SIP_DOMAIN")
    if not sip_domain:
        logger.error("LIVEKIT_SIP_DOMAIN is not set")
        response = VoiceResponse()
        response.say("Internal configuration error. SIP domain missing.")
        return Response(content=str(response), media_type="application/xml")

    response = VoiceResponse()
    dial = response.dial()
    # Strip 'sip:' prefix if present in domain (Twilio's <Sip> adds it automatically)
    clean_sip_domain = sip_domain.replace("sip:", "")
    sip_uri = f"sip:{to_number}@{clean_sip_domain}"

    dial.sip(sip_uri, username="gaurav_dhiman", password="R0a5j#P1u9n")

    logger.info(f"Bridging Twilio call {call_sid} to LiveKit SIP via URI: {sip_uri}")
    return Response(content=str(response), media_type="application/xml")


@voice_router.post("/twilio/status")
async def handle_twilio_status_callback(request: Request):
    """
    Handle Twilio call status callbacks.
    Configure this as the "Call Status Changes" webhook URL in Twilio.
    Updates the call log with final duration and status.
    """
    from src.call_logs.models import CallLogUpdate
    from src.call_logs.service import call_log_service

    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    call_status = form_data.get("CallStatus", "")
    call_duration = form_data.get("CallDuration", "0")

    logger.info(f"Twilio status callback: CallSid={call_sid}, Status={call_status}, Duration={call_duration}")

    if call_sid:
        # Map Twilio statuses to our internal statuses
        status_map = {
            "completed": "completed",
            "busy": "busy",
            "failed": "failed",
            "no-answer": "no-answer",
            "canceled": "missed",
            "in-progress": "answered",
            "ringing": "ringing",
            "queued": "initiated",
        }
        internal_status = status_map.get(call_status, call_status)

        update_data = CallLogUpdate(
            status=internal_status,
            duration=int(call_duration) if call_duration else 0,
            ended_at=datetime.now(timezone.utc) if call_status in ("completed", "busy", "failed", "no-answer", "canceled") else None,
        )

        _, err = await call_log_service.update_call_log_by_sid(call_sid, update_data)
        if err:
            logger.warning(f"Failed to update call log for {call_sid}: {err}")

    # Twilio expects a 200 OK, content is ignored
    return Response(status_code=200)
