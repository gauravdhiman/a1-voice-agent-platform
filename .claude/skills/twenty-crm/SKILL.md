---
name: twenty-crm
description: "Guidance for interacting with Twenty CRM via its MCP server. Use this skill ONLY if Twenty CRM MCP tools (e.g. get_tool_catalog, execute_tool, learn_tools, or find_many_*/create_one_* tools) are available in the current environment."
---

# Twenty CRM MCP Agent Guidance

## Activation Condition

> **CRITICAL RULE**: Use this skill **ONLY if Twenty CRM tools are actively available** in your execution environment (e.g., presence of `get_tool_catalog`, `execute_tool`, `learn_tools`, or tools starting with `find_many_`, `create_one_`, `update_one_`, `delete_one_`). If Twenty CRM tools are not available or disabled, **do NOT attempt to invoke or simulate this skill**.

---

## 1. Twenty CRM MCP Architecture

Twenty CRM uses a **two-tier meta-tool architecture** over MCP:

1. **Top-Level Meta-Tools (7 Tools)**:
   - `get_tool_catalog`: Discover all available tools categorized by function.
   - `learn_tools`: Learn input schemas for tools.
   - `execute_tool`: Execute any underlying tool by name with arguments.
   - `list_object_metadata_names`: List all CRM object types in the workspace.
   - `list_skills`: List specialized guidance packages available in Twenty CRM.
   - `load_skills`: Load step-by-step instructions for complex domain workflows.
   - `search_help_center`: Search Twenty documentation and help center.

2. **Underlying CRM Tools (~240+ Tools)**:
   - Discovered dynamically via `get_tool_catalog`.
   - Executed through `execute_tool(toolName, arguments)`.

---

## 2. Standard Execution Lifecycle

Always follow this 3-step lifecycle when executing tasks in Twenty CRM:

```
Step 1: Discover Tools
   └─► get_tool_catalog({ categories: ["DATABASE_CRUD", "WORKFLOW"] })
       (or list_object_metadata_names() to find object names)

Step 2: Learn Tool Schemas (BATCH ALL IN ONE CALL)
   └─► learn_tools({ toolNames: ["find_many_people", "create_one_person"] })
       ⚠️ MANDATORY: Pass ALL required tool names in a SINGLE array.
       NEVER call learn_tools sequentially per tool!

Step 3: Execute Tool
   └─► execute_tool({ toolName: "create_one_person", arguments: { ... } })
```

---

## 3. Core Operating Rules & Gotchas

### Rule 1: Batch `learn_tools` Calls
- **DO NOT** make separate `learn_tools` calls for each tool.
- **DO**: Pass every tool name you will need in one array:
  ```json
  {
    "toolNames": ["find_many_companies", "create_one_company", "update_one_company"]
  }
  ```

### Rule 2: Top-Level Filter Arguments (No Wrapper Object)
- In `find_many_*`, `update_many_*`, `delete_many_*`, and `group_by_*`:
  - Pass filter criteria as **top-level arguments**.
  - **DO NOT** wrap filters in a `"filter"` object.
  - **DO NOT** place bare operators (`"ilike"`, `"eq"`) at the top level.
- **Correct**:
  ```json
  {
    "toolName": "find_many_people",
    "arguments": {
      "select": ["*"],
      "name": { "firstName": { "ilike": "%John%" } },
      "companyId": { "eq": "123e4567-e89b-12d3-a456-426614174000" }
    }
  }
  ```
- **Incorrect**:
  ```json
  {
    "toolName": "find_many_people",
    "arguments": {
      "filter": { "name": { "ilike": "%John%" } }  // ❌ Incorrect "filter" wrapper
    }
  }
  ```

### Rule 3: Always Include `select` Array
- All `find_many_*` and `find_one_*` tools **require** a `select` array.
- Use `["*"]` to fetch all scalar fields, or specify exact field names (`["id", "name", "companyId"]`).

### Rule 4: Required `position` Argument on Create
- All `create_one_*` tools for standard objects require `position`:
  ```json
  { "position": "last" } // or "first"
  ```

### Rule 5: Currency Field Conversion (`amountMicros`)
- Currency amounts in Twenty CRM are stored in **micros** (1 unit = 1,000,000 micros).
- **Example**: $100 USD = `100000000` micros.
  ```json
  {
    "annualRevenue": {
      "amountMicros": 100000000,
      "currencyCode": "USD"
    }
  }
  ```

### Rule 6: Workflow Triggers
- When creating workflows via `create_complete_workflow`:
  - Trigger `type` MUST be one of: `DATABASE_EVENT`, `MANUAL`, `CRON`, `WEBHOOK`.
  - **NEVER** use `"RECORD_CREATED"` (it is invalid). Use `"DATABASE_EVENT"` with `event: "created"`.

---

## 4. References & Detailed Guides

Refer to these supplementary guides for detailed schemas, filter syntax, and domain examples:

- [CRUD Operations & Schema Guide](references/crud-operations.md)
  - Detailed grammar for `find_many_*`, `find_one_*`, `create_one_*`, `update_one_*`, `delete_one_*`, `group_by_*`.
  - Filter operators (`eq`, `neq`, `in`, `like`, `ilike`, `startsWith`, `endsWith`, `gt`, `gte`, `lt`, `lte`, `is`).
  - Composite fields (Name, Address, Currency, Links, Phones).
  - Relationships & Foreign Keys (`companyId`, `pointOfContactId`, `ownerId`).

- [Meta-Tools, Workflows & Dashboards](references/meta-tools-and-workflows.md)
  - Full meta-tool signatures (`get_tool_catalog`, `learn_tools`, `execute_tool`, `list_object_metadata_names`, `list_skills`, `load_skills`).
  - Workflow creation rules & step types (`DATABASE_EVENT`, `CODE`, `AI_AGENT`).
  - Dashboard & Widget configuration (KPI, Bar, Line, Pie, Record Table).
  - Webhooks and Navigation items.

---

## 5. Quick Examples

### Example A: Searching People by Name & Company
```json
// Step 1: Learn schema
learn_tools({ "toolNames": ["find_many_people"] })

// Step 2: Execute search
execute_tool({
  "toolName": "find_many_people",
  "arguments": {
    "select": ["id", "name", "jobTitle", "companyId"],
    "name": { "lastName": { "ilike": "%Smith%" } },
    "limit": 10,
    "orderBy": [{ "name": { "lastName": "AscNullsFirst" } }]
  }
})
```

### Example B: Creating a Company & Contact
```json
// Step 1: Learn schemas
learn_tools({ "toolNames": ["create_one_company", "create_one_person"] })

// Step 2: Create company
execute_tool({
  "toolName": "create_one_company",
  "arguments": {
    "position": "last",
    "name": "Acme Innovations",
    "domainName": { "primaryLinkLabel": "acme.com", "primaryLinkUrl": "https://acme.com" },
    "annualRevenue": { "amountMicros": 5000000000, "currencyCode": "USD" }
  }
})

// Step 3: Create person linked to company
execute_tool({
  "toolName": "create_one_person",
  "arguments": {
    "position": "last",
    "name": { "firstName": "Alice", "lastName": "Johnson" },
    "emails": { "primaryEmail": "alice@acme.com" },
    "jobTitle": "VP of Engineering",
    "companyId": "<COMPANY_UUID_FROM_STEP_2>"
  }
})
```
