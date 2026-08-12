"""
Pydantic models for platform-admin plan catalog and entitlement management APIs.

Used by ``admin_plan_routes.py`` and ``admin_plan_catalog_service.py``.
See ``docs/03_implementation/plan_entitlements_and_limits.md`` §10.3.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .entitlement_models import (
    EntitlementDefinition,
    EntitlementKind,
    EntitlementValueType,
)
from .plan_version_models import BillingMode, CreditGrantPolicy, PlanVersionStatus


class EntitlementDefinitionUpdate(BaseModel):
    """Mutable fields on catalog definitions (not key/handler)."""

    display_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CreditEventAdminUpdate(BaseModel):
    """Mutable rate fields for one fixed system pricing event.

    Meter and billing interval are runtime-owned semantics. They are returned
    with the catalog row for explanation, but cannot be changed from the admin
    UI because no corresponding arbitrary handler exists in the system.
    """

    description: Optional[str] = Field(None, max_length=500)
    credit_cost: Optional[int] = Field(None, ge=0)


class PlanProductCreate(BaseModel):
    """Create a new plan product family."""

    slug: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    sort_order: int = Field(default=10, ge=0)


class PlanProduct(BaseModel):
    """Plan product row for admin list/detail."""

    id: UUID
    slug: str
    display_name: str
    description: Optional[str] = None
    sort_order: int
    is_active: bool
    stripe_product_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PlanProductCreateResult(BaseModel):
    """Result of creating a plan product, including optional Stripe sync status."""

    product: PlanProduct
    stripe_auto_create_error: Optional[str] = Field(
        default=None,
        description="Set when platform product was created but Stripe Product auto-create failed",
    )


class PlanProductStripeUpdate(BaseModel):
    """Manually link a Stripe Product when auto-create failed."""

    stripe_product_id: str = Field(..., min_length=1, max_length=255)


class PlanVersionEntitlementInput(BaseModel):
    """Sparse entitlement assignment on a draft version."""

    entitlement_key: str
    value: dict[str, Any]
    display_order: Optional[int] = Field(default=None, ge=0)


class PlanVersionEntitlementOrderRequest(BaseModel):
    """Ordered entitlement keys for changing card presentation sequence."""

    entitlement_keys: list[str] = Field(default_factory=list)


class PlanVersionDraftCreate(BaseModel):
    """Create a new draft plan version for a product."""

    display_label: Optional[str] = None
    billing_mode: BillingMode = BillingMode.PAID
    credit_grant_policy: CreditGrantPolicy = CreditGrantPolicy.RECURRING
    price_amount_cents: int = Field(default=0, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    billing_interval: str = Field(default="monthly")
    trial_period_days: Optional[int] = Field(None, ge=0)
    stripe_product_id: Optional[str] = None
    entitlements: list[PlanVersionEntitlementInput] = Field(default_factory=list)


class PlanVersionDraftUpdate(BaseModel):
    """Update a draft plan version (immutable once published)."""

    display_label: Optional[str] = None
    billing_mode: Optional[BillingMode] = None
    credit_grant_policy: Optional[CreditGrantPolicy] = None
    price_amount_cents: Optional[int] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    billing_interval: Optional[str] = None
    trial_period_days: Optional[int] = Field(None, ge=0)
    stripe_product_id: Optional[str] = None
    stripe_price_id: Optional[str] = None
    entitlements: Optional[list[PlanVersionEntitlementInput]] = None


class PlanVersionEntitlement(BaseModel):
    """Entitlement row attached to a plan version."""

    id: UUID
    entitlement_key: str
    value: dict[str, Any]
    display_order: int = Field(default=0, ge=0)


class PlanVersionSummary(BaseModel):
    """Plan version metadata for admin list views (entitlements loaded on demand)."""

    id: UUID
    plan_product_id: UUID
    version_number: int
    status: PlanVersionStatus
    display_label: Optional[str] = None
    billing_mode: BillingMode = BillingMode.PAID
    credit_grant_policy: CreditGrantPolicy = CreditGrantPolicy.RECURRING
    price_amount_cents: int
    currency: str
    billing_interval: str
    trial_period_days: Optional[int] = None
    stripe_product_id: Optional[str] = None
    stripe_price_id: Optional[str] = None
    is_current_for_signup: bool
    published_at: Optional[datetime] = None
    legacy_subscription_plan_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class PlanVersionDetail(PlanVersionSummary):
    """Plan version with entitlements for admin editor."""

    entitlements: list[PlanVersionEntitlement] = Field(default_factory=list)


class PlanProductWithVersions(PlanProduct):
    """Product with nested version summaries for admin list."""

    versions: list[PlanVersionSummary] = Field(default_factory=list)


class PlanVersionCloneRequest(BaseModel):
    """Optional overrides when cloning a version to a new draft."""

    display_label: Optional[str] = None
    price_amount_cents: Optional[int] = Field(None, ge=0)
