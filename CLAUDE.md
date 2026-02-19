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
