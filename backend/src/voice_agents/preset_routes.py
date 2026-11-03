"""Platform-admin API routes for managing voice-engine presets (Phase 3).

A **preset** is a named, platform-admin-managed voice-engine configuration (see
:mod:`shared.voice_agents.preset_models`). Presets are a global catalog with no
RLS, mirroring the platform-tools / platform-skills catalogs. RBAC:

- Preset **CRUD** (create/upsert, update, publish/unpublish, usage, delete) is
  ``platform_admin`` only.
- **Listing / fetch** of published presets is available to any authenticated
  user (org admins pick a preset when configuring an agent). Drafts are
  platform-admin only: ``include_drafts=True`` and viewing a draft preset both
  require ``platform_admin``.
- **Assigning** a preset to an agent is gated by the existing ``agent:update``
  permission in the agent routes (validated there via ``preset_service``).

No versioning: the worker fetches the preset row live on every call, so an
admin's edit takes effect on the next call. Presets carry no secrets.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from opentelemetry import trace
from src.auth.dependencies import assert_platform_role
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile
from src.organization.service import organization_service

from shared.voice_agents.key_resolver import required_provider_keys
from shared.voice_agents.platform_credentials import (
    PlatformVoiceCredentialError,
    platform_voice_provider_credential_service,
)
from shared.voice_agents.preset_models import (
    Preset,
    PresetCatalogResponse,
    PresetCreate,
    PresetCredentialSource,
    PresetType,
    PresetUpdate,
)
from shared.voice_agents.preset_service import preset_service

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

preset_router = APIRouter(prefix="/api/v1/presets", tags=["Voice Presets"])


def _require_platform_admin(user_profile: UserProfile) -> None:
    """Raise 403 if the user is not a platform admin."""
    assert_platform_role(
        user_profile,
        "platform_admin",
        error_message="Platform admin access required",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Preset CRUD (platform admin only)
# ─────────────────────────────────────────────────────────────────────────────


@preset_router.post("/", response_model=Preset, status_code=status.HTTP_201_CREATED)
@tracer.start_as_current_span("preset.routes.create")
async def create_preset(
    preset_data: PresetCreate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> Preset:
    """Create or replace a preset by name (platform admin only).

    Upsert by ``name``: if a preset with the same name exists it is fully
    replaced. The new preset starts as a draft (``is_published=False``) unless
    the body sets otherwise; publish it via ``POST /{id}/publish``.
    """
    current_user_id, user_profile = user_data
    _require_platform_admin(user_profile)

    preset, error = await preset_service.upsert_preset(preset_data)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return preset


# ─────────────────────────────────────────────────────────────────────────────
# Current platform default preset (platform admin only)
#
# The selected published platform-managed row is the fallback config when an
# agent has no preset selected (``preset_id`` NULL). It is editable by id and
# cannot be unpublished or deleted. These compatibility routes are declared
# before any ``/{preset_id}`` route so the literal ``default`` segment does not
# match the UUID path param.
#
# The PUT body is the raw ``SpeechConfig`` dict itself (realtime or pipeline
# discriminated union); the service re-validates it via ``parse_speech_config``
# and re-derives ``preset_type``. Only ``config`` and the derived
# ``preset_type`` are written; use the id-based endpoint to edit metadata.
# ─────────────────────────────────────────────────────────────────────────────


@preset_router.get("/default", response_model=Preset)
@tracer.start_as_current_span("preset.routes.get_default")
async def get_default_preset(
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> Preset:
    """Fetch the current platform default preset (platform admin only).

    The default is the fallback config an agent uses when it has no preset
    selected. It is published and appears in the org-admin picker as the
    dynamic null-selection option. Returns 404 if no default row is designated
    (the worker then falls back to the hardcoded realtime default).
    """
    current_user_id, user_profile = user_data
    _require_platform_admin(user_profile)

    preset, error = await preset_service.get_default_preset()
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    if preset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Default preset not found"
        )
    return preset


@preset_router.put("/default", response_model=Preset)
@tracer.start_as_current_span("preset.routes.update_default")
async def update_default_preset(
    config: dict,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> Preset:
    """Replace the current platform default's ``config`` (platform admin only).

    Only ``config`` and the derived ``preset_type`` are written; the metadata
    stays fixed by this legacy endpoint. The default remains published and
    platform-managed. Returns 400 on an invalid config, 404 if no default row
    exists.
    """
    current_user_id, user_profile = user_data
    _require_platform_admin(user_profile)

    preset, error = await preset_service.update_default_preset(config)
    if error:
        if error == "Default not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return preset


@preset_router.get("/catalog", response_model=PresetCatalogResponse)
@tracer.start_as_current_span("preset.routes.catalog")
async def get_preset_catalog(
    organization_id: UUID = Query(
        ...,
        description=(
            "Organization whose credential readiness should be evaluated. "
            "Required so the catalog can report is_ready per voice profile."
        ),
    ),
    use_platform_credits: bool = Query(
        False,
        description=(
            "When true, readiness ignores org credentials and checks stored "
            "platform keys before platform environment fallbacks."
        ),
    ),
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> PresetCatalogResponse:
    """List published voice profiles for org admins (white-label catalog).

    Returns display metadata and org-scoped readiness flags only — no
    ``config``, ``preset_type``, or provider names. Includes
    ``default_is_ready`` and the selected platform default's display metadata
    for the ``preset_id=null`` option. Readiness reflects whether the platform
    has the provider keys required by that profile; organization credentials do
    not affect a platform-managed default.
    """
    current_user_id, user_profile = user_data

    org, org_error = await organization_service.get_organization_by_id(organization_id)
    if org_error:
        if org_error == "Organization not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=org_error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=org_error
        )

    presets, presets_error = await preset_service.get_presets(only_published=True)
    if presets_error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=presets_error
        )

    default_preset, default_error = await preset_service.get_default_preset()
    if default_error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=default_error
        )

    # Transitional: org admins with organization update permission can self-
    # configure credentials. TODO: drive from org.credentials_self_service when
    # managed white-label mode lands (platform admin only provisioning).
    credentials_self_service = user_profile.has_permission(
        "organization:update", str(organization_id)
    ) or user_profile.has_role("platform_admin")

    platform_provider_names: set[str] = set()
    for preset in presets or []:
        if (
            use_platform_credits
            or preset.credential_source == PresetCredentialSource.PLATFORM
        ):
            platform_provider_names.update(required_provider_keys(preset.config))
    if default_preset and (
        use_platform_credits
        or default_preset.credential_source == PresetCredentialSource.PLATFORM
    ):
        platform_provider_names.update(required_provider_keys(default_preset.config))

    platform_credentials = {}
    if platform_provider_names:
        try:
            platform_credentials = await (
                platform_voice_provider_credential_service.get_provider_credentials(
                    platform_provider_names
                )
            )
        except PlatformVoiceCredentialError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Voice preset readiness is temporarily unavailable",
            ) from None

    return preset_service.build_preset_catalog(
        presets or [],
        default_preset,
        org,
        use_platform_credits=use_platform_credits,
        credentials_self_service=credentials_self_service,
        platform_credentials=platform_credentials,
    )


@preset_router.put("/{preset_id}", response_model=Preset)
@tracer.start_as_current_span("preset.routes.update")
async def update_preset(
    preset_id: UUID,
    preset_data: PresetUpdate,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> Preset:
    """Partially update a preset (platform admin only)."""
    current_user_id, user_profile = user_data
    _require_platform_admin(user_profile)

    preset, error = await preset_service.update_preset(preset_id, preset_data)
    if error:
        if error == "Preset not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return preset


@preset_router.post("/{preset_id}/publish", response_model=Preset)
@tracer.start_as_current_span("preset.routes.publish")
async def publish_preset(
    preset_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> Preset:
    """Publish a draft preset to the global catalog (platform admin only)."""
    current_user_id, user_profile = user_data
    _require_platform_admin(user_profile)

    preset, error = await preset_service.publish_preset(preset_id, True)
    if error:
        if error == "Preset not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return preset


@preset_router.post("/{preset_id}/default", response_model=Preset)
@tracer.start_as_current_span("preset.routes.set_default")
async def set_default_preset(
    preset_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> Preset:
    """Select a published platform-credential preset as the platform default."""
    _, user_profile = user_data
    _require_platform_admin(user_profile)

    preset, error = await preset_service.set_default_preset(preset_id)
    if error:
        if error == "Preset not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return preset


@preset_router.post("/{preset_id}/unpublish", response_model=Preset)
@tracer.start_as_current_span("preset.routes.unpublish")
async def unpublish_preset(
    preset_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> Preset:
    """Revert a published preset to draft (platform admin only).

    Unpublishing hides the preset from new assignments; agents already using it
    keep working (the worker reads the preset by id, not via the listing).
    """
    current_user_id, user_profile = user_data
    _require_platform_admin(user_profile)

    preset, error = await preset_service.publish_preset(preset_id, False)
    if error:
        if error == "Preset not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return preset


@preset_router.get("/{preset_id}/usage")
@tracer.start_as_current_span("preset.routes.usage")
async def get_preset_usage(
    preset_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> dict:
    """List the agents currently referencing a preset (platform admin only).

    Used by the delete flow's 409 ``in_use`` body and the unpublish banner.
    """
    current_user_id, user_profile = user_data
    _require_platform_admin(user_profile)

    usage, error = await preset_service.get_preset_usage(preset_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return {"count": len(usage), "agents": usage}


@preset_router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
@tracer.start_as_current_span("preset.routes.delete")
async def delete_preset(
    preset_id: UUID,
    force: bool = Query(
        False,
        description=(
            "Allow deleting a preset that is in use. Without force, a preset "
            "referenced by any agent returns 409 with the affected agent list "
            "(the FK ON DELETE SET NULL would drop them to the realtime "
            "default); force acknowledges that and proceeds."
        ),
    ),
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> None:
    """Permanently delete a preset (platform admin only)."""
    current_user_id, user_profile = user_data
    _require_platform_admin(user_profile)

    success, error = await preset_service.delete_preset(preset_id, force=force)
    if error:
        if error == "Preset not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
        if error == "in_use":
            usage, _ = await preset_service.get_preset_usage(preset_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "in_use",
                    "message": (
                        "Preset is assigned to agents. Reassign them or "
                        "retry with ?force=true to detach them (they fall "
                        "back to the realtime default)."
                    ),
                    "agents": usage,
                },
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)


# ─────────────────────────────────────────────────────────────────────────────
# Preset listing / fetch (published = any authed; drafts = platform admin)
# ─────────────────────────────────────────────────────────────────────────────


@preset_router.get("/", response_model=List[Preset])
@tracer.start_as_current_span("preset.routes.list")
async def list_presets(
    preset_type: Optional[PresetType] = Query(
        None, description="Filter by preset type (realtime|pipeline)."
    ),
    include_drafts: bool = Query(
        False,
        description=(
            "Include draft (unpublished) presets. Platform admin only — a "
            "non-admin passing true gets 403."
        ),
    ),
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> List[Preset]:
    """List presets.

    By default returns only published presets (the org-admin assignment list).
    ``include_drafts=True`` returns drafts too and requires ``platform_admin``.
    """
    current_user_id, user_profile = user_data
    if include_drafts:
        _require_platform_admin(user_profile)

    presets, error = await preset_service.get_presets(
        only_published=not include_drafts,
        preset_type=preset_type,
        include_drafts=include_drafts,
    )
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    return presets


@preset_router.get("/{preset_id}", response_model=Preset)
@tracer.start_as_current_span("preset.routes.get")
async def get_preset(
    preset_id: UUID,
    user_data: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
) -> Preset:
    """Fetch a single preset by id.

    Published presets are visible to any authenticated user. Draft presets are
    platform-admin only — a non-admin fetching a draft gets 403.
    """
    current_user_id, user_profile = user_data

    preset, error = await preset_service.get_preset_by_id(preset_id)
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error
        )
    if preset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found"
        )
    if not preset.is_published:
        _require_platform_admin(user_profile)
    return preset
