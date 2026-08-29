"""Provider-neutral notification primitives shared by application services."""

from .email_providers import (
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
