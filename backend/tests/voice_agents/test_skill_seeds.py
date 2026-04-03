"""
Tests for built-in skill seed definitions.

Validates that all built-in skills have consistent structure,
valid slugs, non-empty content, and required fields.
"""

import re

import pytest
from src.voice_agents.skill_seeds import BUILT_IN_SKILLS


class TestSkillSeeds:
    """Test cases for built-in skill definitions."""

    def test_expected_skill_count(self):
        """Test that we have the expected number of built-in skills."""
        assert len(BUILT_IN_SKILLS) == 6

    def test_all_skills_have_required_fields(self):
        """Test that every skill has slug, name, description, and content."""
        for skill in BUILT_IN_SKILLS:
            assert "slug" in skill, f"Missing slug in skill: {skill.get('name', 'unknown')}"
            assert "name" in skill, f"Missing name in skill: {skill.get('slug', 'unknown')}"
            assert "description" in skill, f"Missing description in skill: {skill['slug']}"
            assert "content" in skill, f"Missing content in skill: {skill['slug']}"

    def test_slugs_are_valid_kebab_case(self):
        """Test that all slugs follow kebab-case convention."""
        for skill in BUILT_IN_SKILLS:
            assert re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", skill["slug"]), \
                f"Invalid slug: {skill['slug']}"

    def test_slugs_are_unique(self):
        """Test that no duplicate slugs exist."""
        slugs = [s["slug"] for s in BUILT_IN_SKILLS]
        assert len(slugs) == len(set(slugs)), "Duplicate slugs found"

    def test_content_is_non_trivial(self):
        """Test that skill content is substantial (not just a title)."""
        for skill in BUILT_IN_SKILLS:
            assert len(skill["content"]) > 100, \
                f"Skill '{skill['slug']}' content too short ({len(skill['content'])} chars)"

    def test_content_has_markdown_headings(self):
        """Test that content uses markdown structure with headings."""
        for skill in BUILT_IN_SKILLS:
            assert "#" in skill["content"], \
                f"Skill '{skill['slug']}' has no markdown headings"

    def test_expected_slugs_present(self):
        """Test that all expected built-in skill slugs are present."""
        expected = {
            "appointment-booking",
            "call-transfer",
            "faq-responder",
            "after-hours",
            "lead-qualification",
            "payment-collection",
        }
        actual = {s["slug"] for s in BUILT_IN_SKILLS}
        assert actual == expected

    def test_descriptions_are_concise(self):
        """Test that descriptions are reasonable length (for prompt metadata)."""
        for skill in BUILT_IN_SKILLS:
            assert len(skill["description"]) < 200, \
                f"Skill '{skill['slug']}' description too long for prompt metadata"
            assert len(skill["description"]) > 10, \
                f"Skill '{skill['slug']}' description too short"

    def test_content_has_when_to_use_section(self):
        """Test that skills include a 'When to Use' or similar section."""
        for skill in BUILT_IN_SKILLS:
            content_lower = skill["content"].lower()
            has_usage_section = (
                "when to use" in content_lower
                or "procedure" in content_lower
                or "when" in content_lower
            )
            assert has_usage_section, \
                f"Skill '{skill['slug']}' missing usage guidance section"
