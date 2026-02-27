# ServiceNow MCP Server - Claude Instructions

This file contains persistent instructions for Claude Desktop when using the ServiceNow MCP server.

## Service Catalog Ordering Workflow

When a user requests to order something from the ServiceNow Service Catalog, follow this workflow:

### 1. Identify the User
**ALWAYS ask who the order is for** if not explicitly mentioned. Do not default to the service account.

**Example prompts:**
- "Who is this order for? (Please provide email, username, or name)"
- "I'll help you order that. Who should I place this order for?"

**Get user context:**
```
get_user_context("user.email@example.com")
```
This returns the user's sys_id needed for the `requested_for` parameter.

### 2. Search for Item
Use `search_catalog_items` to find the requested item:
```
search_catalog_items("search term")
```

### 3. Get Item Details
Use `get_catalog_item_details` to see what variables are needed:
```
get_catalog_item_details("catalog_item_sys_id")
```

### 4. Collect Variable Values
For each variable marked as `mandatory: true`, collect the value from the user.
- Ask clear questions based on the `question` field
- For Select/Multiple Choice variables, present the available `choices`
- For Reference variables, use `lookup_reference_field` if needed

### 5. Submit Order
**CRITICAL:** Always include the `requested_for` parameter with the user's sys_id:
```
order_catalog_item(
  catalog_item_sys_id="...",
  variables='{"var1": "value1", "var2": "value2"}',
  requested_for="user_sys_id_from_step_1"
)
```

### 6. Confirm Submission
Report back to the user with:
- Request number (REQ...)
- Request item number (RITM...)
- Who the order was placed for
- Summary of what was ordered

## Common Mistakes to Avoid

❌ **DON'T:** Submit orders without specifying `requested_for` - this will default to the service account (claude.desktop)

✅ **DO:** Always ask who the order is for and use `get_user_context` to get their sys_id

❌ **DON'T:** Assume the user is ordering for themselves unless they explicitly say so

✅ **DO:** Ask "Who is this order for?" as part of the natural conversation flow

## Example Conversation Flow

```
User: "I need to order a laptop"

Claude: "I'll help you order a laptop. First, who is this order for?
        (Please provide their email or username)"

User: "It's for beth.anglin@example.com"

Claude: [Calls get_user_context("beth.anglin@example.com")]
        [Calls search_catalog_items("laptop")]

        "I found 3 laptop options for Beth Anglin:
        1. Standard Laptop - $1,200
        2. Development Laptop - $1,800
        3. MacBook Pro - $2,499

        Which one would Beth like?"

User: "The MacBook Pro"

Claude: [Calls get_catalog_item_details(macbook_sys_id)]

        "I'll need a few details for the MacBook Pro order:
        1. Storage size? (256GB, 512GB +$200, 1TB +$500)
        2. Memory? (16GB, 32GB +$400, 64GB +$800)
        3. What color? (Space Gray, Silver)
        4. Justification/business reason?"

User: "512GB, 32GB, Space Gray, and it's for a new developer hire"

Claude: [Calls order_catalog_item with requested_for=beth_sys_id]

        "✅ Order submitted successfully!

        Request: REQ0010001
        Item: RITM0010001
        For: Beth Anglin (beth.anglin@example.com)
        Item: MacBook Pro (Space Gray, 512GB, 32GB RAM)
        Total: $3,099
        Status: Submitted for approval"
```

## Order Tracking

When users ask about order status:
- Use `get_request_status("REQ...")` or `get_request_status("RITM...")`
- Use `list_my_requests("user@example.com")` to see all requests for a user

## Pre-Flight Validation Workflow

When creating ANY record (incidents, change requests, catalog orders, etc.), follow this validation workflow:

### 1. Discover Mandatory Fields FIRST
Before creating a record, call `get_form_mandatory_fields` to discover ALL required fields:

```
get_form_mandatory_fields("incident")
```

This returns:
- Dictionary mandatory fields (always required)
- UI Policy mandatory fields (conditionally required)
- Conditions for when fields become mandatory

