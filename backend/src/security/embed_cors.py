"""CORS handling for public embedded voice-agent endpoints."""

from starlette.datastructures import Headers, MutableHeaders
from starlette.middleware.cors import CORSMiddleware
from starlette.types import Message, Receive, Scope, Send


class EmbedAwareCORSMiddleware(CORSMiddleware):
    """Apply tenant-aware CORS handling to public embed endpoints.

    The regular application CORS allowlist cannot contain every customer's
    website. Embed routes validate the request origin against the agent's
    configured domain allowlist, so they need to reach the route before the
    global CORS middleware rejects the origin.
    """

    _EMBED_PATH_PREFIX = "/api/v1/embed/agent/"
    _EMBED_PATH_SUFFIXES = ("/info", "/token")

    @classmethod
    def _is_public_embed_path(cls, path: str) -> bool:
        """Return whether a request targets a public agent embed endpoint."""
        return path.startswith(cls._EMBED_PATH_PREFIX) and path.endswith(
            cls._EMBED_PATH_SUFFIXES
        )

    @staticmethod
    def _ensure_origin_in_vary(headers: MutableHeaders) -> None:
        """Keep caches from sharing a response across requesting origins."""
        vary = headers.get("Vary")
        if not vary:
            headers["Vary"] = "Origin"
            return

        values = [value.strip().lower() for value in vary.split(",")]
        if "origin" not in values:
            headers["Vary"] = f"{vary}, Origin"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Route public embed CORS through endpoint-level domain validation."""
        if scope["type"] != "http" or not self._is_public_embed_path(
            scope.get("path", "")
        ):
            await super().__call__(scope, receive, send)
            return

        origin = Headers(scope=scope).get("origin")
        if not origin:
            await self.app(scope, receive, send)
            return

        async def send_with_embed_cors(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["Access-Control-Allow-Origin"] = origin
                headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
                headers["Access-Control-Allow-Headers"] = "content-type"
                headers["Access-Control-Max-Age"] = "600"
                self._ensure_origin_in_vary(headers)
            await send(message)

        await self.app(scope, receive, send_with_embed_cors)
