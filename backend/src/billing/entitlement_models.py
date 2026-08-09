"""
Pydantic models for plan-version entitlements and limit enforcement.

Entitlements are resolved from immutable ``plan_versions`` bound to each
``organization_subscriptions.plan_version_id``. See
``docs/03_implementation/plan_entitlements_and_limits.md``.
"""

from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EntitlementKind(str, Enum):
    """Whether a catalog entry is a numeric limit or a boolean feature."""

    LIMIT = "limit"
    FEATURE = "feature"


class EntitlementValueType(str, Enum):
    """Supported value types for entitlement definitions."""

    INTEGER = "integer"
    BOOLEAN = "boolean"
    UNLIMITED = "unlimited"
    DECIMAL = "decimal"
    ENUM = "enum"
    DURATION_SECONDS = "duration_seconds"


class PlanVersionStatus(str, Enum):
    """Lifecycle state for a plan version row."""

    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class EntitlementDefinition(BaseModel):
    """Platform-wide catalog entry describing one limit or feature key."""

    key: str
    kind: EntitlementKind
    display_name: str
    value_type: EntitlementValueType
    unit: Optional[str] = None
    validation_schema: dict[str, Any] = Field(default_factory=dict)
    enforcement_handler: str
    default_enforcement: str = "hard"
    default_when_absent: Optional[dict[str, Any]] = None
    is_active: bool = True
    description: Optional[str] = None


class ResolvedEntitlement(BaseModel):
    """Single resolved limit or feature for an organization."""

    key: str
    kind: EntitlementKind
    assigned: bool
    raw_value: Optional[dict[str, Any]] = None
    effective_value: Any = None
    is_unlimited: bool = False


class OrgEntitlements(BaseModel):
    """Full entitlement view for one organization."""

    organization_id: UUID
    plan_version_id: UUID
    plan_product_slug: str
    plan_version_number: int
    plan_version_label: Optional[str] = None
    is_legacy_version: bool = False
    is_entitled: bool
    cancel_at_period_end: bool = False
    access_until: Optional[str] = None
    limits: dict[str, ResolvedEntitlement] = Field(default_factory=dict)
    features: dict[str, ResolvedEntitlement] = Field(default_factory=dict)
    migration: Optional["OrgPlanMigrationInfo"] = None


class PlanMigrationStatus(str, Enum):
    """Per-subscriber migration lifecycle state."""

    PENDING = "pending"
    GRACE_ACTIVE = "grace_active"
    MIGRATED = "migrated"
    DECLINED_LEGACY = "declined_legacy"
    CANCELLED = "cancelled"


class OrgPlanMigrationInfo(BaseModel):
    """Active plan-version migration offer or grace countdown for an org."""

    migration_id: UUID
    from_plan_version_id: UUID
    to_plan_version_id: UUID
    status: PlanMigrationStatus
    grace_period_ends_at: Optional[str] = None
    target_plan_version_label: Optional[str] = None
    allow_indefinite_legacy: bool = True
    can_self_migrate: bool = True


class PlanMigrationRunResult(BaseModel):
    """Summary from processing due grace-period migrations."""

    processed: int = 0
    migrated: int = 0
    skipped: int = 0
    errors: int = 0


OrgEntitlements.model_rebuild()


class LimitCheckResult(BaseModel):
    """Outcome of a limit check before a mutating action."""

    allowed: bool
    code: str
    limit: Optional[int] = None
    current: int = 0
    message: Optional[str] = None
    upgrade_plan_product_slug: Optional[str] = None


class EntitlementDenied(Exception):
    """Raised when an action violates plan entitlements."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        limit: Optional[int] = None,
        current: int = 0,
        upgrade_plan_product_slug: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.limit = limit
        self.current = current
        self.upgrade_plan_product_slug = upgrade_plan_product_slug

    def to_detail(self) -> dict[str, Any]:
        """Serialize for HTTP 403 responses."""
        return {
            "error": "entitlement_denied",
            "code": self.code,
            "limit": self.limit,
            "current": self.current,
            "upgrade_plan_product_slug": self.upgrade_plan_product_slug,
            "message": self.message,
        }
