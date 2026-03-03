# Service Catalog Ordering Guide

A comprehensive guide to using ServiceNow catalog ordering tools in Claude Desktop.

## Overview

The Service Catalog tools enable you to browse, search, order, and track ServiceNow catalog items directly from Claude Desktop. These tools provide complete end-to-end ordering workflow from discovery to fulfillment tracking.

**Phase 1 - Discovery Tools (5 tools):** Browse and explore catalog items
**Phase 2 - Order Submission Tools (3 tools):** Submit orders and track requests

**Total:** 8 Service Catalog tools available

---

## Phase 1: Discovery Tools

### 1. `list_catalog_items`

Browse all active catalog items in your ServiceNow instance.

**Parameters:**
- `limit` (optional, default 50): Max items to return
- `category_sys_id` (optional): Filter by specific category
- `include_producers` (optional, default true): Include record producers

**Example Queries:**
```
List all catalog items
Show me the first 20 catalog items
List catalog items in category abc123
Show standard catalog items only (no record producers)
```

**Returns:** Array of items with name, description, category path, pricing

---

### 2. `search_catalog_items`

Search catalog items by keyword.

**Parameters:**
- `search_term` (required): Keywords to search
- `limit` (optional, default 20): Max results
- `include_producers` (optional, default true)

**Example Queries:**
```
Search catalog for "laptop"
Find catalog items containing "iphone"
Search for "incident" with limit 10
```

**Returns:** Matching items with relevance to search term

---

### 3. `get_catalog_item_details`

Get complete metadata for a specific catalog item. This is the most comprehensive tool and returns everything needed to understand what information is required to order an item.

**Parameters:**
- `catalog_item_sys_id` (required): The sys_id of the item

**Example Queries:**
```
Get details for catalog item abc123...
Show me complete information for item abc123...
What variables does catalog item abc123... require?
```

**Returns:** Complete JSON including:

#### Basic Info
- Name, description, type
- Table name (for record producers)

#### Pricing
- Base price and display value
- Recurring price and frequency
- List price and cost
- Has pricing flag

#### Variables
For each variable:
- Name and question text
- Type (Select Box, Reference, Text, etc.)
- Mandatory flag
- Help text and examples
- **For Select/Dropdown:** List of choices with pricing per option
- **For Reference:** Table name and qualifier
- **For Text:** Max length

#### Variable Sets
- Single-row sets (grouped variables)
- Multi-row sets (repeatable row groups)
- Minimum/maximum rows for multi-row sets

#### UI Policies
- Trigger conditions (what values activate the policy)
- Policy actions (fields that become visible/mandatory)
- Conditional field logic

#### Price-Affecting Fields
- Variables where choices have different prices
- Checkbox options that add cost

**Use Cases:**
1. **Before ordering:** Understand what information is needed
2. **Smart forms:** Present only relevant questions based on user selections
3. **Cost estimation:** Calculate total cost based on user choices
4. **Validation:** Ensure all mandatory fields are collected

---

### 4. `lookup_reference_field`

Query reference tables to get available options for Reference type variables.

**Parameters:**
- `reference_table` (required): Table to query (e.g., "sys_user")
- `reference_qualifier` (optional): Encoded query filter
- `search_term` (optional): Search keyword
- `limit` (optional, default 10): Max results

**Example Queries:**
```
Lookup sys_user table for "beth"
Search cmdb_ci table for "laptop"
Find users in sys_user where email contains "example"
Lookup core_company table with limit 20
```

**Returns:** Array of records with sys_id, display_value, and common fields

**Note:** JavaScript qualifiers (starting with `javascript:`) cannot be evaluated client-side and will be noted in the response.

---

### 5. `get_user_context`

Get user details for auto-populating order fields.

**Parameters:**
- `user_identifier` (required): Email, user_name, or sys_id

**Example Queries:**
```
Get user context for beth.anglin@example.com
Show me details for user beth.anglin
Get user info for sys_id abc123...
```

**Returns:** User details including:
- sys_id, user_name, name, email
- Title and department
- Location and manager
- Phone numbers

**Use Cases:**
- Auto-populate "requested_for" fields
- Pre-fill location-based fields
- Set default department/cost center

---

## Complete Workflow Example

Here's how to use these tools together to explore a catalog item:

### Step 1: Find Items
```
User: "I need to order a laptop"

Agent: [Calls search_catalog_items("laptop")]

Response: "I found 3 laptop items:
1. MacBook Pro Request - $2,499
2. Standard Laptop - $1,200
3. Development Laptop - $1,800"
```

