"""
Tests for SkillImporter service.

Tests cover: URL parsing (all supported formats), YAML frontmatter parsing,
file kind classification, and fetch_skill_packages integration.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.voice_agents.skill_import import (
    SkillImporter,
    ParsedGitHubSource,
    ImportedFile,
    ImportedSkillPackage,
    _parse_yaml_frontmatter,
    _classify_file_kind,
    GITHUB_API_BASE,
)


class TestParseSourceURL:
    """Test cases for URL parsing from all supported formats."""

    def setup_method(self):
        self.importer = SkillImporter()

    def test_parse_key_shorthand_with_skill(self):
        result = self.importer.parse_source_url("anthropics/skills/cold-email")
        assert result.owner == "anthropics"
        assert result.repo == "skills"
        assert result.base_path == "cold-email"
        assert result.requested_skill_slug == "cold-email"
        assert result.ref == "main"

    def test_parse_key_shorthand_repo_only(self):
        result = self.importer.parse_source_url("anthropics/skills")
        assert result.owner == "anthropics"
        assert result.repo == "skills"
        assert result.base_path == ""
        assert result.requested_skill_slug is None

    def test_parse_github_tree_url(self):
        result = self.importer.parse_source_url(
            "https://github.com/anthropics/skills/tree/main/skills/cold-email"
        )
        assert result.owner == "anthropics"
        assert result.repo == "skills"
        assert result.ref == "main"
        assert result.base_path == "skills/cold-email"
        assert result.requested_skill_slug == "cold-email"

    def test_parse_github_blob_url(self):
        result = self.importer.parse_source_url(
            "https://github.com/anthropics/skills/blob/main/skills/cold-email/SKILL.md"
        )
        assert result.owner == "anthropics"
        assert result.repo == "skills"
        assert result.ref == "main"
        assert result.base_path == "skills/cold-email/SKILL.md"
        assert result.requested_skill_slug == "skill.md"

    def test_parse_github_tree_url_non_main_branch(self):
        result = self.importer.parse_source_url(
            "https://github.com/owner/repo/tree/develop/skills/test-skill"
        )
        assert result.ref == "develop"
        assert result.base_path == "skills/test-skill"

    def test_parse_skills_sh_url(self):
        result = self.importer.parse_source_url(
            "https://skills.sh/anthropics/skills/cold-email"
        )
        assert result.owner == "anthropics"
        assert result.repo == "skills"
        assert result.base_path == "cold-email"
        assert result.requested_skill_slug == "cold-email"

    def test_parse_skills_sh_url_repo_only(self):
        result = self.importer.parse_source_url(
            "https://skills.sh/anthropics/skills"
        )
        assert result.owner == "anthropics"
        assert result.repo == "skills"
        assert result.requested_skill_slug is None

    def test_parse_npx_skillsadd_command(self):
        result = self.importer.parse_source_url(
            "npx skillsadd anthropics/skills/cold-email"
        )
        assert result.owner == "anthropics"
        assert result.repo == "skills"
        assert result.base_path == "cold-email"
        assert result.requested_skill_slug == "cold-email"

    def test_parse_npx_skills_add_command(self):
        result = self.importer.parse_source_url(
            "npx skills add owner/repo --skill my-skill"
        )
        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.requested_skill_slug == "my-skill"

    def test_parse_npx_skills_add_with_url(self):
        result = self.importer.parse_source_url(
            "npx skills add https://github.com/owner/repo --skill specific-skill"
        )
        assert result.owner == "owner"
        assert result.repo == "repo"
        assert result.requested_skill_slug == "specific-skill"

    def test_parse_key_shorthand_with_dots(self):
        result = self.importer.parse_source_url(
            "my.org/my-repo.skills/my-skill.name"
        )
        assert result.owner == "my.org"
        assert result.repo == "my-repo.skills"
        assert result.requested_skill_slug == "my-skill.name"

    def test_parse_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Unsupported URL format"):
            self.importer.parse_source_url("invalid-format")


class TestYAMLFrontmatterParsing:
    """Test cases for YAML frontmatter parsing."""

    def test_parse_full_frontmatter(self):
        content = """---
name: cold-email
description: Draft and send cold emails
license: MIT
---
# Instructions

Actually send the email."""
        fm, body = _parse_yaml_frontmatter(content)
        assert fm["name"] == "cold-email"
        assert fm["description"] == "Draft and send cold emails"
        assert fm["license"] == "MIT"
        assert "Instructions" in body
        assert "Actually send" in body

    def test_parse_no_frontmatter(self):
        content = "# Just markdown\n\nNo frontmatter here."
        fm, body = _parse_yaml_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_parse_empty_frontmatter(self):
        content = """---
---
# Body here"""
        fm, body = _parse_yaml_frontmatter(content)
        assert fm == {}
        assert "Body here" in body

    def test_parse_malformed_frontmatter(self):
        content = """---
incomplete
# No closing"""
        fm, body = _parse_yaml_frontmatter(content)
        assert fm == {}
        assert body == content


class TestFileKindClassification:
    """Test cases for file kind classification."""

    def test_reference_file(self):
        assert _classify_file_kind("references/policies.md") == "reference"
        assert _classify_file_kind("docs/readme.md") == "reference"
        assert _classify_file_kind("ref/guide.md") == "reference"

    def test_script_file(self):
        assert _classify_file_kind("scripts/validate.py") == "script"
        assert _classify_file_kind("script/run.sh") == "script"
        assert _classify_file_kind("bin/setup") == "script"
        assert _classify_file_kind("helper.py") == "script"
        assert _classify_file_kind("utils.js") == "script"
        assert _classify_file_kind("run.sh") == "script"
        assert _classify_file_kind("types.ts") == "script"

    def test_asset_file(self):
        assert _classify_file_kind("assets/logo.png") == "asset"
        assert _classify_file_kind("data/config.json") == "asset"
        assert _classify_file_kind("images/banner.jpg") == "asset"

    def test_other_file(self):
        assert _classify_file_kind("README.md") == "other"
        assert _classify_file_kind("LICENSE") == "other"
        assert _classify_file_kind(".gitignore") == "other"


