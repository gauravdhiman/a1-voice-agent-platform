# PRD: Phone Number Management (Twilio + LiveKit)

**Feature ID:** F2
**Status:** Ready for Implementation (v0.9 - Finalized)
**Last Updated:** 2026-03-01
**Owner:** Genie (AI Assistant)

---

## 1. Overview

### Summary
Enable users to purchase, manage, and use phone numbers directly from the VoiceAI platform. The system will integrate with both Twilio and LiveKit APIs to provide numbers, abstracting the technical complexity from business users.

### Target Users
- Small business owners wanting AI voice agents
- Sales teams needing dedicated phone numbers
- Customer support teams
- Any non-technical user wanting voice agents

---

## 2. Problem Statement

### Current State
- Users must manually set up Twilio accounts
- Technical configuration (TwiML, Webhooks, SIP Trunking) is confusing
- Users need to manage numbers separately from voice agents
- No unified view of phone numbers in the platform

### Pain Points
1. Twilio setup is technically challenging for non-technical users
2. Multiple dashboards to manage (platform + Twilio)
3. No visibility into number status within the platform
4. Difficult to cancel/discard numbers when not needed

---

## 3. Goals

1. **Purchase numbers** without leaving the platform
2. **Manage numbers** (assign to agents, activate, deactivate)
3. **Unified experience** - user doesn't know/care about Twilio vs LiveKit
4. **Cancel numbers** easily when no longer needed

---

## 4. User Stories

### US1: Browse Available Numbers
```
As a user,
I want to see available phone numbers for a specific country,
So that I can choose a number that fits my business needs

Acceptance Criteria:
- User selects country from dropdown
- System shows available numbers with pricing
- Search by area code possible (depending on API capabilities)
- Shows monthly cost in credits upfront
- Maximum 50 results per query (paginated)
```

### US2: Purchase a Number with Credits
```
As a user,
I want to purchase a phone number using my platform credits,
So that I can start receiving calls immediately

Acceptance Criteria:
- One-click purchase using existing credits
- Shows credit balance before and after purchase
- Number added to user's account immediately
- Confirmation shown with number details
- Number appears in dashboard
- Error shown if insufficient credits
- Clear communication about billing terms (no refund on cancel)
```

### US3: Assign Number to Agent
```
As a user,
I want to assign a purchased number to my voice agent,
So that the agent can receive calls on that number

Acceptance Criteria:
- Dropdown to select from owned numbers
- Number activates for agent within 60 seconds
- Visual indicator shows number is active
- Can change assignment anytime
- Validation: number must not already be assigned to another agent
```

### US4: Manage Number Settings
```
As a user,
I want to configure settings for my number,
So that I can control how calls are handled

Acceptance Criteria:
- Enable/disable incoming calls
- Configure voicemail handling
- View call history for number
```

### US5: Cancel Number (No Refund)
```
As a user,
I want to cancel my subscription to a number,
So that I stop paying for it in future billing cycles

Acceptance Criteria:
- One-click cancellation
- No refund for current billing period (clearly communicated)
- Number is released immediately upon cancellation
- Warning shown if number is assigned to an active agent
- Confirmation screen with explicit acknowledgment of no refund
- Cannot assign to new agent after cancellation
- Clear communication that number will stop working immediately
```

### US6: Handle Agent Disconnection on Cancel
```
As a user,
I want to understand what happens when I cancel a number assigned to an agent,
So that I don't lose calls unexpectedly

Acceptance Criteria:
- Warning shown if number is assigned to an active agent
- Option to reassign before confirming cancellation
- If cancelled, number is released immediately (calls stop working right away)
- Clear communication: "You will not be refunded for this billing period"
- Explicit user acknowledgment required before cancellation completes
```

### US7: View Unassigned Numbers
```
As a user,
I want to see numbers I own that aren't assigned to any agent,
So that I can decide whether to use them or release them

Acceptance Criteria:
- Dashboard shows "used" vs "unused" state for each number
- Unused numbers highlighted or listed separately
- Display count of unused numbers on dashboard
- Same billing applies whether used or unused
```

---

## 5. User Experience

