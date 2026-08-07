#!/usr/bin/env python3
"""Dev helper to fully clean up a user and all of their platform resources.

Run this script to delete a test/sandbox user from the database together
with every piece of data they own. It is intended for local development and
test-environment cleanup ("I created a test user, now remove everything").

Behavior
--------
1. Resolves the target user in ``auth.users`` by ``--email`` or ``--user-id``.
2. Finds every organization the user belongs to (via ``user_roles``).
3. For each organization it decides whether the organization may be deleted:

   - **Sole member** (the user is the ONLY member in ``user_roles``): the
     organization and all of its resources (voice agents, agent tools, embed
     configs, embed call logs, call logs, phone numbers, organization skills
     and their files, agent skill assignments, skill update logs, subscriptions,
     billing history, credit transactions, notification logs, invitations,
     memberships) are deleted. This is handled by the database ``ON DELETE
     CASCADE`` chain rooted at ``organizations``, so the whole tenant subtree is
     removed atomically.
   - **Shared organization** (more than one user): the organization and all of
     its resources are LEFT INTACT. Only the target user's membership row is
     removed (plus invitations they sent and their notification logs, via
     ``auth.users`` cascade).
4. Deletes the user's rows that do not cascade from ``auth.users``
   (``notification_logs``, ``email_verification_tokens``), then deletes the
   ``auth.users`` row itself, which cascades to ``identities``, ``sessions``,
   ``refresh_tokens``, ``user_roles`` and invitations the user sent.

Safety
------
- Always run with ``--dry-run`` first; it prints the plan without applying.
- By default the script runs in ``--dry-run`` mode. Use ``--apply`` to apply.
- A confirmation prompt is shown when applying unless ``--yes`` is passed.
- Every mutation runs inside a single transaction and is committed only after
  the last delete succeeds. A failure rolls everything back.
- Global/system data is never touched: ``platform_tools``, ``pipeline_presets``,
  ``platform_skills``, ``platform_skill_files``, ``roles``, ``permissions``,
  ``role_permissions``, ``notification_events``, ``notification_templates``,
  ``credit_events``, ``credit_products``, ``subscription_plans`` and
  ``voice_templates`` (all shared across tenants) are intentionally left in place.

Example
-------
    # Show the plan (no changes)
    cd backend && .venv/bin/python scripts/cleanup_test_user.py --email test@cogninets.local

    # Apply, answering the confirmation prompt
    cd backend && .venv/bin/python scripts/cleanup_test_user.py --email test@cogninets.local --apply

    # Apply without a prompt
    cd backend && .venv/bin/python scripts/cleanup_test_user.py --user-id <uuid> --apply --yes

    # Direct execution (the script is executable and needs python3 + psycopg2)
    backend/scripts/cleanup_test_user.py --help

The script connects using ``DATABASE_URL`` (or ``--database-url``) which points
at the local Supabase Postgres instance. Run it inside the ``backend-dev``
container or from the host with the env loaded.
"""

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import psycopg2
    from psycopg2.extras import DictCursor
except ImportError:  # pragma: no cover - only needed for real DB work
    psycopg2 = None  # type: ignore[assignment]
    DictCursor = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Path setup so the script can run from anywhere.
#   backend/scripts/cleanup_test_user.py
#     parents[1] == backend
#     parents[2] == repo root (where `shared` and `.env` live)
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parents[1]
_ROOT_DIR = Path(__file__).resolve().parents[2]
for _d in (_BACKEND_DIR, _ROOT_DIR):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

try:
    from shared.config import settings
except Exception:  # pragma: no cover - config import is optional
    settings = None

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("cleanup_test_user")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class OrgPlan:
    """Deletion decision for one organization the user belongs to."""

    org_id: str
    org_name: str
    org_slug: str
    member_count: int
    shared_with_user_ids: list[str] = field(default_factory=list)
    delete_org: bool = False

    @property
    def summary(self) -> str:
        """One-line human readable summary of the decision for this org."""
        if self.delete_org:
            return f"[DELETE ORG] {self.org_name} ({self.org_slug}) -- sole member"
        return f"[KEEP ORG]   {self.org_name} ({self.org_slug}) -- {self.member_count} members"


