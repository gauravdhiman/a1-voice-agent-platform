"""
One-time data migration script: Convert built-in org skills to platform skills + forked copies.

Usage (with dry-run):
    cd backend
    .venv/bin/python scripts/migrate_built_in_to_platform.py --dry-run

Usage (apply migration):
    cd backend
    .venv/bin/python scripts/migrate_built_in_to_platform.py

What this does:
1. For each unique built-in skill slug, creates a `platform_skills` record
2. For each org with that built-in skill, creates a forked copy:
   - Copies content, files, name, slug
   - Sets source_skill_id = new platform skill id
   - Sets source_version = "1970.01.01_1" (or current version if available)
   - Sets category = "custom"
3. Updates `agent_skills` to point to new forked copies
4. Deletes old `category = "built_in"` records

Safety:
- Always run with --dry-run first
- Backs up affected rows to JSONL files before mutation
- Uses transactions where possible
- Logs every action
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.config import supabase_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Backup directory
BACKUP_DIR = Path(__file__).parent.parent / "scripts" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def backup_table(supabase, table_name: str, filter_column: str = None, filter_value: str = None) -> str:
    """Backup rows from a table to JSONL before mutation."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"{table_name}_{timestamp}.jsonl"

    query = supabase.table(table_name).select("*")
    if filter_column and filter_value:
        query = query.eq(filter_column, filter_value)

    response = query.execute()
    rows = response.data or []

    with open(backup_file, "w") as f:
        for row in rows:
            f.write(json.dumps(row, default=str) + "\n")

    logger.info(f"Backed up {len(rows)} rows from {table_name} to {backup_file}")
    return str(backup_file)


