"""Send a private dead-man signal to an independent monitoring service."""

import asyncio
import http.client
from urllib.parse import urlsplit


class Heartbeat:
    """Send HTTPS success signals without logging the secret-bearing URL."""

    def __init__(self, url: str):
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
            or parsed.port not in (None, 443)
        ):
            raise ValueError("Maintenance heartbeat must be a valid HTTPS URL")
        self._host = parsed.hostname
        self._path = parsed.path or "/"
        if parsed.query:
            self._path += "?" + parsed.query

    def _send(self) -> None:
        connection = http.client.HTTPSConnection(self._host, timeout=5)
        try:
            connection.request("POST", self._path, body=b"")
            response = connection.getresponse()
            response.read(1024)
            if not 200 <= response.status < 300:
                raise RuntimeError("Maintenance heartbeat rejected")
        finally:
            connection.close()

    async def send(self) -> None:
        """Send a success signal; fail without exposing the URL on error."""
        try:
            await asyncio.to_thread(self._send)
        except Exception:
            raise RuntimeError("Maintenance heartbeat failed") from None
