"""Tests for validation error sanitization."""

from src.security.validation_errors import sanitize_validation_errors


class TestSanitizeValidationErrors:
    """Ensure sensitive request values are stripped from API error payloads."""

    def test_removes_input_field_from_validation_errors(self) -> None:
        errors = [
            {
                "type": "value_error",
                "loc": ["body"],
                "msg": "Value error, Passwords do not match",
                "input": {
                    "email": "user@example.com",
                    "password": "Secret123!",
                    "password_confirm": "",
                },
            }
        ]

        sanitized = sanitize_validation_errors(errors)

        assert len(sanitized) == 1
        assert "input" not in sanitized[0]
        assert sanitized[0]["msg"] == "Value error, Passwords do not match"
