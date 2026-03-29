"""API routes for voice templates."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile
from src.voice_templates.models import VoiceTemplate
from src.voice_templates.service import voice_template_service

router = APIRouter(prefix="/api/v1/voice-templates", tags=["Voice Templates"])


@router.get("/", response_model=list[VoiceTemplate])
async def list_voice_templates(
    industry: Optional[str] = Query(None, description="Filter by industry"),
    _: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """List all active voice templates, optionally filtered by industry."""
    templates, error = await voice_template_service.list_templates(industry=industry)
    if error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error)
    return templates


@router.get("/{template_id}", response_model=VoiceTemplate)
async def get_voice_template(
    template_id: UUID,
    _: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Get a voice template by ID."""
    template, error = await voice_template_service.get_template_by_id(template_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error,
        )
    return template
