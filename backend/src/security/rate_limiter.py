"""Rate limiting configuration using slowapi."""

import logging
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


def _get_identifier(request: Request) -> str:
    """Get rate limit identifier: authenticated user ID or remote IP."""
    # Prefer authenticated user ID for API endpoints
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return str(user.id)
    return get_remote_address(request)


# Single shared limiter instance
# Default: 100 requests/minute per IP (applies globally unless overridden per-route)
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Return JSON 429 response when rate limit is exceeded."""
    logger.warning(f"Rate limit exceeded: {request.url.path} from {get_remote_address(request)}")
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Too many requests. {exc.detail}",
        },
        headers={"Retry-After": "60"},
    )
