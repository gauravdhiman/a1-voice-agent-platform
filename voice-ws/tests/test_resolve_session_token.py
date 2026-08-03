"""Tests for resolving voice session tokens from Twilio connections."""

from __future__ import annotations

from src.twilio_session import resolve_session_token


class TestResolveSessionToken:
    """Unit tests for :func:`resolve_session_token`."""

    def test_prefers_query_token(self) -> None:
        assert (
            resolve_session_token(
                query_token="from-query",
                call_data={"body": {"token": "from-param"}},
            )
            == "from-query"
        )

    def test_falls_back_to_stream_parameter(self) -> None:
        assert (
            resolve_session_token(
                query_token=None,
                call_data={"body": {"token": "from-param"}},
            )
            == "from-param"
        )

    def test_reads_attribute_style_call_data_body(self) -> None:
        class FakeCallData:
            body = {"token": "attr-param"}

        assert (
            resolve_session_token(query_token="", call_data=FakeCallData())
            == "attr-param"
        )

    def test_missing_token_returns_none(self) -> None:
        assert resolve_session_token(query_token=None, call_data={}) is None
