"""
Tests for platform skill seed definitions.

Validates that all platform skill templates have consistent structure,
valid slugs, non-empty content, required fields, and default files.
"""

import re

import pytest
from src.voice_agents.skill_seeds import PLATFORM_SKILL_TEMPLATES


class TestPlatformSkillSeeds:
    """Test cases for platform skill seed definitions."""

    def test_expected_skill_count(self):
        """Test that we have the expected number of platform skill templates."""
        assert len(PLATFORM_SKILL_TEMPLATES) == 6

    def test_all_skills_have_required_fields(self):
        """Test that every skill has slug, name, description, and content."""
        for skill in PLATFORM_SKILL_TEMPLATES:
            assert "slug" in skill, f"Missing slug in skill: {skill.get('name', 'unknown')}"
            assert "name" in skill, f"Missing name in skill: {skill.get('slug', 'unknown')}"
            assert "description" in skill, f"Missing description in skill: {skill['slug']}"
            assert "content" in skill, f"Missing content in skill: {skill['slug']}"

    def test_slugs_are_valid_kebab_case(self):
        """Test that all slugs follow kebab-case convention."""
        for skill in PLATFORM_SKILL_TEMPLATES:
            assert re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", skill["slug"]), \
                f"Invalid slug: {skill['slug']}"

    def test_slugs_are_unique(self):
        """Test that no duplicate slugs exist."""
        slugs = [s["slug"] for s in PLATFORM_SKILL_TEMPLATES]
        assert len(slugs) == len(set(slugs)), "Duplicate slugs found"

    def test_content_is_non_trivial(self):
        """Test that skill content is substantial (not just a title)."""
        for skill in PLATFORM_SKILL_TEMPLATES:
            assert len(skill["content"]) > 100, \
                f"Skill '{skill['slug']}' content too short ({len(skill['content'])} chars)"

    def test_content_has_markdown_headings(self):
        """Test that content uses markdown structure with headings."""
        for skill in PLATFORM_SKILL_TEMPLATES:
            assert "#" in skill["content"], \
                f"Skill '{skill['slug']}' has no markdown headings"

    def test_expected_slugs_present(self):
        """Test that all expected platform skill slugs are present."""
        expected = {
            "appointment-booking",
            "call-transfer",
            "faq-responder",
            "after-hours",
            "lead-qualification",
            "payment-collection",
        }
        actual = {s["slug"] for s in PLATFORM_SKILL_TEMPLATES}
        assert actual == expected

    def test_descriptions_are_concise(self):
        """Test that descriptions are reasonable length (for prompt metadata)."""
        for skill in PLATFORM_SKILL_TEMPLATES:
            assert len(skill["description"]) < 250, \
                f"Skill '{skill['slug']}' description too long for prompt metadata"
            assert len(skill["description"]) > 10, \
                f"Skill '{skill['slug']}' description too short"

    def test_content_has_usage_guidance(self):
        """Test that skills include usage guidance or procedure sections."""
        for skill in PLATFORM_SKILL_TEMPLATES:
            content_lower = skill["content"].lower()
            has_usage_section = (
                "when to use" in content_lower
                or "procedure" in content_lower
                or "flow" in content_lower
                or "how to" in content_lower
                or "overview" in content_lower
            )
            assert has_usage_section, \
                f"Skill '{skill['slug']}' missing usage guidance section"

    def test_default_files_are_valid(self):
        """Test that default files have required fields and valid paths."""
        for skill in PLATFORM_SKILL_TEMPLATES:
            files = skill.get("default_files", [])
            for file_def in files:
                assert "file_path" in file_def, \
                    f"Missing file_path in default file for '{skill['slug']}'"
                assert "content" in file_def, \
                    f"Missing content in default file '{file_def.get('file_path', '?')}'"
                assert file_def["file_path"].endswith(".md"), \
                    f"Default file must be markdown: {file_def['file_path']}"

    def test_appointment_booking_has_reference_files(self):
        """Test that appointment-booking has the expected 5 reference files."""
        ab_skill = next(s for s in PLATFORM_SKILL_TEMPLATES if s["slug"] == "appointment-booking")
        files = ab_skill.get("default_files", [])
        assert len(files) == 5, f"Expected 5 reference files, got {len(files)}"

        expected_paths = {
            "references/service-menu.md",
            "references/hours.md",
            "references/staff-directory.md",
            "references/policies.md",
            "references/faqs.md",
        }
        actual_paths = {f["file_path"] for f in files}
        assert actual_paths == expected_paths, f"Missing or extra files: {actual_paths ^ expected_paths}"

    def test_appointment_booking_content_is_comprehensive(self):
        """Test that appointment-booking has substantial, structured content."""
        ab_skill = next(s for s in PLATFORM_SKILL_TEMPLATES if s["slug"] == "appointment-booking")
        content = ab_skill["content"]

        # Should be at least 10,000 chars (it's ~18K)
        assert len(content) > 10000, \
            f"appointment-booking content should be comprehensive, got {len(content)} chars"

        # Should contain key sections
        assert "## Core Decision Tree" in content
        assert "## NEW BOOKING FLOW" in content
        assert "## RESCHEDULE FLOW" in content
        assert "## CANCELLATION FLOW" in content
        assert "## GUARDRAILS" in content
        assert "## ERROR HANDLING" in content

        # Should reference load_skill_reference for progressive disclosure
        assert "load_skill_reference" in content

    def test_non_booking_skills_have_no_default_files(self):
        """Test that only appointment-booking has default files (for now)."""
        for skill in PLATFORM_SKILL_TEMPLATES:
            if skill["slug"] != "appointment-booking":
                files = skill.get("default_files", [])
                assert len(files) == 0, \
                    f"Skill '{skill['slug']}' unexpectedly has {len(files)} default files"
