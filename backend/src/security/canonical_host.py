"""Reject direct Cloud Run ``*.run.app`` hostnames in production.

Custom domains (``api.247ai.live``) are the only public entrypoint. The
auto-generated ``*.run.app`` URL remains for Google's internal probes, but
browser/API clients that hit it get 403 so traffic stays on the branded domain.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from shared.config import settings

# Probe paths Cloud Run (and our HEALTHCHECK) may hit with a ``*.run.app`` Host.
_PROBE_PATHS = frozenset({"/health", "/health/ready", "/health/live"})


class CanonicalHostMiddleware(BaseHTTPMiddleware):
    """Block non-probe requests whose Host is a Cloud Run default URL."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if settings.environment == "production":
            host = (request.headers.get("host") or "").split(":")[0].lower()
            # Normalise trailing slash (``/health/`` → ``/health``)
            path = request.url.path.rstrip("/") or "/"
            if host.endswith(".run.app") and path not in _PROBE_PATHS:
                return JSONResponse(
                    {
                        "detail": (
                            "This API is only available at https://api.247ai.live. "
                            "Direct Cloud Run URLs are disabled."
                        )
                    },
                    status_code=403,
                )
        return await call_next(request)
