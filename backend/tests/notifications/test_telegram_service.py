"""Tests for Telegram admin alert delivery."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.notifications.telegram_service import TelegramService


class TestTelegramService:
    """Telegram Bot API wrapper."""

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        service = TelegramService()
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"ok": True}

        with patch(
            "src.notifications.telegram_service.httpx.AsyncClient"
        ) as client_factory:
            client = AsyncMock()
            client.post.return_value = response
            client.__aenter__.return_value = client
            client.__aexit__.return_value = None
            client_factory.return_value = client

            sent = await service.send_message("bot-token", "chat-123", "Hello")

        assert sent is True
        client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_message_failure_on_non_200(self):
        service = TelegramService()
        response = MagicMock()
        response.status_code = 400
        response.text = "Bad Request"

        with patch(
            "src.notifications.telegram_service.httpx.AsyncClient"
        ) as client_factory:
            client = AsyncMock()
            client.post.return_value = response
            client.__aenter__.return_value = client
            client.__aexit__.return_value = None
            client_factory.return_value = client

            sent = await service.send_message("bot-token", "chat-123", "Hello")

        assert sent is False
