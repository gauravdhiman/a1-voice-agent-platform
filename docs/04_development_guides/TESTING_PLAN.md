# Comprehensive Testing Plan for AI Voice Agent Platform

## Executive Summary

This document outlines a systematic approach to achieve **95% test coverage** for the AI Voice Agent Platform. The platform currently has minimal test coverage (~1 test file) across ~165+ source files. This plan prioritizes backend unit tests with full mocking of external services.

### Current State Analysis

| Component | Source Files | Existing Tests | Current Coverage |
|-----------|--------------|----------------|------------------|
| **Backend** | ~42 Python files | 1 file (`test_rbac.py`) | Minimal |
| **Shared** | ~21 Python files | 0 | None |
| **Worker** | 2 Python files | 0 | None |
| **Frontend** | ~100+ TypeScript files | 0 | None |

### Testing Strategy Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **External Services** | Full mocking | Fast tests, no external dependencies |
| **Database** | Mocked Supabase client | Pure unit tests, no test DB needed |
| **Test Structure** | Mirror source structure | Easy to find and maintain tests |
| **Priority** | Backend first | Python services are core business logic |

---

## Testing Pyramid

```
┌─────────────────────────────────────────────────────────────────┐
│                    Testing Pyramid                              │
├─────────────────────────────────────────────────────────────────┤
│                      E2E Tests (5%)                             │
│                    ┌───────────────┐                            │
│                    │  Playwright   │  (Future - Phase 4)        │
│                    └───────────────┘                            │
│                                                                 │
│               Integration Tests (15%)                           │
│              ┌───────────────────────┐                          │
│              │  API Route Testing    │  (Future - Phase 2)      │
│              │  Multi-service flows  │                          │
│              └───────────────────────┘                          │
│                                                                 │
│                Unit Tests (80%)                                 │
│    ┌─────────────────────────────────────────────────┐          │
│    │  Service layer tests (mocked Supabase/Stripe)   │  NOW     │
│    │  Utility function tests                         │          │
│    │  Model validation tests                         │          │
│    └─────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Backend Unit Tests (Primary Focus)

### Directory Structure

```
backend/
├── tests/
│   ├── conftest.py                    # Shared fixtures, mocks
│   ├── pytest.ini                     # Pytest configuration
│   │
│   ├── fixtures/                      # Test data factories
│   │   ├── __init__.py
│   │   ├── user_fixtures.py
│   │   ├── organization_fixtures.py
│   │   ├── billing_fixtures.py
│   │   └── voice_agent_fixtures.py
│   │
│   ├── mocks/                         # Mock implementations
│   │   ├── __init__.py
│   │   ├── mock_supabase.py           # Supabase client mock
│   │   ├── mock_stripe.py             # Stripe service mock
│   │   └── mock_resend.py             # Resend email mock
│   │
│   ├── auth/                          # Auth module tests
│   │   ├── __init__.py
│   │   ├── test_service.py            # AuthService tests
│   │   ├── test_routes.py             # Auth API routes
│   │   ├── test_models.py             # Pydantic model tests
│   │   └── test_middleware.py         # Auth middleware tests
│   │
│   ├── billing/                       # Billing module tests
│   │   ├── __init__.py
│   │   ├── test_service.py            # BillingService tests
│   │   ├── test_stripe_service.py     # StripeService tests
│   │   ├── test_webhook_handler.py    # Webhook handler tests
│   │   ├── test_routes.py             # Billing API routes
│   │   └── test_models.py             # Billing model tests
│   │
│   ├── rbac/                          # RBAC module tests
│   │   ├── __init__.py
│   │   ├── roles/
│   │   │   ├── __init__.py
│   │   │   ├── test_service.py
│   │   │   └── test_routes.py
│   │   ├── permissions/
│   │   │   ├── __init__.py
│   │   │   ├── test_service.py
│   │   │   └── test_routes.py
│   │   └── user_roles/
│   │       ├── __init__.py
│   │       ├── test_service.py
│   │       └── test_routes.py
│   │
│   ├── organization/                  # Organization module tests
│   │   ├── __init__.py
│   │   ├── test_service.py            # OrganizationService tests
│   │   ├── test_routes.py
│   │   └── test_models.py
│   │
│   ├── notifications/                 # Notification module tests
│   │   ├── __init__.py
│   │   ├── test_service.py
│   │   ├── test_templates.py
│   │   └── test_routes.py
│   │
│   ├── voice_agents/                  # Voice agents module tests
│   │   ├── __init__.py
│   │   ├── test_routes.py
│   │   ├── test_tool_routes.py
│   │   └── test_voice_routes.py
│   │
│   ├── services/                      # Backend services tests
│   │   ├── __init__.py
│   │   └── test_token_refresh_service.py
│   │
│   └── shared/                        # Shared utils tests
│       ├── __init__.py
│       ├── test_utils.py
│       └── test_security.py
```

---

## Module-by-Module Test Specifications

### 1. Auth Module

**Source File:** `backend/src/auth/service.py` (~630 lines)

**Service:** `AuthService`

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_sign_up_success` | `sign_up()` | Successful user registration with valid data | HIGH |
| `test_sign_up_creates_default_org` | `sign_up()` | Verifies dummy organization and org_admin role created | HIGH |
| `test_sign_up_with_invitation_token` | `sign_up()` | Sign up with valid invitation token | MEDIUM |
| `test_sign_up_existing_user` | `sign_up()` | Returns 409 Conflict for duplicate email | HIGH |
| `test_sign_up_supabase_error` | `sign_up()` | Handles Supabase API failures gracefully | MEDIUM |
| `test_sign_up_metrics_recorded` | `sign_up()` | Verifies auth metrics counter incremented | LOW |
| `test_sign_in_success` | `sign_in()` | Successful login with valid credentials | HIGH |
| `test_sign_in_returns_tokens` | `sign_in()` | Response includes access and refresh tokens | HIGH |
| `test_sign_in_invalid_credentials` | `sign_in()` | Returns 400 for incorrect email/password | HIGH |
| `test_sign_in_user_not_found` | `sign_in()` | Returns 400 for non-existent user | MEDIUM |
| `test_sign_in_supabase_error` | `sign_in()` | Handles Supabase API failures gracefully | MEDIUM |
| `test_sign_out_success` | `sign_out()` | Successfully invalidates session | MEDIUM |
| `test_sign_out_invalid_token` | `sign_out()` | Handles invalid/expired token | MEDIUM |
| `test_refresh_token_success` | `refresh_token()` | Returns new access token | HIGH |
| `test_refresh_token_invalid` | `refresh_token()` | Returns 400 for invalid refresh token | HIGH |
| `test_refresh_token_expired` | `refresh_token()` | Returns 400 for expired refresh token | MEDIUM |
| `test_get_user_success` | `get_user()` | Returns complete user profile | HIGH |
| `test_get_user_includes_roles` | `get_user()` | Profile includes roles and permissions | HIGH |
| `test_get_user_invalid_token` | `get_user()` | Returns 401 for invalid access token | HIGH |
| `test_get_user_by_email_found` | `get_user_by_email()` | Finds and returns existing user | MEDIUM |
| `test_get_user_by_email_not_found` | `get_user_by_email()` | Returns None for non-existent email | MEDIUM |
| `test_get_user_by_email_case_insensitive` | `get_user_by_email()` | Email lookup is case-insensitive | LOW |

**Estimated Tests:** ~22 tests

