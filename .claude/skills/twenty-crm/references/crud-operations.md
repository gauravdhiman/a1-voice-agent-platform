# Twenty CRM CRUD Operations & Schema Guide

This reference provides detailed guidance for executing `DATABASE_CRUD` tools in Twenty CRM via MCP.

---

## 1. Tool Naming Conventions

For any CRM object (e.g. `person`, `company`, `opportunity`, `note`, `task`, `attachment`), Twenty CRM exposes up to 10 CRUD tools:

| Operation | Singular Form | Plural Form | Description |
|-----------|---------------|-------------|-------------|
| **Search / Read Many** | — | `find_many_{objects}` | Search records with filtering, pagination, and sorting. |
| **Get One** | `find_one_{object}` | — | Fetch single record by ID. |
| **Group / Aggregate** | — | `group_by_{objects}` | Aggregate records (COUNT, SUM, AVG, MIN, MAX) grouped by fields. |
| **Create One** | `create_one_{object}` | — | Create a single record. |
| **Create Many** | — | `create_many_{objects}` | Create up to 20 records in a batch. |
| **Update One** | `update_one_{object}` | — | Update single record by ID. |
| **Update Many** | — | `update_many_{objects}` | Apply identical updates to all records matching a filter. |
| **Upsert Many** | — | `upsert_many_{objects}` | Insert or update up to 20 records with distinct field values. |
| **Delete One** | `delete_one_{object}` | — | Soft-delete a single record by ID. |
| **Delete Many** | — | `delete_many_{objects}` | Soft-delete multiple records matching a filter. |

---

## 2. Standard Field Types & Composite Schemas

Twenty CRM uses structured composite objects for rich data fields. Always format these fields correctly when creating or updating records:

### A. Name Composite
```json
{
  "name": {
    "firstName": "John",
    "lastName": "Doe"
  }
}
```

### B. Emails Composite
```json
{
  "emails": {
    "primaryEmail": "john.doe@example.com",
    "additionalEmails": ["john.personal@example.com"]
  }
}
```

### C. Phones Composite
```json
{
  "phones": {
    "primaryPhoneNumber": "+15550199",
    "primaryPhoneCountryCode": "US",
    "primaryPhoneCallingCode": "+1",
    "additionalPhones": []
  }
}
```

### D. Address Composite
```json
{
  "address": {
    "addressStreet1": "123 Tech Boulevard",
    "addressStreet2": "Suite 400",
    "addressCity": "San Francisco",
    "addressState": "CA",
    "addressPostcode": "94107",
    "addressCountry": "United States",
    "addressLat": 37.7749,
    "addressLng": -122.4194
  }
}
```

### E. Currency / Revenue Composite (`amountMicros`)
> **Note**: Currency amounts use **micros** (1 unit = 1,000,000 micros).
```json
{
  "annualRevenue": {
    "amountMicros": 25000000000,  // $25,000.00
    "currencyCode": "USD"
  }
}
```

### F. Links Composite
```json
{
  "linkedinLink": {
    "primaryLinkLabel": "linkedin.com/in/johndoe",
    "primaryLinkUrl": "https://www.linkedin.com/in/johndoe",
    "secondaryLinks": []
  }
}
```

---

## 3. Filtering Syntax (`find_many_*`)

Filtering fields are passed as **top-level keys** on the arguments object.

### Operators Available Per Field Type

| Field Type | Available Operators | Example |
|------------|---------------------|---------|
| **String** | `eq`, `neq`, `in`, `like`, `ilike`, `startsWith`, `endsWith`, `is` | `"name": { "ilike": "%Acme%" }` |
| **Number** | `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `in`, `is` | `"amountMicros": { "gte": 10000000 }` |
| **DateTime** | `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `is` | `"createdAt": { "gte": "2026-01-01T00:00:00Z" }` |
| **Enum** | `eq`, `neq`, `in`, `is` | `"stage": { "in": ["MEETING", "PROPOSAL"] }` |
| **Null Check** | `is: "NULL"` or `is: "NOT_NULL"` | `"companyId": { "is": "NOT_NULL" }` |

### Logical Combinators (`and`, `or`, `not`)

You can combine filter conditions using top-level `and`, `or`, and `not`:

```json
{
  "select": ["id", "name", "stage", "amount"],
  "and": [
    { "stage": { "eq": "PROPOSAL" } },
    { "amount": { "amountMicros": { "gte": 50000000 } } }
  ],
  "or": [
    { "ownerId": { "eq": "user-uuid-1" } },
    { "ownerId": { "eq": "user-uuid-2" } }
  ]
}
```

---

## 4. Sorting & Pagination

### Pagination
- `limit`: Maximum number of records to return (default: `10`, max: `100`).
- `offset`: Number of records to skip (default: `0`).

### Sorting (`orderBy`)
- Directions: `AscNullsFirst`, `AscNullsLast`, `DescNullsFirst`, `DescNullsLast`.
- **Scalar fields**:
  ```json
  "orderBy": [{ "createdAt": "DescNullsLast" }]
  ```
- **Composite fields** (use nested object, NOT dot-notation):
  ```json
  "orderBy": [{ "name": { "lastName": "AscNullsFirst" } }]
  ```

---

## 5. Standard Object Field Cheat Sheet

### Person (`person` / `people`)
- **Key Fields**: `name` (composite), `emails` (composite), `phones` (composite), `jobTitle` (string), `companyId` (UUID FK), `linkedinLink` (composite), `avatarUrl` (string).
- **Foreign Keys**: `companyId`, `ownerId`, `lastMeetingId`, `lastEmailId`, `lastContactById`.

### Company (`company` / `companies`)
- **Key Fields**: `name` (string), `domainName` (composite link), `address` (composite), `annualRevenue` (composite currency), `linkedinLink` (composite link).
- **Foreign Keys**: `accountOwnerId`, `lastContactItemMessageId`, `lastContactItemCalendarEventId`.

### Opportunity (`opportunity` / `opportunities`)
- **Key Fields**: `name` (string), `stage` (enum: `NEW`, `SCREENING`, `MEETING`, `PROPOSAL`, `CUSTOMER`), `amount` (composite currency), `closeDate` (ISO datetime).
- **Foreign Keys**: `companyId`, `pointOfContactId`, `ownerId`.

### Task (`task` / `tasks`)
- **Key Fields**: `title` (string), `status` (enum: `TODO`, `IN_PROGRESS`, `DONE`), `dueAt` (ISO datetime).
- **Foreign Keys**: `assigneeId`.

### Note (`note` / `notes`)
- **Key Fields**: `title` (string), `body` (markdown/text string).