### Step 2: Get Details
```
User: "Tell me about the MacBook Pro"

Agent: [Calls get_catalog_item_details(macbook_sys_id)]

Response: "MacBook Pro Request details:
- Base Price: $2,499
- Required Information:
  • Purpose/Justification (text)
  • Storage Size (128GB, 256GB +$100, 512GB +$300)
  • Memory (16GB, 32GB +$200)
  • Delivery Location (reference: sys_user)
  • Cost Center (reference: finance_cost_center)"
```

### Step 3: Lookup Reference Options
```
User: "What delivery locations are available?"

Agent: [Calls lookup_reference_field("sys_user", search_term="beth")]

Response: "Available users:
- Beth Anglin (beth.anglin@example.com) - Chicago Office
- Beth Cooper (beth.cooper@example.com) - New York Office"
```

### Step 4: Get User Context
```
Agent: [Calls get_user_context("beth.anglin@example.com")]

Response: "User details:
- Name: Beth Anglin
- Location: Chicago Office - Floor 3
- Department: Engineering
- Manager: Mike Chen"
```

### Step 5: Calculate Total Cost
```
Based on selections:
- MacBook Pro Base: $2,499
- 512GB Storage: +$300
- 32GB Memory: +$200
─────────────────
Total: $2,999
```

---

## Understanding Variables

### Variable Types

| Type | Description | Example |
|------|-------------|---------|
| Single Line Text | Short text input | Project name |
| Multi Line Text | Long text input | Justification |
| Select Box | Dropdown menu | Storage size |
| Multiple Choice | Radio buttons | Priority level |
| Check Box | Yes/No checkbox | Add warranty? |
| Reference | Lookup to another table | User, Location, CI |
| Date | Date picker | Start date |
| Date/Time | Date and time picker | Scheduled time |

### Mandatory vs Optional

- **Mandatory:** Must be filled before submission (red asterisk in UI)
- **Optional:** Can be left blank

Use the `mandatory` flag in variable metadata to determine requirements.

### Variable Sets

**Single-Row Variable Sets:**
- Group related variables together
- Display as a section/fieldset
- All variables in set are shown together

**Multi-Row Variable Sets:**
- Allow adding multiple rows of the same variables
- Example: "Add multiple products" with name/quantity per row
- Check `min_rows` and `max_rows` for constraints

---

## Understanding UI Policies

UI Policies make fields conditionally visible or mandatory based on other field values.

### How They Work

1. **Trigger Conditions:** User selects a specific value
2. **Policy Actions:** Other fields become visible/mandatory

### Example

```
Trigger: when_do_you_need_this = "specific_time_frame"
Actions:
  - start_date: becomes mandatory
  - end_date: becomes mandatory
```

**In Practice:**
1. User answers "When do you need this?"
2. If they select "Specific time frame"
3. Ask for start and end dates immediately

### Parsing UI Policies

The `get_catalog_item_details` tool returns parsed UI policies with:
- `trigger_conditions`: Array of variable/value pairs that activate the policy
- `policy_actions`: Array of fields affected and how (visible, mandatory, read-only)

**Best Practice:** After collecting each field, check if any UI policies are triggered and gather newly required fields immediately.

---

## Understanding Pricing

### Price Fields

| Field | Description |
|-------|-------------|
| base_price | One-time cost of the item |
| recurring_price | Ongoing cost (monthly/annually) |
| list_price | MSRP before discounts |
| cost | Internal cost to organization |

### Choice-Level Pricing

Some Select Box / Multiple Choice fields have different prices per option:

```json
{
  "choices": [
    {"text": "128 GB", "value": "128gb", "price": "0", "price_display": "Included"},
    {"text": "256 GB", "value": "256gb", "price": "100", "price_display": "+$100.00"},
    {"text": "512 GB", "value": "512gb", "price": "300", "price_display": "+$300.00"}
  ]
}
```

**Tracking Total Cost:**
```
Running Total = base_price
For each selection with price:
  Running Total += choice.price
```

### Checkbox Pricing

Checkboxes can add flat fees:
```
"Add AppleCare+ Protection?" = Yes → +$199
```

---

## Common Patterns

### Pattern 1: Browse and Explore
```
User: "What can I order?"
→ list_catalog_items()
→ Show categories and popular items
```

### Pattern 2: Targeted Search
```
User: "I need a laptop"
→ search_catalog_items("laptop")
→ Present matching items with prices
```

### Pattern 3: Deep Dive
```
User: "Tell me about item X"
→ get_catalog_item_details(sys_id)
→ Show all variables, pricing, requirements
```

### Pattern 4: Reference Lookup
```
User selecting Reference field: "Which location?"
→ lookup_reference_field("cmn_location", search_term="chicago")
→ Show matching locations
```

### Pattern 5: Auto-Population
```
Before asking questions:
→ get_user_context(user_email)
→ Pre-fill location, department, manager fields
```

