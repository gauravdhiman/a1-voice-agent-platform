/**
 * Billing-related type definitions
 */

// Enums
export type SubscriptionStatus =
  | "trial"
  | "active"
  | "past_due"
  | "cancelled"
  | "expired"
  | "incomplete"
  | "incomplete_expired";

export type TransactionType =
  "earned" | "purchased" | "consumed" | "expired" | "refunded";

export type TransactionSource =
  | "subscription"
  | "purchase"
  | "event_consumption"
  | "expiry"
  | "refund"
  | "admin_adjustment";

export type BillingStatus =
  "pending" | "paid" | "failed" | "refunded" | "cancelled";

export type PlanInterval = "monthly" | "annual";
export type BillingMode = "free" | "paid";
export type CreditGrantPolicy = "recurring" | "one_time";

// Subscription Plan interfaces
export interface SubscriptionPlan {
  id: string;
  name: string;
  description: string | null;
  stripe_price_id: string;
  stripe_product_id: string;
  price_amount: number; // in cents
  currency: string;
  interval: PlanInterval;
  interval_count: number;
  included_credits: number;
  max_users: number | null;
  features: Record<string, unknown> | null;
  is_active: boolean;
  trial_period_days: number | null;
  created_at: string;
  updated_at: string;
}

export interface SubscriptionPlanCreate {
  name: string;
  description?: string;
  stripe_price_id: string;
  stripe_product_id: string;
  price_amount: number;
  currency?: string;
  interval: PlanInterval;
  interval_count?: number;
  included_credits?: number;
  max_users?: number;
  features?: Record<string, unknown>;
  is_active?: boolean;
  trial_period_days?: number;
}

export interface SubscriptionPlanUpdate {
  name?: string;
  description?: string;
  price_amount?: number;
  included_credits?: number;
  max_users?: number;
  features?: Record<string, unknown>;
  is_active?: boolean;
  trial_period_days?: number;
}

