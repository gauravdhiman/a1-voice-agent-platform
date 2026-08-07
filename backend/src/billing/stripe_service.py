"""
Stripe integration service for payment processing.
"""

import logging
from typing import Any, Optional

import stripe

from shared.config import settings

logger = logging.getLogger(__name__)

# Initialize Stripe with secret key
stripe.api_key = getattr(settings, "stripe_secret_key", None)


class StripeService:
    """Service for handling Stripe API operations."""

    def __init__(self):
        """Initialize Stripe service."""
        if not stripe.api_key:
            logger.warning(
                "Stripe API key not configured. Stripe functionality will be disabled."
            )

        # Set frontend URL for redirects
        self.frontend_url = settings.app_base_url or "http://localhost:3000"

    async def create_customer(
        self,
        email: str,
        name: str,
        organization_id: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> stripe.Customer:
        """Create a new Stripe customer."""
        try:
            customer_metadata = {
                "organization_id": str(organization_id),
                **(metadata or {}),
            }

            customer = stripe.Customer.create(
                email=email, name=name, metadata=customer_metadata
            )

            logger.info(
                f"Created Stripe customer {customer.id} for organization {organization_id}"
            )
            return customer

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise

    async def get_customer(self, customer_id: str) -> stripe.Customer:
        """Retrieve a Stripe customer."""
        try:
            return stripe.Customer.retrieve(customer_id)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve Stripe customer {customer_id}: {e}")
            raise

    async def update_customer(self, customer_id: str, **kwargs) -> stripe.Customer:
        """Update a Stripe customer."""
        try:
            return stripe.Customer.modify(customer_id, **kwargs)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update Stripe customer {customer_id}: {e}")
            raise

    async def create_price(
        self,
        product_id: str,
        unit_amount: int,
        currency: str = "USD",
        interval: str = "month",
        metadata: Optional[dict[str, Any]] = None,
    ) -> stripe.Price:
        """Create an immutable Stripe Price for a published plan version.

        Args:
            product_id: Stripe Product ID the price belongs to.
            unit_amount: Price in smallest currency unit (cents).
            currency: ISO currency code (default USD).
            interval: Billing interval — ``month`` or ``year``.
            metadata: Optional metadata stored on the Stripe Price.

        Returns:
            Created Stripe Price object.

        Raises:
            stripe.error.StripeError: When Stripe API call fails.
        """
        try:
            price = stripe.Price.create(
                product=product_id,
                unit_amount=unit_amount,
                currency=currency.lower(),
                recurring={"interval": interval},
                metadata=metadata or {},
            )
            logger.info(
                "Created Stripe price %s for product %s (%s %s)",
                price.id,
                product_id,
                unit_amount,
                currency,
            )
            return price
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe price for product {product_id}: {e}")
            raise

    async def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        mode: str = "subscription",
        metadata: Optional[dict[str, Any]] = None,
        trial_period_days: Optional[int] = None,
    ) -> stripe.checkout.Session:
        """Create a Stripe checkout session."""
        try:
            session_params = {
                "customer": customer_id,
                "payment_method_types": ["card"],
                "line_items": [{"price": price_id, "quantity": 1}],
                "mode": mode,
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": metadata or {},
            }

            if mode == "subscription":
                subscription_data = {}
                if trial_period_days:
                    subscription_data["trial_period_days"] = trial_period_days
                if metadata:
                    subscription_data["metadata"] = metadata
                if subscription_data:
                    session_params["subscription_data"] = subscription_data

            session = stripe.checkout.Session.create(**session_params)

            logger.info(
                f"Created checkout session {session.id} for customer {customer_id}"
            )
            return session

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise

    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_period_days: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> stripe.Subscription:
        """Create a Stripe subscription."""
        try:
            subscription_params = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "metadata": metadata or {},
            }

            if trial_period_days:
                subscription_params["trial_period_days"] = trial_period_days

            subscription = stripe.Subscription.create(**subscription_params)

            logger.info(
                f"Created subscription {subscription.id} for customer {customer_id}"
            )
            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription: {e}")
            raise

    async def get_subscription(self, subscription_id: str) -> stripe.Subscription:
        """Retrieve a Stripe subscription."""
        try:
            return stripe.Subscription.retrieve(subscription_id)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve subscription {subscription_id}: {e}")
            raise

    async def update_subscription(
        self, subscription_id: str, **kwargs
    ) -> stripe.Subscription:
        """Update a Stripe subscription."""
        try:
            return stripe.Subscription.modify(subscription_id, **kwargs)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update subscription {subscription_id}: {e}")
            raise

    async def change_subscription_price(
        self,
        subscription_id: str,
        new_price_id: str,
        *,
        at_period_end: bool = False,
    ) -> stripe.Subscription:
        """Swap the subscription line item to a new Stripe Price.

        Used when migrating subscribers to a new plan version. When
        ``at_period_end`` is True, the price change applies at the next billing
        cycle with no proration.

        Args:
            subscription_id: Stripe subscription ID.
            new_price_id: Target Stripe Price ID from the new plan version.
            at_period_end: If True, defer price change to next renewal.

        Returns:
            Updated Stripe Subscription object.
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            items = subscription.get("items", {}).get("data", [])
            if not items:
                raise ValueError(
                    f"Subscription {subscription_id} has no line items to update"
                )
            item_id = items[0]["id"]
            modify_params: dict[str, Any] = {
                "items": [{"id": item_id, "price": new_price_id}],
                "proration_behavior": "none",
            }
            if at_period_end:
                modify_params["billing_cycle_anchor"] = "unchanged"

            updated = stripe.Subscription.modify(subscription_id, **modify_params)
            logger.info(
                "Changed Stripe subscription %s to price %s (at_period_end=%s)",
                subscription_id,
                new_price_id,
                at_period_end,
            )
            return updated
        except stripe.error.StripeError as e:
            logger.error(
                f"Failed to change subscription {subscription_id} price: {e}"
            )
            raise

    async def cancel_subscription(
        self, subscription_id: str, at_period_end: bool = True
    ) -> stripe.Subscription:
        """Cancel a Stripe subscription."""
        try:
            if at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id, cancel_at_period_end=True
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)

            logger.info(
                f"Cancelled subscription {subscription_id} (at_period_end={at_period_end})"
            )
            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription {subscription_id}: {e}")
            raise

    async def create_portal_session(
        self, customer_id: str, return_url: str
    ) -> stripe.billing_portal.Session:
        """Create a Stripe customer portal session."""
        try:
            logger.info(
                f"Creating portal session for customer {customer_id} with return URL {return_url}"
            )

            session = stripe.billing_portal.Session.create(
                customer=customer_id, return_url=return_url
            )

            logger.info(
                f"Created portal session {session.id} for customer {customer_id}: {session.url}"
            )
            return session

        except stripe.error.StripeError as e:
            logger.error(
                f"Stripe error creating portal session for customer {customer_id}: {e}"
            )
            logger.error(f"Stripe error type: {type(e)}")
            logger.error(f"Stripe error code: {getattr(e, 'code', 'N/A')}")
            logger.error(f"Stripe error param: {getattr(e, 'param', 'N/A')}")
            raise

    async def get_invoice(self, invoice_id: str) -> stripe.Invoice:
        """Retrieve a Stripe invoice."""
        try:
            return stripe.Invoice.retrieve(invoice_id)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve invoice {invoice_id}: {e}")
            raise

    async def get_payment_intent(self, payment_intent_id: str) -> stripe.PaymentIntent:
        """Retrieve a Stripe payment intent."""
        try:
            return stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve payment intent {payment_intent_id}: {e}")
            raise

    async def list_customer_invoices(
        self, customer_id: str, limit: int = 10
    ) -> list[stripe.Invoice]:
        """list invoices for a customer."""
        try:
            invoices = stripe.Invoice.list(customer=customer_id, limit=limit)
            return invoices.data
        except stripe.error.StripeError as e:
            logger.error(f"Failed to list invoices for customer {customer_id}: {e}")
            raise

    def construct_webhook_event(
        self, payload: bytes, signature: str, webhook_secret: str
    ) -> stripe.Event:
        """Construct and verify a Stripe webhook event."""
        try:
            return stripe.Webhook.construct_event(payload, signature, webhook_secret)
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise

    async def reactivate_subscription(
        self, subscription_id: str
    ) -> stripe.Subscription:
        """Reactivate a cancelled subscription."""
        try:
            subscription = stripe.Subscription.modify(
                subscription_id, cancel_at_period_end=False
            )

            logger.info(f"Reactivated subscription: {subscription_id}")
            return subscription

        except stripe.error.StripeError as e:
            logger.error(
                f"Stripe error reactivating subscription {subscription_id}: {e}"
            )
            raise

    async def create_subscription_checkout_session(
        self, price_id: str, customer_id: str, organization_id: str, plan_id: str
    ) -> stripe.checkout.Session:
        """Create a Stripe Checkout session for subscription."""
        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                customer=customer_id,
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                success_url=f"{self.frontend_url}/billing/success?org_id={organization_id}&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{self.frontend_url}/billing/cancel?org_id={organization_id}",
                metadata={
                    "organization_id": organization_id,
                    "plan_id": plan_id,
                    "type": "subscription",
                },
                subscription_data={
                    "metadata": {"organization_id": organization_id, "plan_id": plan_id}
                },
                allow_promotion_codes=True,
                billing_address_collection="required",
                customer_update={"shipping": "auto"},
            )

            logger.info(f"Created subscription checkout session: {session.id}")
            return session

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating subscription checkout: {e}")
            raise

    async def create_credits_checkout_session(
        self, price_id: str, customer_id: str, organization_id: str, product_id: str
    ) -> stripe.checkout.Session:
        """Create a Stripe Checkout session for credit purchase."""
        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                customer=customer_id,
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                success_url=f"{self.frontend_url}/billing/success?org_id={organization_id}&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{self.frontend_url}/billing/cancel?org_id={organization_id}",
                metadata={
                    "organization_id": organization_id,
                    "product_id": product_id,
                    "type": "credits",
                },
                payment_intent_data={
                    "metadata": {
                        "organization_id": organization_id,
                        "product_id": product_id,
                        "type": "credits",
                    }
                },
                allow_promotion_codes=True,
                billing_address_collection="required",
            )

            logger.info(f"Created credits checkout session: {session.id}")
            return session

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating credits checkout: {e}")
            raise

    async def create_customer_portal_session(
        self, customer_id: str, organization_id: str
    ) -> stripe.billing_portal.Session:
        """Create a Stripe Customer Portal session."""
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id, return_url=f"{self.frontend_url}/billing"
            )

            logger.info(f"Created customer portal session for customer: {customer_id}")
            return session

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer portal: {e}")
            raise


# Global instance
stripe_service = StripeService()