**Mock Requirements:**
- `supabase.auth.sign_up()`
- `supabase.auth.sign_in_with_password()`
- `supabase.auth.sign_out()`
- `supabase.auth.refresh_session()`
- `supabase.auth.get_user()`
- `supabase.auth.admin.list_users()`
- `role_service.get_role_by_name()`
- `user_role_service.assign_role_to_user()`
- `organization_service.create_organization()`

---

### 2. Billing Module

**Source File:** `backend/src/billing/service.py` (~1033 lines)

**Service:** `BillingService`

#### Subscription Plan Management

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_create_subscription_plan_success` | `create_subscription_plan()` | Creates plan with all fields | HIGH |
| `test_create_subscription_plan_minimal` | `create_subscription_plan()` | Creates plan with required fields only | MEDIUM |
| `test_get_subscription_plans_all` | `get_subscription_plans()` | Returns all plans when active_only=False | HIGH |
| `test_get_subscription_plans_active_only` | `get_subscription_plans()` | Filters to active plans only | HIGH |
| `test_get_subscription_plans_empty` | `get_subscription_plans()` | Returns empty list when no plans | LOW |
| `test_get_subscription_plan_by_id` | `get_subscription_plan()` | Returns plan by UUID | HIGH |
| `test_get_subscription_plan_not_found` | `get_subscription_plan()` | Returns None for non-existent ID | MEDIUM |
| `test_update_subscription_plan` | `update_subscription_plan()` | Updates plan fields | MEDIUM |
| `test_update_subscription_plan_partial` | `update_subscription_plan()` | Partial update preserves other fields | MEDIUM |

#### Organization Subscription Management

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_create_org_subscription_success` | `create_organization_subscription()` | Creates subscription for org | HIGH |
| `test_create_org_subscription_with_trial` | `create_organization_subscription()` | Sets trial_start and trial_end | HIGH |
| `test_create_org_subscription_creates_stripe_customer` | `create_organization_subscription()` | Creates Stripe customer if not provided | HIGH |
| `test_create_org_subscription_allocates_credits` | `create_organization_subscription()` | Adds included_credits from plan | HIGH |
| `test_get_org_subscription_with_plan` | `get_organization_subscription()` | Returns subscription with plan details | HIGH |
| `test_get_org_subscription_not_found` | `get_organization_subscription()` | Returns None for org without subscription | MEDIUM |
| `test_update_org_subscription_status` | `update_organization_subscription()` | Updates subscription status | MEDIUM |
| `test_update_org_subscription_plan_change` | `update_organization_subscription()` | Resets credits on plan change | HIGH |

#### Credit Management

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_get_credit_balance_total` | `get_credit_balance()` | Returns correct total_credits | HIGH |
| `test_get_credit_balance_breakdown` | `get_credit_balance()` | Returns subscription vs purchased breakdown | HIGH |
| `test_get_credit_balance_expiring_soon` | `get_credit_balance()` | Calculates credits expiring in 30 days | MEDIUM |
| `test_add_subscription_credits` | `add_subscription_credits()` | Adds credits with expiry | HIGH |
| `test_add_purchased_credits` | `add_purchased_credits()` | Adds credits without expiry | HIGH |
| `test_reset_subscription_credits_increase` | `reset_subscription_credits()` | Increases balance on upgrade | HIGH |
| `test_reset_subscription_credits_decrease` | `reset_subscription_credits()` | Decreases balance on downgrade | HIGH |
| `test_reset_subscription_credits_no_change` | `reset_subscription_credits()` | Returns None when already at target | LOW |
| `test_consume_credits_success` | `consume_credits()` | Deducts credits and creates transaction | HIGH |
| `test_consume_credits_insufficient` | `consume_credits()` | Returns success=False when insufficient | HIGH |
| `test_consume_credits_event_not_found` | `consume_credits()` | Raises error for invalid event name | MEDIUM |

#### Credit Events and Products

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_get_credit_events_all` | `get_credit_events()` | Returns all credit events | MEDIUM |
| `test_get_credit_events_active_only` | `get_credit_events()` | Filters to active events | MEDIUM |
| `test_get_credit_products` | `get_credit_products()` | Returns credit products ordered by amount | MEDIUM |

#### Billing History

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_create_billing_history` | `create_billing_history()` | Creates billing history entry | MEDIUM |
| `test_get_billing_history` | `get_billing_history()` | Returns history ordered by date desc | MEDIUM |
| `test_get_billing_history_limit` | `get_billing_history()` | Respects limit parameter | LOW |

#### Billing Summary

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_get_billing_summary_complete` | `get_organization_billing_summary()` | Returns comprehensive summary | HIGH |
| `test_get_billing_summary_no_subscription` | `get_organization_billing_summary()` | Handles org without subscription | MEDIUM |

#### Polymorphic Relationship Validation

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_validate_transaction_references_valid` | `validate_transaction_references()` | All references valid | LOW |
| `test_validate_transaction_references_orphaned` | `validate_transaction_references()` | Detects orphaned references | LOW |

**Estimated Tests:** ~35 tests

**Mock Requirements:**
- `supabase.table("subscription_plans").*`
- `supabase.table("organization_subscriptions").*`
- `supabase.table("organizations").*`
- `supabase.table("credit_transactions").*`
- `supabase.table("credit_events").*`
- `supabase.table("credit_products").*`
- `supabase.table("billing_history").*`
- `stripe_service.create_customer()`

---

### 3. Organization Module

**Source File:** `backend/src/organization/service.py` (~846 lines)

**Service:** `OrganizationService`

#### Organization CRUD

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_create_organization_success` | `create_organization()` | Creates org with all fields | HIGH |
| `test_create_organization_with_website` | `create_organization()` | Handles website URL field | MEDIUM |
| `test_create_organization_with_business_details` | `create_organization()` | Includes business_details JSON | MEDIUM |
| `test_get_organization_by_id_found` | `get_organization_by_id()` | Returns org by UUID | HIGH |
| `test_get_organization_by_id_not_found` | `get_organization_by_id()` | Returns None with error message | HIGH |
| `test_get_organization_by_slug_found` | `get_organization_by_slug()` | Returns org by slug | MEDIUM |
| `test_get_organization_by_slug_not_found` | `get_organization_by_slug()` | Returns None for invalid slug | MEDIUM |
| `test_get_all_organizations` | `get_all_organizations()` | Returns list of all orgs | MEDIUM |
| `test_get_all_organizations_empty` | `get_all_organizations()` | Returns empty list when none exist | LOW |
| `test_update_organization_all_fields` | `update_organization()` | Updates all provided fields | HIGH |
| `test_update_organization_partial` | `update_organization()` | Only updates specified fields | HIGH |
| `test_update_organization_no_changes` | `update_organization()` | Returns current org when no fields | LOW |
| `test_update_organization_not_found` | `update_organization()` | Returns None for invalid ID | MEDIUM |
| `test_delete_organization_success` | `delete_organization()` | Deletes org successfully | HIGH |
| `test_delete_organization_not_found` | `delete_organization()` | Returns False for invalid ID | MEDIUM |

