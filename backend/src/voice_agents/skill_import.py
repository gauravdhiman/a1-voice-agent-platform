"""
Skill import service for fetching skills from GitHub and skills.sh.

Fetches the entire skill package (SKILL.md + all reference files) via the
GitHub REST API — no git clone or shell commands. Stores all files in the
database for progressive disclosure at runtime.

URL formats supported:
- GitHub: https://github.com/owner/repo/tree/main/skills/my-skill
- GitHub: https://github.com/owner/repo (imports all skills in repo)
- skills.sh: https://skills.sh/owner/repo/skill-name
- Key shorthand: owner/repo/skill-name
- Key shorthand: owner/repo (all skills)
"""

import base64
import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"


@dataclass
class ParsedGitHubSource:
    """Parsed components of a GitHub URL."""

    owner: str
    repo: str
    ref: str = "main"
    base_path: str = ""  # e.g., "skills/my-skill"
    requested_skill_slug: Optional[str] = None


@dataclass
class ImportedFile:
    """A file discovered during import."""

    file_path: str  # Relative to skill root, e.g., "references/policies.md"
    content: str
    file_kind: str  # reference, script, asset, other


@dataclass
class ImportedSkillPackage:
    """Complete skill package ready for storage."""

    slug: str
    name: str
    description: Optional[str]
    content: str  # Main SKILL.md content (with frontmatter stripped)
    files: List[ImportedFile] = field(default_factory=list)
    source_url: str = ""
    source_ref: str = ""


def _classify_file_kind(file_path: str) -> str:
    """Classify a file into a kind based on its path and extension."""
    lower = file_path.lower()
    if lower.endswith((".sh", ".py", ".js", ".ts", ".bash")):
        return "script"
    if any(lower.startswith(p) for p in ("scripts/", "script/", "bin/")):
        return "script"
    if any(lower.startswith(p) for p in ("assets/", "asset/", "data/", "images/")):
        return "asset"
    if any(lower.startswith(p) for p in ("references/", "reference/", "docs/", "ref/")):
        return "reference"
    return "other"