### 2. Collect All Required Data
Based on the mandatory fields discovered:
- Ask the user for any missing required fields
- Explain which fields are mandatory and why
- For UI Policy fields, explain the conditions

### 3. Validate BEFORE Submission
Always call `validate_record_data` before creating records:

```
validate_record_data(
    "incident",
    '{"short_description": "...", "caller_id": "...", "priority": "1"}',
    strict_mode=True
)
```

### 4. Only Submit If Validation Passes
If `validate_record_data` returns `"valid": true`, proceed with creation.
If validation fails, report the missing fields to the user and ask for them.

### Example Validation Flow

```
User: "Create a P1 incident for database outage"

Claude:
1. Calls get_form_mandatory_fields("incident")
2. Sees: short_description, caller_id, impact (for P1) are required
3. Asks: "I need a few more details:
   - Who is the caller?
   - What's the impact? (1-3)"
4. User provides: caller=john@example.com, impact=1
5. Calls validate_record_data with all fields
6. Validation passes ✅
7. Calls create_incident
8. Reports success
```

## Record Creation Best Practices

✅ **DO:**
- Always discover mandatory fields first (`get_form_mandatory_fields`)
- Always validate before submission (`validate_record_data`)
- Ask for missing fields with clear explanations
- Use `strict_mode=True` for critical records

❌ **DON'T:**
- Submit records without validation
- Ignore UI Policy mandatory fields
- Assume field requirements (they vary by table and conditions)

## AI Agent Performance Analysis Workflow

When analyzing AI Agent conversation performance, follow this workflow to handle different discovery methods:

### Standard AI Agents (Directly Configured)

For agents configured directly in AI Agent Hub:

1. Use `analyze_conversation("conversation_sys_id")` directly
2. The tool will find the execution plan via the agent reference
3. Analysis proceeds normally

### Virtual Agent (VA) Discovered AI Agents **[SPECIAL CASE]**

**Problem:** VA-discovered agents show up in execution plans with `agent` field = null or empty

**How to Identify:**
- Agent was discovered through Virtual Agent
- Execution plan shows `agent` as null/empty
- Normal analysis workflow fails to find execution plan

**Solution - Special Lookup Workflow:**

1. **Query the execution task table** to find the execution plan:
   ```
   snow_query(
     table="sn_aia_execution_task",
     query="description=Conversational Support Agent^order=200",
     fields="execution_plan,sys_id,description,order"
   )
   ```

2. **Get the execution plan sys_id** by dot-walking:
   - Take the `execution_plan` field from the result
   - This is the execution plan sys_id you need

3. **Continue with normal analysis** using this execution plan sys_id

### Example VA Agent Analysis

```
User: "Analyze the performance of my Conversational Support Agent"

Claude:
1. Attempts analyze_conversation(conversation_id)
2. Notices execution plan has agent=null (VA-discovered)
3. Queries sn_aia_execution_task:
   - description = "Conversational Support Agent"
   - order = 200
4. Gets execution_plan sys_id from result
5. Proceeds with performance analysis using this execution plan
6. Reports findings as normal
```

### Why This Happens

- **VA-discovered agents** don't have a direct agent record
- They're discovered dynamically through Virtual Agent topics
- Execution plans reference them differently than standard agents
- The execution task table maintains the connection

### When to Use This Workaround

Use the `sn_aia_execution_task` lookup when:
- ✅ Agent shows as null/empty in execution plan
- ✅ Agent was discovered via Virtual Agent
- ✅ User mentions "Conversational Support Agent" or similar VA agent
- ✅ Normal agent lookup fails

Continue with standard workflow when:
- ❌ Agent has a proper agent reference in execution plan
- ❌ Agent was created directly in AI Agent Hub
- ❌ analyze_conversation works normally

## Important Notes

- The MCP server authenticates as `claude.desktop` (service account)
- Orders must explicitly specify `requested_for` to order on behalf of users
- The service account needs proper permissions to order on behalf of others
- Always confirm order details before submission
- Report both the REQ and RITM numbers to the user
- For VA-discovered AI Agents, use the sn_aia_execution_task lookup workaround

