"""
API routes for billing functionality.
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import JSONResponse
from src.auth.dependencies import (
    assert_billing_access,
    assert_platform_role,
    check_billing_permissions,
)
from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile
from src.billing.entitlement_models import OrgEntitlements
from src.billing.entitlement_service import entitlement_service
from src.billing.models import (
    AdminCreditGrantRequest,
    AdminCreditGrantResponse,
    BillingHistory,
    CreditBalance,
    CreditConsumptionRequest,
    CreditConsumptionResponse,
    CreditEvent,
    CreditProduct,
    CreditPurchaseResponse,
    CreditTransactionsResponse,
    CreditUsageResponse,
    OrganizationBillingSummary,
    OrganizationSubscriptionUpdate,
    OrganizationSubscriptionWithPlan,
    SubscriptionCheckoutResponse,
    SubscriptionPlan,
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    TransactionType,
)
from src.billing.plan_migration_service import plan_migration_service
from src.billing.service import billing_service
from src.billing.stripe_service import stripe_service
from src.billing.versioned_subscription_models import (
    CustomerPlanVersion,
    FreePlanActivationRequest,
    FreePlanActivationResponse,
    PlanChangeConfirmationResponse,
    PlanChangeConfirmRequest,
    PlanChangePreview,
    PlanChangePreviewRequest,
    SubscriptionActivationStatus,
    VersionedSubscriptionCheckoutRequest,
    VersionedSubscriptionCheckoutResponse,
)
from src.billing.versioned_subscription_service import (
    PlanChangeInProgressError,
    versioned_subscription_service,
)
from src.billing.webhook_handler import InvalidStripeWebhook, handle_stripe_webhook
from src.organization.service import organization_service
from src.rbac.user_roles.service import user_role_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


# Subscription Plans
@router.get("/plans", response_model=list[SubscriptionPlan])
async def get_subscription_plans(active_only: bool = True):
    """Get all available subscription plans."""
    try:
        return await billing_service.get_subscription_plans(active_only=active_only)
    except Exception as e:
        logger.error(f"Error fetching subscription plans: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch subscription plans"
        )


@router.get("/plans/available", response_model=list[CustomerPlanVersion])
async def get_available_plan_versions():
    """List the published plan versions currently available for signup."""
    try:
        return await versioned_subscription_service.list_available_plan_versions()
    except Exception as e:
        logger.error(f"Error fetching available plan versions: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch available plan versions"
        ) from e


@router.post("/plans", response_model=SubscriptionPlan)
async def create_subscription_plan(
    plan_data: SubscriptionPlanCreate,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Create a new subscription plan. (Platform Admin only)"""
    try:
        user_id, user_profile = user_auth

        assert_platform_role(
            user_profile,
            "platform_admin",
            error_message="User does not have permission to create subscription plans",
        )

        return await billing_service.create_subscription_plan(plan_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription plan: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to create subscription plan"
        )


