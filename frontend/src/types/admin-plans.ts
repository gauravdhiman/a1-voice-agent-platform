/**
 * Types for platform-admin plan catalog and entitlement management APIs.
 */

export type PlanVersionStatus = "draft" | "published" | "deprecated" | "retired";

export type EntitlementKind = "limit" | "feature";

export type EntitlementValueType =
  | "integer"
  | "boolean"
  | "unlimited"
  | "decimal"
  | "enum"
  | "duration_seconds";

export type MigrationMode =
  | "new_signups_only"
  | "grace_then_optional"
  | "grace_then_required"
  | "immediate_required";

export type StripeMigrationTiming =
  | "immediate"
  | "at_period_end"
  | "at_grace_end";

export interface EntitlementDefinition {
  key: string;
  kind: EntitlementKind;
  display_name: string;
  value_type: EntitlementValueType;
  unit?: string | null;
  validation_schema?: Record<string, unknown>;
  enforcement_handler: string;
  default_enforcement?: string;
  default_when_absent?: Record<string, unknown> | null;
  is_active: boolean;
  description?: string | null;
}

export interface EntitlementDefinitionUpdate {
  display_name?: string;
  description?: string | null;
  is_active?: boolean;
}

export interface PlanProduct {
  id: string;
  slug: string;
  display_name: string;
  description?: string | null;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PlanVersionEntitlement {
  id: string;
  entitlement_key: string;
  value: Record<string, unknown>;
}

export interface PlanVersionDetail {
  id: string;
  plan_product_id: string;
  version_number: number;
  status: PlanVersionStatus;
  display_label?: string | null;
  price_amount_cents: number;
  currency: string;
  billing_interval: string;
  trial_period_days?: number | null;
  stripe_product_id?: string | null;
  stripe_price_id?: string | null;
  is_current_for_signup: boolean;
  published_at?: string | null;
  legacy_subscription_plan_id?: string | null;
  entitlements: PlanVersionEntitlement[];
  created_at: string;
  updated_at: string;
}

export interface PlanProductWithVersions extends PlanProduct {
  versions: PlanVersionDetail[];
}

export interface PlanProductCreate {
  slug: string;
  display_name: string;
  description?: string;
  sort_order?: number;
}

export interface PlanVersionEntitlementInput {
  entitlement_key: string;
  value: Record<string, unknown>;
}

export interface PlanVersionDraftCreate {
  display_label?: string;
  price_amount_cents?: number;
  currency?: string;
  billing_interval?: string;
  trial_period_days?: number | null;
  stripe_product_id?: string | null;
  entitlements?: PlanVersionEntitlementInput[];
}

export interface PlanVersionDraftUpdate {
  display_label?: string;
  price_amount_cents?: number;
  currency?: string;
  billing_interval?: string;
  trial_period_days?: number | null;
  stripe_product_id?: string | null;
  entitlements?: PlanVersionEntitlementInput[];
}

export interface PlanVersionCloneRequest {
  display_label?: string;
  price_amount_cents?: number;
}

export interface PlanVersionPublishRequest {
  migration_mode?: MigrationMode;
  grace_period_days?: number | null;
  auto_migrate_on_expiry?: boolean;
  allow_indefinite_legacy?: boolean;
  stripe_migration_timing?: StripeMigrationTiming;
  compliance_policy?: string | null;
}

export interface PlanVersionPublishResult {
  plan_version_id: string;
  from_plan_version_id?: string | null;
  publish_event_id: string;
  stripe_price_id: string;
  migration_rows_created: number;
  subscribers_migrated_immediately: number;
}