def _parse_yaml_frontmatter(content: str) -> Tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.

    Returns (frontmatter_dict, body_without_frontmatter).
    If no frontmatter, returns ({}, original_content).
    """
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    frontmatter_str = parts[1].strip()
    body = parts[2].strip()

    # Simple YAML key-value parser (avoid full YAML dependency)
    frontmatter = {}
    for line in frontmatter_str.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value:
                frontmatter[key] = value

    return frontmatter, body


class SkillImporter:
    """Import skills from GitHub and skills.sh via REST API.

    No shell commands (git, npx) are executed. All fetching is done
    via HTTPS API calls to GitHub.
    """

    def __init__(self, github_token: Optional[str] = None):
        """Initialize with optional GitHub token for higher rate limits."""
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "A1-Voice-Agent-Platform",
        }
        if github_token:
            self.headers["Authorization"] = f"token {github_token}"

    def parse_source_url(self, source: str) -> ParsedGitHubSource:
        """Parse any supported URL format into GitHub components.

        Supports:
        - owner/repo/skill (key shorthand)
        - owner/repo (all skills in repo)
        - https://skills.sh/owner/repo/skill
        - https://github.com/owner/repo/tree/ref/path
        - https://github.com/owner/repo
        - npx skillsadd owner/repo (command format from skills.sh)
        - npx skills add URL --skill skill-name (command format)
        """
        source = source.strip()

        # Strip npx command prefixes: "npx skillsadd ...", "npx skills add ..."
        source = re.sub(r"^npx\s+skillsadd\s+", "", source)
        source = re.sub(r"^npx\s+skills\s+add\s+", "", source)

        # Extract --skill flag if present
        skill_flag_match = re.search(r"--skill\s+([A-Za-z0-9_.-]+)", source)
        extracted_skill_slug = skill_flag_match.group(1).lower() if skill_flag_match else None
        if skill_flag_match:
            source = source[: skill_flag_match.start()].strip()

        source = source.strip()

        # Key-style: owner/repo/skill
        if not source.startswith("http") and re.match(
            r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", source
        ):
            parts = source.split("/")
            return ParsedGitHubSource(
                owner=parts[0],
                repo=parts[1],
                base_path=parts[2],
                requested_skill_slug=parts[2].lower(),
            )

        # Key-style: owner/repo
        if not source.startswith("http") and re.match(
            r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", source
        ):
            parts = source.split("/")
            return ParsedGitHubSource(
                owner=parts[0],
                repo=parts[1],
                base_path=extracted_skill_slug or "",
                requested_skill_slug=extracted_skill_slug,
            )

        # skills.sh URL
        skills_sh_match = re.match(
            r"^https?://(?:www\.)?skills\.sh/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:/([A-Za-z0-9_.-]+))?",
            source,
        )
        if skills_sh_match:
            owner, repo, skill_slug = skills_sh_match.groups()
            return ParsedGitHubSource(
                owner=owner,
                repo=repo,
                base_path=skill_slug or "",
                requested_skill_slug=skill_slug.lower() if skill_slug else None,
            )

        # GitHub URL
        parsed = urlparse(source)
        if "github.com" in parsed.netloc:
            path_parts = parsed.path.strip("/").split("/")
            if len(path_parts) < 2:
                raise ValueError(f"Invalid GitHub URL: {source}")

            owner = path_parts[0]
            repo = path_parts[1]
            ref = "main"
            base_path = ""

            # https://github.com/owner/repo/tree/ref/path/to/skill
            if len(path_parts) > 3 and path_parts[2] == "tree":
                ref = path_parts[3]
                if len(path_parts) > 4:
                    base_path = "/".join(path_parts[4:])

            # https://github.com/owner/repo/blob/ref/path (single file)
            elif len(path_parts) > 3 and path_parts[2] == "blob":
                ref = path_parts[3]
                if len(path_parts) > 4:
                    base_path = "/".join(path_parts[4:])

            result = ParsedGitHubSource(
                owner=owner,
                repo=repo,
                ref=ref,
                base_path=base_path,
                requested_skill_slug=base_path.split("/")[-1].lower() if base_path else None,
            )
            # Override with --skill flag if present
            if extracted_skill_slug:
                result.requested_skill_slug = extracted_skill_slug
                if not result.base_path:
                    result.base_path = extracted_skill_slug
            return result

        raise ValueError(
            f"Unsupported URL format: '{source}'. "
            f"Supported formats: GitHub URL, skills.sh URL, owner/repo/skill, "
            f"or 'npx skillsadd owner/repo'."
        )

    async def fetch_skill_packages(
        self, source: str
    ) -> List[ImportedSkillPackage]:
        """Fetch complete skill package(s) from a URL.

        Returns a list because a repo URL might contain multiple skills.
        """
        parsed = self.parse_source_url(source)
        logger.info(
            f"Importing from GitHub: {parsed.owner}/{parsed.repo} "
            f"ref={parsed.ref} path={parsed.base_path}"
        )

        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            # 1. Get the repo tree recursively
            tree_url = (
                f"{GITHUB_API_BASE}/repos/{parsed.owner}/{parsed.repo}"
                f"/git/trees/{parsed.ref}?recursive=1"
            )
            tree_response = await client.get(tree_url)
            if tree_response.status_code != 200:
                raise ValueError(
                    f"Failed to fetch GitHub tree: {tree_response.status_code} "
                    f"for {parsed.owner}/{parsed.repo}"
                )

            tree_data = tree_response.json()
            all_files = [
                entry
                for entry in tree_data.get("tree", [])
                if entry.get("type") == "blob"
            ]

            # 2. Filter to files under base_path
            base_prefix = f"{parsed.base_path}/" if parsed.base_path else ""

            # Find all SKILL.md files to discover skills
            skill_md_files = [
                f
                for f in all_files
                if f["path"].lower().endswith("skill.md")
                and (not base_prefix or f["path"].startswith(base_prefix))
            ]

            # If no exact prefix match, try broader search (e.g., "skills/cold-email/SKILL.md")
            if not skill_md_files and parsed.requested_skill_slug:
                slug = parsed.requested_skill_slug
                skill_md_files = [
                    f
                    for f in all_files
                    if f["path"].lower().endswith("skill.md")
                    and f"/{slug}/" in f["path"].lower()
                ]
                # Update base_prefix to match the found path
                if skill_md_files:
                    found_dir = "/".join(skill_md_files[0]["path"].split("/")[:-1])
                    base_prefix = f"{found_dir}/" if found_dir else ""
                    logger.info(f"Found skill at alternate path: {base_prefix}")

            if not skill_md_files:
                raise ValueError(
                    f"No SKILL.md files found in {parsed.owner}/{parsed.repo}"
                    + (f" under {parsed.base_path}" if parsed.base_path else "")
                )

            # 3. For each SKILL.md, build the skill package
            packages = []
            for skill_md_entry in skill_md_files:
                skill_dir = "/".join(skill_md_entry["path"].split("/")[:-1])
                skill_dir_prefix = f"{skill_dir}/" if skill_dir else ""

                # Filter requested skill if specified
                dir_name = skill_dir.split("/")[-1] if skill_dir else ""
                if (
                    parsed.requested_skill_slug
                    and dir_name.lower() != parsed.requested_skill_slug
                ):
                    continue

                # Fetch SKILL.md content
                skill_md_content = await self._fetch_file_content(
                    client, parsed.owner, parsed.repo, parsed.ref,
                    skill_md_entry["path"],
                )
                if not skill_md_content:
                    continue

                # Parse frontmatter
                frontmatter, body = _parse_yaml_frontmatter(skill_md_content)
                slug = (
                    frontmatter.get("name", "")
                    or dir_name
                    or parsed.repo
                ).lower().replace(" ", "-")
                name = frontmatter.get("name", slug.replace("-", " ").title())
                description = frontmatter.get("description")

                # Fetch all other files in this skill directory
                other_files = [
                    f
                    for f in all_files
                    if f["path"].startswith(skill_dir_prefix)
                    and f["path"] != skill_md_entry["path"]
                    and f["path"].lower() != f"{skill_dir_prefix}skill.md"
                ]

                imported_files = []
                for file_entry in other_files:
                    # Get relative path within skill directory
                    rel_path = file_entry["path"]
                    if skill_dir_prefix:
                        rel_path = file_entry["path"][len(skill_dir_prefix):]

                    file_content = await self._fetch_file_content(
                        client, parsed.owner, parsed.repo, parsed.ref,
                        file_entry["path"],
                    )
                    if file_content:
                        imported_files.append(
                            ImportedFile(
                                file_path=rel_path,
                                content=file_content,
                                file_kind=_classify_file_kind(rel_path),
                            )
                        )

                source_url = (
                    f"https://github.com/{parsed.owner}/{parsed.repo}"
                    + (f"/tree/{parsed.ref}/{skill_dir}" if skill_dir else "")
                )

                packages.append(
                    ImportedSkillPackage(
                        slug=slug,
                        name=name,
                        description=description,
                        content=body,
                        files=imported_files,
                        source_url=source_url,
                        source_ref=parsed.ref,
                    )
                )

            if not packages:
                raise ValueError(
                    f"No matching skills found for "
                    f"'{parsed.requested_skill_slug}' in "
                    f"{parsed.owner}/{parsed.repo}"
                )

            logger.info(
                f"Fetched {len(packages)} skill(s) with "
                f"{sum(len(p.files) for p in packages)} total files"
            )
            return packages

    async def _fetch_file_content(
        self,
        client: httpx.AsyncClient,
        owner: str,
        repo: str,
        ref: str,
        path: str,
    ) -> Optional[str]:
        """Fetch a single file's content from GitHub API."""
        try:
            url = (
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
                f"/contents/{path}?ref={ref}"
            )
            response = await client.get(url)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {path}: {response.status_code}")
                return None

            data = response.json()
            if data.get("encoding") == "base64" and data.get("content"):
                return base64.b64decode(data["content"]).decode("utf-8")
            elif data.get("content"):
                return data["content"]
            return None
        except Exception as e:
            logger.warning(f"Error fetching {path}: {e}")
            return None
