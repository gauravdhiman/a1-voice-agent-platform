import logging
from fastapi import APIRouter, Request, Response
from twilio.twiml.voice_response import VoiceResponse
from shared.voice_agents.service import voice_agent_service
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

    dial.sip(sip_uri, username='gaurav_dhiman', password='R0a5j#P1u9n')

    logger.info(f"Bridging Twilio call {call_sid} to LiveKit SIP via URI: {sip_uri}")
    return Response(content=str(response), media_type="application/xml")