### Number Purchase Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Buy Phone Number                                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Country: [United States ▼]                                  │
│  Area Code: [Optional]                                       │
│  Search: [________________]                                 │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Available Numbers (max 50 per page)                   │   │
│  │ ┌─────────────────────────────────────────────────┐ │   │
│  │ │ +1 (555) 123-4567    200 credits/mo  [Select] │ │   │
│  │ │ +1 (555) 987-6543    200 credits/mo  [Select] │ │   │
│  │ │ +1 (212) 555-0199    500 credits/mo  [Select]│ │   │
│  │ └─────────────────────────────────────────────────┘ │   │
│  │                                                      │   │
│  │ [< Previous]  Page 1 of 10  [Next >]                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  Your Balance: 1,500 credits                                │
│  Selected: +1 (555) 123-4567 (200 credits/month)           │
│                                                              │
│  ⚠️ By purchasing, you agree to being charged monthly.     │
│    If you cancel, the number will be released immediately  │
│    and you will not be refunded for the current period.   │
│                                                              │
│  [ Purchase Number ]          [Cancel]                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Dashboard - Numbers Tab
```
┌─────────────────────────────────────────────────────────────┐
│  My Phone Numbers                     [+ Buy New Number]   │
│  ⚠️ You have 2 unused numbers                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ +1 (555) 123-4567        Status: Active (used)      │  │
│  │ Assigned to: Sales Agent                             │  │
│  │ Monthly: 200 credits                                 │  │
│  │ [Change] [Settings] [Cancel]                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ +1 (555) 987-6543        Status: Unused             │  │
│  │ Not assigned to any agent                           │  │
│  │ Monthly: 200 credits                                 │  │
│  │ [Assign to Agent] [Release]                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Cancellation Flow
```
┌─────────────────────────────────────────────────────────────┐
│  Cancel Phone Number?                                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Number: +1 (555) 123-4567                                  │
│  Monthly Cost: 200 credits                                  │
│                                                              │
│  ⚠️ WARNING: This number is assigned to "Sales Agent"     │
│  Cancelling will release the number immediately and        │
│  calls will stop working right away.                        │
│                                                              │
│  ☐ I understand I will not be refunded for this period     │
│    and the number will be released immediately.             │
│                                                              │
│  [Keep Number]          [Cancel Number (No Refund)]          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Key Decisions (Finalized)

### D1: Cancellation Policy ✓
**Final Decision:** Immediate release with no refund
- Cancel anytime → number released immediately
- No refund for current billing period
- Clear communication required at purchase and cancellation
- Simpler implementation (no tracking of "marked for release" numbers)

### D2: Unassigned Numbers ✓
- Users can buy numbers without assigning to an agent
- Show "used" vs "unused" state in UI
- Display unused number count on dashboard
- Same pricing applies whether used or not
- No auto-release (user responsibility)

### D3: Search/Display Limit ✓
- Maximum 50 results per query (pagination)
- Not a cap on ownership - users can own unlimited numbers
- Search filters depend on underlying API capabilities

### D4: No Local Pool ✓
- Direct integration with Twilio/LiveKit APIs
- No local pool management
- Released numbers go back to provider immediately

### D5: Agent Assignment Validation
- Prevent assigning same number to multiple agents
- Check number is not already assigned before linking

---

## 7. Out of Scope (for v1)

- Number porting (transferring existing numbers)
- SMS functionality
- International number purchasing (start with US)
- Bulk purchases
- Custom search filters beyond API capabilities

---

## 8. Success Criteria

- [ ] User can purchase a number in < 2 minutes
- [ ] Number works with voice agent within 60 seconds
- [ ] Cancellation completes instantly with clear messaging
- [ ] Zero support tickets for basic setup
- [ ] Clear communication about cancellation effects
- [ ] Unused numbers prominently displayed on dashboard

---

## Appendix: Credits System Integration

### Pricing Tiers (in credits)
| Number Type | Monthly Cost |
|-------------|--------------|
| US Local | 200 credits |
| US Toll-Free | 500 credits |
| International | TBD |

### Credit Purchase Flow
- Users buy credits via Stripe (existing)
- Credits used for number purchases
- Refunds not provided for early cancellation

---

## 9. API Documentation

All phone number endpoints are prefixed with `/api/v1/phone-numbers` and require authentication.

### Authentication

All endpoints require a valid JWT token in the `Authorization` header:

```bash
Authorization: Bearer <jwt_token>
```

Purchase, list, assign, and cancel endpoints require `check_billing_permissions` which validates:
- User is authenticated
- User belongs to the organization
- Organization has billing permissions

### Endpoints

#### 9.1 Search Available Phone Numbers

Search for phone numbers available for purchase from the provider.

**Endpoint:** `GET /api/v1/phone-numbers/available`

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| country_code | string | No | Country code (default: "US") |
| phone_number_type | string | No | Type: "local", "toll_free", "mobile" (default: "local") |
| area_code | string | No | Filter by area code |
| contains | string | No | Pattern to search for in number |
| page | integer | No | Page number (default: 1) |
| page_size | integer | No | Results per page, max 50 (default: 50) |

**Request Example:**