class TestFetchSkillPackages:
    """Integration tests for fetch_skill_packages."""

    @pytest.mark.asyncio
    async def test_fetch_single_skill_success(self):
        importer = SkillImporter()

        from unittest.mock import Mock

        mock_client = AsyncMock()

        # Mock tree response — json() is sync, not async
        tree_resp = Mock()
        tree_resp.status_code = 200
        tree_resp.json.return_value = {
            "tree": [
                {"path": "skills/cold-email/SKILL.md", "type": "blob"},
                {"path": "skills/cold-email/references/policies.md", "type": "blob"},
                {"path": "skills/cold-email/scripts/validate.py", "type": "blob"},
            ]
        }

        # Mock file content responses
        skill_resp = Mock()
        skill_resp.status_code = 200
        skill_resp.json.return_value = {
            "encoding": "base64",
            "content": "LS0tCm5hbWU6IGNvbGQtZW1haWwKZGVzY3JpcHRpb246IFNlbmQgY29sZCBlbWFpbHMKLS0tCiMgSW5zdHJ1Y3Rpb25zCgpBY3R1YWxseSBzZW5kIHRoZSBlbWFpbC4=",
        }

        ref_resp = Mock()
        ref_resp.status_code = 200
        ref_resp.json.return_value = {
            "encoding": "base64",
            "content": "IyBQb2xpY2llcwoKQmUgcmVzcGVjdGZ1bC4=",
        }

        script_resp = Mock()
        script_resp.status_code = 200
        script_resp.json.return_value = {
            "encoding": "base64",
            "content": "IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwoKZGVmIHZhbGlkYXRlKGVtYWlsKToKICAgIHBhc3M=",
        }

        async def get_side_effect(*args, **kwargs):
            url = args[0] if args else kwargs.get("url", "")
            if "/git/trees/" in url:
                return tree_resp
            elif "SKILL.md" in url:
                return skill_resp
            elif "policies.md" in url:
                return ref_resp
            elif "validate.py" in url:
                return script_resp
            return Mock(status_code=404)

        mock_client.get = AsyncMock(side_effect=get_side_effect)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            packages = await importer.fetch_skill_packages(
                "anthropics/skills/cold-email"
            )

        assert len(packages) == 1
        pkg = packages[0]
        assert pkg.slug == "cold-email"
        assert pkg.name == "cold-email"
        assert "Instructions" in pkg.content
        assert len(pkg.files) == 2

        file_paths = {f.file_path for f in pkg.files}
        assert "references/policies.md" in file_paths
        assert "scripts/validate.py" in file_paths

    @pytest.mark.asyncio
    async def test_fetch_no_skill_md_found(self):
        importer = SkillImporter()

        from unittest.mock import Mock

        mock_client = AsyncMock()
        tree_resp = Mock()
        tree_resp.status_code = 200
        tree_resp.json.return_value = {"tree": []}
        mock_client.get = AsyncMock(return_value=tree_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="No SKILL.md files found"):
                await importer.fetch_skill_packages("owner/repo")

    @pytest.mark.asyncio
    async def test_fetch_tree_api_error(self):
        importer = SkillImporter()

        from unittest.mock import Mock

        mock_client = AsyncMock()
        tree_resp = Mock()
        tree_resp.status_code = 404
        mock_client.get = AsyncMock(return_value=tree_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ValueError, match="Failed to fetch GitHub tree"):
                await importer.fetch_skill_packages("owner/repo")


class TestImportedFile:
    """Test cases for ImportedFile dataclass."""

    def test_imported_file_creation(self):
        f = ImportedFile(
            file_path="references/policies.md",
            content="# Policies",
            file_kind="reference",
        )
        assert f.file_path == "references/policies.md"
        assert f.content == "# Policies"
        assert f.file_kind == "reference"


class TestImportedSkillPackage:
    """Test cases for ImportedSkillPackage dataclass."""

    def test_package_with_files(self):
        files = [
            ImportedFile(file_path="refs/a.md", content="# A", file_kind="reference"),
            ImportedFile(file_path="scripts/b.py", content="print('hello')", file_kind="script"),
        ]
        pkg = ImportedSkillPackage(
            slug="test-skill",
            name="Test Skill",
            description="A test",
            content="# Main content",
            files=files,
            source_url="https://github.com/owner/repo",
            source_ref="main",
        )
        assert pkg.slug == "test-skill"
        assert pkg.name == "Test Skill"
        assert len(pkg.files) == 2
        assert pkg.source_url == "https://github.com/owner/repo"
        assert pkg.source_ref == "main"

    def test_package_without_files(self):
        pkg = ImportedSkillPackage(
            slug="simple",
            name="Simple",
            description=None,
            content="# Simple",
        )
        assert len(pkg.files) == 0


class TestParsedGitHubSource:
    """Test cases for ParsedGitHubSource dataclass."""

    def test_default_ref_is_main(self):
        src = ParsedGitHubSource(owner="owner", repo="repo")
        assert src.ref == "main"
        assert src.base_path == ""
        assert src.requested_skill_slug is None
