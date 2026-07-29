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
from supabase import Client

from shared.config import supabase_config
from shared.voice_agents.preset_models import (
    Preset,
    PresetCreate,
    PresetType,
    PresetUpdate,
)
from shared.voice_agents.speech_config import parse_speech_config

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

        try:
            existing = (
                self.supabase.table("pipeline_presets")
                .select("*")
                .eq("name", data.name)
                .execute()
            )
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
        referencing agents (they fall back to the realtime default) and the
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
                .select("id")
                .eq("id", str(preset_id))
                .execute()
            )
            if not exists.data:
                return None, "Preset not found"

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


# Module-level singleton (mirrors tool_service.tool_service).
preset_service = PresetService()


__all__ = ["PresetService", "preset_service"]