```bash
curl -X GET "http://localhost:8000/api/v1/phone-numbers/available?country_code=US&phone_number_type=local&area_code=555" \
  -H "Authorization: Bearer <token>"
```

**Response (200 OK):**

```json
{
  "items": [
    {
      "phone_number": "+15551234567",
      "phone_number_type": "local",
      "country_code": "US",
      "area_code": "555",
      "monthly_cost_credits": 200,
      "capabilities": {
        "voice": true,
        "sms": false,
        "mms": false
      },
      "locality": "San Francisco",
      "postal_code": "94102"
    }
  ],
  "total_count": 1,
  "page": 1,
  "page_size": 50,
  "total_pages": 1
}
```

**Response Model:** `PhoneNumberSearchResponse`

| Field | Type | Description |
|-------|------|-------------|
| items | array | List of available phone numbers |
| total_count | integer | Total results matching query |
| page | integer | Current page number |
| page_size | integer | Results per page |
| total_pages | integer | Total pages available |

---

#### 9.2 Purchase Phone Number

Purchase a phone number using organization credits.

**Endpoint:** `POST /api/v1/phone-numbers/purchase`

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| Authorization | Yes | Bearer token |
| organization_id | Yes | UUID of the organization (query param) |

**Request Body:**

```json
{
  "phone_number": "+15551234567",
  "country_code": "US",
  "phone_number_type": "local"
}
```

**Request Model:** `PhoneNumberPurchaseRequest`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| phone_number | string | Yes | Phone number to purchase in E.164 format |
| country_code | string | No | Country code (default: "US") |
| phone_number_type | string | No | Type: "local", "toll_free", "mobile" (default: "local") |

**Request Example:**

```bash
curl -X POST "http://localhost:8000/api/v1/phone-numbers/purchase?organization_id=<org_uuid>" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+15551234567", "country_code": "US", "phone_number_type": "local"}'
```

**Response (200 OK):**

```json
{
  "success": true,
  "phone_number": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "phone_number": "+15551234567",
    "provider": "twilio",
    "provider_sid": "PN1234567890abcdef",
    "phone_number_type": "local",
    "country_code": "US",
    "area_code": "555",
    "monthly_cost_credits": 200,
    "status": "purchased",
    "assigned_agent_id": null,
    "is_incoming_enabled": true,
    "is_outgoing_enabled": false,
    "organization_id": "987fcdeb-51a2-3d45-6789-0abcdef12345",
    "purchased_at": "2026-03-01T10:30:00Z",
    "cancelled_at": null,
    "created_at": "2026-03-01T10:30:00Z",
    "updated_at": "2026-03-01T10:30:00Z"
  },
  "message": "Successfully purchased +15551234567",
  "credit_balance_after": 1300
}
```

**Response Model:** `PhoneNumberPurchaseResponse`

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Whether purchase was successful |
| phone_number | PhoneNumber | Purchased phone number details |
| message | string | Success message |
| credit_balance_after | integer | Organization credit balance after purchase |

**Error Responses:**

- **400 Bad Request:** Invalid request (e.g., number already taken)
- **402 Payment Required:** Insufficient credits
- **500 Internal Server Error:** Server error

---

#### 9.3 List Organization Phone Numbers

Get all phone numbers owned by an organization.

**Endpoint:** `GET /api/v1/phone-numbers`

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| Authorization | Yes | Bearer token |
| organization_id | Yes | UUID of the organization (query param) |

**Request Example:**

```bash
curl -X GET "http://localhost:8000/api/v1/phone-numbers?organization_id=<org_uuid>" \
  -H "Authorization: Bearer <token>"
```

**Response (200 OK):**

```json
{
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "phone_number": "+15551234567",
      "provider": "twilio",
      "provider_sid": "PN1234567890abcdef",
      "phone_number_type": "local",
      "country_code": "US",
      "area_code": "555",
      "monthly_cost_credits": 200,
      "status": "active",
      "assigned_agent_id": "abc12345-6789-0abc-def0-123456789abc",
      "is_incoming_enabled": true,
      "is_outgoing_enabled": false,
      "organization_id": "987fcdeb-51a2-3d45-6789-0abcdef12345",
      "purchased_at": "2026-03-01T10:30:00Z",
      "cancelled_at": null,
      "created_at": "2026-03-01T10:30:00Z",
      "updated_at": "2026-03-01T10:30:00Z",
      "agent_name": "Sales Agent"
    },
    {
      "id": "223e4567-e89b-12d3-a456-426614174001",
      "phone_number": "+15559876543",
      "provider": "twilio",
      "provider_sid": "PN0987654321abcdef",
      "phone_number_type": "toll_free",
      "country_code": "US",
      "area_code": null,
      "monthly_cost_credits": 500,
      "status": "purchased",
      "assigned_agent_id": null,
      "is_incoming_enabled": true,
      "is_outgoing_enabled": false,
      "organization_id": "987fcdeb-51a2-3d45-6789-0abcdef12345",
      "purchased_at": "2026-02-15T14:20:00Z",
      "cancelled_at": null,
      "created_at": "2026-02-15T14:20:00Z",
      "updated_at": "2026-02-15T14:20:00Z",
      "agent_name": null
    }
  ],
  "total_count": 2,
  "unused_count": 1
}
```

