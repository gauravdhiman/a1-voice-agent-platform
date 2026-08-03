"""Unit tests for Twilio Media Streams serializer helpers."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from pipecat.serializers.twilio import TwilioFrameSerializer

from src.twilio_session import build_twilio_serializer


class TestBuildTwilioSerializer:
    """Tests for :func:`build_twilio_serializer`."""

    def test_requires_stream_id(self) -> None:
        with pytest.raises(ValueError, match="stream_id"):
            build_twilio_serializer({})

    def test_auto_hang_up_disabled_without_credentials(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            serializer = build_twilio_serializer(
                {"stream_id": "MZ123", "call_id": "CA123"},
                account_sid="",
                auth_token="",
            )
        assert isinstance(serializer, TwilioFrameSerializer)
        assert serializer._params.auto_hang_up is False

    def test_auto_hang_up_enabled_with_credentials(self) -> None:
        serializer = build_twilio_serializer(
            {"stream_id": "MZ123", "call_id": "CA123"},
            account_sid="AC123",
            auth_token="secret",
        )
        assert isinstance(serializer, TwilioFrameSerializer)
        assert serializer._params.auto_hang_up is True
        assert serializer._stream_sid == "MZ123"
        assert serializer._call_sid == "CA123"

    def test_accepts_attribute_style_call_data(self) -> None:
        class FakeCallData:
            stream_id = "MZ999"
            call_id = "CA999"

        serializer = build_twilio_serializer(
            FakeCallData(),
            account_sid="AC1",
            auth_token="tok",
        )
        assert serializer._stream_sid == "MZ999"
