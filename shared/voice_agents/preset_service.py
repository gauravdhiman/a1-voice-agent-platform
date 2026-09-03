"""Platform-admin-managed voice-engine preset service (Phase 3).

A **preset** is a named, platform-admin-managed voice-engine configuration stored
in the ``pipeline_presets`` table (a global catalog with no RLS, mirroring the
``platform_tools`` MCP-server catalog). An agent references a preset by
``preset_id``; the worker loads that preset **live on every call** (no versioning
— admin edits take effect on the next call). See
:mod:`shared.voice_agents.preset_models` for the model contract.

This service mirrors :class:`shared.voice_agents.tool_service.ToolService`:

- the ``(result, error)`` tuple contract;
- Supabase/PostgREST via ``self.supabase.table(...)``;
- upsert-by-name for authoring;
- the ``is_published`` draft↔published lifecycle;
- a usage join + ``in_use`` guardrail on delete;
- a ``preset_service`` module-level singleton.

Two preset types only — ``realtime`` / ``pipeline`` — matching the
``SpeechConfig`` discriminated union. ``preset_type`` is a denormalized filter
column **derived from ``config.engine_mode`` on every write** (never set by
hand): the service re-validates ``config`` via :func:`parse_speech_config` and
sets ``preset_type`` from the parsed config's ``engine_mode``.

Presets carry **no secrets** — the per-provider API keys live on the
organization (``organizations.provider_credentials``, encrypted), not in the
preset. The worker's :mod:`shared.voice_agents.key_resolver` pairs a preset's
``config`` with the org's credentials.
"""

import logging
from typing import List, Optional
from uuid import UUID

from opentelemetry import trace
from pydantic import ValidationError

