"""Backward-compatible imports for the shared email provider contract."""

import resend as resend  # noqa: F401 - preserve the legacy patch/import path

from shared.notifications.email_providers import (
    EmailMessage,
    EmailProvider,
    EmailSendResult,
    ResendEmailProvider,
    build_email_provider,
    build_resend_email_provider,
)

__all__ = [
    "EmailMessage",
    "EmailProvider",
    "EmailSendResult",
    "ResendEmailProvider",
    "build_email_provider",
    "build_resend_email_provider",
]