---

## Limitations & Notes

### Phase 1 (Current)

✅ **Available:**
- Browse and search catalog items
- View complete item metadata
- Understand pricing and variables
- Lookup reference field options
- Get user context

❌ **Not Yet Available:**
- Actual order submission
- Shopping cart management
- Request status tracking
- Approval workflow visibility

### JavaScript Reference Qualifiers

Some Reference fields use `javascript:` expressions to filter options. These cannot be evaluated client-side and will be noted in responses. The raw qualifier is returned for informational purposes.

### Large Items

Items with 50+ variables may return large JSON responses. Consider:
- Asking users to narrow down what they need
- Presenting variables in stages
- Focusing on mandatory fields first

---

## Troubleshooting

### "Catalog item not found"

**Cause:** Invalid sys_id or inactive item
**Solution:** Use search_catalog_items to find the correct sys_id

### "Reference table not accessible"

**Cause:** User lacks read access to the reference table
**Solution:** Check ServiceNow ACLs or use a service account with broader permissions

### "No variables returned"

**Possible Reasons:**
1. Item has no variables (click-through item)
2. Variables are in variable sets only
3. API permissions issue

**Solution:** Check item type and variable set configuration

### Empty choice lists

**Cause:** Choices not configured or ACL restrictions
**Solution:** Verify choices exist in question_choice table

---

## API Endpoints Used

These tools use standard ServiceNow Table API endpoints:

| Tool | Primary Tables |
|------|----------------|
| list_catalog_items | sc_cat_item, sc_category |
| search_catalog_items | sc_cat_item |
| get_catalog_item_details | sc_cat_item, item_option_new, item_option_new_set, io_set_item, question_choice, catalog_ui_policy, catalog_ui_policy_action |
| lookup_reference_field | Any table (dynamic) |
| get_user_context | sys_user |

**API Format:** `/api/now/table/{table}?sysparm_query=...`

---

## Phase 2: Order Submission Tools

### 6. `order_catalog_item`

Submit a Service Catalog order with variables.

**Parameters:**
- `catalog_item_sys_id` (required): The sys_id of the catalog item
- `variables` (optional): JSON string of variable key-value pairs (default "{}")
- `requested_for` (optional): User sys_id to order for (defaults to current user)
- `quantity` (optional, default 1): Number of items to order
- `special_instructions` (optional): Additional notes or instructions

**Example Queries:**
```
Order iPhone 13 item abc123... with variables {"color": "green", "storage": "256"}
Submit an order for catalog item xyz789... for user beth.anglin@example.com
Order 2 laptops from catalog item def456...
```

**Returns:** Request number (REQ...), request item number (RITM...), and order status

**Example Response:**
```json
{
  "success": true,
  "order_submitted": true,
  "request_number": "REQ0010001",
  "request_sys_id": "abc123...",
  "request_item_number": "RITM0010001",
  "request_item_sys_id": "xyz789...",
  "order_status": "Open",
  "catalog_item": "ec80c13297968d1021983d1e6253af32",
  "quantity": 1,
  "variables_submitted": {
    "color": "green",
    "storage": "256"
  }
}
```

**Use Cases:**
1. **Direct ordering:** Submit order immediately after gathering variables
2. **Batch ordering:** Submit multiple orders programmatically
3. **Order on behalf:** Submit orders for other users (with proper permissions)

---

### 7. `get_request_status`

Track the status and progress of a Service Catalog request.

**Parameters:**
- `request_number` (required): Request number (REQ...) or request item number (RITM...)

**Example Queries:**
```
Get status of request REQ0010001
Check on RITM0010001
What's the status of my request REQ0010001?
```

**Returns:** Complete request details including state, stage, approval status, assignments

**Example Response:**
```json
{
  "success": true,
  "request_number": "REQ0010001",
  "sys_id": "abc123...",
  "state": "Work in Progress",
  "stage": "Fulfillment",
  "approval": "Approved",
  "active": true,
  "opened_at": "2024-01-15 10:30:00",
  "opened_by": "System Administrator",
  "requested_for": "Beth Anglin",
  "short_description": "Apple iPhone 13",
  "assignment_group": "Hardware Fulfillment",
  "assigned_to": "John Smith",
  "request_items": [
    {
      "number": "RITM0010001",
      "sys_id": "xyz789...",
      "state": "Work in Progress",
      "stage": "Fulfillment",
      "short_description": "Apple iPhone 13 - Green 256GB"
    }
  ]
}
```

**Use Cases:**
1. **Track fulfillment:** Monitor order progress from submission to completion
2. **Check approvals:** See if request is pending approval
3. **View assignments:** Identify who is working on the request

---

### 8. `list_my_requests`

View Service Catalog requests for a specific user.