def migrate(dry_run: bool = True) -> None:
    """Run the migration."""
    logger.info(f"Starting migration (dry_run={dry_run})")

    supabase = supabase_config.client
    if not supabase:
        logger.error("Failed to initialize Supabase client. Check .env configuration.")
        sys.exit(1)

    # Step 1: Backup everything before we touch it
    logger.info("Step 1: Creating backups...")
    backup_org_skills = backup_table(supabase, "organization_skills", "category", "built_in")
    backup_org_files = backup_table(supabase, "organization_skill_files")
    backup_agent_skills = backup_table(supabase, "agent_skills")

    if dry_run:
        logger.info("\n=== DRY RUN ===")
        logger.info("Backups created. No changes applied.")
        logger.info(f"  - Org skills (built_in): {backup_org_skills}")
        logger.info(f"  - Org skill files: {backup_org_files}")
        logger.info(f"  - Agent skills: {backup_agent_skills}")
        logger.info("\nRun without --dry-run to apply changes.")
        return

    # Step 2: Get all built-in skills grouped by slug
    logger.info("\nStep 2: Fetching built-in skills...")
    built_in_response = (
        supabase.table("organization_skills")
        .select("*, organization_skill_files(*)")
        .eq("category", "built_in")
        .execute()
    )

    built_in_skills = built_in_response.data or []
    if not built_in_skills:
        logger.info("No built-in skills found. Nothing to migrate.")
        return

    # Group by slug
    by_slug: dict[str, list] = {}
    for skill in built_in_skills:
        slug = skill["slug"]
        by_slug.setdefault(slug, []).append(skill)

    logger.info(f"Found {len(built_in_skills)} built-in skills across {len(by_slug)} unique slugs")

    # Step 3: Create platform_skills records (one per unique slug)
    logger.info("\nStep 3: Creating platform_skills records...")
    platform_skill_ids: dict[str, UUID] = {}

    for slug, skills in by_slug.items():
        # Use the first skill as the canonical template
        canonical = skills[0]

        platform_skill = {
            "slug": slug,
            "name": canonical["name"],
            "description": canonical.get("description"),
            "content": canonical["content"],
            "version": canonical.get("version") or "1970.01.01_1",
            "content_hash": canonical.get("content_hash"),
            "is_active": True,
            "author": canonical.get("author") or "Platform",
        }

        response = supabase.table("platform_skills").insert(platform_skill).execute()
        if response.data:
            platform_id = response.data[0]["id"]
            platform_skill_ids[slug] = UUID(platform_id)
            logger.info(f"  Created platform skill: {slug} (id={platform_id})")

            # Copy default files to platform_skill_files
            files = canonical.get("organization_skill_files", [])
            for file in files:
                supabase.table("platform_skill_files").insert({
                    "skill_id": platform_id,
                    "file_path": file["file_path"],
                    "content": file["content"],
                    "file_kind": file["file_kind"],
                    "content_hash": file.get("content_hash"),
                }).execute()
            logger.info(f"    Copied {len(files)} files to platform_skill_files")
        else:
            logger.error(f"  FAILED to create platform skill: {slug}")

    # Step 4: Create forked copies in each org
    logger.info("\nStep 4: Creating forked copies in organizations...")
    old_to_new_skill_ids: dict[UUID, UUID] = {}

    for slug, skills in by_slug.items():
        platform_id = platform_skill_ids.get(slug)
        if not platform_id:
            continue

        for old_skill in skills:
            org_id = old_skill["organization_id"]
            old_skill_id = UUID(old_skill["id"])

            forked_skill = {
                "organization_id": org_id,
                "slug": old_skill["slug"],
                "name": old_skill["name"],
                "description": old_skill.get("description"),
                "content": old_skill["content"],
                "category": "custom",  # All org skills are now custom
                "is_active": old_skill.get("is_active", True),
                "version": old_skill.get("version"),
                "author": old_skill.get("author"),
                "content_hash": old_skill.get("content_hash"),
                "source_skill_id": str(platform_id),
                "source_version": old_skill.get("version") or "1970.01.01_1",
                "is_visible": True,
            }

            response = supabase.table("organization_skills").insert(forked_skill).execute()
            if response.data:
                new_skill_id = UUID(response.data[0]["id"])
                old_to_new_skill_ids[old_skill_id] = new_skill_id
                logger.info(f"  Forked {slug} for org {org_id}: old={old_skill_id} → new={new_skill_id}")

                # Copy files
                files = old_skill.get("organization_skill_files", [])
                for file in files:
                    supabase.table("organization_skill_files").insert({
                        "skill_id": str(new_skill_id),
                        "file_path": file["file_path"],
                        "content": file["content"],
                        "file_kind": file["file_kind"],
                        "content_hash": file.get("content_hash"),
                    }).execute()
            else:
                logger.error(f"  FAILED to fork {slug} for org {org_id}")

    # Step 5: Update agent_skills to point to new forked copies
    logger.info("\nStep 5: Updating agent_skills assignments...")
    agent_skills_response = supabase.table("agent_skills").select("*").execute()
    agent_skills = agent_skills_response.data or []

    updated_count = 0
    for assignment in agent_skills:
        old_skill_id = UUID(assignment["skill_id"])
        new_skill_id = old_to_new_skill_ids.get(old_skill_id)
        if new_skill_id:
            supabase.table("agent_skills").update({
                "skill_id": str(new_skill_id)
            }).eq("id", assignment["id"]).execute()
            updated_count += 1
            logger.info(f"  Updated agent_skill {assignment['id']}: {old_skill_id} → {new_skill_id}")

    logger.info(f"  Updated {updated_count} agent skill assignments")

    # Step 6: Delete old built-in records
    logger.info("\nStep 6: Deleting old built-in skill records...")
    deleted_count = 0
    for old_skill in built_in_skills:
        old_id = old_skill["id"]
        supabase.table("organization_skills").delete().eq("id", old_id).execute()
        deleted_count += 1
        logger.info(f"  Deleted old built-in skill: {old_id} ({old_skill['slug']})")

    logger.info(f"\nMigration complete!")
    logger.info(f"  Platform skills created: {len(platform_skill_ids)}")
    logger.info(f"  Forked copies created: {len(old_to_new_skill_ids)}")
    logger.info(f"  Agent assignments updated: {updated_count}")
    logger.info(f"  Old records deleted: {deleted_count}")
    logger.info(f"\nBackups saved to: {BACKUP_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate built-in org skills to platform skills + forked copies")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them")
    args = parser.parse_args()

    migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