@dataclass
class CleanupPlan:
    """The complete cleanup plan computed for a single user."""

    user_id: str
    user_email: Optional[str] = None
    orgs: list[OrgPlan] = field(default_factory=list)

    @property
    def delete_org_ids(self) -> list[str]:
        """Ids of organizations scheduled for deletion."""
        return [o.org_id for o in self.orgs if o.delete_org]

    @property
    def kept_org_ids(self) -> list[str]:
        """Ids of organizations that remain untouched."""
        return [o.org_id for o in self.orgs if not o.delete_org]


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def resolve_user(
    db, email: Optional[str] = None, user_id: Optional[str] = None
) -> Optional[dict]:
    """Look up an ``auth.users`` row by email or id.

    Args:
        db: An open psycopg2 connection.
        email: User email (case-insensitive match).
        user_id: ``auth.users.id`` to match.

    Returns:
        Dict with ``id`` and ``email`` keys, or ``None`` if not found.
    """
    if not email and not user_id:
        raise ValueError("Provide either --email or --user-id")

    if user_id:
        sql = "SELECT id, email FROM auth.users WHERE id = %s"
        param: object = user_id
    else:
        sql = "SELECT id, email FROM auth.users WHERE LOWER(email) = LOWER(%s) LIMIT 1"
        param = email

    with db.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(sql, (param,))
        row = cur.fetchone()
        return dict(row) if row else None


def _list_user_orgs(db, user_id: str) -> list[dict]:
    """List every org the user belongs to plus shared members and counts.

    Args:
        db: An open psycopg2 connection.
        user_id: ``auth.users`` id.

    Returns:
        List of dicts with ``org_id``, ``org_name``, ``org_slug``,
        ``member_ids`` (all distinct user ids in the org) and ``member_count``.
    """
    sql = """
        SELECT o.id                 AS org_id,
               o.name               AS org_name,
               o.slug               AS org_slug,
               ARRAY_AGG(DISTINCT ur.user_id) FILTER (
                   WHERE ur.user_id IS NOT NULL
               )::text[]            AS member_ids
        FROM user_roles ur
        JOIN organizations o ON o.id = ur.organization_id
        WHERE o.id IN (
            SELECT organization_id
            FROM user_roles
            WHERE user_id = %s AND organization_id IS NOT NULL
        )
        GROUP BY o.id, o.name, o.slug
        ORDER BY o.name
    """
    with db.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(sql, (user_id,))
        rows = cur.fetchall()

    results = []
    for r in rows:
        member_ids = _normalize_member_ids(r["member_ids"])
        results.append(
            {
                "org_id": str(r["org_id"]),
                "org_name": r["org_name"],
                "org_slug": r["org_slug"],
                "member_ids": member_ids,
                "member_count": len(member_ids),
            }
        )
    return results


def _normalize_member_ids(raw_ids) -> list[str]:
    """Normalize a DB member-id value into a list of uuid strings.

    Depending on the psycopg2 typecaster setup, ``uuid[]`` aggregate results
    come back either as a proper Python list or as a raw Postgres array
    literal string (e.g. ``{uuid-1,uuid-2}``). Iterating the literal string
    yields one character per item, so it must be parsed before use.

    Args:
        raw_ids: The value returned by the ``ARRAY_AGG`` query (list, raw
            literal string, or ``None``).

    Returns:
        A list of uuid strings, or an empty list when the value is falsy.
    """
    if not raw_ids:
        return []
    if isinstance(raw_ids, str):
        inner = raw_ids.strip().strip("{}").strip()
        if not inner:
            return []
        return [part.strip() for part in inner.split(",")]
    return [str(item) for item in raw_ids]