**Parameters:**
- `requested_for` (optional): User sys_id, email, or user_name (if empty, returns all requests)
- `limit` (optional, default 20): Max requests to return (max 100)
- `active_only` (optional, default true): Only show active requests

**Example Queries:**
```
List my requests
Show requests for beth.anglin@example.com
List all requests (including closed) for user xyz123...
Show the last 10 requests for beth.anglin
```

**Returns:** Array of requests with number, state, stage, approval status

**Example Response:**
```json
{
  "success": true,
  "total_count": 5,
  "requests": [
    {
      "request_number": "REQ0010005",
      "sys_id": "abc123...",
      "state": "Open",
      "stage": "Request Approved",
      "approval": "Approved",
      "active": true,
      "opened_at": "2024-01-20 14:00:00",
      "requested_for": "Beth Anglin",
      "short_description": "Apple iPhone 13 Pro"
    },
    {
      "request_number": "REQ0010001",
      "sys_id": "xyz789...",
      "state": "Closed Complete",
      "stage": "Completed",
      "approval": "Approved",
      "active": false,
      "opened_at": "2024-01-15 10:30:00",
      "requested_for": "Beth Anglin",
      "short_description": "Standard Laptop"
    }
  ]
}
```

**Use Cases:**
1. **Request history:** View all orders placed by a user
2. **Active orders:** Check what's currently in progress
3. **Audit trail:** Track completed requests

---

## Complete End-to-End Workflow

Here's a full ordering workflow from search to fulfillment tracking:

### Step 1: Search for Item
```
User: "I need to order an iPhone"

Agent: [Calls search_catalog_items("iphone")]

Response: "Found 2 iPhone items:
1. Apple iPhone 13 - $799
2. Apple iPhone 13 Pro - $999"
```

### Step 2: Get Item Details
```
User: "Tell me about the iPhone 13"

Agent: [Calls get_catalog_item_details(iphone_13_sys_id)]

Response: "Apple iPhone 13 details:
- Base Price: $799
- Required Variables:
  • Replacement for lost/broken? (yes/no)
  • Monthly data allowance (select)
  • Choose color (green/blue/pink/black/white/red)
  • Choose storage (128GB, 256GB, 512GB)"
```

### Step 3: Gather Variable Values
```
User: "I want the green one with 256GB storage, not a replacement, and 10GB data"

Agent: Variables collected:
- is_replacement: "no"
- data_allowance: "10GB"
- color: "green"
- storage: "256"
```

### Step 4: Submit Order
```
Agent: [Calls order_catalog_item(
  catalog_item_sys_id="ec80c13297968d1021983d1e6253af32",
  variables='{"is_replacement": "no", "data_allowance": "10GB", "color": "green", "storage": "256"}'
)]

Response: "Order submitted successfully!
- Request Number: REQ0010001
- Request Item: RITM0010001
- Status: Open
- Item: Apple iPhone 13 (Green, 256GB)"
```

### Step 5: Track Status
```
User: "What's the status of my order?"

Agent: [Calls get_request_status("REQ0010001")]

Response: "Your iPhone 13 order (REQ0010001):
- State: Work in Progress
- Stage: Fulfillment
- Approval: Approved
- Assigned to: Hardware Fulfillment Team
- Opened: 2024-01-15 10:30:00"
```

### Step 6: View All Requests
```
User: "Show me all my requests"

Agent: [Calls list_my_requests("beth.anglin@example.com")]

Response: "You have 3 active requests:
1. REQ0010005 - iPhone 13 Pro (Approved, in fulfillment)
2. REQ0010003 - Standard Laptop (Pending approval)
3. REQ0010001 - iPhone 13 (Approved, completed)"
```

---

## API Endpoints Used (Phase 2)

| Tool | API Endpoint |
|------|-------------|
| order_catalog_item | `/api/sn_sc/servicecatalog/items/{sys_id}/order_now` (POST) |
| get_request_status | `/api/now/table/sc_request` or `/api/now/table/sc_req_item` (GET) |
| list_my_requests | `/api/now/table/sc_request` (GET) |

---

## Support

- **Setup Issues:** See main [README.md](README.md) for server configuration
- **AI Agent Guide:** [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md) for AI Agent workflows
- **AI Search:** [AI_SEARCH_QUICKSTART.md](AI_SEARCH_QUICKSTART.md) for knowledge search

**ServiceNow Permissions Required:**
- `api_access_user` - REST API access
- Read access to Service Catalog tables (sc_cat_item, item_option_new, etc.)

---

**Status:** ✅ Complete - All 8 Service Catalog tools available
- **Phase 1:** Discovery Tools (5 tools) ✅
- **Phase 2:** Order Submission Tools (3 tools) ✅