#### Invitation Management

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_create_invitation_new_user` | `create_invitation()` | Creates invitation and sends email | HIGH |
| `test_create_invitation_existing_user_not_member` | `create_invitation()` | Adds existing user directly | HIGH |
| `test_create_invitation_existing_user_already_member` | `create_invitation()` | Returns USER_ALREADY_MEMBER error | HIGH |
| `test_create_invitation_cancels_pending` | `create_invitation()` | Cancels existing pending invitations | MEDIUM |
| `test_create_invitation_sends_email` | `create_invitation()` | Verifies notification service called | MEDIUM |
| `test_create_invitation_email_failure_continues` | `create_invitation()` | Doesn't fail if email fails | MEDIUM |
| `test_process_invitation_success` | `process_invitation()` | Assigns role and updates status | HIGH |
| `test_process_invitation_not_found` | `process_invitation()` | Returns error for invalid token | MEDIUM |
| `test_process_invitation_already_accepted` | `process_invitation()` | Returns error if already used | MEDIUM |
| `test_process_invitation_expired` | `process_invitation()` | Updates status and returns error | MEDIUM |

**Estimated Tests:** ~25 tests

**Mock Requirements:**
- `supabase.table("organizations").*`
- `supabase.table("invitations").*`
- `auth_service.get_user_by_email()`
- `role_service.get_role_by_name()`
- `user_role_service.assign_role_to_user()`
- `user_role_service.get_user_roles()`
- `notification_service.send_notification()`

---

### 4. Notifications Module

**Source File:** `backend/src/notifications/service.py` (~658 lines)

**Service:** `NotificationService`

#### Notification Events

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_create_notification_event` | `create_notification_event()` | Creates event with all fields | MEDIUM |
| `test_get_notification_event` | `get_notification_event()` | Gets event by ID | MEDIUM |
| `test_get_notification_event_by_key` | `get_notification_event_by_key()` | Gets event by unique key | HIGH |
| `test_get_notification_event_by_key_not_found` | `get_notification_event_by_key()` | Returns None for invalid key | MEDIUM |
| `test_list_notification_events` | `list_notification_events()` | Lists all events | MEDIUM |
| `test_list_notification_events_by_category` | `list_notification_events()` | Filters by category | LOW |
| `test_update_notification_event` | `update_notification_event()` | Updates event fields | LOW |
| `test_delete_notification_event` | `delete_notification_event()` | Deletes event | LOW |

#### Notification Templates

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_create_notification_template` | `create_notification_template()` | Creates template | MEDIUM |
| `test_get_notification_template` | `get_notification_template()` | Gets template by ID | MEDIUM |
| `test_list_notification_templates` | `list_notification_templates()` | Lists all templates | LOW |
| `test_update_notification_template` | `update_notification_template()` | Updates template | LOW |
| `test_delete_notification_template` | `delete_notification_template()` | Deletes template | LOW |

#### Send Notification

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_send_notification_success` | `send_notification()` | Sends email via Resend | HIGH |
| `test_send_notification_disabled_event` | `send_notification()` | Returns failure for disabled event | HIGH |
| `test_send_notification_builtin_template` | `send_notification()` | Uses built-in template from registry | HIGH |
| `test_send_notification_custom_template` | `send_notification()` | Uses custom DB template | MEDIUM |
| `test_send_notification_template_variables` | `send_notification()` | Replaces template variables | HIGH |
| `test_send_notification_resend_error` | `send_notification()` | Logs failure and updates status | MEDIUM |
| `test_send_notification_creates_log` | `send_notification()` | Creates notification_logs entry | MEDIUM |

#### Utility Functions

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_validate_template_variables_success` | `validate_template_variables()` | All required vars present | HIGH |
| `test_validate_template_variables_missing` | `validate_template_variables()` | Raises ValueError for missing | HIGH |
| `test_validate_template_variables_with_defaults` | `validate_template_variables()` | Applies default app vars | MEDIUM |
| `test_validate_builtin_template_variables` | `validate_builtin_template_variables()` | Validates for event key | MEDIUM |
| `test_sanitize_template_variables` | `sanitize_template_variables()` | Escapes HTML characters | HIGH |
| `test_sanitize_template_variables_xss` | `sanitize_template_variables()` | Prevents XSS attacks | HIGH |

#### Stats and Logs

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_get_notification_logs` | `get_notification_logs()` | Returns logs with filters | LOW |
| `test_get_notification_stats` | `get_notification_stats()` | Returns aggregated stats | LOW |

**Estimated Tests:** ~28 tests

**Mock Requirements:**
- `supabase.table("notification_events").*`
- `supabase.table("notification_templates").*`
- `supabase.table("notification_logs").*`
- `resend.Emails.send()`

---

### 5. RBAC Module

**Source Files:**
- `backend/src/rbac/roles/service.py`
- `backend/src/rbac/permissions/service.py`
- `backend/src/rbac/user_roles/service.py`

#### Role Service

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_create_role` | `create_role()` | Creates new role | HIGH |
| `test_create_role_duplicate` | `create_role()` | Handles duplicate name | MEDIUM |
| `test_get_role_by_id` | `get_role_by_id()` | Gets role by UUID | MEDIUM |
| `test_get_role_by_name` | `get_role_by_name()` | Gets role by name | HIGH |
| `test_get_role_by_name_not_found` | `get_role_by_name()` | Returns None for invalid name | MEDIUM |
| `test_get_all_roles` | `get_all_roles()` | Returns all roles | HIGH |
| `test_update_role` | `update_role()` | Updates role fields | MEDIUM |
| `test_delete_role` | `delete_role()` | Deletes role | MEDIUM |

#### Permission Service

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_create_permission` | `create_permission()` | Creates permission | MEDIUM |
| `test_get_permission_by_name` | `get_permission_by_name()` | Gets by name | MEDIUM |
| `test_get_all_permissions` | `get_all_permissions()` | Lists all permissions | MEDIUM |
| `test_get_role_permissions` | `get_role_permissions()` | Gets permissions for role | HIGH |
| `test_assign_permission_to_role` | `assign_permission_to_role()` | Links permission to role | MEDIUM |

#### User Role Service

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_assign_role_to_user` | `assign_role_to_user()` | Creates user-role assignment | HIGH |
| `test_assign_role_to_user_with_org` | `assign_role_to_user()` | Org-scoped assignment | HIGH |
| `test_get_user_roles` | `get_user_roles()` | Gets roles for user | HIGH |
| `test_get_user_roles_by_org` | `get_user_roles()` | Filters by organization | HIGH |
| `test_get_user_permissions` | `get_user_permissions()` | Gets flattened permissions | HIGH |
| `test_get_all_user_roles_with_permissions` | `get_all_user_roles_with_permissions()` | Full role+permission tree | HIGH |
| `test_remove_role_from_user` | `remove_role_from_user()` | Removes assignment | MEDIUM |
| `test_user_has_permission` | `user_has_permission()` | Checks specific permission | HIGH |

**Estimated Tests:** ~21 tests

**Mock Requirements:**
- `supabase.table("roles").*`
- `supabase.table("permissions").*`
- `supabase.table("role_permissions").*`
- `supabase.table("user_roles").*`

---

### 6. Voice Agents / Tool Service (Shared Module)

**Source File:** `shared/voice_agents/tool_service.py` (~482 lines)

**Service:** `ToolService`

#### Utility Functions

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_validate_token_status_authenticated` | `validate_token_status()` | Returns AUTHENTICATED for valid token | HIGH |
| `test_validate_token_status_expired` | `validate_token_status()` | Returns EXPIRED within 5min buffer | HIGH |
| `test_validate_token_status_not_authenticated` | `validate_token_status()` | Returns NOT_AUTHENTICATED for empty | HIGH |
| `test_validate_token_status_invalid_data` | `validate_token_status()` | Returns NOT_AUTHENTICATED for invalid | MEDIUM |
| `test_get_connection_status_no_auth_required` | `get_connection_status()` | Returns CONNECTED_NO_AUTH | HIGH |
| `test_get_connection_status_auth_valid` | `get_connection_status()` | Returns CONNECTED_AUTH_VALID | HIGH |
| `test_get_connection_status_auth_invalid` | `get_connection_status()` | Returns CONNECTED_AUTH_INVALID | HIGH |