def classify_org(row: dict, target_user_id: str) -> OrgPlan:
    """Decide whether one org should be deleted given the target user.

    Rules:
    - Delete the org only when the target user is the ONLY member.
    - Any other scenario (multiple members) keeps the org and all of its
      resources; only the target user's membership row is removed later.

    Args:
        row: One org dict from :func:`_list_user_orgs`.
        target_user_id: The user being cleaned up.

    Returns:
        An :class:`OrgPlan` with ``delete_org`` set accordingly.
    """
    member_ids = row["member_ids"]
    shared = [m for m in member_ids if m != target_user_id]
    delete_org = not shared  # target user is the only member
    return OrgPlan(
        org_id=row["org_id"],
        org_name=row["org_name"],
        org_slug=row["org_slug"],
        member_count=row["member_count"],
        shared_with_user_ids=shared,
        delete_org=delete_org,
    )


def build_cleanup_plan(
    db, user_id: str, user_email: Optional[str] = None
) -> CleanupPlan:
    """Compute the cleanup plan for a user.

    Args:
        db: An open psycopg2 connection.
        user_id: ``auth.users`` id of the target user.
        user_email: Email of the user (for reporting).

    Returns:
        :class:`CleanupPlan` with per-org decisions.
    """
    plan = CleanupPlan(user_id=str(user_id), user_email=user_email)
    for row in _list_user_orgs(db, user_id):
        plan.orgs.append(classify_org(row, str(user_id)))
    return plan


def delete_organizations(db, org_ids: list[str]) -> None:
    """Delete organizations (and, by cascade, all of their resources).

    The database FK graph removes the full tenant subtree: ``organizations`` ->
    ``voice_agents`` -> ``agent_tools``/``agent_embed_configs`` ->
    ``token_refresh_leases``/``embed_call_logs``, plus ``organization_skills`` ->
    ``organization_skill_files``/``agent_skills``/``skill_update_logs``, plus
    billing/subscription/notification/invitation/membership rows. Because
    ``platform_tools`` and ``pipeline_presets`` are global catalogs, deleting an
    org never affects them.

    Args:
        db: An open psycopg2 connection.
        org_ids: Ids of organizations to delete (sole-member orgs only).
    """
    if not org_ids:
        return
    with db.cursor() as cur:
        for org_id in org_ids:
            cur.execute("DELETE FROM organizations WHERE id = %s", (org_id,))


def _delete_user_rows(db, user_id: str) -> None:
    """Delete user rows that do NOT cascade from ``auth.users``.

    ``notification_logs.user_id`` and ``email_verification_tokens.user_id``
    have no ``ON DELETE CASCADE`` FK, so they are removed explicitly before the
    auth row is deleted. Everything else (``user_roles``, invitations the user
    sent) cascades automatically.

    Args:
        db: An open psycopg2 connection.
        user_id: The user id to purge.
    """
    with db.cursor() as cur:
        cur.execute("DELETE FROM notification_logs WHERE user_id = %s", (user_id,))
        cur.execute(
            "DELETE FROM email_verification_tokens WHERE user_id = %s", (user_id,)
        )


def delete_user(db, user_id: str) -> None:
    """Delete the target user from ``auth.users`` (cascades the rest).

    Args:
        db: An open psycopg2 connection.
        user_id: The ``auth.users`` id to delete.
    """
    with db.cursor() as cur:
        cur.execute("DELETE FROM auth.users WHERE id = %s", (user_id,))


def _database_url(arg_url: Optional[str]) -> str:
    """Resolve the database connection string from args or the environment.

    Priority: ``--database-url`` > ``DATABASE_URL`` env > ``settings.database_url``.

    Args:
        arg_url: The ``--database-url`` command line value (if any).

    Returns:
        A Postgres connection URL.

    Raises:
        SystemExit: If no URL can be found anywhere.
    """
    url = resolve_database_url(arg_url)
    if not url:
        logger.error(
            "No DATABASE_URL found. Set DATABASE_URL in the environment/.env "
            "or pass --database-url."
        )
        raise SystemExit(2)
    return url


