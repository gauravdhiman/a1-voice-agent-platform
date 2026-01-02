import logging
import json
from fastapi import APIRouter, Request, Response
from twilio.twiml.voice_response import VoiceResponse
from livekit import api
from shared.voice_agents.service import voice_agent_service
from src.voice_agents.livekit_service import livekit_service
from shared.voice_agents.session_service import session_manager
import os

logger = logging.getLogger(__name__)
voice_router = APIRouter(prefix="/api/v1/voice", tags=["Voice Webhooks"])

@voice_router.post("/twilio/incoming")
async def handle_twilio_incoming(request: Request):
    """
    Handle incoming calls from Twilio.
    This endpoint should be configured as the "A Call Comes In" webhook in Twilio.
    """
    form_data = await request.form()
    to_number = form_data.get("To")
    from_number = form_data.get("From")
    call_sid = form_data.get("CallSid")

    logger.info(f"Incoming call from {from_number} to {to_number} (CallSid: {call_sid})")

    # 1. Find the agent associated with this phone number
    # We'll need a way to look up agents by phone number
    # For now, let's add a method to voice_agent_service
    agent, error = await voice_agent_service.get_agent_by_phone(to_number)
    
    if error or not agent:
        logger.warning(f"No agent found for phone number {to_number}")
        response = VoiceResponse()
        response.say("I'm sorry, this number is not assigned to an active agent.")
        return Response(content=str(response), media_type="application/xml")

    # 2. Create a LiveKit room for this call
    room_name = f"call-{call_sid}"
    
    # Start a session snapshot for tool consistency
    session = await session_manager.start_session(agent.id)
    
    metadata = json.dumps({
        "agent_id": str(agent.id),
        "session_id": session.session_id,
        "call_sid": call_sid,
        "from": from_number,
        "to": to_number
    })
    
    try:
        lkapi = livekit_service.get_api_client()
        await lkapi.room.create_room(
            api.CreateRoomRequest(
                name=room_name,
                empty_timeout=300,
                metadata=metadata
            )
        )
        await lkapi.aclose()
    except Exception as e:
        logger.error(f"Failed to create LiveKit room: {e}")
        response = VoiceResponse()
        response.say("I'm sorry, there was a technical error connecting your call.")
        return Response(content=str(response), media_type="application/xml")

    # 3. Use LiveKit SIP to bridge the call
    # We need to tell Twilio to dial the LiveKit SIP URI
    # The SIP URI depends on the LiveKit Cloud configuration or self-hosted setup
    # Usually: sip:<room_name>@<sip_domain>
    
    sip_domain = os.getenv("LIVEKIT_SIP_DOMAIN")
    if not sip_domain:
        logger.error("LIVEKIT_SIP_DOMAIN is not set")
        response = VoiceResponse()
        response.say("Internal configuration error. SIP domain missing.")
        return Response(content=str(response), media_type="application/xml")

    response = VoiceResponse()
    dial = response.dial()
    # Pass metadata via SIP headers if needed
    dial.sip(f"sip:{room_name}@{sip_domain}")
    
    logger.info(f"Bridging Twilio call {call_sid} to LiveKit room {room_name} via SIP")
    return Response(content=str(response), media_type="application/xml")