#### Platform Tools

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_upsert_platform_tool_create` | `upsert_platform_tool()` | Creates new platform tool | HIGH |
| `test_upsert_platform_tool_update` | `upsert_platform_tool()` | Updates existing tool | HIGH |
| `test_get_platform_tools_all` | `get_platform_tools()` | Gets all tools | MEDIUM |
| `test_get_platform_tools_active_only` | `get_platform_tools()` | Filters to active tools | HIGH |

#### Agent Tools

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_configure_agent_tool_create` | `configure_agent_tool()` | Creates new agent tool config | HIGH |
| `test_configure_agent_tool_update` | `configure_agent_tool()` | Updates existing config | HIGH |
| `test_configure_agent_tool_encrypts_sensitive` | `configure_agent_tool()` | Encrypts sensitive_config | HIGH |
| `test_get_agent_tools` | `get_agent_tools()` | Returns tools without sensitive data | HIGH |
| `test_get_agent_tools_includes_platform_tool` | `get_agent_tools()` | Joins with platform_tools | MEDIUM |
| `test_get_agent_tools_calculates_status` | `get_agent_tools()` | Includes auth/connection status | HIGH |
| `test_get_agent_tools_with_sensitive_config` | `get_agent_tools_with_sensitive_config()` | Decrypts sensitive_config | HIGH |
| `test_update_agent_tool` | `update_agent_tool()` | Updates config fields | MEDIUM |
| `test_update_agent_tool_unselected_functions` | `update_agent_tool()` | Updates function list | MEDIUM |
| `test_delete_agent_tool` | `delete_agent_tool()` | Removes agent tool | MEDIUM |
| `test_get_all_agent_tools_with_auth` | `get_all_agent_tools_with_auth()` | Gets tools for token refresh | MEDIUM |

**Estimated Tests:** ~22 tests

**Mock Requirements:**
- `supabase.table("platform_tools").*`
- `supabase.table("agent_tools").*`
- `encrypt_data()` / `decrypt_data()`

---

### 7. Security Utilities (Shared Module)

**Source File:** `shared/common/security.py` (~70 lines)

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_encrypt_data_dict` | `encrypt_data()` | Encrypts dictionary to string | HIGH |
| `test_encrypt_data_empty` | `encrypt_data()` | Returns empty string for empty dict | HIGH |
| `test_encrypt_data_none` | `encrypt_data()` | Returns empty string for None | HIGH |
| `test_decrypt_data_valid` | `decrypt_data()` | Decrypts back to dictionary | HIGH |
| `test_decrypt_data_empty` | `decrypt_data()` | Returns {} for empty string | HIGH |
| `test_decrypt_data_invalid` | `decrypt_data()` | Returns {} for invalid data | HIGH |
| `test_encrypt_decrypt_roundtrip` | Both | Data survives encryption roundtrip | HIGH |
| `test_encrypt_decrypt_complex_data` | Both | Handles nested dicts/lists | MEDIUM |
| `test_get_fernet_with_key` | `get_fernet()` | Uses ENCRYPTION_KEY env var | MEDIUM |
| `test_get_fernet_fallback` | `get_fernet()` | Uses dev fallback when no key | MEDIUM |

**Estimated Tests:** ~10 tests

**Mock Requirements:**
- `os.getenv("ENCRYPTION_KEY")`

---

### 8. Token Refresh Service

**Source File:** `backend/src/services/token_refresh_service.py`

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_start_service` | `start()` | Starts background scheduler | MEDIUM |
| `test_stop_service` | `stop()` | Stops scheduler gracefully | MEDIUM |
| `test_refresh_expiring_tokens` | `_refresh_expiring_tokens()` | Refreshes tokens within threshold | HIGH |
| `test_refresh_token_success` | `_refresh_token()` | Updates token in database | HIGH |
| `test_refresh_token_failure` | `_refresh_token()` | Handles OAuth refresh failure | MEDIUM |

**Estimated Tests:** ~5 tests

---

## Test Infrastructure

### Configuration Files

#### `backend/pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests (fast, mocked dependencies)
    integration: Integration tests (slower, may use real services)
    slow: Slow running tests
filterwarnings =
    ignore::DeprecationWarning
