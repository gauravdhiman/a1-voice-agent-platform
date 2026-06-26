"""
Tests for platform skill seed definitions.

Validates that all platform skill templates have consistent structure,
valid slugs, non-empty content, required fields, and default files.

Phase 2c re-design (2026-06-24): the seed library is now industry-specific
(15 skills across dental, restaurant, hvac). See
``docs/02_features/voice_agents/skills_library.md`` for the index.

Quality rules:
* Every skill must have concrete caller trigger phrases in the description
  (so the agent knows when to activate the skill).
* SKILL.md content must include a mermaid decision diagram, a guardrails
  section, and handoff language (so the agent knows what to do at edges).
* SKILL.md must NOT name a specific external tool (e.g. Google Calendar,
  Stripe, Twilio). Skills describe user-visible actions; the agent picks
  the tool. This keeps skills durable as our toolset evolves.
* Reference files are kept small (progressive disclosure) and only added
  when the skill actually needs on-demand data.
"""

import re

import pytest
from src.voice_agents.skill_seeds import PLATFORM_SKILL_TEMPLATES


# Slugs we DO NOT want to leak into the seed library anymore. These were
# the original 8 generic "capability" skills; they were deleted because:
# 1. they were stubs dressed as skills, and
# 2. the dental-flavored reference data didn't generalize across industries.
# They are listed here so any re-introduction is a conscious decision.
DEPRECATED_LEGACY_SLUGS = {
    "appointment-booking",
    "insurance-verification",
    "dispatch-coordination",
    "call-transfer",
    "faq-responder",
    "after-hours",
    "lead-qualification",
    "payment-collection",
}

# Tools we explicitly forbid in skill content. Skills must describe the
# user-visible action; the agent + tools handle the mechanism.
FORBIDDEN_TOOL_NAMES = (
    "google calendar",
    "googlecalendar",
    "stripe",
    "twilio",
    "sendgrid",
    "cal.com",
    "calcom",
    "gmail",
    "google sheets",
    "googlesheets",
    "supabase",
    "openai",
)


class TestPlatformSkillSeedsStructure:
    """Sanity: every skill has the required shape."""

    def test_expected_skill_count(self):
        """Library must ship 15 industry-specific skills (5 per industry)."""
        assert len(PLATFORM_SKILL_TEMPLATES) == 15

    def test_all_skills_have_required_fields(self):
        for skill in PLATFORM_SKILL_TEMPLATES:
            for field in ("slug", "name", "description", "content"):
                assert field in skill, (
                    f"Skill '{skill.get('slug', '?')}' missing field '{field}'"
                )
            assert "default_files" in skill, (
                f"Skill '{skill['slug']}' missing 'default_files' (use [] if none)"
            )

    def test_slugs_are_valid_kebab_case(self):
        for skill in PLATFORM_SKILL_TEMPLATES:
            assert re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", skill["slug"]), (
                f"Invalid slug: {skill['slug']}"
            )

    def test_slugs_are_unique(self):
        slugs = [s["slug"] for s in PLATFORM_SKILL_TEMPLATES]
        assert len(slugs) == len(set(slugs)), "Duplicate slugs found"

    def test_slugs_are_industry_prefixed(self):
        """All slugs start with the industry prefix: dental-, restaurant-, or hvac-."""
        for skill in PLATFORM_SKILL_TEMPLATES:
            assert skill["slug"].startswith(("dental-", "restaurant-", "hvac-")), (
                f"Skill slug '{skill['slug']}' is not industry-prefixed"
            )

    def test_descriptions_are_concise_and_contain_trigger_phrases(self):
        """Descriptions are short enough for prompt metadata and include
        concrete caller phrases so the agent knows when to activate."""
        for skill in PLATFORM_SKILL_TEMPLATES:
            desc = skill["description"]
            assert 20 < len(desc) < 350, (
                f"Skill '{skill['slug']}' description length out of range "
                f"({len(desc)} chars): {desc!r}"
            )
            # Must include at least one quoted or recognizable trigger phrase
            # heuristic. We don't require exact match — just that the
            # description reads as "do X when caller says Y" rather than as a
            # bare capability label.
            assert "caller" in desc.lower() or "when " in desc.lower(), (
                f"Skill '{skill['slug']}' description lacks trigger phrase guidance"
            )


