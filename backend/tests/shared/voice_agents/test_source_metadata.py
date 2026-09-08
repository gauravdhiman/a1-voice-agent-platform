import pytest

from shared.voice_agents.source_metadata import (
    normalize_domain,
    normalize_source_url,
    source_type_for_purpose,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://WWW.Example.com:443/path", "example.com"),
        ("support.example.com", "support.example.com"),
        ("https://user:password@example.com", None),
        ("null", None),
        ("not a domain", None),
        ("", None),
    ],
)
def test_normalize_domain(value: str, expected: str | None) -> None:
    assert normalize_domain(value) == expected


def test_normalize_source_url_removes_query_and_fragment() -> None:
    assert (
        normalize_source_url("https://WWW.Example.com/support?customer=private#details")
        == "https://example.com/support"
    )


def test_normalize_source_url_falls_back_when_host_does_not_match() -> None:
    assert (
        normalize_source_url(
            "https://attacker.example/landing",
            fallback="https://example.com",
        )
        == "https://example.com/"
    )


def test_normalize_source_url_rejects_non_http_schemes() -> None:
    assert normalize_source_url("javascript:alert(1)") is None


def test_normalize_source_url_does_not_truncate_long_paths() -> None:
    long_url = f"https://example.com/{'a' * 2048}"

    assert normalize_source_url(long_url, fallback="https://example.com") == (
        "https://example.com/"
    )


@pytest.mark.parametrize(
    ("purpose", "expected"),
    [
        ("phone", "phone"),
        ("test_call", "web_test"),
        ("embed", "web_embed"),
        ("public", "web_public"),
        ("unknown", None),
    ],
)
def test_source_type_for_purpose(purpose: str, expected: str | None) -> None:
    assert source_type_for_purpose(purpose) == expected