```

#### `backend/tests/conftest.py` - Key Fixtures

```python
"""
Shared pytest fixtures for all backend tests.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

# ============================================
# Mock Clients
# ============================================

@pytest.fixture
def mock_supabase_client():
    """Create a mocked Supabase client."""
    client = MagicMock()
    # Setup table mock that returns chainable methods
    table_mock = MagicMock()
    table_mock.select.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.delete.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.execute.return_value = MagicMock(data=[])
    client.table.return_value = table_mock
    return client

@pytest.fixture
def mock_supabase_auth():
    """Create a mocked Supabase auth client."""
    auth = MagicMock()
    auth.sign_up = MagicMock()
    auth.sign_in_with_password = MagicMock()
    auth.sign_out = MagicMock()
    auth.refresh_session = MagicMock()
    auth.get_user = MagicMock()
    auth.admin = MagicMock()
    auth.admin.list_users = MagicMock()
    return auth

@pytest.fixture
def mock_stripe_service():
    """Create a mocked Stripe service."""
    service = MagicMock()
    service.create_customer = AsyncMock()
    service.create_subscription = AsyncMock()
    service.cancel_subscription = AsyncMock()
    return service

@pytest.fixture
def mock_resend():
    """Create a mocked Resend email service."""
    with patch('resend.Emails.send') as mock:
        mock.return_value = {"id": "test-email-id"}
        yield mock

# ============================================
# Sample Data Fixtures
# ============================================

@pytest.fixture
def sample_user_id():
    """Generate a sample user UUID."""
    return uuid4()

@pytest.fixture
def sample_org_id():
    """Generate a sample organization UUID."""
    return uuid4()

@pytest.fixture
def sample_user_data(sample_user_id):
    """Sample user data from Supabase."""
    return {
        "id": str(sample_user_id),
        "email": "test@example.com",
        "user_metadata": {
            "first_name": "Test",
            "last_name": "User"
        },
        "email_confirmed_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

@pytest.fixture
def sample_organization_data(sample_org_id):
    """Sample organization data."""
    return {
        "id": str(sample_org_id),
        "name": "Test Organization",
        "description": "A test organization",
        "slug": "test-org",
        "website": "https://example.com",
        "is_active": True,
        "business_details": {"industry": "Technology"},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

@pytest.fixture
def sample_subscription_plan_data():
    """Sample subscription plan data."""
    return {
        "id": str(uuid4()),
        "name": "Pro Plan",
        "description": "Professional tier",
        "price_amount": 4900,
        "price_currency": "usd",
        "billing_period": "monthly",
        "included_credits": 1000,
        "trial_period_days": 14,
        "is_active": True,
        "stripe_price_id": "price_test123",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

# ============================================
# Service Fixtures with Mocked Dependencies
# ============================================

@pytest.fixture
def auth_service(mock_supabase_client, mock_supabase_auth):
    """AuthService with mocked Supabase."""
    with patch('src.auth.service.supabase_config') as mock_config:
        mock_config.client = mock_supabase_client
        mock_config.is_configured.return_value = True
        mock_supabase_client.auth = mock_supabase_auth
        
        from src.auth.service import AuthService
        service = AuthService()
        service.supabase_config = mock_config
        yield service

@pytest.fixture
def billing_service(mock_supabase_client, mock_stripe_service):
    """BillingService with mocked dependencies."""
    with patch('src.billing.service.supabase_config') as mock_config:
        mock_config.client = mock_supabase_client
        
        with patch('src.billing.service.stripe_service', mock_stripe_service):
            from src.billing.service import BillingService
            service = BillingService()
            yield service

@pytest.fixture
def organization_service(mock_supabase_client):
    """OrganizationService with mocked Supabase."""
    with patch('src.organization.service.supabase_config') as mock_config:
        mock_config.client = mock_supabase_client
        mock_config.is_configured.return_value = True
        
        from src.organization.service import OrganizationService
        service = OrganizationService()
        service.supabase_config = mock_config
        yield service

@pytest.fixture
def tool_service(mock_supabase_client):
    """ToolService with mocked Supabase."""
    with patch('shared.voice_agents.tool_service.supabase_config') as mock_config:
        mock_config.client = mock_supabase_client
        
        from shared.voice_agents.tool_service import ToolService
        service = ToolService()
        yield service
```

---

## Test Implementation Order

| Phase | Module | Estimated Tests | Priority | Complexity |
|-------|--------|-----------------|----------|------------|
| 1.1 | Security Utilities | ~10 | HIGH | LOW |
| 1.2 | Auth Service | ~22 | HIGH | MEDIUM |
| 1.3 | Billing Service | ~35 | HIGH | HIGH |
| 1.4 | RBAC Services | ~21 | MEDIUM | MEDIUM |
| 1.5 | Organization Service | ~25 | MEDIUM | MEDIUM |
| 1.6 | Tool Service (Shared) | ~22 | HIGH | MEDIUM |
| 1.7 | Notifications Service | ~28 | MEDIUM | LOW |
| 1.8 | Token Refresh Service | ~5 | LOW | LOW |

**Total Phase 1 Estimated Tests:** ~168 tests

---

## Running Tests

### Commands

```bash
# Run all tests
cd backend
pytest

# Run with coverage
pytest --cov=src --cov=../shared --cov-report=html

# Run specific module
pytest tests/auth/

# Run specific test file
pytest tests/auth/test_service.py

# Run specific test
pytest tests/auth/test_service.py::TestAuthService::test_sign_up_success

# Run with markers
pytest -m unit           # Only unit tests
pytest -m "not slow"     # Skip slow tests

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Coverage Goals

| Phase | Target Coverage | Timeline |
|-------|-----------------|----------|
| Week 1 | ~15% | Auth + Security setup |
| Week 2 | ~30% | Billing tests |
| Week 3 | ~50% | RBAC + Organization |
| Week 4 | ~70% | Tool Service + Notifications |
| Week 5 | ~85% | API routes + remaining |
| Week 6 | ~95% | Edge cases + refinement |

---

## Phase 2: Integration Tests (Future)

After Phase 1 achieves 80%+ coverage:

1. **API Route Integration Tests**
   - Test full request/response cycle
   - Verify authentication middleware
   - Test error handling

2. **Multi-Service Workflow Tests**
   - User signup -> org creation -> role assignment flow
   - Subscription creation -> credit allocation flow
   - Invitation -> signup -> org join flow

3. **Database Integration Tests (Optional)**
   - Use test Supabase project
   - Test actual database constraints
   - Verify RLS policies

---

## Phase 3: Frontend Tests

### Current State

| Component | Source Files | Existing Tests | Current Coverage |
|-----------|--------------|----------------|------------------|
| **Frontend** | ~100+ TypeScript/TSX files | 0 | None |

### Testing Strategy

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Test Runner** | Vitest | Faster than Jest, better Next.js support |
| **Component Testing** | React Testing Library | User-centric testing approach |
| **API Mocking** | MSW (Mock Service Worker) | Real network interception |
| **Rendering** | @testing-library/react | Standard React testing utilities |
| **User Interaction** | @testing-library/user-event | More realistic user actions |
| **Query Mocking** | Vitest + TanStack Query mocks | Test data fetching logic |
| **Supabase Mocking** | Mock Supabase client | Isolate auth/realtime logic |
| **Priority** | Services > Hooks > Components | Test business logic first, then UI |

### Technology Stack

```bash
# Core Testing
vitest: ^2.1.0                # Test runner
@testing-library/react: ^16.0.0  # React component testing
@testing-library/jest-dom: ^6.6.0  # Custom matchers
@testing-library/user-event: ^14.5.0  # User interaction simulation
jsdom: ^25.0.0                # DOM environment

# API Mocking
msw: ^2.6.0                   # Mock Service Worker for API mocking

# Query Mocking
@tanstack/react-query-devtools: ^5.0.0  # Already in deps

# Utilities
@vitest/ui: ^2.1.0            # Vitest UI for interactive testing
```

---

### Directory Structure

```
frontend/
├── tests/
│   ├── setup.ts                   # Vitest setup file
│   ├── mocks/                     # Mock implementations
│   │   ├── handlers.ts            # MSW request handlers
│   │   ├── server.ts              # MSW server setup
│   │   ├── supabase.mock.ts       # Supabase client mock
│   │   └── query-client.mock.ts   # React Query mock
│   │
│   ├── utils/                     # Test utilities
│   │   ├── test-utils.tsx         # Custom render functions
│   │   ├── matchers.ts            # Custom matchers
│   │   └── data-factories.ts      # Sample data generators
│   │
│   ├── services/                  # Service layer tests
│   │   ├── test-auth-service.test.ts
│   │   ├── test-agent-service.test.ts
│   │   ├── test-billing-service.test.ts
│   │   ├── test-organization-service.test.ts
│   │   └── test-rbac-service.test.ts
│   │
│   ├── hooks/                     # Custom hook tests
│   │   ├── test-use-agent-queries.test.ts
│   │   ├── test-use-realtime.test.ts
│   │   ├── test-use-billing-info.test.ts
│   │   ├── test-use-user-profile.test.ts
│   │   ├── test-use-organizations.test.ts
│   │   └── test-use-rbac.test.ts
│   │
│   ├── components/                # Component tests
│   │   ├── auth/
│   │   │   ├── test-signin-form.test.tsx
│   │   │   ├── test-signup-form.test.tsx
│   │   │   ├── test-protected-route.test.tsx
│   │   │   └── test-forgot-password-dialog.test.tsx
│   │   │
│   │   ├── agents/
│   │   │   ├── test-agent-card.test.tsx
│   │   │   ├── test-agent-create-widget.test.tsx
│   │   │   └── test-agent-delete-dialog.test.tsx
│   │   │
│   │   ├── tools/
│   │   │   ├── test-tool-card.test.tsx
│   │   │   ├── test-tool-config-drawer.test.tsx
│   │   │   ├── test-tool-filters.test.tsx
│   │   │   └── test-tool-disconnect-dialog.test.tsx
│   │   │
│   │   ├── organizations/
│   │   │   ├── test-organization-selector.test.tsx
│   │   │   ├── test-organization-create-dialog.test.tsx
│   │   │   ├── test-organization-edit-dialog.test.tsx
│   │   │   └── test-organization-delete-dialog.test.tsx
│   │   │
│   │   ├── organization-members/
│   │   │   └── test-invite-member-dialog.test.tsx
│   │   │
│   │   ├── billing/
│   │   │   ├── test-plan-selection.test.tsx
│   │   │   ├── test-credit-purchase.test.tsx
│   │   │   ├── test-subscription-management.test.tsx
│   │   │   └── test-cancel-subscription-dialog.test.tsx
│   │   │
│   │   └── data-table/
│   │       ├── test-data-table.test.tsx
│   │       ├── test-data-table-toolbar.test.tsx
│   │       └── test-data-table-pagination.test.tsx
│   │
│   ├── lib/                       # Utility function tests
│   │   ├── test-utils.test.ts     # cn(), formatToolName(), etc.
│   │   ├── test-api-client.test.ts
│   │   ├── test-user-utils.test.ts
│   │   └── test-organization-utils.test.ts
│   │
│   └── integration/               # Integration tests (future)
│       └── test-user-journey.test.tsx
│
├── vitest.config.ts              # Vitest configuration
└── vitest.workspace.ts           # Workspace configuration
```

---

### Test Infrastructure Setup

#### `frontend/vitest.config.ts`

```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    css: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'tests/',
        '**/*.config.{js,ts}',
        '**/*.d.ts',
      ],
    },
    include: ['src/**/*.{test,spec}.{ts,tsx}', 'tests/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules/', 'dist/'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

#### `frontend/tests/setup.ts`

```typescript
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom'
import { afterEach, vi } from 'vitest'
import { QueryClient } from '@tanstack/react-query'

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock Supabase
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
      refreshSession: vi.fn(),
      signInWithPassword: vi.fn(),
      signOut: vi.fn(),
    },
    from: vi.fn(),
  },
}))

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
  }),
  useSearchParams: () => ({
    get: vi.fn(),
  }),
  useParams: () => ({}),
}))
```

---

## Module-by-Module Test Specifications

### 1. Service Layer Tests (Highest Priority)

Service tests verify API interactions, error handling, and data transformations. These are the most critical tests as they isolate business logic from UI.

#### 1.1 AuthService (`frontend/src/services/auth-service.ts`)

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_getCurrentUser_success` | `getCurrentUser()` | Returns user profile on success | HIGH |
| `test_getCurrentUser_unauthorized` | `getCurrentUser()` | Returns error when 401 | HIGH |
| `test_getCurrentUser_network_error` | `getCurrentUser()` | Returns error on network failure | MEDIUM |
| `test_processInvitation_success` | `processInvitation()` | Processes invitation token | HIGH |
| `test_processInvitation_invalid_token` | `processInvitation()` | Returns error for invalid token | HIGH |
| `test_processInvitation_expired` | `processInvitation()` | Returns error for expired token | MEDIUM |
| `test_signIn_success` | `signIn()` | Returns tokens on success | HIGH |
| `test_signIn_invalid_credentials` | `signIn()` | Returns error for bad credentials | HIGH |
| `test_signOut_success` | `signOut()` | Signs out successfully | MEDIUM |

**Estimated Tests:** ~9 tests

**Mock Requirements:**
- `apiClient.get()`, `apiClient.post()`
- MSW handlers for `/api/v1/auth/*` endpoints

---

#### 1.2 AgentService (`frontend/src/services/agent-service.ts`)

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_getMyAgents_success` | `getMyAgents()` | Returns array of user's agents | HIGH |
| `test_getMyAgents_empty` | `getMyAgents()` | Returns empty array when none | HIGH |
| `test_getAgentById_success` | `getAgentById()` | Returns single agent | HIGH |
| `test_getAgentById_not_found` | `getAgentById()` | Returns error for 404 | HIGH |
| `test_createAgent_success` | `createAgent()` | Creates agent and returns ID | HIGH |
| `test_createAgent_validation_error` | `createAgent()` | Returns error for invalid data | HIGH |
| `test_updateAgent_success` | `updateAgent()` | Updates agent fields | HIGH |
| `test_deleteAgent_success` | `deleteAgent()` | Deletes agent | MEDIUM |
| `test_getAgentTools_success` | `getAgentTools()` | Returns tools for agent | HIGH |
| `test_configureAgentTool_success` | `configureAgentTool()` | Configures tool | HIGH |
| `test_disconnectTool_success` | `disconnectTool()` | Disconnects tool | HIGH |

**Estimated Tests:** ~11 tests

---

#### 1.3 BillingService (`frontend/src/services/billing-service.ts`)

| Test Case | Method | Description | Priority |
|-----------|--------|-------------|----------|
| `test_getBillingInfo_success` | `getBillingInfo()` | Returns billing info | HIGH |
| `test_getBillingInfo_no_subscription` | `getBillingInfo()` | Handles no subscription | HIGH |
| `test_getSubscriptionPlans_success` | `getSubscriptionPlans()` | Returns all plans | HIGH |
| `test_getSubscriptionPlans_active_only` | `getSubscriptionPlans()` | Filters to active | HIGH |
| `test_createSubscription_success` | `createSubscription()` | Creates subscription | HIGH |
| `test_createSubscription_stripe_error` | `createSubscription()` | Handles Stripe error | MEDIUM |
| `test_cancelSubscription_success` | `cancelSubscription()` | Cancels subscription | HIGH |
| `test_getCreditBalance_success` | `getCreditBalance()` | Returns balance | HIGH |
| `test_purchaseCredits_success` | `purchaseCredits()` | Purchases credits | HIGH |
| `test_getBillingSummary_success` | `getBillingSummary()` | Returns summary | HIGH |

**Estimated Tests:** ~10 tests

---

#### 1.4 OrganizationService & RBACService

Similar patterns for organization and RBAC services.

**Estimated Tests:** ~8 tests (Organization) + ~6 tests (RBAC) = ~14 tests

---

### 2. Custom Hook Tests (High Priority)

Hook tests verify React Query integration, caching logic, and side effects.

#### 2.1 useAgentQueries (`frontend/src/hooks/use-agent-queries.ts`)

| Test Case | Hook | Description | Priority |
|-----------|------|-------------|----------|
| `test_useMyAgents_success` | `useMyAgents()` | Fetches and returns agents | HIGH |
| `test_useMyAgents_loading` | `useMyAgents()` | Shows loading state | HIGH |
| `test_useMyAgents_error` | `useMyAgents()` | Handles error state | HIGH |
| `test_useAgent_success` | `useAgent()` | Fetches single agent | HIGH |
| `test_useAgent_invalid_id` | `useAgent()` | Handles invalid ID | MEDIUM |
| `test_useOrgAgents_success` | `useOrgAgents()` | Fetches org agents | HIGH |
| `test_useOrgAgents_empty` | `useOrgAgents()` | Handles empty list | MEDIUM |
| `test_usePlatformTools_success` | `usePlatformTools()` | Fetches available tools | HIGH |
| `test_useAgentTools_success` | `useAgentTools()` | Fetches agent tools | HIGH |
| `test_createAgentMutation_success` | `useCreateAgent()` | Creates and invalidates cache | HIGH |
| `test_createAgentMutation_error` | `useCreateAgent()` | Handles error | MEDIUM |
| `test_deleteAgentMutation_success` | `useDeleteAgent()` | Deletes and invalidates cache | HIGH |
| `test_configureToolMutation_success` | `useConfigureTool()` | Configures and updates cache | HIGH |

**Estimated Tests:** ~13 tests

---

#### 2.2 useRealtime (`frontend/src/hooks/use-realtime.ts`)

| Test Case | Hook | Description | Priority |
|-----------|------|-------------|----------|
| `test_useRealtime_subscribes_on_mount` | `useRealtime()` | Creates subscription on mount | HIGH |
| `test_useRealtime_unsubscribes_on_unmount` | `useRealtime()` | Cleans up on unmount | HIGH |
| `test_useRealtime_invalidates_on_update` | `useRealtime()` | Invalidates queries on DB update | HIGH |
| `test_useRealtime_handles_error` | `useRealtime()` | Handles subscription error | MEDIUM |
| `test_useRealtime_multiple_tables` | `useRealtime()` | Subscribes to multiple tables | MEDIUM |

**Estimated Tests:** ~5 tests

---

#### 2.3 useBillingInfo, useUserProfile, useOrganizations, useRBAC

Similar patterns for other data-fetching hooks.

**Estimated Tests:** ~20 tests total

---

### 3. Component Tests (Medium Priority)

Component tests verify user interactions, rendering logic, and integration with hooks.

#### 3.1 Auth Components

| Test Case | Component | Description | Priority |
|-----------|-----------|-------------|----------|
| `test_signin_form_renders` | `SignInForm` | Renders all fields | HIGH |
| `test_signin_form_validation` | `SignInForm` | Shows errors for invalid input | HIGH |
| `test_signin_form_submit` | `SignInForm` | Calls signIn on submit | HIGH |
| `test_signup_form_renders` | `SignUpForm` | Renders all fields | HIGH |
| `test_signup_form_submit` | `SignUpForm` | Calls signUp on submit | HIGH |
| `test_protected_route_unauthenticated` | `ProtectedRoute` | Redirects when not authenticated | HIGH |
| `test_protected_route_authenticated` | `ProtectedRoute` | Renders children when authenticated | HIGH |
| `test_forgot_password_dialog_renders` | `ForgotPasswordDialog` | Renders correctly | MEDIUM |
| `test_forgot_password_dialog_submit` | `ForgotPasswordDialog` | Sends reset email | MEDIUM |

**Estimated Tests:** ~9 tests

---

#### 3.2 Agent Components

| Test Case | Component | Description | Priority |
|-----------|-----------|-------------|----------|
| `test_agent_card_renders` | `AgentCard` | Displays agent info | HIGH |
| `test_agent_card_click` | `AgentCard` | Calls onClick handler | HIGH |
| `test_agent_card_status_badge` | `AgentCard` | Shows correct status | MEDIUM |
| `test_agent_create_widget_renders` | `AgentCreateWidget` | Renders create form | HIGH |
| `test_agent_create_widget_submit` | `AgentCreateWidget` | Creates agent | HIGH |
| `test_agent_delete_dialog_renders` | `AgentDeleteDialog` | Shows warning message | MEDIUM |
| `test_agent_delete_dialog_confirm` | `AgentDeleteDialog` | Deletes on confirm | MEDIUM |

**Estimated Tests:** ~7 tests

---

#### 3.3 Tool Components

| Test Case | Component | Description | Priority |
|-----------|-----------|-------------|----------|
| `test_tool_card_renders_tool_info` | `ToolCard` | Displays tool name, description | HIGH |
| `test_tool_card_status_badge` | `ToolCard` | Shows correct connection status | HIGH |
| `test_tool_card_expired_token` | `ToolCard` | Shows expired badge | HIGH |
| `test_tool_card_click_connect` | `ToolCard` | Opens config drawer | HIGH |
| `test_tool_card_click_edit` | `ToolCard` | Opens config drawer for configured tool | HIGH |
| `test_tool_config_drawer_renders` | `ToolConfigDrawer` | Shows OAuth flow | HIGH |
| `test_tool_config_drawer_submit` | `ToolConfigDrawer` | Configures tool | HIGH |
| `test_tool_disconnect_dialog_renders` | `ToolDisconnectDialog` | Shows warning | MEDIUM |
| `test_tool_disconnect_dialog_confirm` | `ToolDisconnectDialog` | Disconnects on confirm | MEDIUM |
| `test_tool_filters_renders` | `ToolFilters` | Shows filter options | MEDIUM |
| `test_tool_filters_filters_list` | `ToolFilters` | Filters tools by status | MEDIUM |

**Estimated Tests:** ~11 tests

---

#### 3.4 Organization Components

| Test Case | Component | Description | Priority |
|-----------|-----------|-------------|----------|
| `test_organization_selector_renders` | `OrganizationSelector` | Shows organizations | HIGH |
| `test_organization_selector_select` | `OrganizationSelector` | Changes current organization | HIGH |
| `test_organization_create_dialog_renders` | `OrganizationCreateDialog` | Shows form | HIGH |
| `test_organization_create_dialog_submit` | `OrganizationCreateDialog` | Creates organization | HIGH |
| `test_organization_edit_dialog_renders` | `OrganizationEditDialog` | Pre-fills data | MEDIUM |
| `test_organization_edit_dialog_submit` | `OrganizationEditDialog` | Updates organization | MEDIUM |
| `test_organization_delete_dialog_renders` | `OrganizationDeleteDialog` | Shows warning | MEDIUM |
| `test_organization_delete_dialog_confirm` | `OrganizationDeleteDialog` | Deletes on confirm | MEDIUM |

**Estimated Tests:** ~8 tests

---

#### 3.5 Organization Members Components

| Test Case | Component | Description | Priority |
|-----------|-----------|-------------|----------|
| `test_invite_member_dialog_renders` | `InviteMemberDialog` | Shows form | HIGH |
| `test_invite_member_dialog_submit` | `InviteMemberDialog` | Sends invitation | HIGH |
| `test_invite_member_dialog_validation` | `InviteMemberDialog` | Shows errors for invalid email | MEDIUM |

**Estimated Tests:** ~3 tests

---

#### 3.6 Billing Components

| Test Case | Component | Description | Priority |
|-----------|-----------|-------------|----------|
| `test_plan_selection_renders` | `PlanSelection` | Shows available plans | HIGH |
| `test_plan_selection_select` | `PlanSelection` | Selects plan | HIGH |
| `test_plan_selection_checkout` | `PlanSelection` | Calls Stripe checkout | HIGH |
| `test_credit_purchase_renders` | `CreditPurchase` | Shows credit products | HIGH |
| `test_credit_purchase_buy` | `CreditPurchase` | Purchases credits | HIGH |
| `test_subscription_management_renders` | `SubscriptionManagement` | Shows subscription info | HIGH |
| `test_subscription_management_cancel` | `SubscriptionManagement` | Opens cancel dialog | MEDIUM |
| `test_cancel_subscription_dialog_confirm` | `CancelSubscriptionDialog` | Cancels subscription | MEDIUM |

**Estimated Tests:** ~8 tests

---

#### 3.7 DataTable Components

| Test Case | Component | Description | Priority |
|-----------|-----------|-------------|----------|
| `test_data_table_renders_rows` | `DataTable` | Shows data rows | MEDIUM |
| `test_data_table_pagination` | `DataTable` | Handles pagination | MEDIUM |
| `test_data_table_sorting` | `DataTable` | Sorts by column | MEDIUM |
| `test_data_table_toolbar_renders` | `DataTableToolbar` | Shows filters | LOW |
| `test_data_table_filters_data` | `DataTableToolbar` | Filters table data | LOW |

**Estimated Tests:** ~5 tests

---

### 4. Utility Function Tests (Medium Priority)

| Test Case | Function | Description | Priority |
|-----------|----------|-------------|----------|
| `test_cn_merges_classes` | `cn()` | Merges and dedupes classes | HIGH |
| `test_formatToolName_snake_case` | `formatToolName()` | Formats snake_case to Title Case | HIGH |
| `test_formatToolName_multiple_words` | `formatToolName()` | Handles multiple words | MEDIUM |
| `test_api_client_sets_auth_token` | `setAuthToken()` | Sets Authorization header | HIGH |
| `test_api_client_clears_auth_token` | `clearAuthToken()` | Removes Authorization header | HIGH |
| `test_api_client_refreshes_on_401` | `request()` | Retries with refreshed token | HIGH |

**Estimated Tests:** ~6 tests

---

### 5. Integration Tests (Low Priority - Future)

Full user flow tests using MSW for API mocking.

| Test Flow | Description | Priority |
|-----------|-------------|----------|
| User Signup Flow | Sign up form → create org → dashboard | MEDIUM |
| Agent Creation Flow | Create agent → configure tools | MEDIUM |
| Tool Connection Flow | Select tool → OAuth flow → verify connected | MEDIUM |
| Subscription Flow | Select plan → checkout → verify billing info | LOW |
| Invitation Flow | Invite user → signup → join org | LOW |

**Estimated Tests:** ~5 tests

---

## Test Implementation Order

| Phase | Module | Estimated Tests | Priority | Complexity |
|-------|--------|-----------------|----------|------------|
| 3.1 | Test Infrastructure (setup, mocks) | - | HIGH | MEDIUM |
| 3.2 | Service Layer (Auth, Agent, Billing) | ~30 | HIGH | LOW |
| 3.3 | Custom Hooks (useAgentQueries, useRealtime, etc.) | ~38 | HIGH | MEDIUM |
| 3.4 | Utility Functions | ~6 | MEDIUM | LOW |
| 3.5 | Auth Components | ~9 | MEDIUM | LOW |
| 3.6 | Agent Components | ~7 | MEDIUM | MEDIUM |
| 3.7 | Tool Components | ~11 | MEDIUM | MEDIUM |
| 3.8 | Organization Components | ~8 | MEDIUM | MEDIUM |
| 3.9 | Organization Members Components | ~3 | MEDIUM | LOW |
| 3.10 | Billing Components | ~8 | MEDIUM | MEDIUM |
| 3.11 | DataTable Components | ~5 | LOW | LOW |
| 3.12 | Integration Tests (Future) | ~5 | LOW | HIGH |

**Total Phase 3 Estimated Tests:** ~130 tests

---

## Running Frontend Tests

### Commands

```bash
# Run all tests
cd frontend
npm test

# Run with coverage
npm test -- --coverage

# Run in watch mode
npm test -- --watch

# Run specific test file
npm test tests/services/test-auth-service.test.ts

# Run specific test
npm test tests/services/test-auth-service.test.ts -t "test_getCurrentUser_success"

# Run with UI
npm test -- --ui

# Run tests matching pattern
npm test -- --run --grep "auth"
```

### Coverage Goals

| Phase | Target Coverage | Timeline |
|-------|-----------------|----------|
| Week 1 | ~20% | Test infrastructure + Services |
| Week 2 | ~40% | Hooks + Utilities |
| Week 3 | ~60% | Auth + Agent components |
| Week 4 | ~75% | Tool + Organization components |
| Week 5 | ~85% | Billing + Remaining components |
| Week 6 | ~90%+ | Integration tests + refinement |

---

## Key Testing Patterns

### Service Test Pattern

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { authAPI } from '@/services/auth-service'
import { server } from '../mocks/server'
import { rest } from 'msw'

describe('AuthService', () => {
  beforeEach(() => {
    server.listen()
  })

  afterEach(() => {
    server.resetHandlers()
  })

  it('getCurrentUser returns user profile', async () => {
    // Arrange
    const mockUser = { id: '1', email: 'test@example.com' }
    server.use(
      rest.get('/api/v1/auth/me', (req, res, ctx) => {
        return res(ctx.status(200), ctx.json({ data: mockUser }))
      })
    )

    // Act
    const result = await authAPI.getCurrentUser()

    // Assert
    expect(result.success).toBe(true)
    expect(result.user).toEqual(mockUser)
  })
})
```

### Hook Test Pattern

```typescript
import { describe, it, expect, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useMyAgents } from '@/hooks/use-agent-queries'

describe('useAgentQueries', () => {
  it('fetches and returns agents', async () => {
    // Arrange
    const queryClient = new QueryClient()
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    )

    // Act
    const { result } = renderHook(() => useMyAgents(), { wrapper })

    // Assert
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toBeDefined()
  })
})
```

### Component Test Pattern

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SignInForm } from '@/components/auth/signin-form'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

describe('SignInForm', () => {
  it('calls signIn on form submit', async () => {
    // Arrange
    const user = userEvent.setup()
    const queryClient = new QueryClient()
    const mockSignIn = vi.fn().mockResolvedValue({ success: true })

    render(
      <QueryClientProvider client={queryClient}>
        <SignInForm />
      </QueryClientProvider>
    )

    // Act
    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')
    await user.click(submitButton)

    // Assert
    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      })
    })
  })
})
```

---

## Appendix C: Frontend Testing Dependencies

```bash
# Install dependencies
cd frontend
npm install -D vitest @vitest/ui @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom msw

# Or add to package.json
{
  "devDependencies": {
    "vitest": "^2.1.0",
    "@vitest/ui": "^2.1.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/user-event": "^14.5.0",
    "jsdom": "^25.0.0",
    "msw": "^2.6.0"
  }
}
```

---

## Phase 4: End-to-End (E2E) Tests (Current Focus)

### Strategy
E2E tests will use **Playwright** (Python-based) to verify critical user journeys across the entire stack (Frontend, Backend, and Database). Tests will run against a live development environment (Docker).

### Critical User Journeys
1.  **Authentication & Onboarding**
    *   New user signup -> Email confirmation (mocked) -> Sign in.
    *   Initial organization creation during onboarding.
2.  **Organization & Member Management**
    *   Create/Edit/Delete organizations.
    *   Invite new members -> Accept invitation -> Verify role-based access.
3.  **Voice Agent Lifecycle**
    *   Create voice agent -> Configure basic settings.
    *   Assign tools to agent -> Configure tool parameters.
    *   Verify agent configuration is correctly persisted.
4.  **Tool Integration & OAuth**
    *   Initiate OAuth flow for a platform tool (e.g., Google Calendar).
    *   Verify successful connection and token storage.
5.  **Billing & Credits**
    *   Subscribe to a plan (Stripe Test Mode).
    *   Purchase credit products.
    *   Verify credit balance updates after actions.

### Implementation Plan
1.  **Framework Setup**: Consolidate E2E tests into a unified structure using `pytest-playwright`.
2.  **Environment Configuration**: Ensure tests can run against Docker containers with consistent seed data.
3.  **Authentication Helpers**: Create reusable fixtures for logging in as different roles (Super Admin, Org Admin, Member).
4.  **Test Suite Development**: Implement tests for the journeys above, starting with Auth and Organization management.

---

## Running Tests

```bash
# Add to requirements-dev.txt
pytest==8.3.4
pytest-asyncio==0.24.0
pytest-cov==4.1.0
pytest-mock==3.12.0
httpx==0.26.0  # For async HTTP client testing
```

---

## Appendix B: References

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Project Architecture](../01_architecture/system_architecture.md)
- [Backend README](../../backend/README.md)
- [Existing Testing Guide](./testing.md)

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| January 2026 | 1.0 | Initial testing plan created |

---

**Note:** This is a living document. Update as tests are implemented and new requirements emerge.
