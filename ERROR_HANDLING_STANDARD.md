# ServiceNow MCP Server - Enhanced Error Handling Standard

## Overview

This document defines the standardized error response format for all MCP tools. Following this pattern makes debugging faster, errors more actionable, and Claude better able to diagnose issues automatically.

---

## Standard Error Response Envelope

All MCP tools should return a JSON response following this structure:

```json
{
  "success": true | false,
  "data": { ... },
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error description",
    "detail": "Additional context or stack trace",
    "field": "specific_field_name"  // Optional: which field caused the error
  },
  "meta": {
    "execution_time_ms": 123.45,
    "instance": "https://dev12345.service-now.com",
    "tool": "tool_name",
    "timestamp": "2024-02-16T10:30:00Z"
  }
}
```

### Fields Explained

**`success`** (boolean, required)
- `true` = Operation completed successfully
- `false` = Operation failed

**`data`** (object, required when success=true)
- Contains the actual response data
- Structure varies by tool
- Omit or set to `null` when `success=false`

**`error`** (object, required when success=false)
- `code` - Machine-readable error code (see Error Codes below)
- `message` - Human-readable error message
- `detail` - Additional context, stack trace, or debugging info
- `field` - (Optional) Which input parameter caused the error

**`meta`** (object, optional but recommended)
- `execution_time_ms` - How long the operation took
- `instance` - ServiceNow instance URL
- `tool` - Name of the MCP tool that was called
- `timestamp` - ISO 8601 timestamp of when the response was generated

---

## Error Codes

Use these standardized error codes:

### Connection & Authentication
- `CONNECTION_FAILED` - Cannot reach ServiceNow instance
- `AUTH_FAILED` - Invalid credentials
- `PERMISSION_DENIED` - User lacks required role/ACL (403)
- `RATE_LIMIT_EXCEEDED` - API rate limit hit (429)

### Input Validation
- `INVALID_INPUT` - Invalid parameter value
- `MISSING_REQUIRED_FIELD` - Required parameter not provided
- `INVALID_JSON` - Malformed JSON in input
- `INVALID_QUERY` - Malformed ServiceNow query string

### Data Not Found
- `RECORD_NOT_FOUND` - Requested record doesn't exist (404)
- `TABLE_NOT_FOUND` - Table doesn't exist or is inaccessible
- `USER_NOT_FOUND` - User lookup failed

### ServiceNow Errors
- `SERVICENOW_ERROR` - Generic ServiceNow API error (500)
- `TIMEOUT` - Request timed out
- `TRANSACTION_CANCELLED` - Transaction cancelled by business rule
- `VALIDATION_FAILED` - ServiceNow validation rule blocked the operation

### Internal Errors
- `INTERNAL_ERROR` - Unexpected error in MCP tool code
- `PARSE_ERROR` - Failed to parse ServiceNow response

---

## Example Implementations

### Example 1: Successful Response

```python
@mcp.tool()
def get_user_details(user_id: str) -> str:
    import time
    start_time = time.time()

    client = get_client()
    result = client.table_get(
        table="sys_user",
        sys_id=user_id,
        fields=["name", "email", "title"],
        display_value="true"
    )

    execution_time = (time.time() - start_time) * 1000

    if result["success"]:
        user = result["data"].get("result", {})

        return json.dumps({
            "success": True,
            "data": {
                "user": user
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "instance": client.base_url,
                "tool": "get_user_details"
            }
        }, indent=2)
    else:
        return json.dumps({
            "success": False,
            "data": None,
            "error": {
                "code": "SERVICENOW_ERROR",
                "message": "Failed to retrieve user",
                "detail": result["error"]
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "instance": client.base_url,
                "tool": "get_user_details"
            }
        }, indent=2)
```

### Example 2: Input Validation Error

