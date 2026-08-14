"""Tests for platform skill seed execution details."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.voice_agents.skill_service import SkillService


class TestSkillSeedService:
    """Verify safe platform skill seed behavior."""

    @pytest.mark.asyncio
    async def test_seed_does_not_prune_orphans_by_default(self):
        """Normal apply must not delete source rows that need review."""
        service = SkillService()
        client = MagicMock()
        service.supabase_config = MagicMock()
        service.supabase_config.client = client
        client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = (
            []
        )
        cleanup = AsyncMock(return_value=0)

        with patch("src.voice_agents.skill_seeds.PLATFORM_SKILL_TEMPLATES", []):
            with patch.object(service, "_prune_orphan_platform_skills", cleanup):
                count, error = await service.seed_platform_skills()

        assert count == 0
        assert error is None
        cleanup.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_seed_awaits_orphan_cleanup_when_explicitly_requested(self):
        """Only an explicit prune request may remove obsolete platform rows."""
        service = SkillService()
        client = MagicMock()
        service.supabase_config = MagicMock()
        service.supabase_config.client = client
        client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = (
            []
        )
        cleanup = AsyncMock(return_value=0)

        with patch("src.voice_agents.skill_seeds.PLATFORM_SKILL_TEMPLATES", []):
            with patch.object(service, "_prune_orphan_platform_skills", cleanup):
                count, error = await service.seed_platform_skills(prune_orphans=True)

        assert count == 0
        assert error is None
        cleanup.assert_awaited_once()