def _print_plan(plan: CleanupPlan) -> None:
    """Render the plan summary to the log."""
    logger.info("User: %s (%s)", plan.user_id, plan.user_email or "no email")
    logger.info("Organizations: %d", len(plan.orgs))
    for org in plan.orgs:
        logger.info("  %s", org.summary)
    logger.info(
        "Will delete %d org(s), keep %d org(s).",
        len(plan.delete_org_ids),
        len(plan.kept_org_ids),
    )


def _confirm(message: str, yes: bool) -> bool:
    """Prompt the user for confirmation unless ``--yes`` was given.

    Args:
        message: Text shown before the prompt.
        yes: Whether to skip the prompt.

    Returns:
        True if confirmed, False otherwise.
    """
    if yes:
        return True
    try:
        answer = input(f"{message} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point."""
    doc_first_line = (__doc__ or __name__).splitlines()[0]
    parser = argparse.ArgumentParser(
        description=doc_first_line,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  %(prog)s --email test@cogninets.local --apply --yes",
    )
    ident = parser.add_mutually_exclusive_group(required=True)
    ident.add_argument("--email", help="Email of the user to clean up")
    ident.add_argument("--user-id", help="auth.users UUID of the user to clean up")
    parser.add_argument(
        "--database-url", help="Postgres URL (defaults to DATABASE_URL from env)"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default is dry-run which only prints the plan)",
    )
    parser.add_argument(
        "--yes", action="store_true", help="Skip the confirmation prompt"
    )
    args = parser.parse_args(argv)

    if psycopg2 is None:
        logger.error(
            "psycopg2 is not installed in this Python environment. "
            "Run the script from the backend venv or container, e.g.: "
            "cd backend && .venv/bin/python scripts/cleanup_test_user.py --help"
        )
        return 1

    db_url = _database_url(args.database_url)
    try:
        db = psycopg2.connect(db_url)  # connection opened with autocommit off
    except psycopg2.Error as exc:  # pragma: no cover - depends on infra
        logger.error("Failed to connect to database: %s", exc)
        return 1

    try:
        user = resolve_user(db, email=args.email, user_id=args.user_id)
        if not user:
            logger.error(
                "User %s not found in auth.users.",
                args.email or args.user_id,
            )
            return 1

        plan = build_cleanup_plan(db, user["id"], user["email"])
        _print_plan(plan)

        if not args.apply:
            logger.info("\n[DRY RUN] No changes made. Re-run with --apply to delete.")
            return 0

        if not _confirm("Delete the user and the listed orgs?", args.yes):
            logger.info("Aborted by user.")
            return 0

        try:
            with db:
                delete_organizations(db, plan.delete_org_ids)
                _delete_user_rows(db, user["id"])
                delete_user(db, user["id"])
        except psycopg2.Error as exc:  # pragma: no cover - depends on infra
            db.rollback()
            logger.error("Deletion failed; rolled back: %s", exc)
            return 2

        logger.info("Cleanup complete for %s", plan.user_id)
        return 0
    except (KeyboardInterrupt, ValueError, SystemExit):
        raise
    finally:
        db.close()


def resolve_database_url(arg_url: Optional[str]) -> Optional[str]:
    """Resolve the connection URL using the same priority as the CLI.

    This function doubles as the safe resolution used by both the CLI and unit
    tests, without importing third-party settings at module import time.

    Args:
        arg_url: URL passed via ``--database-url``.

    Returns:
        The resolved URL (from arg, ``DATABASE_URL`` env, or settings), or
        ``None`` when nothing is available.
    """
    env_url = os.environ.get("DATABASE_URL") or None
    settings_url = None
    if settings is not None:
        settings_url = getattr(settings, "database_url", None)
    return arg_url or env_url or settings_url


if __name__ == "__main__":
    raise SystemExit(main())