```python
@mcp.tool()
def create_incident(
    short_description: str,
    priority: int
) -> str:
    # Validate input
    if not short_description:
        return json.dumps({
            "success": False,
            "error": {
                "code": "MISSING_REQUIRED_FIELD",
                "message": "short_description is required",
                "field": "short_description"
            },
            "meta": {
                "tool": "create_incident"
            }
        }, indent=2)

    if priority not in [1, 2, 3, 4, 5]:
        return json.dumps({
            "success": False,
            "error": {
                "code": "INVALID_INPUT",
                "message": "priority must be 1-5",
                "detail": f"Received: {priority}",
                "field": "priority"
            },
            "meta": {
                "tool": "create_incident"
            }
        }, indent=2)

    # ... rest of implementation
```

### Example 3: Permission Denied (403)

```python
@mcp.tool()
def query_agents() -> str:
    client = get_client()
    result = client.table_get(table="sn_aia_agent", limit=10)

    if not result["success"]:
        # Check for permission error
        if "403" in str(result.get("status_code", "")):
            return json.dumps({
                "success": False,
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "Access denied to sn_aia_agent table",
                    "detail": result["error"],
                    "recommendation": "Grant 'sn_aia.agent_admin' role or read ACL to the service account"
                },
                "meta": {
                    "tool": "query_agents",
                    "instance": client.base_url
                }
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": {
                    "code": "SERVICENOW_ERROR",
                    "message": "Failed to query agents",
                    "detail": result["error"]
                },
                "meta": {
                    "tool": "query_agents"
                }
            }, indent=2)

    # ... success path
```

---

## Benefits of This Standard

### 1. Faster Debugging
**Before:**
```
"Error: 403 - Forbidden"
```
❌ What table? What role is missing? Is this a bug or expected?

**After:**
```json
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Access denied to sn_aia_agent table",
    "detail": "HTTP 403: Forbidden",
    "recommendation": "Grant 'sn_aia.agent_admin' role to the service account"
  },
  "meta": {
    "tool": "query_agents",
    "instance": "https://dev12345.service-now.com"
  }
}
```
✅ Immediate clarity on what's wrong and how to fix it

### 2. Better Claude Understanding
Claude can parse structured errors and provide better help:
```
User: "Why did that fail?"

Claude: "The tool failed with PERMISSION_DENIED. Your service account
        doesn't have access to the sn_aia_agent table. You need to grant
        the 'sn_aia.agent_admin' role. Would you like me to help verify
        your current roles using the health_check() tool?"
```

### 3. Automated Error Recovery
```python
# Claude can detect common errors and retry with different parameters
response = json.loads(tool_result)
if not response["success"]:
    if response["error"]["code"] == "RATE_LIMIT_EXCEEDED":
        # Wait and retry
        time.sleep(5)
        retry()
    elif response["error"]["code"] == "PERMISSION_DENIED":
        # Try alternative method
        use_different_table()
```

### 4. Performance Monitoring
The `execution_time_ms` in metadata helps identify slow operations:
```
"This query took 3500ms - that's unusually slow. Check instance performance."
```

---

## Migration Guide: Updating Existing Tools

You don't need to update all 50+ tools at once. Follow this phased approach:

### Phase 1: Update New Tools (✅ Already Done)
All Phase 0 tools (`query_system_properties`, `health_check`, `execute_scripted_rest_api`) use the new standard.

### Phase 2: Update High-Impact Tools
Prioritize tools that are called frequently or prone to errors:
1. `snow_query` - Most used generic tool
2. `create_ai_agent` - Complex operation with many failure modes
3. `order_catalog_item` - Critical workflow with validation
4. `query_execution_plans` - Frequently used for debugging

### Phase 3: Update on Bug Fix
When you encounter a bug or confusing error in a tool, update it to the new standard while fixing it.

### Phase 4: Batch Update Remaining Tools
Once the pattern is proven, bulk update remaining tools.

---

## Template for New Tools

Copy this template when building new tools:

```python
@mcp.tool()
def my_new_tool(
    required_param: str,
    optional_param: str = "default"
) -> str:
    """
    Tool description.

    Args:
        required_param: Description
        optional_param: Description

    Returns:
        JSON response with success, data, error, and meta fields
    """
    import time
    from datetime import datetime

    start_time = time.time()
    client = get_client()

    # Input validation
    if not required_param:
        return json.dumps({
            "success": False,
            "error": {
                "code": "MISSING_REQUIRED_FIELD",
                "message": "required_param is required",
                "field": "required_param"
            },
            "meta": {
                "tool": "my_new_tool",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }, indent=2)

    # Main operation
    try:
        result = client.table_get(...)
        execution_time = (time.time() - start_time) * 1000

        if result["success"]:
            return json.dumps({
                "success": True,
                "data": {
                    "result": result["data"]
                },
                "meta": {
                    "execution_time_ms": round(execution_time, 2),
                    "instance": client.base_url,
                    "tool": "my_new_tool",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            }, indent=2)
        else:
            # Categorize error
            error_code = "SERVICENOW_ERROR"
            if "403" in str(result.get("status_code", "")):
                error_code = "PERMISSION_DENIED"
            elif "404" in str(result.get("status_code", "")):
                error_code = "RECORD_NOT_FOUND"
            elif "429" in str(result.get("status_code", "")):
                error_code = "RATE_LIMIT_EXCEEDED"

            return json.dumps({
                "success": False,
                "error": {
                    "code": error_code,
                    "message": "Operation failed",
                    "detail": result["error"]
                },
                "meta": {
                    "execution_time_ms": round(execution_time, 2),
                    "instance": client.base_url,
                    "tool": "my_new_tool"
                }
            }, indent=2)

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        return json.dumps({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Unexpected error in tool execution",
                "detail": str(e)
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "my_new_tool"
            }
        }, indent=2)
```

---

## Testing Your Error Responses

Use this checklist when implementing or updating a tool:

- [ ] Success case returns `success: true` with populated `data` field
- [ ] Failure case returns `success: false` with populated `error` field
- [ ] Error includes meaningful `code` from the standard list
- [ ] Error `message` is human-readable
- [ ] Error `detail` provides debugging context
- [ ] `meta.execution_time_ms` is populated (helps identify slow operations)
- [ ] `meta.tool` matches the actual tool name
- [ ] 403 errors map to `PERMISSION_DENIED` with actionable recommendation
- [ ] 404 errors map to `RECORD_NOT_FOUND` with specific record details
- [ ] Invalid input returns `INVALID_INPUT` or `MISSING_REQUIRED_FIELD`

---

## Real-World Impact

### Before Enhanced Error Handling
```
User: "Create an AI Agent called 'Help Desk Bot'"
Tool: "Error: 403 - Forbidden"
User: "What? Why?"
```
→ 5 minutes of back-and-forth debugging

### After Enhanced Error Handling
```
User: "Create an AI Agent called 'Help Desk Bot'"
Tool:
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Access denied to sn_aia_agent table",
    "recommendation": "Grant 'sn_aia.agent_admin' role to claude.desktop@servicenow.com"
  }
}

Claude: "The tool failed because your service account needs the
         'sn_aia.agent_admin' role. Should I check your current
         roles with health_check() to verify?"
```
→ Immediate diagnosis and fix path

---

## Summary

✅ **DO:**
- Return structured JSON responses with `success`, `data`, `error`, `meta`
- Use standardized error codes
- Include execution time for performance tracking
- Provide actionable error messages and recommendations
- Validate input and fail fast with clear messages

❌ **DON'T:**
- Return plain text error messages
- Use generic "Error" without details
- Omit which field caused validation errors
- Forget to include the tool name in metadata
- Return success=true when operation actually failed

**The goal:** Every error should be self-explanatory and actionable, even without looking at code or logs.