@router.get("/plans/{plan_id}", response_model=SubscriptionPlan)
async def get_subscription_plan(plan_id: UUID):
    """Get a specific subscription plan."""
    try:
        plan = await billing_service.get_subscription_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Subscription plan not found")
        return plan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching subscription plan {plan_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscription plan")


@router.put("/plans/{plan_id}", response_model=SubscriptionPlan)
async def update_subscription_plan(
    plan_id: UUID,
    plan_data: SubscriptionPlanUpdate,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Update a subscription plan. (Platform Admin only)"""
    try:
        user_id, user_profile = user_auth

        assert_platform_role(
            user_profile,
            "platform_admin",
            error_message="Platform admin access required to update subscription plans",
        )

        plan = await billing_service.update_subscription_plan(plan_id, plan_data)
        if not plan:
            raise HTTPException(status_code=404, detail="Subscription plan not found")
        return plan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription plan {plan_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update subscription plan"
        )


# Organization Subscriptions
@router.post(
    "/subscription/free",
    response_model=FreePlanActivationResponse,
)
async def activate_free_plan(
    request: FreePlanActivationRequest,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Activate a published free plan for an organization without Stripe."""
    try:
        _, user_profile = user_auth
        assert_billing_access(
            user_profile,
            request.organization_id,
            error_message="Insufficient permissions for billing operations in this organization",
        )
        return await versioned_subscription_service.activate_free_plan(
            request.organization_id, request.plan_version_id
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error activating free plan: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to activate free plan"
        ) from e


@router.post(
    "/checkout/versioned-subscription",
    response_model=VersionedSubscriptionCheckoutResponse,
)
async def create_versioned_subscription_checkout(
    request: VersionedSubscriptionCheckoutRequest,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Create Stripe Checkout for a published paid plan version."""
    try:
        _, user_profile = user_auth
        assert_billing_access(
            user_profile,
            request.organization_id,
            error_message="Insufficient permissions for billing operations in this organization",
        )
        return await versioned_subscription_service.create_paid_checkout(
            request, customer_email=user_profile.email
        )
    except HTTPException:
        raise
    except PlanChangeInProgressError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error creating versioned subscription checkout: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to create subscription checkout"
        ) from e


@router.post(
    "/subscription/plan-change/preview",
    response_model=PlanChangePreview,
)
async def preview_plan_change(
    request: PlanChangePreviewRequest,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Return a read-only explanation of a target plan transition."""
    try:
        _, user_profile = user_auth
        assert_billing_access(
            user_profile,
            request.organization_id,
            error_message="Insufficient permissions for billing operations in this organization",
        )
        return await versioned_subscription_service.preview_plan_change(
            request.organization_id, request.target_plan_version_id
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error previewing plan change: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to preview plan change"
        ) from e


@router.post(
    "/subscription/plan-change/confirm",
    response_model=PlanChangeConfirmationResponse,
)
async def confirm_plan_change(
    request: PlanChangeConfirmRequest,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Apply a confirmed plan transition through Stripe and local state."""
    try:
        _, user_profile = user_auth
        assert_billing_access(
            user_profile,
            request.organization_id,
            error_message="Insufficient permissions for billing operations in this organization",
        )
        return await versioned_subscription_service.confirm_plan_change(
            request, customer_email=user_profile.email
        )
    except HTTPException:
        raise
    except PlanChangeInProgressError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error confirming plan change: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to confirm plan change"
        ) from e


@router.get(
    "/subscription/status/{organization_id}",
    response_model=SubscriptionActivationStatus,
)
async def get_subscription_activation_status(
    organization_id: UUID,
    _: tuple[UUID, UserProfile] = Depends(check_billing_permissions),
):
    """Return the plan-selection state used by onboarding and dashboard routing."""
    try:
        return await versioned_subscription_service.get_activation_status(
            organization_id
        )
    except Exception as e:
        logger.error(
            "Error fetching subscription activation status for %s: %s",
            organization_id,
            e,
        )
        raise HTTPException(
            status_code=500, detail="Failed to fetch subscription activation status"
        ) from e


@router.get(
    "/subscription/{organization_id}", response_model=OrganizationSubscriptionWithPlan
)
async def get_organization_subscription(
    organization_id: UUID,
    _: tuple[UUID, UserProfile] = Depends(check_billing_permissions),
):
    """Get organization subscription details."""
    try:
        subscription = await billing_service.get_organization_subscription(
            organization_id
        )
        if not subscription:
            raise HTTPException(
                status_code=404, detail="Organization subscription not found"
            )
        return subscription
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error fetching organization subscription for {organization_id}: {e}"
        )
        raise HTTPException(
            status_code=500, detail="Failed to fetch organization subscription"
        )


@router.get("/entitlements/{organization_id}", response_model=OrgEntitlements)
async def get_organization_entitlements(
    organization_id: UUID,
    _: tuple[UUID, UserProfile] = Depends(check_billing_permissions),
):
    """Get resolved plan-version entitlements and limits for an organization."""
    try:
        return await entitlement_service.get_org_entitlements(organization_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(
            f"Error fetching entitlements for organization {organization_id}: {e}"
        )
        raise HTTPException(
            status_code=500, detail="Failed to fetch organization entitlements"
        ) from e


@router.post("/subscription/migrate")
async def migrate_subscription_plan(
    request: dict[str, Any],
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Self-service migrate to a newer plan version before grace period ends."""
    try:
        user_id, user_profile = user_auth
        organization_id = request.get("organization_id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required")

        org_id = UUID(str(organization_id))
        assert_billing_access(
            user_profile,
            org_id,
            error_message="Insufficient permissions for billing operations in this organization",
        )

        result = await plan_migration_service.migrate_organization(org_id)
        return {"success": True, **result}
    except PlanChangeInProgressError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Error migrating subscription for org %s: %s", organization_id, exc
        )
        raise HTTPException(
            status_code=500, detail="Failed to migrate subscription plan"
        ) from exc


@router.post("/subscription/checkout", response_model=SubscriptionCheckoutResponse)
async def create_subscription_checkout(
    organization_id: UUID,
    plan_id: UUID,
    success_url: str,
    cancel_url: str,
    user_auth: tuple[UUID, UserProfile] = Depends(check_billing_permissions),
):
    """Create a Stripe checkout session for subscription."""
    try:
        _, user_profile = user_auth
        # Get subscription plan
        plan = await billing_service.get_subscription_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Subscription plan not found")

        # Check if organization already has a subscription
        existing_subscription = await billing_service.get_organization_subscription(
            organization_id
        )
        if existing_subscription:
            raise HTTPException(
                status_code=400, detail="Organization already has a subscription"
            )

        # Get organization details
        organization, error = await organization_service.get_organization_by_id(
            organization_id
        )
        if error:
            raise HTTPException(status_code=500, detail="Failed to fetch organization")

        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")

        # Create or get Stripe customer
        customer = await stripe_service.create_customer(
            email=user_profile.email,
            name=organization.name,
            organization_id=str(organization_id),
            metadata={"plan_id": str(plan_id)},
        )

        # Create checkout session
        session = await stripe_service.create_checkout_session(
            customer_id=customer.id,
            price_id=plan.stripe_price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            mode="subscription",
            metadata={"organization_id": str(organization_id), "plan_id": str(plan_id)},
            trial_period_days=plan.trial_period_days,
        )

        return SubscriptionCheckoutResponse(
            checkout_url=session.url, session_id=session.id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription checkout: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/subscription/portal")
async def create_customer_portal(
    request: dict[str, Any],
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Create a Stripe customer portal session."""
    try:
        user_id, user_profile = user_auth

        # Extract organization_id from request and validate access
        organization_id = request.get("organization_id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required")

        # Check organization access permissions. The 3-way OR is:
        # platform_admin (org-agnostic) OR org_admin on the target
        # org OR `billing:subscribe` permission on the target org.
        # (Same rule as `check_billing_permissions` for path-scoped
        # routes; here the org id is in the JSON body.)
        org_id = UUID(organization_id)
        assert_billing_access(
            user_profile,
            org_id,
            error_message="Insufficient permissions for billing operations in this organization",
        )
        # Extract parameters from request body
        return_url = request.get("return_url")

        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required")
        if not return_url:
            raise HTTPException(status_code=400, detail="return_url is required")

        # Convert organization_id to UUID
        try:
            organization_uuid = UUID(organization_id)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid organization_id format"
            )

        logger.info(f"Creating customer portal for organization {organization_uuid}")

        # Get organization subscription
        subscription = await billing_service.get_organization_subscription(
            organization_uuid
        )
        if not subscription:
            logger.error(f"No subscription found for organization {organization_uuid}")
            raise HTTPException(
                status_code=404, detail="Organization subscription not found"
            )

        if not subscription.stripe_customer_id:
            if (subscription.metadata or {}).get("billing_mode") == "free":
                raise HTTPException(
                    status_code=409,
                    detail="Free plan subscriptions do not have a Stripe billing portal",
                )
            raise HTTPException(
                status_code=404,
                detail="No Stripe billing customer found for organization",
            )

        logger.info(
            f"Found subscription {subscription.id} with customer {subscription.stripe_customer_id}"
        )

        # Validate customer exists in Stripe
        try:
            customer = await stripe_service.get_customer(
                subscription.stripe_customer_id
            )
            logger.info(f"Validated customer {customer.id} exists in Stripe")
        except Exception as e:
            logger.error(
                f"Customer {subscription.stripe_customer_id} not found in Stripe: {e}"
            )
            raise HTTPException(status_code=400, detail="Customer not found in Stripe")

        # Create portal session
        portal_session = await stripe_service.create_portal_session(
            customer_id=subscription.stripe_customer_id, return_url=return_url
        )

        logger.info(f"Created portal session: {portal_session.url}")
        return {"portal_url": portal_session.url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating customer portal: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create customer portal: {str(e)}"
        )


# Credits
@router.get("/credits/{organization_id}", response_model=CreditBalance)
async def get_credit_balance(
    organization_id: UUID,
    _: tuple[UUID, UserProfile] = Depends(check_billing_permissions),
):
    """Get organization credit balance."""
    try:
        return await billing_service.get_credit_balance(organization_id)
    except Exception as e:
        logger.error(f"Error fetching credit balance for {organization_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch credit balance")


@router.get(
    "/credits/{organization_id}/transactions",
    response_model=CreditTransactionsResponse,
)
async def get_credit_transactions(
    organization_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    transaction_type: TransactionType | None = Query(None),
    _: tuple[UUID, UserProfile] = Depends(check_billing_permissions),
):
    """Return the organization's paginated, event-enriched credit ledger."""
    try:
        return await billing_service.get_credit_transactions(
            organization_id,
            page=page,
            page_size=page_size,
            transaction_type=transaction_type,
        )
    except Exception as e:
        logger.error(
            "Error fetching credit transactions for %s: %s", organization_id, e
        )
        raise HTTPException(
            status_code=500, detail="Failed to fetch credit transactions"
        ) from e


@router.get("/credits/{organization_id}/usage", response_model=CreditUsageResponse)
async def get_credit_usage(
    organization_id: UUID,
    _: tuple[UUID, UserProfile] = Depends(check_billing_permissions),
):
    """Return dashboard-ready balances, current-period usage, and ledger rows."""
    try:
        return await billing_service.get_credit_usage(organization_id)
    except Exception as e:
        logger.error("Error fetching credit usage for %s: %s", organization_id, e)
        raise HTTPException(
            status_code=500, detail="Failed to fetch credit usage"
        ) from e


@router.post(
    "/credits/{organization_id}/admin-grants",
    response_model=AdminCreditGrantResponse,
)
async def allocate_admin_credits(
    organization_id: UUID,
    request: AdminCreditGrantRequest,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Allocate non-expiring bonus credits (platform admin only)."""
    try:
        user_id, user_profile = user_auth
        assert_platform_role(
            user_profile,
            "platform_admin",
            error_message="Platform admin access required to allocate credits",
        )
        return await billing_service.grant_admin_credits(
            organization_id=organization_id,
            credits=request.credits,
            created_by=user_id,
            reason=request.reason.strip(),
            idempotency_key=request.idempotency_key,
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("Error allocating admin credits to %s: %s", organization_id, e)
        raise HTTPException(
            status_code=500, detail="Failed to allocate organization credits"
        ) from e


@router.post("/credits/consume", response_model=CreditConsumptionResponse)
async def consume_credits(
    consumption_request: CreditConsumptionRequest,
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Consume credits for an event."""
    try:
        user_id, user_profile = user_auth

        # Check billing permissions for the organization in the request
        assert_billing_access(
            user_profile,
            consumption_request.organization_id,
            error_message="Insufficient permissions for billing operations in this organization",
        )

        return await billing_service.consume_credits(consumption_request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error consuming credits: {e}")
        raise HTTPException(status_code=500, detail="Failed to consume credits")


@router.get("/credit-events", response_model=list[CreditEvent])
async def get_credit_events(active_only: bool = True):
    """Get all credit events."""
    try:
        return await billing_service.get_credit_events(active_only=active_only)
    except Exception as e:
        logger.error(f"Error fetching credit events: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch credit events")


@router.get("/credit-products", response_model=list[CreditProduct])
async def get_credit_products(active_only: bool = True):
    """Get all credit products."""
    try:
        return await billing_service.get_credit_products(active_only=active_only)
    except Exception as e:
        logger.error(f"Error fetching credit products: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch credit products")


@router.post("/credit-products/checkout", response_model=CreditPurchaseResponse)
async def create_credit_purchase_checkout(
    organization_id: UUID,
    product_id: UUID,
    success_url: str,
    cancel_url: str,
    user_auth: tuple[UUID, UserProfile] = Depends(check_billing_permissions),
):
    """Create a Stripe checkout session for credit purchase."""
    try:
        current_user_id, user_profile = user_auth

        # Get credit product
        products = await billing_service.get_credit_products(active_only=True)
        product = next((p for p in products if p.id == product_id), None)
        if not product:
            raise HTTPException(status_code=404, detail="Credit product not found")

        # Credit top-ups are gated on the plan's 'credit_topup_enabled' feature.
        if not await entitlement_service.check_feature(
            organization_id, "credit_topup_enabled"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Credit top-ups are not enabled for your current plan. "
                    "Upgrade your plan to purchase additional credits."
                ),
            )

        # Get organization subscription for customer ID
        subscription = await billing_service.get_organization_subscription(
            organization_id
        )
        if not subscription:
            raise HTTPException(
                status_code=404, detail="Organization subscription not found"
            )

        # Create checkout session
        session = await stripe_service.create_checkout_session(
            customer_id=subscription.stripe_customer_id,
            price_id=product.stripe_price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            mode="payment",
            metadata={
                "organization_id": str(organization_id),
                "product_id": str(product_id),
                "credit_amount": str(product.credit_amount),
            },
        )

        return CreditPurchaseResponse(checkout_url=session.url, session_id=session.id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating credit purchase checkout: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


# Billing History
@router.get("/history/{organization_id}", response_model=list[BillingHistory])
async def get_billing_history(
    organization_id: UUID,
    limit: int = 10,
    _: tuple[UUID, UserProfile] = Depends(check_billing_permissions),
):
    """Get billing history for an organization."""
    try:
        return await billing_service.get_billing_history(organization_id, limit=limit)
    except Exception as e:
        logger.error(f"Error fetching billing history for {organization_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch billing history")


# Billing Summary
@router.get("/summary/{organization_id}", response_model=OrganizationBillingSummary)
async def get_billing_summary(
    organization_id: UUID,
    _: tuple[UUID, UserProfile] = Depends(check_billing_permissions),
):
    """Get comprehensive billing summary for an organization."""
    try:
        summary = await billing_service.get_organization_billing_summary(
            organization_id
        )
        subscription = summary.subscription
        if subscription and subscription.plan_version_id:
            plan_version = (
                await versioned_subscription_service.get_plan_version_for_display(
                    subscription.plan_version_id
                )
            )
            subscription.plan_version = plan_version.model_dump(mode="json")
            summary.amount_due = plan_version.price_amount_cents
        return summary
    except Exception as e:
        logger.error(f"Error fetching billing summary for {organization_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch billing summary")


# Webhooks
@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    try:
        logger.info("Stripe webhook endpoint hit")

        # Get webhook payload and signature
        payload = await request.body()
        signature = request.headers.get("stripe-signature")

        logger.info(f"Webhook payload size: {len(payload)} bytes")
        logger.info(f"Stripe signature present: {signature is not None}")

        if not signature:
            logger.error("Missing Stripe signature")
            raise HTTPException(status_code=400, detail="Missing Stripe signature")

        # Complete processing before returning 2xx. Acknowledging the event
        # before subscription state is persisted prevents Stripe from retrying
        # transient database/provider failures.
        await handle_stripe_webhook(payload, signature)
        return JSONResponse(content={"status": "success"})

    except InvalidStripeWebhook as e:
        logger.warning("Rejected invalid Stripe webhook: %s", e)
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Stripe webhook processing failed")
        raise HTTPException(status_code=500, detail="Webhook processing failed") from e


# Checkout and Payment Management
@router.post("/checkout/subscription", response_model=dict[str, Any])
async def create_subscription_checkout(
    request: dict[str, Any],
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Create a Stripe Checkout session for subscription."""
    try:
        user_id, user_profile = user_auth

        # Extract and validate organization access
        organization_id = request.get("organization_id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required")

        # Check billing permissions for this organization
        org_id = UUID(organization_id)
        assert_billing_access(
            user_profile,
            org_id,
            error_message="Insufficient permissions for billing operations in this organization",
        )
        plan_id = request.get("plan_id")

        if not plan_id:
            raise HTTPException(status_code=400, detail="plan_id is required")

        # Convert plan_id to UUID and get the subscription plan
        try:
            plan_uuid = UUID(plan_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid plan_id format")

        plan = await billing_service.get_subscription_plan(plan_uuid)
        if not plan:
            raise HTTPException(status_code=404, detail="Subscription plan not found")

        # Get organization details
        org_result = (
            billing_service.supabase.table("organizations")
            .select("*")
            .eq("id", organization_id)
            .execute()
        )

        if not org_result.data:
            raise HTTPException(status_code=404, detail="Organization not found")

        org = org_result.data[0]

        # Create or get Stripe customer
        existing_subscription = await billing_service.get_organization_subscription(
            UUID(organization_id)
        )

        if existing_subscription and existing_subscription.stripe_customer_id:
            customer_id = existing_subscription.stripe_customer_id
        else:
            # Create new customer
            customer = await stripe_service.create_customer(
                email=user_profile.email,
                name=org["name"],
                organization_id=organization_id,
            )
            customer_id = customer.id

        # Create checkout session
        checkout_session = await stripe_service.create_subscription_checkout_session(
            price_id=plan.stripe_price_id,
            customer_id=customer_id,
            organization_id=organization_id,
            plan_id=plan_id,
        )

        return {"session_url": checkout_session.url, "session_id": checkout_session.id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription checkout: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/checkout/credits", response_model=dict[str, Any])
async def create_credits_checkout(
    request: dict[str, Any],
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Create a Stripe Checkout session for credit purchase."""
    try:
        user_id, user_profile = user_auth

        # Extract and validate organization access
        product_id = request.get("product_id")
        organization_id = request.get("organization_id")

        if not product_id or not organization_id:
            raise HTTPException(
                status_code=400, detail="product_id and organization_id are required"
            )

        # Check billing permissions for this organization
        org_id = UUID(organization_id)
        assert_billing_access(
            user_profile,
            org_id,
            error_message="Insufficient permissions for billing operations in this organization",
        )

        # Get the credit product
        products = await billing_service.get_credit_products()
        product = next((p for p in products if str(p.id) == product_id), None)

        if not product:
            raise HTTPException(status_code=404, detail="Credit product not found")

        # Credit top-ups are gated on the plan's 'credit_topup_enabled' feature.
        if not await entitlement_service.check_feature(org_id, "credit_topup_enabled"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Credit top-ups are not enabled for your current plan. "
                    "Upgrade your plan to purchase additional credits."
                ),
            )

        # Get organization details
        org_result = (
            billing_service.supabase.table("organizations")
            .select("*")
            .eq("id", organization_id)
            .execute()
        )

        if not org_result.data:
            raise HTTPException(status_code=404, detail="Organization not found")

        org = org_result.data[0]

        # Get or create customer
        existing_subscription = await billing_service.get_organization_subscription(
            UUID(organization_id)
        )

        if existing_subscription and existing_subscription.stripe_customer_id:
            customer_id = existing_subscription.stripe_customer_id
        else:
            customer = await stripe_service.create_customer(
                email=user_profile.email,
                name=org["name"],
                organization_id=organization_id,
            )
            customer_id = customer.id

        # Create checkout session for one-time payment
        checkout_session = await stripe_service.create_credits_checkout_session(
            price_id=product.stripe_price_id,
            customer_id=customer_id,
            organization_id=organization_id,
            product_id=product_id,
            credit_amount=product.credit_amount,
        )

        return {"session_url": checkout_session.url, "session_id": checkout_session.id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating credits checkout: {e}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/portal", response_model=dict[str, str])
async def create_customer_portal_session(
    request: dict[str, Any],
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Create a Stripe Customer Portal session for subscription management."""
    try:
        user_id, user_profile = user_auth

        # Extract and validate organization access
        organization_id = request.get("organization_id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required")

        # Check billing permissions for this organization
        org_id = UUID(organization_id)
        assert_billing_access(
            user_profile,
            org_id,
            error_message="Insufficient permissions for billing operations in this organization",
        )

        # Get organization subscription
        subscription = await billing_service.get_organization_subscription(
            UUID(organization_id)
        )

        if not subscription:
            raise HTTPException(
                status_code=404, detail="No subscription found for organization"
            )
        if not subscription.stripe_customer_id:
            if (subscription.metadata or {}).get("billing_mode") == "free":
                raise HTTPException(
                    status_code=409,
                    detail="Free plan subscriptions do not have a Stripe billing portal",
                )
            raise HTTPException(
                status_code=404,
                detail="No Stripe billing customer found for organization",
            )

        # Create customer portal session
        portal_session = await stripe_service.create_customer_portal_session(
            customer_id=subscription.stripe_customer_id, organization_id=organization_id
        )

        return {"portal_url": portal_session.url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating customer portal session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create portal session")


@router.post("/subscription/cancel")
async def cancel_subscription(
    request: dict[str, Any],
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Cancel subscription at the end of the current period."""
    try:
        user_id, user_profile = user_auth

        # Extract and validate organization access
        organization_id = request.get("organization_id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required")

        # Check billing permissions for this organization
        org_id = UUID(organization_id)
        assert_billing_access(
            user_profile,
            org_id,
            error_message="Insufficient permissions for billing operations in this organization",
        )

        # Get organization subscription
        subscription = await billing_service.get_organization_subscription(
            UUID(organization_id)
        )

        if not subscription or not subscription.stripe_subscription_id:
            raise HTTPException(status_code=404, detail="No active subscription found")

        # Cancel subscription in Stripe
        await stripe_service.cancel_subscription(subscription.stripe_subscription_id)

        # Update local subscription record
        await billing_service.update_organization_subscription(
            UUID(organization_id),
            OrganizationSubscriptionUpdate(cancel_at_period_end=True),
        )

        return {
            "message": "Subscription will be cancelled at the end of the current period"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


@router.post("/subscription/reactivate")
async def reactivate_subscription(
    request: dict[str, Any],
    user_auth: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
):
    """Reactivate a cancelled subscription."""
    try:
        user_id, user_profile = user_auth

        # Extract and validate organization access
        organization_id = request.get("organization_id")
        if not organization_id:
            raise HTTPException(status_code=400, detail="organization_id is required")

        # Check billing permissions for this organization
        org_id = UUID(organization_id)
        assert_billing_access(
            user_profile,
            org_id,
            error_message="Insufficient permissions for billing operations in this organization",
        )

        # Get organization subscription
        subscription = await billing_service.get_organization_subscription(
            UUID(organization_id)
        )

        if not subscription or not subscription.stripe_subscription_id:
            raise HTTPException(status_code=404, detail="No subscription found")

        # Reactivate subscription in Stripe
        stripe_subscription = await stripe_service.reactivate_subscription(
            subscription.stripe_subscription_id
        )

        # Reactivating a scheduled cancellation to Free invalidates that
        # pending-plan marker; keeping it would block later plan selections.
        update_fields: dict[str, Any] = {"cancel_at_period_end": False}
        raw_metadata = getattr(subscription, "metadata", None)
        metadata = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}
        pending_plan_change = metadata.get("pending_plan_change") or {}
        if isinstance(stripe_subscription, dict):
            stripe_schedule = stripe_subscription.get("schedule")
        else:
            stripe_schedule = getattr(stripe_subscription, "schedule", None)
        target_billing_mode = pending_plan_change.get("target_billing_mode")
        if pending_plan_change.get("status") == "scheduled" and (
            target_billing_mode == "free"
            or (target_billing_mode is None and stripe_schedule is None)
        ):
            metadata.pop("pending_plan_change", None)
            update_fields["metadata"] = metadata

        # Update local subscription record only after Stripe confirms reactivation.
        await billing_service.update_organization_subscription(
            UUID(organization_id),
            OrganizationSubscriptionUpdate(**update_fields),
        )

        return {"message": "Subscription reactivated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reactivating subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to reactivate subscription")