**Response Model:** `PhoneNumberListResponse`

| Field | Type | Description |
|-------|------|-------------|
| items | array | List of phone numbers with agent details |
| total_count | integer | Total numbers owned |
| unused_count | integer | Numbers not assigned to any agent |

**Phone Number Status Values:**

| Status | Description |
|--------|-------------|
| available | Number is available for purchase |
| purchased | Number has been purchased |
| active | Number is active and assigned to agent |
| inactive | Number is inactive |
| cancelled | Number has been cancelled/released |

---

#### 9.4 Assign Phone Number to Agent

Assign a purchased phone number to a voice agent.

**Endpoint:** `POST /api/v1/phone-numbers/{phone_number_id}/assign`

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| Authorization | Yes | Bearer token |
| organization_id | Yes | UUID of the organization (query param) |

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| phone_number_id | UUID | ID of the phone number to assign |

**Request Body:**

```json
{
  "agent_id": "abc12345-6789-0abc-def0-123456789abc"
}
```

**Request Model:** `PhoneNumberAssignRequest`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| agent_id | UUID | Yes | UUID of the agent to assign the number to |

**Request Example:**

```bash
curl -X POST "http://localhost:8000/api/v1/phone-numbers/123e4567-e89b-12d3-a456-426614174000/assign?organization_id=<org_uuid>" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "abc12345-6789-0abc-def0-123456789abc"}'
```

**Response (200 OK):**

```json
{
  "success": true,
  "phone_number": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "phone_number": "+15551234567",
    "provider": "twilio",
    "provider_sid": "PN1234567890abcdef",
    "phone_number_type": "local",
    "country_code": "US",
    "area_code": "555",
    "monthly_cost_credits": 200,
    "status": "active",
    "assigned_agent_id": "abc12345-6789-0abc-def0-123456789abc",
    "is_incoming_enabled": true,
    "is_outgoing_enabled": false,
    "organization_id": "987fcdeb-51a2-3d45-6789-0abcdef12345",
    "purchased_at": "2026-03-01T10:30:00Z",
    "cancelled_at": null,
    "created_at": "2026-03-01T10:30:00Z",
    "updated_at": "2026-03-01T10:35:00Z"
  }
}
```

**Error Responses:**

- **404 Not Found:** Phone number not found or not owned by organization
- **409 Conflict:** Phone number is already assigned to another agent
- **400 Bad Request:** Phone number cannot be assigned (e.g., cancelled)

---

#### 9.5 Cancel Phone Number

Cancel (release) a phone number. This will release the number immediately and calls will stop working. No refund is provided.

**Endpoint:** `DELETE /api/v1/phone-numbers/{phone_number_id}`

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| Authorization | Yes | Bearer token |
| organization_id | Yes | UUID of the organization (query param) |

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| phone_number_id | UUID | ID of the phone number to cancel |

**Request Example:**

```bash
curl -X DELETE "http://localhost:8000/api/v1/phone-numbers/123e4567-e89b-12d3-a456-426614174000?organization_id=<org_uuid>" \
  -H "Authorization: Bearer <token>"
```

**Response (200 OK):**

```json
{
  "success": true,
  "message": "Phone number cancelled. It is now released and calls will not work."
}
```

**Error Responses:**

- **404 Not Found:** Phone number not found or not owned by organization
- **400 Bad Request:** Phone number cannot be cancelled

**Warning:** Cancelling a phone number will:
- Release the number immediately from Twilio
- Stop all incoming calls to that number
- Not provide a refund for the current billing period

---

### Credit Pricing

| Number Type | Monthly Cost |
|-------------|--------------|
| US Local | 200 credits |
| US Toll-Free | 500 credits |
| US Mobile | 200 credits |

---

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| PHONE_NUMBER_NOT_FOUND | 404 | Phone number not found |
| INSUFFICIENT_CREDITS | 402 | Organization has insufficient credits |
| ALREADY_ASSIGNED | 409 | Phone number is already assigned to an agent |
| INVALID_STATUS | 400 | Phone number status doesn't allow the operation |

---

*End of API Documentation v1.0*
