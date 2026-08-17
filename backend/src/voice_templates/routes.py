"""API routes for voice templates."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.auth.dependencies import assert_platform_role
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile
from src.voice_templates.models import (
    VoiceTemplate,
    VoiceTemplateCreate,
    VoiceTemplateUpdate,
)
from src.voice_templates.service import voice_template_service

router = APIRouter(prefix="/api/v1/voice-templates", tags=["Voice Templates"])
platform_router = APIRouter(
    prefix="/api/v1/platform/voice-templates",
    tags=["Platform Voice Templates"],
)


def _require_platform_admin(user_profile: UserProfile) -> None:
    """Raise 403 when the caller is not a platform administrator."""
    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="Platform admin access required",
    )


@router.get("/", response_model=list[VoiceTemplate])
async def list_voice_templates(
    industry: Optional[str] = Query(None, description="Filter by industry"),
    _: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """List all active voice templates, optionally filtered by industry."""
    templates, error = await voice_template_service.list_templates(industry=industry)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
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
            status_code=(
                status.HTTP_404_NOT_FOUND
                if "not found" in error.lower()
                else status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=error,
        )
    return template


@platform_router.get("/", response_model=list[VoiceTemplate])
async def list_admin_voice_templates(
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> list[VoiceTemplate]:
    """List active and inactive templates for platform-admin management."""
    _, user_profile = user_data
    _require_platform_admin(user_profile)
    templates, error = await voice_template_service.list_templates(
        industry=None,
        include_inactive=True,
    )
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return templates


@platform_router.get("/{template_id}", response_model=VoiceTemplate)
async def get_admin_voice_template(
    template_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> VoiceTemplate:
    """Get an active or inactive template for platform-admin editing."""
    _, user_profile = user_data
    _require_platform_admin(user_profile)
    template, error = await voice_template_service.get_template_by_id(
        template_id,
        include_inactive=True,
    )
    if error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    return template


@platform_router.post(
    "/", response_model=VoiceTemplate, status_code=status.HTTP_201_CREATED
)
async def create_admin_voice_template(
    template_data: VoiceTemplateCreate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> VoiceTemplate:
    """Create a reusable voice template (platform admin only)."""
    _, user_profile = user_data
    _require_platform_admin(user_profile)
    template, error = await voice_template_service.create_template(template_data)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return template


@platform_router.put("/{template_id}", response_model=VoiceTemplate)
async def update_admin_voice_template(
    template_id: UUID,
    template_data: VoiceTemplateUpdate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> VoiceTemplate:
    """Update a reusable voice template (platform admin only)."""
    _, user_profile = user_data
    _require_platform_admin(user_profile)
    template, error = await voice_template_service.update_template(
        template_id,
        template_data,
    )
    if error:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in error.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=error)
    return template


@platform_router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_voice_template(
    template_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> None:
    """Permanently delete a reusable voice template (platform admin only)."""
    _, user_profile = user_data
    _require_platform_admin(user_profile)
    _, error = await voice_template_service.delete_template(template_id)
    if error:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in error.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=error)