// Organization Subscription interfaces
export interface OrganizationSubscription {
  id: string;
  organization_id: string;
  subscription_plan_id: string | null;
  plan_version_id: string | null;
  stripe_subscription_id: string | null;
  stripe_customer_id: string | null;
  status: SubscriptionStatus;
  current_period_start: string | null;
  current_period_end: string | null;
  trial_start: string | null;
  trial_end: string | null;
  cancel_at_period_end: boolean;
  cancelled_at: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface OrganizationSubscriptionWithPlan extends OrganizationSubscription {
  plan: SubscriptionPlan | null;
}

export interface OrganizationSubscriptionCreate {
  organization_id: string;
  subscription_plan_id: string;
  stripe_customer_id?: string;
}

/** Published immutable plan version displayed during founder onboarding. */
export interface CustomerPlanVersion {
  id: string;
  plan_product_id: string;
  /** Catalog display order; does not determine whether a target is eligible. */
  tier_rank: number;
  product_slug: string;
  product_name: string;
  product_description: string | null;
  version_number: number;
  display_label: string | null;
  billing_mode: BillingMode;
  credit_grant_policy: CreditGrantPolicy;
  price_amount_cents: number;
  currency: string;
  billing_interval: PlanInterval | string;
  trial_period_days: number | null;
  stripe_price_id: string | null;
  entitlements: Record<string, Record<string, unknown>>;
}

export type PlanChangeEffectiveMode = "checkout" | "immediate" | "period_end";

export interface PlanChangePreview {
  transition_id: string;
  organization_id: string;
  current_plan: CustomerPlanVersion;
  target_plan: CustomerPlanVersion;
  effective_mode: PlanChangeEffectiveMode;
  effective_at: string | null;
  price_delta_cents: number;
  credit_delta: number | null;
  proration_behavior: string;
  purchased_credits_preserved: boolean;
}

export interface PlanChangeConfirmationResponse {
  status: "checkout_pending" | "applied" | "scheduled";
  target_plan_version_id: string;
  effective_at: string | null;
  checkout_url?: string | null;
  session_id?: string | null;
}

/** Subscription row returned after a versioned free activation. */
export interface VersionedSubscriptionRecord {
  id: string;
  organization_id: string;
  subscription_plan_id: string | null;
  plan_version_id: string;
  stripe_subscription_id: string | null;
  stripe_customer_id: string | null;
  status: SubscriptionStatus;
  current_period_start: string | null;
  current_period_end: string | null;
  metadata: Record<string, unknown>;
}

/** Result of an idempotent free-plan activation. */
export interface FreePlanActivationResponse {
  subscription: VersionedSubscriptionRecord;
  created: boolean;
}

/** Request sent to the versioned paid checkout endpoint. */
export interface VersionedSubscriptionCheckoutRequest {
  organization_id: string;
  plan_version_id: string;
  success_url: string;
  cancel_url: string;
}

/** Redirect details returned by Stripe Checkout creation. */
export interface VersionedSubscriptionCheckoutResponse {
  checkout_url: string;
  session_id: string;
  plan_version_id: string;
}

export type SubscriptionActivationState =
  | "unselected"
  | "checkout_pending"
  | "active"
  | "trial"
  | "past_due"
  | "cancelled";

/** Status used to decide whether the onboarding flow may finish. */
export interface SubscriptionActivationStatus {
  organization_id: string;
  state: SubscriptionActivationState;
  subscription_id: string | null;
  plan_version_id: string | null;
  billing_mode: BillingMode | null;
  subscription_status: SubscriptionStatus | null;
}

// Credit Event interfaces
export interface CreditEvent {
  id: string;
  name: string;
  description: string | null;
  credit_cost: number;
  category: string;
  is_active: boolean;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface CreditEventCreate {
  name: string;
  description?: string;
  credit_cost: number;
  category: string;
  is_active?: boolean;
  metadata?: Record<string, unknown>;
}

// Credit Transaction interfaces
export interface CreditTransaction {
  id: string;
  organization_id: string;
  transaction_type: TransactionType;
  amount: number;
  balance_after: number;
  source: TransactionSource;
  source_id: string | null;
  credit_event_id: string | null;
  expires_at: string | null;
  stripe_payment_intent_id: string | null;
  description: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface CreditTransactionWithEvent extends CreditTransaction {
  credit_event: CreditEvent | null;
}

export interface CreditUsageCategory {
  category: string;
  credits_consumed: number;
  transaction_count: number;
}

export interface CreditTransactionsResponse {
  items: CreditTransactionWithEvent[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CreditUsageResponse {
  organization_id: string;
  balance: CreditBalance;
  period_start: string | null;
  period_end: string | null;
  period_credits_granted: number;
  period_credits_used: number;
  period_credits_remaining: number;
  usage_by_category: CreditUsageCategory[];
  transactions: CreditTransactionWithEvent[];
}

// Credit Product interfaces
export interface CreditProduct {
  id: string;
  name: string;
  description: string | null;
  stripe_price_id: string;
  stripe_product_id: string;
  credit_amount: number;
  price_amount: number; // in cents
  currency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreditProductCreate {
  name: string;
  description?: string;
  stripe_price_id: string;
  stripe_product_id: string;
  credit_amount: number;
  price_amount: number;
  currency?: string;
  is_active?: boolean;
}

// Billing History interfaces
export interface BillingHistory {
  id: string;
  organization_id: string;
  stripe_invoice_id: string | null;
  stripe_payment_intent_id: string | null;
  amount: number; // in cents
  currency: string;
  status: BillingStatus;
  description: string | null;
  invoice_url: string | null;
  receipt_url: string | null;
  billing_reason: string | null;
  metadata: Record<string, unknown> | null;
  paid_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BillingHistoryCreate {
  organization_id: string;
  stripe_invoice_id?: string;
  stripe_payment_intent_id?: string;
  amount: number;
  currency?: string;
  status: BillingStatus;
  description?: string;
  invoice_url?: string;
  receipt_url?: string;
  billing_reason?: string;
  metadata?: Record<string, unknown>;
  paid_at?: string;
}

// API Response interfaces
export interface SubscriptionCheckoutResponse {
  checkout_url: string;
  session_id: string;
}

export interface CreditPurchaseResponse {
  checkout_url: string;
  session_id: string;
}

export interface OrganizationBillingSummary {
  organization_id: string;
  subscription: OrganizationSubscriptionWithPlan | null;
  credit_balance: number;
  current_period_usage: number;
  next_billing_date: string | null;
  amount_due: number | null;
}

export interface CreditBalance {
  total_credits: number;
  subscription_credits: number;
  admin_granted_credits?: number;
  purchased_credits: number;
  expiring_soon: number;
  expires_at: string | null;
}

export interface AdminCreditGrantRequest {
  credits: number;
  reason: string;
  idempotency_key?: string;
}

export interface AdminCreditGrantResponse {
  organization_id: string;
  credits: number;
  created: boolean;
  grant_id?: string | null;
  balance: CreditBalance;
  transaction: CreditTransaction;
}

export interface UsageStats {
  period_start: string;
  period_end: string;
  total_events: number;
  credits_consumed: number;
  events_by_category: Record<string, number>;
  credits_by_category: Record<string, number>;
}

// Credit Consumption interfaces
export interface CreditConsumptionRequest {
  organization_id: string;
  event_name: string;
  quantity?: number;
  metadata?: Record<string, unknown>;
}

export interface CreditConsumptionResponse {
  success: boolean;
  credits_consumed: number;
  balance_after: number;
  transaction_id: string;
}

// Plan entitlements (version-bound limits and migration status)
export type PlanMigrationStatus =
  "pending" | "grace_active" | "migrated" | "declined_legacy" | "cancelled";

export interface OrgPlanMigrationInfo {
  migration_id: string;
  from_plan_version_id: string;
  to_plan_version_id: string;
  status: PlanMigrationStatus;
  grace_period_ends_at: string | null;
  target_plan_version_label: string | null;
  allow_indefinite_legacy: boolean;
  can_self_migrate: boolean;
}

export interface ResolvedEntitlement {
  key: string;
  kind: "limit" | "feature";
  assigned: boolean;
  raw_value: Record<string, unknown> | null;
  effective_value: unknown;
  is_unlimited: boolean;
}

export interface OrgEntitlements {
  organization_id: string;
  plan_version_id: string;
  plan_product_slug: string;
  plan_version_number: number;
  plan_version_label: string | null;
  is_legacy_version: boolean;
  is_entitled: boolean;
  cancel_at_period_end: boolean;
  access_until: string | null;
  limits: Record<string, ResolvedEntitlement>;
  features: Record<string, ResolvedEntitlement>;
  migration: OrgPlanMigrationInfo | null;
}

export interface PlanMigrationResponse {
  success: boolean;
  migration_id: string;
  to_plan_version_id: string;
  status: string;
}

// UI Helper interfaces
export interface PlanFeature {
  name: string;
  included: boolean;
  value?: string | number;
  description?: string;
}

export interface PlanComparison {
  plans: SubscriptionPlan[];
  features: string[];
  recommended?: string; // plan id
}

export interface BillingAlert {
  type: "info" | "warning" | "error" | "success";
  title: string;
  message: string;
  action?: {
    label: string;
    url: string;
  };
}

// Utility functions for billing
export const formatPrice = (
  amount: number,
  currency: string = "USD",
): string => {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency.toUpperCase(),
  }).format(amount / 100);
};

export const formatCredits = (credits: number): string => {
  return new Intl.NumberFormat("en-US").format(credits);
};

export const getSubscriptionStatusColor = (
  status: SubscriptionStatus,
): string => {
  switch (status) {
    case "active":
      return "green";
    case "trial":
      return "blue";
    case "past_due":
      return "yellow";
    case "cancelled":
    case "expired":
      return "red";
    default:
      return "gray";
  }
};

export const getSubscriptionStatusLabel = (
  status: SubscriptionStatus,
): string => {
  switch (status) {
    case "trial":
      return "Trial";
    case "active":
      return "Active";
    case "past_due":
      return "Past Due";
    case "cancelled":
      return "Cancelled";
    case "expired":
      return "Expired";
    case "incomplete":
      return "Incomplete";
    case "incomplete_expired":
      return "Incomplete Expired";
    default:
      return "Unknown";
  }
};

export const getBillingStatusColor = (status: BillingStatus): string => {
  switch (status) {
    case "paid":
      return "green";
    case "pending":
      return "yellow";
    case "failed":
      return "red";
    case "refunded":
      return "blue";
    case "cancelled":
      return "gray";
    default:
      return "gray";
  }
};

export const getBillingStatusLabel = (status: BillingStatus): string => {
  switch (status) {
    case "pending":
      return "Pending";
    case "paid":
      return "Paid";
    case "failed":
      return "Failed";
    case "refunded":
      return "Refunded";
    case "cancelled":
      return "Cancelled";
    default:
      return "Unknown";
  }
};
