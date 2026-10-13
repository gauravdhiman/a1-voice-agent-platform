"""Legal document versioning, acceptance tracking, and publish notification."""

from .service import legal_service
from .update_outbox import legal_update_outbox

__all__ = ["legal_service", "legal_update_outbox"]
