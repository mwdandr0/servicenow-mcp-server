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

## Important Notes

- The MCP server authenticates as `claude.desktop` (service account)
- Orders must explicitly specify `requested_for` to order on behalf of users
- The service account needs proper permissions to order on behalf of others
- Always confirm order details before submission
- Report both the REQ and RITM numbers to the user
