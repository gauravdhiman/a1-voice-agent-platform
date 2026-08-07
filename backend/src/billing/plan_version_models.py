"""
Pydantic models for plan product versioning, publish events, and migration policy.

Published plan versions are immutable; subscribers bind to a specific version via
``organization_subscriptions.plan_version_id``. See
``docs/03_implementation/plan_entitlements_and_limits.md``.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PlanVersionStatus(str, Enum):
    """Lifecycle status for a plan version row."""

    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class MigrationMode(str, Enum):
    """How existing subscribers are treated when a new version is published."""

    NEW_SIGNUPS_ONLY = "new_signups_only"
    GRACE_THEN_OPTIONAL = "grace_then_optional"
    GRACE_THEN_REQUIRED = "grace_then_required"
    IMMEDIATE_REQUIRED = "immediate_required"


class StripeMigrationTiming(str, Enum):
    """When Stripe subscription price should change during migration."""

    IMMEDIATE = "immediate"
    AT_PERIOD_END = "at_period_end"
    AT_GRACE_END = "at_grace_end"


class PlanVersionPublishRequest(BaseModel):
    """Request body for publishing a draft plan version."""

    migration_mode: MigrationMode = Field(
        default=MigrationMode.NEW_SIGNUPS_ONLY,
        description="Migration policy for subscribers on the superseded version",
    )
    grace_period_days: Optional[int] = Field(
        default=None,
        ge=0,
        description="Grace period before required migration (when applicable)",
    )
    auto_migrate_on_expiry: bool = Field(
        default=False,
        description="Automatically migrate subs when grace period ends",
    )
    allow_indefinite_legacy: bool = Field(
        default=True,
        description="Whether subs may remain on the legacy version indefinitely",
    )
    stripe_migration_timing: StripeMigrationTiming = Field(
        default=StripeMigrationTiming.AT_PERIOD_END,
    )
    compliance_policy: Optional[str] = Field(
        default="soft_block",
        description="Policy when migrated org exceeds new limits",
    )


class PlanVersionPublishResult(BaseModel):
    """Result returned after a successful publish."""

    plan_version_id: UUID
    from_plan_version_id: Optional[UUID] = None
    publish_event_id: UUID
    stripe_price_id: str
    migration_rows_created: int = 0
    subscribers_migrated_immediately: int = 0
    published_at: datetime


class ResolvedCheckoutPlan(BaseModel):
    """Plan resolution from a Stripe price ID at checkout / webhook time."""

    plan_version_id: UUID
    subscription_plan_id: Optional[UUID] = None
    stripe_price_id: str
