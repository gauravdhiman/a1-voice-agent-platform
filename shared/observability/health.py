"""Bounded asynchronous readiness with a short cache and single-flight probing."""

import asyncio
import time

import httpx
from starlette.responses import JSONResponse

from .signals import record


class Readiness:
    """Probe the Supabase REST dependency without user data or blocking worker I/O."""

    def __init__(self, settings, *, ttl=5.0, timeout=2.0):
        self.settings = settings
        self.ttl = ttl
        self.timeout = timeout
        self._lock = asyncio.Lock()
        self._expires = 0.0
        self._ready = False

    async def check(self) -> bool:
        """Return a cached dependency result; outages never expose provider details."""
        if time.monotonic() < self._expires:
            return self._ready
        async with self._lock:
            if time.monotonic() < self._expires:
                return self._ready
            ready = False
            if self.settings.supabase_url and self.settings.supabase_service_key:
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.get(
                            self.settings.supabase_url.rstrip("/")
                            + "/rest/v1/organizations",
                            params={"select": "id", "limit": "0"},
                            headers={
                                "apikey": self.settings.supabase_service_key,
                                "Authorization": (
                                    f"Bearer {self.settings.supabase_service_key}"
                                ),
                            },
                        )
                        ready = response.status_code == 200
                except (httpx.HTTPError, ValueError):
                    pass
            self._ready = ready
            self._expires = time.monotonic() + self.ttl
            record("platform.readiness.checks", outcome="success" if ready else "error")
            return ready

    async def response(self) -> JSONResponse:
        """HTTP 503 means unavailable; liveness remains independent."""
        ready = await self.check()
        return JSONResponse(
            {"status": "ready" if ready else "unavailable"},
            status_code=200 if ready else 503,
        )