---

## AI Agent Building Workflow

When a user wants to build a new AI Agent in ServiceNow, follow this conversational workflow. The experience is collaborative and conversational — ask questions, present options, and get approval at each key step before proceeding.

### Step 1: Establish Context (4 Required Questions)

Ask these questions before generating anything:

1. **Guidance level**: How much detail do they want? High (explain every step), Medium (key checkpoints), or Low (essentials only)?
2. **Deployment platform**: Virtual Agent / Teams / Slack (VA) or Now Assist Platform (NAP for multi-agent workflows)?
3. **Primary purpose**: What should the agent do? (e.g., "IT support for password resets and access issues")
4. **Target users**: Who interacts with it? (employees, customers, IT staff, managers, etc.)

Also ask: **What team or group currently handles this work?** — needed for the discovery step.

### Step 2: Environment Discovery

Call `discover_agent_build_context` with the use case and optionally the assignment group:

```
discover_agent_build_context(
  use_case="IT Support",
  assignment_group="Desktop Support",
  time_range_days=365
)
```

Present findings to the user:
- Total agents on the instance + domains already covered
- Top work categories by volume and percentage
- Ask: "Should the agent focus on [top categories], or all [use case] work?"

**CRITICAL**: Store `existing_ai_agents.agent_names` — check every proposed name against this list.

### Step 3: Generate Agent Name (3 Options, Uniqueness Required)

Generate 3 name options following these rules:
- Maximum 100 characters
- NEVER suggest a name that matches any entry in `existing_ai_agents.agent_names`
- Follow `name_patterns` from discovery (e.g., if agents use "...Agent" suffix, follow that)
- Each option should reflect different naming approaches (descriptive, audience-focused, capability-focused)

Present each with a brief rationale. Get user selection before proceeding.

### Step 4: Generate Description (≤2000 characters — ALWAYS VALIDATE)

**For VA agents**: Include natural language keywords from `nl_discovery_keywords` — these drive NL Discovery routing.
**For NAP agents**: Describe capabilities and orchestration role.

Present with explicit character count: `"**Description** (X of 2000 characters):"`

If over 2000: optimize automatically and re-present. Never present over-limit content.
Get approval before proceeding.

### Step 5: Generate Role (≤2000 characters — ALWAYS VALIDATE)

Define the agent's expertise, knowledge domain, operational approach, and constraints.
Use `user_language_patterns` and `resolution_approaches` from discovery for authenticity.

Present with character count. Validate, optimize if needed, get approval.

### Step 6: Generate Agent Instructions (No character limit)

Follow these prompt engineering standards:
- **Token anchor** critical constraints at the top (character limits, required behaviors)
- Use `workflow_steps` from discovery as the numbered workflow structure
- Include **verification gates** after every major step — analytical report format, NEVER checkbox lists
- Use action keywords consistently: analyze, evaluate, fetch, generate, verify
- Incorporate `user_phrases` from discovery as sample user language examples
- Include explicit tool usage instructions for each recommended tool
- Include error handling and edge cases

Present in a code block for easy copying. Get approval before creating.

### Step 7: Get Explicit Approval Before Creating

Summarize all four components and ask:
"Are you ready for me to create this agent in ServiceNow? (Yes/No)"

Do NOT call `create_ai_agent` until the user explicitly confirms.

### Step 8: Create the Agent

```
create_ai_agent(
  name="[Approved name]",
  description="[Approved description]",
  agent_role="[Approved role]",
  agent_instructions="[Approved instructions]"
)
```

Return the Agent Studio link to the user as a clickable URL immediately.

### Step 9: Tool Provisioning

Present the `tool_recommendations_detailed` from discovery:

"Your agent needs tools to work. Based on [X] records analyzed, I recommend:
1. **[Tool Type]**: [Why needed] — [Example usage]
2. **[Tool Type]**: [Why needed] — [Example usage]
..."

