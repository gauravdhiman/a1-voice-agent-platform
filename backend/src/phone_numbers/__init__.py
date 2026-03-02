"""
Phone numbers module for managing phone number purchases and assignments.
"""

from .routes import router as phone_number_router
from .service import phone_number_service

__all__ = ["phone_number_router", "phone_number_service"]