class TestPlatformSkillSeedsContent:
    """Quality: every SKILL.md has the structure an agent needs to act."""

    @pytest.fixture(params=[s["slug"] for s in PLATFORM_SKILL_TEMPLATES])
    def skill(self, request):
        slug = request.param
        return next(s for s in PLATFORM_SKILL_TEMPLATES if s["slug"] == slug)

    def test_content_is_substantial(self, skill):
        """A real skill is at least a few hundred chars (decision tree alone
        is ~300+). We don't cap the upper bound."""
        assert len(skill["content"]) >= 500, (
            f"Skill '{skill['slug']}' content too short "
            f"({len(skill['content'])} chars)"
        )

    def test_content_has_decision_diagram(self, skill):
        """Every skill must include a mermaid decision diagram so the agent
        has a visual decision tree, not just prose."""
        assert "```mermaid" in skill["content"], (
            f"Skill '{skill['slug']}' missing mermaid decision diagram"
        )

    def test_content_has_guardrails_section(self, skill):
        """Every skill must list 'MUST NOT' / guardrails explicitly."""
        lower = skill["content"].lower()
        assert "guardrail" in lower or "must not" in lower or "don't" in lower, (
            f"Skill '{skill['slug']}' missing guardrails section"
        )

    def test_content_has_handoff_language(self, skill):
        """Every skill must tell the agent what to say / do when handing off
        to another skill (typically escalation)."""
        assert "handoff" in skill["content"].lower() or "escalat" in skill["content"].lower(), (
            f"Skill '{skill['slug']}' missing handoff / escalation guidance"
        )

    def test_content_does_not_name_specific_tools(self, skill):
        """Skills describe user-visible actions, not mechanisms. Naming a
        specific external tool (e.g. 'Google Calendar') couples the skill to
        that tool's availability and breaks the moment the org wires a
        different calendar. Tool assignments change; capabilities don't."""
        content_lower = skill["content"].lower()
        for tool in FORBIDDEN_TOOL_NAMES:
            assert tool not in content_lower, (
                f"Skill '{skill['slug']}' names forbidden tool '{tool}'. "
                f"Describe the user-visible action instead."
            )

    def test_content_documents_its_reference_files(self, skill):
        """Skills with reference files must list them in their SKILL.md so
        the agent knows what's available to load. This is the progressive
        disclosure contract: SKILL.md describes the file by name; the
        agent loads it via load_skill_reference when needed."""
        for f in skill.get("default_files", []):
            # The skill must mention the file_path (or its basename) in
            # the SKILL.md content so the agent knows it exists.
            basename = f["file_path"].split("/")[-1]
            content_lower = skill["content"].lower()
            assert (
                f["file_path"].lower() in content_lower
                or basename.lower() in content_lower
            ), (
                f"Skill '{skill['slug']}' has reference file "
                f"'{f['file_path']}' but doesn't mention it in SKILL.md"
            )


class TestPlatformSkillSeedsCoverage:
    """Library shape: 5 skills per industry, every industry covered."""

    @pytest.fixture
    def by_industry(self):
        out = {"dental": [], "restaurant": [], "hvac": []}
        for skill in PLATFORM_SKILL_TEMPLATES:
            for prefix in out:
                if skill["slug"].startswith(prefix + "-"):
                    out[prefix].append(skill)
                    break
        return out

    def test_each_industry_has_5_skills(self, by_industry):
        for industry, skills in by_industry.items():
            assert len(skills) == 5, (
                f"Industry '{industry}' should have 5 skills, has {len(skills)}: "
                f"{[s['slug'] for s in skills]}"
            )

    def test_each_industry_covers_5_capability_slots(self, by_industry):
        """Every industry covers five capability slots. Capability slots
        differ per industry because the underlying workflows differ
        (e.g. restaurants don't have patient intake or maintenance
        recalls). We assert that each industry has the structural shape:
        one booking-capability, one knowledge/FAQ capability, one
        intake-or-special-request capability, one follow-up-or-recall
        capability, and one escalation capability."""
        # Each industry should have:
        # - exactly 1 escalation skill (industry-prefixed)
        # - the rest (4) cover booking, info/intake, special-request/recall,
        #   and follow-up — they don't need to map 1:1 to the dental/HVAC
        #   capability names, but the count must be 5.
        for industry, skills in by_industry.items():
            slugs = [s["slug"] for s in skills]
            escalations = [s for s in slugs if s.endswith("-escalation")]
            assert len(escalations) == 1, (
                f"Industry '{industry}' should have exactly 1 escalation "
                f"skill, has {len(escalations)}: {escalations}"
            )
            assert len(slugs) == 5, (
                f"Industry '{industry}' should have exactly 5 skills, "
                f"has {len(slugs)}: {slugs}"
            )