For each tool, determine the best path:
1. Call `list_agent_tools(tool_type="[type]")` to search for existing matches
2. **Strong match found** → `clone_tool(source_sys_id, new_name, target_agent_sys_id=agent_sys_id)` — preferred
3. **No match** → `create_tool()` + `add_tool_to_agent()`
4. **Platform-native** (Knowledge Graph, Search, Web Search) → `add_tool_to_agent()` directly

Report each result: "✅ [Tool name] attached" or "⚠️ [Tool name] needs manual configuration"

### Post-Delivery

After tools are provisioned:
- Confirm agent Studio link is accessible
- Provide 5 test queries from `user_phrases` discovery data
- For VA deployments: remind to verify NL Discovery keywords in the description
- Offer next steps: testing, deployment to Teams/Slack, building additional agents

---

## Character Limit Rules — Always Enforce

| Field | Limit | If Exceeded |
|---|---|---|
| Agent Name | 100 chars | Shorten and re-present |
| Description | 2000 chars | Optimize (remove non-essential), re-present |
| Role | 2000 chars | Condense while preserving core expertise |
| Instructions | No limit | No validation needed |

## Name Uniqueness Rule — Always Enforce

Before presenting ANY name option, verify it does not appear in `existing_ai_agents.agent_names` from `discover_agent_build_context`. Generate a different name if any conflict exists. Never present a duplicate name to the user.

---

## Dashboard & Report Generation

When a user asks to "report on", "dashboard", "visualize", "show me a summary of", "build a report", or says "make this pretty" / "turn this into HTML", generate a **single self-contained HTML file** using the style below.

### When to Generate a Report

| Trigger | Action |
|---|---|
| "Build a report on open changes" | Query the data → generate HTML |
| "Show me a dashboard for P1 incidents" | Query with filters → generate HTML |
| "Visualize this week's approvals" | Query `sysapproval_approver` → generate HTML |
| "Make this pretty" / "format as HTML" | Reformat data already in conversation — **do NOT re-query** |

### Visual Style — Always Use This

- **Background**: `#0d1117` · Panels: `#161b24` · Borders: `rgba(255,255,255,0.08)`
- **Priority colors**: Critical = `#f85149` · High = `#d97706` · Moderate = `#388bfd` · Low/Planning = `#6e7681`
- **State colors**: Open/Active = `#388bfd` · Resolved = `#3fb950` · On Hold = `#d29922` · Closed = `#6e7681`
- **Font**: `system-ui, -apple-system, sans-serif` for labels · `'SF Mono', 'Fira Code', monospace` for numbers and IDs
- **No gradients, shadows, or decorative elements** — dense, data-forward, utilitarian

### Charts — Always Load from CDN

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
```

Chart types: area/line for time-series, doughnut for distribution, horizontal bar for assignee/group breakdown.

### Standard Layout

1. **Fixed top nav bar** — logo, clickable tab navigation (Dashboard / Data / Patterns / Metrics / Settings), live pulsing green dot, instance name + timestamp
2. **Fixed left sidebar** — mirrors nav tabs with icons, highlights active tab
3. **Search + filter chips** — keyword search bar, chip buttons for quick filters (All, Critical, High, New, On Hold, or relevant states)
4. **Dashboard tab** — row of 4 metric tiles → severity/state count bar with stacked percentage bar → time-series area chart → 3 bottom panels (scrollable record list · assignee/group bar charts · cluster spotlight for related records)
5. **Data tab** — full sortable table (click column header to sort), click any row to open a **detail modal** showing all fields
6. **Patterns tab** — auto-detected clusters/anomalies (same app, same assignee, same time window, repeated errors)
7. **Metrics tab** — doughnut + bar charts for priority, state, and assignee distribution
8. **Settings tab** — instance info, data summary, toggle preferences
9. **Detail modal** — all record fields formatted, closes on Escape or click outside

### Supported Data Types

Use identical layout and style for **any** ServiceNow data:
- Incidents · Changes · Problems · Tasks
- Approvals · Catalog Requests
- AI Agent conversations · Knowledge Articles
- Any custom table query

### Output Rule

Always produce a **single self-contained HTML file** — all CSS and JS inline, no external dependencies except Chart.js CDN. The file should be saveable and shareable on its own.
