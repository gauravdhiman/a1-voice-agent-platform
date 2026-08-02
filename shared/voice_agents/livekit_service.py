import logging
import os
import uuid
from datetime import timedelta
from typing import Optional

from livekit import api

from shared.config.settings import settings

logger = logging.getLogger(__name__)

AGENT_DISPATCH_NAME = "voice-agent"


class LiveKitService:
    def __init__(self) -> None:
        self.api_key: str | None = settings.livekit_api_key or os.getenv("LIVEKIT_API_KEY")
        self.api_secret: str | None = settings.livekit_api_secret or os.getenv("LIVEKIT_API_SECRET")
        self.url: str | None = settings.livekit_url or os.getenv("LIVEKIT_URL")

        if not all([self.api_key, self.api_secret, self.url]):
            logger.warning("LiveKit environment variables are not fully set")

    def get_api_client(self) -> api.LiveKitAPI:
        return api.LiveKitAPI(self.url, self.api_key, self.api_secret)

    async def create_room(self, room_name: str, empty_timeout: int = 300) -> api.Room:
        """Create a LiveKit room.

        Args:
            room_name: Unique room name to create.
            empty_timeout: Seconds before an empty room is closed.

        Returns:
            The created LiveKit ``Room`` proto.
        """
        lkapi = self.get_api_client()
        try:
            room = await lkapi.room.create_room(
                api.CreateRoomRequest(name=room_name, empty_timeout=empty_timeout)
            )
            return room
        finally:
            await lkapi.aclose()

    async def create_agent_dispatch(
        self, room_name: str, agent_name: str = AGENT_DISPATCH_NAME
    ) -> api.AgentDispatch:
        """Explicitly dispatch a worker agent into an existing LiveKit room.

        Relying on LiveKit Cloud automatic dispatch rules after ``create_room``
        is unreliable for browser test/embed rooms — the room can be created
        successfully while the worker never receives a job, leaving the caller
        in a silent room. Calling ``agent_dispatch.create_dispatch`` makes
        worker assignment deterministic.

        Args:
            room_name: Name of an existing LiveKit room.
            agent_name: Named agent to dispatch. Defaults to the platform's
                single named voice worker.

        Returns:
            The created ``AgentDispatch`` proto.

        Raises:
            Exception: Propagates LiveKit API errors to the caller.
        """
        lkapi = self.get_api_client()
        try:
            dispatch = await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name=agent_name,
                    room=room_name,
                )
            )
            logger.info(
                "Created agent dispatch for room %s (agent_name=%r, id=%s)",
                room_name,
                agent_name,
                getattr(dispatch, "id", None),
            )
            return dispatch
        finally:
            await lkapi.aclose()

    async def delete_room(self, room_name: str) -> None:
        """Delete a LiveKit room."""
        lkapi = self.get_api_client()
        try:
            await lkapi.room.delete_room(api.DeleteRoomRequest(room=room_name))
        finally:
            await lkapi.aclose()

    def generate_token(
        self,
        room_name: str,
        identity: str,
        name: Optional[str] = None,
        expiration: timedelta = timedelta(minutes=10),
    ) -> str:
        """Generate an access token for a participant."""
        token = (
            api.AccessToken(self.api_key, self.api_secret)
            .with_identity(identity)
            .with_name(name or identity)
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                )
            )
            .with_ttl(expiration)
        )
        return token.to_jwt()

    def generate_test_token(
        self,
        agent_id: str,
        user_id: str,
        expiration: timedelta = timedelta(minutes=10),
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Generate a LiveKit token for browser-based agent testing.

        Args:
            agent_id: The ID of the agent to test
            user_id: The ID of the user initiating the test
            expiration: Token expiration time (default 10 minutes)

        Returns:
            Tuple of (token, server_url, room_name) or (None, None, None) if failed
        """
        if not all([self.api_key, self.api_secret, self.url]):
            logger.error("LiveKit not configured - cannot generate test token")
            return None, None, None

        # Generate unique room name for this test session
        # Format: test_{agent_id}_{random}
        random_suffix = uuid.uuid4().hex[:8]
        room_name = f"test_{agent_id}_{random_suffix}"

        # Identity for the test participant
        identity = f"test_user_{user_id}"

        try:
            token = self.generate_token(
                room_name=room_name,
                identity=identity,
                name="Test User",
                expiration=expiration,
            )
            logger.info(f"Generated test token for agent {agent_id}, room {room_name}")
            return token, self.url, room_name
        except Exception as e:
            logger.error(f"Failed to generate test token: {e}", exc_info=True)
            return None, None, None


livekit_service = LiveKitService()