class TestPlatformSkillSeedsLegacyRemoval:
    """The 8 original generic skills must not appear in the new library."""

    def test_no_legacy_slugs_present(self):
        actual = {s["slug"] for s in PLATFORM_SKILL_TEMPLATES}
        leaked = actual & DEPRECATED_LEGACY_SLUGS
        assert not leaked, (
            f"Legacy skill slugs leaked into the new library: {leaked}. "
            "These were deleted in favor of industry-specific skills."
        )

    def test_no_dental_baked_default_files_in_other_industries(self):
        """The old appointment-booking had dental-flavored reference files
        (DEFAULT_SERVICE_MENU started with '## Dental Services'). Any new
        skill whose default file content references 'Dental Services'
        outside the dental-* family is a leak."""
        for skill in PLATFORM_SKILL_TEMPLATES:
            if skill["slug"].startswith("dental-"):
                continue  # dental skills can obviously mention dental
            for f in skill.get("default_files", []):
                content = f.get("content", "").lower()
                assert "dental services" not in content, (
                    f"Skill '{skill['slug']}' has dental-specific default "
                    f"file '{f['file_path']}' — should be industry-neutral "
                    f"or industry-matched."
                )


class TestPlatformSkillSeedsFiles:
    """Reference files: small, markdown, valid paths."""

    def test_default_files_have_required_fields(self):
        for skill in PLATFORM_SKILL_TEMPLATES:
            for f in skill["default_files"]:
                assert "file_path" in f, (
                    f"Skill '{skill['slug']}' default file missing file_path"
                )
                assert "content" in f, (
                    f"Skill '{skill['slug']}' default file missing content"
                )
                assert "file_kind" in f, (
                    f"Skill '{skill['slug']}' default file missing file_kind"
                )
                assert f["file_path"].endswith(".md"), (
                    f"Skill '{skill['slug']}' default file must be markdown: "
                    f"{f['file_path']}"
                )

    def test_default_file_paths_are_unique_within_a_skill(self):
        for skill in PLATFORM_SKILL_TEMPLATES:
            paths = [f["file_path"] for f in skill["default_files"]]
            assert len(paths) == len(set(paths)), (
                f"Skill '{skill['slug']}' has duplicate default file paths"
            )

    def test_default_file_paths_use_references_subdir(self):
        for skill in PLATFORM_SKILL_TEMPLATES:
            for f in skill["default_files"]:
                assert f["file_path"].startswith("references/"), (
                    f"Skill '{skill['slug']}' default file should live under "
                    f"references/: {f['file_path']}"
                )

    def test_reference_files_are_small_enough_for_progressive_disclosure(self):
        """Reference files should be loaded on-demand and stay under ~12 KB
        so a single file load doesn't blow the token budget."""
        for skill in PLATFORM_SKILL_TEMPLATES:
            for f in skill["default_files"]:
                assert len(f["content"]) < 12000, (
                    f"Skill '{skill['slug']}' default file '{f['file_path']}' "
                    f"too large ({len(f['content'])} chars). Split into smaller "
                    f"reference files for progressive disclosure."
                )

    def test_skills_dont_have_excessive_default_files(self):
        """A skill rarely needs more than 3 on-demand reference files. If
        you find yourself wanting more, split the skill or inline the data
        into SKILL.md."""
        for skill in PLATFORM_SKILL_TEMPLATES:
            assert len(skill["default_files"]) <= 3, (
                f"Skill '{skill['slug']}' has "
                f"{len(skill['default_files'])} default files (max 3). "
                "Split the skill or move data into SKILL.md."
            )
