"""API models for immutable plan selection and subscription activation."""

from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .models import SubscriptionStatus
from .plan_version_models import BillingMode


class SubscriptionActivationState(str, Enum):
    """User-facing state for the plan-selection step."""

    UNSELECTED = "unselected"
    CHECKOUT_PENDING = "checkout_pending"
    ACTIVE = "active"
    TRIAL = "trial"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"


class CustomerPlanVersion(BaseModel):
    """Published plan version shown in the customer plan selector."""

    id: UUID
    plan_product_id: UUID
    product_slug: str
    product_name: str
    product_description: Optional[str] = None
    version_number: int
    display_label: Optional[str] = None
    billing_mode: BillingMode
    price_amount_cents: int
    currency: str
    billing_interval: str
    trial_period_days: Optional[int] = None
    stripe_price_id: Optional[str] = None
    entitlements: dict[str, dict[str, Any]] = Field(default_factory=dict)


class FreePlanActivationRequest(BaseModel):
    """Request to associate an organization with a published free version."""

    organization_id: UUID
    plan_version_id: UUID


class VersionedSubscriptionCheckoutRequest(BaseModel):
    """Request to begin Stripe Checkout for a published paid version."""

    organization_id: UUID
    plan_version_id: UUID
    success_url: str = Field(..., min_length=1)
    cancel_url: str = Field(..., min_length=1)


class VersionedSubscriptionRecord(BaseModel):
    """Subscription fields needed by onboarding and billing status screens."""

    id: UUID
    organization_id: UUID
    subscription_plan_id: Optional[UUID] = None
    plan_version_id: UUID
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    status: SubscriptionStatus
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FreePlanActivationResponse(BaseModel):
    """Response returned after a free plan is activated or reused."""

    subscription: VersionedSubscriptionRecord
    created: bool


class VersionedSubscriptionCheckoutResponse(BaseModel):
    """Stripe Checkout redirect details for a paid plan version."""

    checkout_url: str
    session_id: str
    plan_version_id: UUID


class SubscriptionActivationStatus(BaseModel):
    """Current plan-selection state for an organization."""

    organization_id: UUID
    state: SubscriptionActivationState
    subscription_id: Optional[UUID] = None
    plan_version_id: Optional[UUID] = None
    billing_mode: Optional[BillingMode] = None
    subscription_status: Optional[SubscriptionStatus] = None
