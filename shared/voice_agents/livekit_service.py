import os
import logging
from typing import Optional
from livekit import api

logger = logging.getLogger(__name__)

class LiveKitService:
    def __init__(self):
        self.api_key: str | None = os.getenv("LIVEKIT_API_KEY")
        self.api_secret: str | None = os.getenv("LIVEKIT_API_SECRET")
        self.url: str | None = os.getenv("LIVEKIT_URL")
        
        if not all([self.api_key, self.api_secret, self.url]):
            logger.warning("LiveKit environment variables are not fully set")

    def get_api_client(self) -> api.LiveKitAPI:
        return api.LiveKitAPI(self.url, self.api_key, self.api_secret)

    async def create_room(self, room_name: str, empty_timeout: int = 300) -> api.Room:
        """Create a LiveKit room."""
        lkapi = self.get_api_client()
        try:
            room = await lkapi.room.create_room(
                api.CreateRoomRequest(
                    name=room_name,
                    empty_timeout=empty_timeout
                )
            )
            return room
        finally:
            await lkapi.aclose()

    async def delete_room(self, room_name: str):
        """Delete a LiveKit room."""
        lkapi = self.get_api_client()
        try:
            await lkapi.room.delete_room(
                api.DeleteRoomRequest(room=room_name)
            )
        finally:
            await lkapi.aclose()

    def generate_token(self, room_name: str, identity: str, name: Optional[str] = None) -> str:
        """Generate an access token for a participant."""
        token = api.AccessToken(self.api_key, self.api_secret) \
            .with_identity(identity) \
            .with_name(name or identity) \
            .with_grants(api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            ))
        return token.to_jwt()

livekit_service = LiveKitService()