from shared.config import supabase_config
from shared.voice_agents.model_capabilities import model_capability_service
from shared.voice_agents.preset_models import (
    RESERVED_DEFAULT_NAME,
    Preset,
    PresetCatalogItem,
    PresetCatalogResponse,
    PresetCreate,
    PresetType,
    PresetUpdate,
)
from shared.voice_agents.speech_config import parse_speech_config
from supabase import Client

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class PresetService:
    """Service for platform-admin CRUD on voice-engine presets."""

    def __init__(self) -> None:
        self.supabase_config = supabase_config

    @property
    def supabase(self) -> Optional[Client]:
        """Get the Supabase client."""
        return self.supabase_config.client

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _derive_preset_type(
        config_dict: dict,
    ) -> tuple[Optional[PresetType], Optional[str]]:
        """Validate a raw config dict and derive its preset_type.

        Args:
            config_dict: The raw ``config`` dict (e.g. from a model_dump or a
                caller-supplied body).

        Returns:
            ``(PresetType, None)`` on success, or ``(None, error)`` if the dict
            fails ``SpeechConfig`` validation.
        """
        try:
            cfg = parse_speech_config(config_dict)
        except ValidationError as e:
            return None, f"Invalid speech config: {e}"
        return PresetType(cfg.engine_mode.value), None

    @staticmethod
    async def _validate_model_capabilities(config_dict: dict) -> Optional[str]:
        """Reject a live config whose provider capabilities are incompatible.

        Capability validation is fail-closed for providers that have a
        resolver. The resolver returns safe, admin-facing messages; unexpected
        resolver failures are also converted to a generic error so a broken
        catalog cannot publish a preset that has not been verified.
        """
        try:
            config = parse_speech_config(config_dict)
            check = await model_capability_service.validate_speech_config(config)
        except Exception:  # noqa: BLE001 - publishing must fail closed
            logger.exception("Voice preset model capability validation failed")
            return (
                "The selected model could not be validated right now. "
                "Try again before publishing the preset."
            )
        if not check.valid:
            return check.message or "The selected model failed capability validation."
        return None

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @tracer.start_as_current_span("preset.upsert_preset")
    async def upsert_preset(
        self, data: PresetCreate
    ) -> tuple[Optional[Preset], Optional[str]]:
        """Create or replace a preset by name (platform-admin authoring).

        Validates ``config`` and derives ``preset_type`` from its
        ``engine_mode`` before persisting. If a row with the same ``name``
        exists, it is fully replaced (update by id); otherwise a new row is
        inserted. The ``is_published`` lifecycle is owned by
        :meth:`publish_preset`; an upsert carries whatever ``is_published`` the
        body supplies (default ``False`` = draft).

        Args:
            data: The preset to create/replace.

        Returns:
            ``(Preset, None)`` on success, or ``(None, error)`` on validation
            failure or a Supabase error.
        """
        # ``data.config`` is normally a validated SpeechConfig model; a caller
        # that bypassed Pydantic may hand us a raw dict. Normalize to a dict.
        config_dict = (
            data.config.model_dump(mode="json")
            if not isinstance(data.config, dict)
            else data.config
        )
        preset_type, err = self._derive_preset_type(config_dict)
        if err:
            return None, err

        # Guard: the reserved name belongs to the single system-default row,
        # managed via its own config editor — reject authoring a preset that
        # would clobber it by name.
        if data.name == RESERVED_DEFAULT_NAME:
            return None, f"'{RESERVED_DEFAULT_NAME}' is a reserved preset name"

        try:
            existing = (
                self.supabase.table("pipeline_presets")
                .select("*")
                .eq("name", data.name)
                .execute()
            )
            existing_row = existing.data[0] if existing.data else {}
            if data.is_published or bool(existing_row.get("is_published")):
                capability_error = await self._validate_model_capabilities(config_dict)
                if capability_error:
                    return None, capability_error

            data_dict = data.model_dump(exclude_none=True, mode="json")
            data_dict["config"] = config_dict
            data_dict["preset_type"] = preset_type.value

            if existing.data:
                response = (
                    self.supabase.table("pipeline_presets")
                    .update(data_dict)
                    .eq("id", existing.data[0]["id"])
                    .execute()
                )
            else:
                response = (
                    self.supabase.table("pipeline_presets").insert(data_dict).execute()
                )

            if not response.data:
                return None, "Failed to upsert preset"
            return Preset(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error upserting preset: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("preset.update_preset")
    async def update_preset(
        self, preset_id: UUID, data: PresetUpdate
    ) -> tuple[Optional[Preset], Optional[str]]:
        """Partially update a preset by id.

        Only the supplied fields are written (``exclude_unset=True``). When
        ``config`` is supplied it is re-validated and ``preset_type`` is
        re-derived from its ``engine_mode``; without a new ``config``,
        ``preset_type`` is left untouched.

        Args:
            preset_id: The preset row id.
            data: The partial update.

        Returns:
            ``(Preset, None)`` on success, or ``(None, error)`` (``"Preset not
            found"`` if the row is missing, a validation error string for a bad
            config, or a Supabase error message).
        """
        data_dict = data.model_dump(exclude_unset=True, mode="json")
        if "config" in data_dict:
            preset_type, err = self._derive_preset_type(data_dict["config"])
            if err:
                return None, err
            data_dict["preset_type"] = preset_type.value

        try:
            # Guard: the system-default row is edited only via
            # :meth:`update_default_preset` (its config editor); the generic
            # update path refuses it so name/is_published/is_default stay fixed.
            existing = (
                self.supabase.table("pipeline_presets")
                .select("id,is_default,is_published,config")
                .eq("id", str(preset_id))
                .limit(1)
                .execute()
            )
            if not existing.data:
                return None, "Preset not found"
            if existing.data[0].get("is_default"):
                return None, (
                    "The system default preset is managed via its own config editor"
                )

            existing_row = existing.data[0]
            target_config = data_dict.get("config", existing_row.get("config"))
            target_is_published = data_dict.get(
                "is_published", existing_row.get("is_published", False)
            )
            config_changed_on_published = "config" in data_dict and bool(
                existing_row.get("is_published")
            )
            if target_is_published or config_changed_on_published:
                if not isinstance(target_config, dict):
                    return None, "Preset has no valid speech configuration"
                capability_error = await self._validate_model_capabilities(
                    target_config
                )
                if capability_error:
                    return None, capability_error

            response = (
                self.supabase.table("pipeline_presets")
                .update(data_dict)
                .eq("id", str(preset_id))
                .execute()
            )
            if not response.data:
                return None, "Preset not found"
            return Preset(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error updating preset {preset_id}: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("preset.get_default_preset")
    async def get_default_preset(self) -> tuple[Optional[Preset], Optional[str]]:
        """Fetch the single system-default preset row (``is_default=True``).

        The default is the fallback config an agent uses when it has no preset
        selected (``preset_id`` NULL — a legacy agent, or one whose preset was
        deleted via the FK ``ON DELETE SET NULL``). It is seeded by the
        migration with today's realtime config and is editable via
        :meth:`update_default_preset`. It is NOT published and never appears in
        the org-admin picker.

        Returns:
            ``(Preset, None)`` if the default row exists, ``(None, None)`` if
            none is designated (the worker then falls back to the hardcoded
            ``default_realtime_config()``), or ``(None, error)`` on a Supabase
            error. A missing default is NOT an error.
        """
        try:
            response = (
                self.supabase.table("pipeline_presets")
                .select("*")
                .eq("is_default", True)
                .limit(1)
                .execute()
            )
            if not response.data:
                return None, None
            return Preset(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error getting default preset: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("preset.update_default_preset")
    async def update_default_preset(
        self, config: dict
    ) -> tuple[Optional[Preset], Optional[str]]:
        """Replace the system-default preset's ``config`` (platform admin only).

        Only ``config`` and the derived ``preset_type`` are written; the row's
        ``name``/``is_published``/``is_default`` stay fixed (it is always the
        admin-only, non-published fallback). The config is re-validated via
        :func:`parse_speech_config` and ``preset_type`` is re-derived from its
        ``engine_mode`` before persisting.

        Args:
            config: A raw ``SpeechConfig`` dict (realtime or pipeline
                discriminated union).

        Returns:
            ``(Preset, None)`` on success, or ``(None, error)`` where error is a
            validation message, ``"Default not found"`` (no ``is_default`` row),
            or a Supabase error message.
        """
        preset_type, err = self._derive_preset_type(config)
        if err:
            return None, err
        capability_error = await self._validate_model_capabilities(config)
        if capability_error:
            return None, capability_error
        try:
            response = (
                self.supabase.table("pipeline_presets")
                .update({"config": config, "preset_type": preset_type.value})
                .eq("is_default", True)
                .execute()
            )
            if not response.data:
                return None, "Default not found"
            return Preset(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error updating default preset: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("preset.get_presets")
    async def get_presets(
        self,
        *,
        only_published: bool = True,
        preset_type: Optional[PresetType] = None,
        include_drafts: bool = False,
    ) -> tuple[List[Preset], Optional[str]]:
        """List presets, filtered by the publish lifecycle and optionally type.

        Args:
            only_published: When True (default), filter to ``is_published=True``
                unless ``include_drafts`` is set. Ignored when ``include_drafts``
                is True (platform-admin management view returns drafts too).
            preset_type: Optional ``PresetType`` filter (realtime/pipeline).
            include_drafts: When True, return drafts + published (platform-admin
                only — the route enforces this). When False, only published rows
                are returned.

        Returns:
            ``(list[Preset], None)`` on success, or ``( [], error)`` on failure.
        """
        try:
            query = self.supabase.table("pipeline_presets").select("*")
            if not include_drafts and only_published:
                query = query.eq("is_published", True)
            if preset_type is not None:
                query = query.eq("preset_type", preset_type.value)
            response = query.execute()
            return [Preset(**item) for item in response.data], None
        except Exception as e:
            logger.error(f"Error getting presets: {e}", exc_info=True)
            return [], str(e)

    @tracer.start_as_current_span("preset.get_preset_by_id")
    async def get_preset_by_id(
        self, preset_id: UUID
    ) -> tuple[Optional[Preset], Optional[str]]:
        """Fetch a single preset by id (draft or published).

        Used by the worker (live fetch each call) and by the agent-assignment
        validation. Returns draft or published rows; assignment validation
        enforces ``is_published`` separately.

        Args:
            preset_id: The preset row id.

        Returns:
            ``(Preset, None)`` if found, ``(None, None)`` if not found, or
            ``(None, error)`` on a Supabase error. A missing preset is NOT an
            error — the worker falls back to the realtime default on ``None``.
        """
        try:
            response = (
                self.supabase.table("pipeline_presets")
                .select("*")
                .eq("id", str(preset_id))
                .limit(1)
                .execute()
            )
            if not response.data:
                return None, None
            return Preset(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error getting preset {preset_id}: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("preset.publish_preset")
    async def publish_preset(
        self, preset_id: UUID, published: bool
    ) -> tuple[Optional[Preset], Optional[str]]:
        """Flip a preset's ``is_published`` state (publish/unpublish).

        Publishing makes the preset visible to org admins for assignment;
        unpublishing hides it from new assignments (existing agents keep working
        — the worker reads the preset by id, not via the listing).

        Args:
            preset_id: The preset row id.
            published: True to publish, False to revert to draft.

        Returns:
            ``(Preset, None)`` on success, or ``(None, error)`` (``"Preset not
            found"`` if the row is missing).
        """
        try:
            # Guard: the system-default row is not publishable — it is the
            # admin-only fallback (never shown in the org-admin picker, which
            # lists published presets only).
            existing = (
                self.supabase.table("pipeline_presets")
                .select("id,is_default,config")
                .eq("id", str(preset_id))
                .limit(1)
                .execute()
            )
            if not existing.data:
                return None, "Preset not found"
            if existing.data[0].get("is_default"):
                return None, "The system default preset is not publishable"

            if published:
                config = existing.data[0].get("config")
                if not isinstance(config, dict):
                    return None, "Preset has no valid speech configuration"
                capability_error = await self._validate_model_capabilities(config)
                if capability_error:
                    return None, capability_error

            response = (
                self.supabase.table("pipeline_presets")
                .update({"is_published": published})
                .eq("id", str(preset_id))
                .execute()
            )
            if not response.data:
                return None, "Preset not found"
            return Preset(**response.data[0]), None
        except Exception as e:
            logger.error(f"Error publishing preset {preset_id}: {e}", exc_info=True)
            return None, str(e)

    @tracer.start_as_current_span("preset.get_preset_usage")
    async def get_preset_usage(
        self, preset_id: UUID
    ) -> tuple[Optional[List[dict]], Optional[str]]:
        """List the agents currently referencing a preset (delete guardrail).

        Args:
            preset_id: The preset row id.

        Returns:
            ``(agents, None)`` where ``agents`` is a list of dicts
            ``{"id", "name", "organization_id"}`` (empty if unused), or
            ``(None, error)`` on failure.
        """
        try:
            response = (
                self.supabase.table("voice_agents")
                .select("id,name,organization_id")
                .eq("preset_id", str(preset_id))
                .execute()
            )
            return list(response.data or []), None
        except Exception as e:
            logger.error(
                f"Error fetching usage for preset {preset_id}: {e}", exc_info=True
            )
            return None, str(e)

    @tracer.start_as_current_span("preset.delete_preset")
    async def delete_preset(
        self, preset_id: UUID, *, force: bool = False
    ) -> tuple[Optional[bool], Optional[str]]:
        """Permanently delete a preset (platform-admin only).

        Guardrail: a preset referenced by any agent cannot be deleted without
        ``force`` — return ``"in_use"`` so the route can surface the affected
        agents in a 409 body. With ``force=True`` (or when unused), the
        ``voice_agents.preset_id`` FK ``ON DELETE SET NULL`` detaches
        referencing agents (they fall back to the System Default preset row) and the
        preset row is removed.

        Args:
            preset_id: The preset row id.
            force: When True, allow deleting an in-use preset.

        Returns:
            ``(True, None)`` on success, or ``(None, error)`` where error is
            ``"Preset not found"``, ``"in_use"``, or a Supabase error message.
        """
        try:
            exists = (
                self.supabase.table("pipeline_presets")
                .select("id,is_default")
                .eq("id", str(preset_id))
                .execute()
            )
            if not exists.data:
                return None, "Preset not found"
            if exists.data[0].get("is_default"):
                return None, "The system default preset cannot be deleted"

            usage, usage_error = await self.get_preset_usage(preset_id)
            if usage_error:
                return None, usage_error
            if usage and not force:
                return None, "in_use"

            # FK ON DELETE SET NULL detaches referencing agents; just delete.
            self.supabase.table("pipeline_presets").delete().eq(
                "id", str(preset_id)
            ).execute()
            return True, None
        except Exception as e:
            logger.error(f"Error deleting preset {preset_id}: {e}", exc_info=True)
            return None, str(e)

    @staticmethod
    def build_preset_catalog(
        presets: List[Preset],
        default_preset: Optional[Preset],
        org: Optional[object],
        *,
        use_platform_credits: bool = False,
        credentials_self_service: bool = True,
    ) -> PresetCatalogResponse:
        """Build the org-facing white-label preset catalog with readiness flags.

        Maps published presets to :class:`PresetCatalogItem` rows (no config or
        engine metadata). Readiness is computed server-side via
        :func:`shared.voice_agents.key_resolver.is_preset_ready`.

        Args:
            presets: Published preset rows from :meth:`get_presets`.
            default_preset: The system-default row (unused for readiness; kept
                for API symmetry and future metadata). ``default_is_ready`` is
                always ``True`` because org admins do not configure credentials
                for the platform-managed fallback.
            org: Organization object for credential resolution, or ``None``.
            use_platform_credits: Per-agent billing toggle (platform keys only).
            credentials_self_service: Whether org admins may self-configure keys.

        Returns:
            A :class:`PresetCatalogResponse` for the org-admin picker.
        """
        from shared.voice_agents.key_resolver import is_preset_ready

        items: list[PresetCatalogItem] = []
        for preset in presets:
            if preset.is_default:
                continue
            cfg = parse_speech_config(preset.config)
            items.append(
                PresetCatalogItem(
                    id=preset.id,
                    name=preset.name,
                    description=preset.description,
                    is_ready=is_preset_ready(
                        cfg,
                        org,
                        use_platform_credits=use_platform_credits,
                        org_credentials_only=True,
                    ),
                )
            )

        default_ready = True
        # The system-default fallback (preset_id=null) is platform-managed. Org
        # admins never configure credentials for it — the worker resolves keys
        # via platform env / platform credits. Readiness checks apply only to
        # published presets in ``items`` above.

        return PresetCatalogResponse(
            presets=items,
            default_is_ready=default_ready,
            credentials_self_service=credentials_self_service,
        )


# Module-level singleton (mirrors tool_service.tool_service).
preset_service = PresetService()


__all__ = ["PresetService", "preset_service"]
