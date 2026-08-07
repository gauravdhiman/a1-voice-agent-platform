# Twenty CRM Meta-Tools, Workflows & Dashboards Guide

This reference provides detailed guidance for top-level meta-tools, Workflows, Dashboards, Webhooks, and System Metadata in Twenty CRM via MCP.

---

## 1. Top-Level Meta-Tools Reference

Twenty CRM exposes 7 primary meta-tools in MCP. These tools orchestrate tool discovery, schema learning, and execution.

### `get_tool_catalog`
- **Purpose**: Browse available tools by functional category.
- **Parameters**:
  ```typescript
  {
    categories?: ("DATABASE_CRUD" | "ACTION" | "WORKFLOW" | "METADATA" | "VIEW" | "DASHBOARD" | "NAVIGATION_MENU_ITEM" | "WEBHOOK")[]
  }
  ```
- **Usage Note**: Call this when starting a session or looking for specialized tools beyond basic CRUD.

---

### `learn_tools`
- **Purpose**: Retrieve precise input schemas for specific tools before invoking them.
- **Parameters**:
  ```typescript
  {
    toolNames: string[],          // REQUIRED — Array of exact tool names
    aspects?: ("description" | "schema")[]  // Default: ["description", "schema"]
  }
  ```
- **CRITICAL**: Pass ALL tools you plan to use in a SINGLE array. Never execute sequential `learn_tools` calls for individual tools.

---

### `execute_tool`
- **Purpose**: Execute an underlying tool by name.
- **Parameters**:
  ```typescript
  {
    toolName: string,             // REQUIRED — Exact tool name from catalog
    arguments: Record<string, any> // REQUIRED — Arguments matching learn_tools schema
  }
  ```

---

### `list_object_metadata_names`
- **Purpose**: List all custom and standard object metadata names in the workspace.
- **Parameters**: `{}`

---

### `list_skills` & `load_skills`
- **`list_skills`**: List specialized skill packages available in Twenty (e.g., `workflow-building`, `dashboard-building`, `data-manipulation`, `metadata-building`).
- **`load_skills`**:
  ```typescript
  { skillNames: string[] }  // e.g. ["workflow-building", "data-manipulation"]
  ```

---

## 2. Workflows (`WORKFLOW` Category)

Twenty CRM features a built-in workflow engine for automating business processes.

### Creating a Complete Workflow (`create_complete_workflow`)

Use `create_complete_workflow` to create a trigger, steps, and edges in a single call.

```json
{
  "toolName": "create_complete_workflow",
  "arguments": {
    "name": "Auto-Assign New High Value Deal",
    "trigger": {
      "type": "DATABASE_EVENT",
      "settings": {
        "objectName": "opportunity",
        "eventName": "opportunity.created"
      }
    },
    "steps": [
      {
        "id": "123e4567-e89b-12d3-a456-426614174001",
        "name": "Check Deal Value",
        "type": "CODE",
        "valid": true,
        "settings": { ... }
      }
    ],
    "edges": [
      { "from": "trigger", "to": "123e4567-e89b-12d3-a456-426614174001" }
    ]
  }
}
```

### Critical Workflow Rules
1. **Trigger Types**: MUST be `DATABASE_EVENT`, `MANUAL`, `CRON`, or `WEBHOOK`.
   - ❌ **NEVER** use `"RECORD_CREATED"` or `"RECORD_UPDATED"`. These are invalid. Use `DATABASE_EVENT`.
2. **Step IDs**: Every step MUST have a valid UUID as `id`.
3. **Trigger Edge ID**: Use `"trigger"` as the `from` step ID for edges originating from the trigger.
4. **Variable References**: Use Mustache syntax:
   - `{{trigger.fieldName}}` for trigger payload values.
   - `{{<step-id>.result.fieldName}}` for step outputs.

---

## 3. Dashboards (`DASHBOARD` Category)

Use `create_complete_dashboard` to build interactive dashboards with layouts, tabs, and widgets.

### Widget Configuration Types

1. **`AGGREGATE_CHART`** (KPI Card):
   - Shows single summary metric (e.g. Total Revenue, Total Deals).
   ```json
   {
     "type": "GRAPH",
     "objectName": "opportunity",
     "configuration": {
       "configurationType": "AGGREGATE_CHART",
       "aggregateFieldName": "amount",
       "aggregateOperation": "SUM"
     }
   }
   ```

2. **`BAR_CHART`**:
   - Compares metrics across groups (e.g. Deals by Stage).
   ```json
   {
     "type": "GRAPH",
     "objectName": "opportunity",
     "configuration": {
       "configurationType": "BAR_CHART",
       "aggregateFieldName": "id",
       "aggregateOperation": "COUNT",
       "primaryAxisGroupByFieldName": "stage",
       "layout": "VERTICAL"
     }
   }
   ```

3. **`LINE_CHART`**:
   - Shows trends over time.
   ```json
   {
     "type": "GRAPH",
     "objectName": "opportunity",
     "configuration": {
       "configurationType": "LINE_CHART",
       "aggregateFieldName": "amount",
       "aggregateOperation": "SUM",
       "primaryAxisGroupByFieldName": "createdAt"
     }
   }
   ```

4. **`PIE_CHART`**:
   - Shows distribution proportions.
   ```json
   {
     "type": "GRAPH",
     "objectName": "company",
     "configuration": {
       "configurationType": "PIE_CHART",
       "aggregateFieldName": "id",
       "aggregateOperation": "COUNT",
       "groupByFieldName": "addressCountry"
     }
   }
   ```

---

## 4. Webhooks (`WEBHOOK` Category)

Register outgoing webhooks for external integrations using `create_webhook`:

```json
{
  "toolName": "create_webhook",
  "arguments": {
    "targetUrl": "https://api.mycompany.com/webhooks/twenty",
    "description": "Notify internal service when a deal is closed",
    "operations": [
      { "kind": "record", "object": "opportunity", "event": "updated" },
      { "kind": "record", "object": "person", "event": "created" }
    ],
    "secret": "whsec_39f28a7c29b"
  }
}
```

---

## 5. Navigation Items (`NAVIGATION_MENU_ITEM` Category)

Pin objects, views, or links to the sidebar using `create_navigation_menu_item`:

- **Types**: `FOLDER`, `LINK`, `OBJECT`, `VIEW`, `RECORD`, `PAGE_LAYOUT`.
- **Scopes**: `user` (personal favorite) or `workspace` (shared with everyone).
