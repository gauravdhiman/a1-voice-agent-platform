"""Rate limiting configuration using slowapi."""

import logging

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from shared.config import settings

logger = logging.getLogger(__name__)


def _get_identifier(request: Request) -> str:
    """Get rate limit identifier: authenticated user ID or remote IP."""
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return str(user.id)
    return get_remote_address(request)


# Single shared limiter instance — keyed by user ID when available, else IP.
# Default: 100 requests/minute (applies globally unless overridden per-route).
def build_rate_limiter() -> Limiter:
    """Share quotas through configured Redis; isolated local runs use memory.

    Redis failures fail closed rather than falling back to per-process budgets.
    Deployments must provision REDIS_URL before running multiple backend instances.
    """
    return Limiter(
        key_func=_get_identifier,
        default_limits=["100/minute"],
        storage_uri=settings.redis_url or "memory://",
        key_prefix=f"247ai:{settings.environment}",
        in_memory_fallback_enabled=False,
        swallow_errors=False,
    )


limiter = build_rate_limiter()


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Return JSON 429 response when rate limit is exceeded."""
    logger.warning(
        "Rate limit exceeded: %s from %s", request.url.path, get_remote_address(request)
    )
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Too many requests. {exc.detail}",
        },
        headers={"Retry-After": "60"},
    )
