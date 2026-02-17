import os
import json
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

import requests
from mcp.server.fastmcp import FastMCP

# =============================================================================
# SERVICENOW CLIENT (Reusable HTTP client with session management)
# =============================================================================

class ServiceNowClient:
    """Lightweight ServiceNow REST API Client for MCP."""

    def __init__(self):
        # Support both env variable naming conventions
        instance = os.getenv("SERVICENOW_INSTANCE") or os.getenv("SNOW_INSTANCE")
        username = os.getenv("SERVICENOW_USERNAME") or os.getenv("SNOW_USERNAME")
        password = os.getenv("SERVICENOW_PASSWORD") or os.getenv("SNOW_PASSWORD")

        if not instance:
            raise ValueError("SERVICENOW_INSTANCE or SNOW_INSTANCE environment variable is required")

        # Handle various instance URL formats
        if instance.startswith("http"):
            self.base_url = instance.rstrip("/")
        elif "." not in instance:
            self.base_url = f"https://{instance}.service-now.com"
        else:
            self.base_url = f"https://{instance}"

        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        self.timeout = 30

    def _request(self, method: str, endpoint: str, params: dict = None, data: dict = None) -> dict:
        """Make HTTP request to ServiceNow."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(
                method=method, url=url, params=params,
                json=data, timeout=self.timeout
            )
            result = {
                "success": response.ok,
                "status_code": response.status_code,
                "data": response.json() if response.text else None,
                "error": None if response.ok else f"HTTP {response.status_code}: {response.reason}"
            }
            return result
        except Exception as e:
            return {"success": False, "status_code": None, "data": None, "error": str(e)}

    def table_get(self, table: str, sys_id: str = None, query: str = None,
                  fields: list = None, limit: int = 100, offset: int = 0,
                  order_by: str = None, display_value: str = "false") -> dict:
        endpoint = f"/api/now/table/{table}/{sys_id}" if sys_id else f"/api/now/table/{table}"
        params = {
            "sysparm_limit": limit,
            "sysparm_offset": offset,
            "sysparm_display_value": display_value,
            "sysparm_exclude_reference_link": "true"
        }
        if query: params["sysparm_query"] = query
        if fields: params["sysparm_fields"] = ",".join(fields)
        if order_by: params["sysparm_orderby"] = order_by
        return self._request("GET", endpoint, params=params)

    def table_create(self, table: str, data: dict) -> dict:
        return self._request("POST", f"/api/now/table/{table}", data=data)

    def table_update(self, table: str, sys_id: str, data: dict) -> dict:
        return self._request("PATCH", f"/api/now/table/{table}/{sys_id}", data=data)

    def table_delete(self, table: str, sys_id: str) -> dict:
        return self._request("DELETE", f"/api/now/table/{table}/{sys_id}")

    def aggregate(self, table: str, query: str = None, group_by: list = None,
                  count: bool = True, sum_fields: list = None, avg_fields: list = None) -> dict:
        params = {"sysparm_count": "true" if count else "false"}
        if query: params["sysparm_query"] = query
        if group_by: params["sysparm_group_by"] = ",".join(group_by)
        if sum_fields: params["sysparm_sum_fields"] = ",".join(sum_fields)
        if avg_fields: params["sysparm_avg_fields"] = ",".join(avg_fields)
        return self._request("GET", f"/api/now/stats/{table}", params=params)


# =============================================================================
# MCP SERVER SETUP
# =============================================================================

mcp = FastMCP("servicenow-debug")

# Initialize ServiceNow client (lazy loading)
_client: Optional[ServiceNowClient] = None

def get_client() -> ServiceNowClient:
    """Get or create ServiceNow client."""
    global _client
    if _client is None:
        _client = ServiceNowClient()
    return _client

# Legacy direct access for existing specialized tools
INSTANCE = os.getenv("SERVICENOW_INSTANCE")
USERNAME = os.getenv("SERVICENOW_USERNAME")
PASSWORD = os.getenv("SERVICENOW_PASSWORD")


# =============================================================================
# SECTION 1: GENERIC TABLE OPERATIONS
# =============================================================================

@mcp.tool()
def snow_query(
    table: str,
    query: str = "",
    fields: str = "",
    limit: int = 20,
    order_by: str = "-sys_created_on",
    display_value: bool = True
) -> str:
    """
    Query records from a ServiceNow table with encoded query support.

    Args:
        table: Table name (e.g., 'incident', 'sys_user', 'change_request', 'cmdb_ci')
        query: Encoded query string. Examples:
               - 'active=true' (simple filter)
               - 'active=true^priority=1' (AND condition)
               - 'priority=1^ORpriority=2' (OR condition)
               - 'opened_byLIKEFred' (contains)
               - 'sys_created_on>2024-01-01' (date comparison)
               - 'stateIN1,2,3' (in list)
               - 'assigned_toISEMPTY' (is empty)
        fields: Comma-separated field names to return. Leave empty for all fields.
        limit: Maximum records to return (default 20, max 1000)
        order_by: Field to sort by. Prefix with '-' for descending. (default: -sys_created_on)
        display_value: If true, returns display values instead of sys_ids (default: true)

    Returns:
        JSON string with query results or error message
    """
    client = get_client()
    field_list = [f.strip() for f in fields.split(",")] if fields else None

    result = client.table_get(
        table=table,
        query=query or None,
        fields=field_list,
        limit=min(limit, 1000),
        order_by=order_by,
        display_value="true" if display_value else "false"
    )

    if result["success"]:
        records = result["data"].get("result", [])
        return json.dumps({
            "count": len(records),
            "records": records
        }, indent=2)
    else:
        return json.dumps({"error": result["error"]}, indent=2)


@mcp.tool()
def snow_get_record(
    table: str,
    sys_id: str,
    fields: str = "",
    display_value: bool = True
) -> str:
    """
    Get a single record by sys_id.

    Args:
        table: Table name (e.g., 'incident', 'sys_user')
        sys_id: The sys_id of the record to retrieve
        fields: Comma-separated field names to return. Leave empty for all fields.
        display_value: If true, returns display values instead of sys_ids

    Returns:
        JSON string with the record or error message
    """
    client = get_client()
    field_list = [f.strip() for f in fields.split(",")] if fields else None

    result = client.table_get(
        table=table,
        sys_id=sys_id,
        fields=field_list,
        display_value="true" if display_value else "false"
    )

    if result["success"]:
        return json.dumps(result["data"].get("result", {}), indent=2)
    else:
        return json.dumps({"error": result["error"]}, indent=2)


@mcp.tool()
def snow_create_record(
    table: str,
    data: str
) -> str:
    """
    Create a new record in a ServiceNow table.

    Args:
        table: Table name (e.g., 'incident', 'change_request')
        data: JSON string with field values. Example:
              '{"short_description": "New issue", "urgency": "2", "impact": "2"}'

    Returns:
        JSON string with the created record (including new sys_id) or error message
    """
    client = get_client()

    try:
        record_data = json.loads(data)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON in data: {e}"}, indent=2)

    result = client.table_create(table=table, data=record_data)

    if result["success"]:
        created = result["data"].get("result", {})
        return json.dumps({
            "success": True,
            "sys_id": created.get("sys_id"),
            "number": created.get("number"),
            "record": created
        }, indent=2)
    else:
        return json.dumps({"error": result["error"]}, indent=2)


@mcp.tool()
def snow_update_record(
    table: str,
    sys_id: str,
    data: str
) -> str:
    """
    Update an existing record in ServiceNow.

    Args:
        table: Table name
        sys_id: The sys_id of the record to update
        data: JSON string with fields to update. Example:
              '{"state": "6", "close_notes": "Issue resolved"}'

    Returns:
        JSON string with the updated record or error message
    """
    client = get_client()

    try:
        update_data = json.loads(data)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON in data: {e}"}, indent=2)

    result = client.table_update(table=table, sys_id=sys_id, data=update_data)

    if result["success"]:
        return json.dumps({
            "success": True,
            "record": result["data"].get("result", {})
        }, indent=2)
    else:
        return json.dumps({"error": result["error"]}, indent=2)


@mcp.tool()
def snow_delete_record(
    table: str,
    sys_id: str
) -> str:
    """
    Delete a record from ServiceNow.

    Args:
        table: Table name
        sys_id: The sys_id of the record to delete

    Returns:
        JSON string confirming deletion or error message
    """
    client = get_client()
    result = client.table_delete(table=table, sys_id=sys_id)

    if result["success"]:
        return json.dumps({"success": True, "message": f"Record {sys_id} deleted from {table}"}, indent=2)
    else:
        return json.dumps({"error": result["error"]}, indent=2)


@mcp.tool()
def snow_count(
    table: str,
    query: str = ""
) -> str:
    """
    Count records in a ServiceNow table.

    Args:
        table: Table name (e.g., 'incident', 'sys_user')
        query: Optional filter query (e.g., 'active=true^priority=1')

    Returns:
        JSON string with the count
    """
    client = get_client()
    result = client.aggregate(table=table, query=query or None, count=True)

    if result["success"]:
        stats = result["data"].get("result", {}).get("stats", {})
        count = int(stats.get("count", 0))
        return json.dumps({"table": table, "query": query, "count": count}, indent=2)
    else:
        return json.dumps({"error": result["error"]}, indent=2)


@mcp.tool()
def snow_aggregate(
    table: str,
    query: str = "",
    group_by: str = "",
    sum_fields: str = "",
    avg_fields: str = ""
) -> str:
    """
    Perform aggregate queries on ServiceNow data (COUNT, SUM, AVG grouped by fields).

    Args:
        table: Table name
        query: Optional filter query
        group_by: Comma-separated fields to group by (e.g., 'priority,state')
        sum_fields: Comma-separated numeric fields to sum
        avg_fields: Comma-separated numeric fields to average

    Returns:
        JSON string with aggregate results
    """
    client = get_client()

    group_list = [g.strip() for g in group_by.split(",")] if group_by else None
    sum_list = [s.strip() for s in sum_fields.split(",")] if sum_fields else None
    avg_list = [a.strip() for a in avg_fields.split(",")] if avg_fields else None

    result = client.aggregate(
        table=table,
        query=query or None,
        group_by=group_list,
        sum_fields=sum_list,
        avg_fields=avg_list
    )

    if result["success"]:
        return json.dumps(result["data"].get("result", {}), indent=2)
    else:
        return json.dumps({"error": result["error"]}, indent=2)


@mcp.tool()
def snow_table_schema(table: str) -> str:
    """
    Get the schema (field definitions) for a ServiceNow table.

    Args:
        table: Table name to get schema for

    Returns:
        JSON with field definitions including name, type, max_length, mandatory, etc.
    """
    client = get_client()

    result = client.table_get(
        table="sys_dictionary",
        query=f"name={table}^internal_type!=collection",
        fields=["element", "column_label", "internal_type", "max_length", "mandatory", "reference"],
        limit=200,
        display_value="true"
    )

    if result["success"]:
        fields = result["data"].get("result", [])
        schema = {
            "table": table,
            "field_count": len(fields),
            "fields": [
                {
                    "name": f.get("element"),
                    "label": f.get("column_label"),
                    "type": f.get("internal_type"),
                    "max_length": f.get("max_length"),
                    "mandatory": f.get("mandatory") == "true",
                    "reference": f.get("reference")
                }
                for f in fields if f.get("element")
            ]
        }
        return json.dumps(schema, indent=2)
    else:
        return json.dumps({"error": result["error"]}, indent=2)


@mcp.tool()
def snow_test_connection() -> str:
    """
    Test the ServiceNow API connection.

    Returns:
        JSON with connection status and current user info
    """
    client = get_client()
    username = USERNAME

    result = client.table_get(
        table="sys_user",
        query=f"user_name={username}",
        fields=["user_name", "name", "email", "title"],
        limit=1,
        display_value="true"
    )

    if result["success"]:
        users = result["data"].get("result", [])
        if users:
            return json.dumps({
                "success": True,
                "message": "Connection successful",
                "instance": client.base_url,
                "user": users[0]
            }, indent=2)
        else:
            return json.dumps({
                "success": True,
                "message": "Connection successful but user not found",
                "instance": client.base_url
            }, indent=2)
    else:
        return json.dumps({
            "success": False,
            "error": result["error"],
            "instance": client.base_url
        }, indent=2)


# ============================================================================
# PHASE 0: QUICK WINS - PLATFORM UTILITIES
# ============================================================================

@mcp.tool()
def query_system_properties(
    name_filter: str = "",
    limit: int = 50
) -> str:
    """
    Query ServiceNow system properties (configuration settings).

    System properties control instance behavior like timeouts, feature flags,
    API limits, and application-specific settings. This is essential for
    debugging configuration issues.

    Args:
        name_filter: Filter property names (uses LIKE). Examples:
                    - "glide.ai" - All AI-related properties
                    - "sn_aia" - All AI Agent properties
                    - "timeout" - All timeout settings
                    - "sn_aia.agent.timeout" - Specific property
        limit: Maximum properties to return (default 50)

    Returns:
        JSON with property name, value, description, and category

    Examples:
        - query_system_properties("sn_aia") - All AI Agent settings
        - query_system_properties("glide.smtp") - Email configuration
        - query_system_properties("timeout") - All timeout settings
    """
    client = get_client()

    query_parts = []
    if name_filter:
        query_parts.append(f"nameLIKE{name_filter}")

    query = "^".join(query_parts) if query_parts else ""

    result = client.table_get(
        table="sys_properties",
        query=query if query else None,
        fields=["name", "value", "description", "type", "sys_id"],
        limit=limit,
        order_by="name",
        display_value="true"
    )

    if not result["success"]:
        return json.dumps({
            "success": False,
            "error": result["error"]
        }, indent=2)

    properties = result["data"].get("result", [])

    output = {
        "success": True,
        "count": len(properties),
        "properties": []
    }

    for prop in properties:
        # Handle both dict and string values from display_value
        def get_val(field_data):
            if isinstance(field_data, dict):
                return field_data.get("display_value", field_data.get("value"))
            return field_data

        output["properties"].append({
            "name": get_val(prop.get("name")),
            "value": get_val(prop.get("value")),
            "description": get_val(prop.get("description", "")),
            "type": get_val(prop.get("type", "")),
            "sys_id": get_val(prop.get("sys_id"))
        })

    return json.dumps(output, indent=2)


@mcp.tool()
def health_check() -> str:
    """
    Comprehensive ServiceNow MCP connection health check.

    Goes beyond basic connectivity to verify:
    - API connection and authentication
    - Service account roles and permissions
    - Access to critical tables (AI Agent, catalog, CMDB, etc.)
    - Instance version and patch level
    - API response time

    Returns detailed health report with:
    - Connection status
    - User identity and roles
    - Table access verification
    - Instance metadata
    - Performance metrics
    - Actionable recommendations if issues found

    Use this for:
    - Initial setup verification
    - Troubleshooting permission errors (like the 403 on sn_aia_agent)
    - Performance diagnosis
    - Pre-flight checks before major operations
    """
    import time
    from datetime import datetime

    client = get_client()
    username = USERNAME

    output = {
        "success": True,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "instance": client.base_url,
        "checks": {},
        "warnings": [],
        "errors": [],
        "recommendations": []
    }

    # ========================================================================
    # CHECK 1: Basic Connection & User Identity
    # ========================================================================
    start_time = time.time()
    user_result = client.table_get(
        table="sys_user",
        query=f"user_name={username}",
        fields=["sys_id", "user_name", "name", "email", "title", "active"],
        limit=1,
        display_value="true"
    )
    connection_time = (time.time() - start_time) * 1000

    if not user_result["success"]:
        output["success"] = False
        output["errors"].append(f"Connection failed: {user_result['error']}")
        output["checks"]["connection"] = {"status": "FAILED", "error": user_result["error"]}
        return json.dumps(output, indent=2)

    users = user_result["data"].get("result", [])
    if not users:
        output["success"] = False
        output["errors"].append(f"User '{username}' not found in sys_user table")
        output["checks"]["connection"] = {"status": "FAILED"}
        return json.dumps(output, indent=2)

    user = users[0]

    def get_val(field_data):
        if isinstance(field_data, dict):
            return field_data.get("display_value", field_data.get("value"))
        return field_data

    user_sys_id = get_val(user.get("sys_id"))
    user_active = get_val(user.get("active"))

    output["checks"]["connection"] = {
        "status": "OK",
        "response_time_ms": round(connection_time, 2),
        "user": {
            "sys_id": user_sys_id,
            "username": get_val(user.get("user_name")),
            "name": get_val(user.get("name")),
            "email": get_val(user.get("email")),
            "title": get_val(user.get("title")),
            "active": user_active
        }
    }

    if user_active != "true":
        output["warnings"].append(f"Service account is INACTIVE")
        output["recommendations"].append("Activate the service account in ServiceNow")

    if connection_time > 1000:
        output["warnings"].append(f"Slow API response time: {connection_time:.0f}ms")
        output["recommendations"].append("Check instance performance or network latency")

    # ========================================================================
    # CHECK 2: User Roles
    # ========================================================================
    roles_result = client.table_get(
        table="sys_user_has_role",
        query=f"user={user_sys_id}",
        fields=["role"],
        limit=100,
        display_value="true"
    )

    if roles_result["success"]:
        role_records = roles_result["data"].get("result", [])
        roles = [get_val(r.get("role")) for r in role_records]

        output["checks"]["roles"] = {
            "status": "OK",
            "count": len(roles),
            "roles": roles
        }

        # Check for critical roles
        # Note: AI Agent admin role varies by instance (sn_aia.admin in Zurich+, sn_aia.agent_admin in older versions)
        has_admin = "admin" in roles
        has_aia_admin = any(role in roles for role in ["sn_aia.admin", "sn_aia.agent_admin"])
        has_catalog_admin = "catalog_admin" in roles
        has_itil = "itil" in roles

        output["checks"]["roles"]["has_admin"] = has_admin
        output["checks"]["roles"]["has_ai_agent_admin"] = has_aia_admin
        output["checks"]["roles"]["has_catalog_admin"] = has_catalog_admin
        output["checks"]["roles"]["has_itil"] = has_itil

        # Warnings for missing critical roles
        if not has_admin and not has_aia_admin:
            output["warnings"].append("Missing admin or AI Agent admin role")
            output["recommendations"].append(
                "Grant 'admin' or 'sn_aia.admin' role for full AI Agent access"
            )

        if not has_catalog_admin and not has_admin:
            output["warnings"].append("Missing catalog_admin role (needed for catalog operations)")

        if not has_itil and not has_admin:
            output["warnings"].append("Missing itil role (needed for ITSM operations)")
    else:
        output["checks"]["roles"] = {"status": "FAILED", "error": roles_result["error"]}
        output["warnings"].append("Could not retrieve user roles")

    # ========================================================================
    # CHECK 3: Critical Table Access
    # ========================================================================
    critical_tables = [
        ("sn_aia_agent", "AI Agents"),
        ("sn_aia_execution_plan", "AI Agent Executions"),
        ("sys_generative_ai_log", "LLM Logs"),
        ("sys_cs_conversation", "Conversations"),
        ("sc_cat_item", "Service Catalog"),
        ("incident", "Incidents"),
        ("cmdb_ci", "CMDB")
    ]

    table_access = {}
    for table_name, friendly_name in critical_tables:
        test_result = client.table_get(
            table=table_name,
            query="sys_idISNOTEMPTY",
            fields=["sys_id"],
            limit=1,
            display_value="false"
        )

        if test_result["success"]:
            table_access[table_name] = {
                "status": "OK",
                "friendly_name": friendly_name,
                "accessible": True
            }
        else:
            table_access[table_name] = {
                "status": "FAILED",
                "friendly_name": friendly_name,
                "accessible": False,
                "error": test_result["error"]
            }

            if "403" in str(test_result["error"]) or "ACL" in str(test_result["error"]).upper():
                output["errors"].append(
                    f"Permission denied for {table_name} ({friendly_name})"
                )
                output["recommendations"].append(
                    f"Grant read access to {table_name} table or assign appropriate role"
                )
            else:
                output["warnings"].append(
                    f"Could not access {table_name}: {test_result['error']}"
                )

    output["checks"]["table_access"] = table_access

    # Count accessible tables
    accessible_count = sum(1 for t in table_access.values() if t["accessible"])
    total_count = len(critical_tables)

    if accessible_count < total_count:
        output["success"] = False

    # ========================================================================
    # CHECK 4: Instance Version
    # ========================================================================
    version_result = client.table_get(
        table="sys_properties",
        query="name=glide.war",
        fields=["value"],
        limit=1,
        display_value="false"
    )

    if version_result["success"]:
        version_records = version_result["data"].get("result", [])
        if version_records:
            glide_war = get_val(version_records[0].get("value", ""))

            # Parse version family (e.g., "zurich", "tokyo", "vancouver")
            import re
            family_match = re.search(r'glide-(\w+)-', glide_war)
            family = family_match.group(1) if family_match else "unknown"

            # Parse patch number
            patch_match = re.search(r'patch(\d+)', glide_war)
            patch = int(patch_match.group(1)) if patch_match else 0

            output["checks"]["instance_version"] = {
                "status": "OK",
                "family": family,
                "patch_number": patch,
                "glide_war": glide_war
            }
        else:
            output["checks"]["instance_version"] = {"status": "NOT_FOUND"}
    else:
        output["checks"]["instance_version"] = {
            "status": "FAILED",
            "error": version_result["error"]
        }

    # ========================================================================
    # SUMMARY
    # ========================================================================
    output["summary"] = {
        "overall_status": "HEALTHY" if output["success"] and not output["errors"] else "DEGRADED" if output["warnings"] else "CRITICAL",
        "tables_accessible": f"{accessible_count}/{total_count}",
        "response_time_ms": round(connection_time, 2),
        "issues_found": len(output["errors"]) + len(output["warnings"])
    }

    return json.dumps(output, indent=2)


@mcp.tool()
def execute_scripted_rest_api(
    api_path: str,
    method: str = "GET",
    body: str = "{}",
    query_params: str = ""
) -> str:
    """
    Execute ANY Scripted REST API on the ServiceNow instance.

    This is the ESCAPE HATCH for infinite extensibility. Instead of building
    dedicated MCP tools for every capability, build a Scripted REST API in
    ServiceNow and call it through this generic executor.

    Args:
        api_path: Path to the Scripted REST API (e.g., "/api/x_company/custom/get_user_details")
                 - Must start with /api/
                 - Format: /api/{namespace}/{api_name}/{resource_path}
        method: HTTP method (GET, POST, PUT, PATCH, DELETE) - default GET
        body: JSON body for POST/PUT/PATCH requests - default "{}"
        query_params: URL query string (e.g., "id=123&limit=10") - default ""

    Returns:
        JSON response from the Scripted REST API

    Example Use Cases:

    1. Custom CMDB Impact Analysis:
       - Build Scripted REST API: /api/x_company/cmdb/impact_analysis
       - Call: execute_scripted_rest_api("/api/x_company/cmdb/impact_analysis", "GET", "{}", "ci_id=abc123")
       - Returns: Complete dependency tree and impact scope

    2. Complex Reporting:
       - Build: /api/x_company/reports/agent_deflection_rate
       - Call: execute_scripted_rest_api("/api/x_company/reports/agent_deflection_rate", "GET", "{}", "days=30")
       - Returns: Pre-calculated metrics instead of loading 1000s of records

    3. Multi-Table Transactions:
       - Build: /api/x_company/workflows/provision_user
       - Call: execute_scripted_rest_api("/api/x_company/workflows/provision_user", "POST", '{"email":"user@example.com"}')
       - Returns: User record + group assignments + catalog requests in one atomic operation

    4. Custom Business Logic:
       - Build: /api/x_company/custom/validate_change_window
       - Call: execute_scripted_rest_api("/api/x_company/custom/validate_change_window", "POST", '{"start":"2024-02-20 10:00:00"}')
       - Returns: Validation result with conflict detection

    Why Use This Instead of Building Dedicated MCP Tools?

    ✅ Keep complex logic in ServiceNow (full GlideRecord, GlideSystem access)
    ✅ Leverage ServiceNow's transaction handling and security model
    ✅ Iterate faster (change API, no MCP server restart needed)
    ✅ Reuse APIs across multiple clients (MCP, mobile, integrations)
    ✅ One generic MCP tool unlocks infinite capabilities

    Security Notes:
    - Scripted REST APIs respect ServiceNow ACLs and roles
    - The MCP service account needs read access to the API's scope
    - Always validate input in the Scripted REST API code
    - Use POST/PUT for operations that modify data (proper REST semantics)

    Example Scripted REST API (ServiceNow side):
    ```javascript
    (function process(request, response) {
        var body = request.body.data;
        var ciId = body.ci_id;

        // Complex GlideRecord logic here
        var impactAnalysis = performImpactAnalysis(ciId);

        return {
            success: true,
            data: impactAnalysis
        };
    })(request, response);
    ```
    """
    client = get_client()

    # Validate API path
    if not api_path.startswith("/api/"):
        return json.dumps({
            "success": False,
            "error": "api_path must start with /api/ (e.g., /api/x_company/custom/my_api)"
        }, indent=2)

    # Validate HTTP method
    method = method.upper()
    if method not in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
        return json.dumps({
            "success": False,
            "error": f"Invalid HTTP method: {method}. Must be GET, POST, PUT, PATCH, or DELETE"
        }, indent=2)

    # Build full URL
    url = f"{client.base_url}{api_path}"
    if query_params:
        url = f"{url}?{query_params}"

    # Parse body JSON
    try:
        body_data = json.loads(body) if body else {}
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "error": f"Invalid JSON in body parameter: {str(e)}"
        }, indent=2)

    # Execute request
    try:
        import requests as req

        response = client.session.request(
            method=method,
            url=url,
            json=body_data if method in ["POST", "PUT", "PATCH"] else None,
            timeout=client.timeout
        )

        # Try to parse JSON response
        try:
            response_data = response.json()
        except:
            response_data = {"raw_response": response.text}

        result = {
            "success": response.ok,
            "status_code": response.status_code,
            "data": response_data,
            "method": method,
            "url": url
        }

        if not response.ok:
            result["error"] = f"HTTP {response.status_code}: {response.reason}"

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Request failed: {str(e)}",
            "method": method,
            "url": url
        }, indent=2)


# ============================================================================
# PHASE 1: ITSM CORE TOOLS
# ============================================================================

# ============================================================================
# INCIDENT MANAGEMENT
# ============================================================================

@mcp.tool()
def create_incident(
    short_description: str,
    description: str = "",
    caller_email: str = "",
    priority: int = 3,
    category: str = "",
    assignment_group: str = "",
    impact: int = 3,
    urgency: int = 3
) -> str:
    """
    Create an incident with proper field validation and auto-population.

    This is better than using snow_create_record because it:
    - Auto-looks up caller by email
    - Validates priority/impact/urgency ranges
    - Sets sensible defaults
    - Returns incident number + sys_id + direct URL
    - Handles assignment group lookup

    Args:
        short_description: Brief summary of the issue (required)
        description: Detailed description of the issue
        caller_email: Email of the person reporting the issue (auto-lookup)
        priority: 1=Critical, 2=High, 3=Medium, 4=Low, 5=Planning (default: 3)
        category: Category (inquiry, software, hardware, network, database, etc.)
        assignment_group: Name of assignment group (will lookup sys_id)
        impact: 1=High, 2=Medium, 3=Low (default: 3)
        urgency: 1=High, 2=Medium, 3=Low (default: 3)

    Returns:
        JSON with incident number, sys_id, and URL

    Examples:
        create_incident("Password reset needed", caller_email="john.doe@example.com", priority=4)
        create_incident("Database outage", "Prod DB is down", "admin@example.com", priority=1, category="database")
    """
    import time
    from datetime import datetime

    start_time = time.time()
    client = get_client()

    # Validate required field
    if not short_description:
        return json.dumps({
            "success": False,
            "error": {
                "code": "MISSING_REQUIRED_FIELD",
                "message": "short_description is required",
                "field": "short_description"
            }
        }, indent=2)

    # Validate priority range
    if priority not in [1, 2, 3, 4, 5]:
        return json.dumps({
            "success": False,
            "error": {
                "code": "INVALID_INPUT",
                "message": "priority must be 1-5 (1=Critical, 2=High, 3=Medium, 4=Low, 5=Planning)",
                "detail": f"Received: {priority}",
                "field": "priority"
            }
        }, indent=2)

    # Validate impact/urgency ranges
    if impact not in [1, 2, 3]:
        return json.dumps({
            "success": False,
            "error": {
                "code": "INVALID_INPUT",
                "message": "impact must be 1-3 (1=High, 2=Medium, 3=Low)",
                "field": "impact"
            }
        }, indent=2)

    if urgency not in [1, 2, 3]:
        return json.dumps({
            "success": False,
            "error": {
                "code": "INVALID_INPUT",
                "message": "urgency must be 1-3 (1=High, 2=Medium, 3=Low)",
                "field": "urgency"
            }
        }, indent=2)

    # Build incident data
    incident_data = {
        "short_description": short_description,
        "priority": str(priority),
        "impact": str(impact),
        "urgency": str(urgency)
    }

    if description:
        incident_data["description"] = description

    if category:
        incident_data["category"] = category

    # Lookup caller by email
    if caller_email:
        caller_result = client.table_get(
            table="sys_user",
            query=f"email={caller_email}",
            fields=["sys_id", "name"],
            limit=1
        )

        if caller_result["success"] and caller_result["data"].get("result"):
            caller = caller_result["data"]["result"][0]
            incident_data["caller_id"] = caller["sys_id"]
        else:
            return json.dumps({
                "success": False,
                "error": {
                    "code": "USER_NOT_FOUND",
                    "message": f"Caller not found with email: {caller_email}",
                    "field": "caller_email"
                }
            }, indent=2)

    # Lookup assignment group
    if assignment_group:
        group_result = client.table_get(
            table="sys_user_group",
            query=f"nameLIKE{assignment_group}^ORsys_id={assignment_group}",
            fields=["sys_id", "name"],
            limit=1
        )

        if group_result["success"] and group_result["data"].get("result"):
            group = group_result["data"]["result"][0]
            incident_data["assignment_group"] = group["sys_id"]
        else:
            return json.dumps({
                "success": False,
                "error": {
                    "code": "RECORD_NOT_FOUND",
                    "message": f"Assignment group not found: {assignment_group}",
                    "field": "assignment_group"
                }
            }, indent=2)

    # Create the incident
    result = client.table_create(table="incident", data=incident_data)
    execution_time = (time.time() - start_time) * 1000

    if result["success"]:
        incident = result["data"].get("result", {})

        def get_val(field_data):
            if isinstance(field_data, dict):
                return field_data.get("display_value", field_data.get("value"))
            return field_data

        number = get_val(incident.get("number"))
        sys_id = get_val(incident.get("sys_id"))

        return json.dumps({
            "success": True,
            "data": {
                "number": number,
                "sys_id": sys_id,
                "url": f"{client.base_url}/incident.do?sys_id={sys_id}",
                "state": get_val(incident.get("state")),
                "priority": get_val(incident.get("priority")),
                "assigned_to": get_val(incident.get("assigned_to")),
                "assignment_group": get_val(incident.get("assignment_group"))
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "instance": client.base_url,
                "tool": "create_incident"
            }
        }, indent=2)
    else:
        return json.dumps({
            "success": False,
            "error": {
                "code": "SERVICENOW_ERROR",
                "message": "Failed to create incident",
                "detail": result["error"]
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "create_incident"
            }
        }, indent=2)


@mcp.tool()
def update_incident(
    incident_id: str,
    state: str = "",
    assigned_to_email: str = "",
    assignment_group: str = "",
    work_notes: str = "",
    comments: str = "",
    priority: int = 0,
    resolution_code: str = "",
    close_notes: str = ""
) -> str:
    """
    Update an incident with state transition validation.

    Args:
        incident_id: Incident number (INC0012345) or sys_id
        state: New state (new, in_progress, on_hold, resolved, closed, cancelled)
        assigned_to_email: Email of assignee (will lookup)
        assignment_group: Name of assignment group
        work_notes: Internal work notes (not visible to customer)
        comments: Customer-visible comments
        priority: Update priority (1-5)
        resolution_code: Resolution code (only for resolve/close)
        close_notes: Close notes (only for close)

    Returns:
        JSON with updated incident details

    Examples:
        update_incident("INC0012345", state="in_progress", work_notes="Investigating issue")
        update_incident("INC0012345", assigned_to_email="tech@example.com")
        update_incident("INC0012345", state="resolved", resolution_code="Solved (Permanently)")
    """
    import time
    start_time = time.time()
    client = get_client()

    if not incident_id:
        return json.dumps({
            "success": False,
            "error": {
                "code": "MISSING_REQUIRED_FIELD",
                "message": "incident_id is required",
                "field": "incident_id"
            }
        }, indent=2)

    # Lookup incident
    query = f"number={incident_id}" if incident_id.startswith("INC") else f"sys_id={incident_id}"
    inc_result = client.table_get(table="incident", query=query, limit=1)

    if not inc_result["success"] or not inc_result["data"].get("result"):
        return json.dumps({
            "success": False,
            "error": {
                "code": "RECORD_NOT_FOUND",
                "message": f"Incident not found: {incident_id}"
            }
        }, indent=2)

    incident = inc_result["data"]["result"][0]
    def get_val(field_data):
        if isinstance(field_data, dict):
            return field_data.get("value", field_data.get("display_value"))
        return field_data

    inc_sys_id = get_val(incident.get("sys_id"))

    # Build update data
    update_data = {}

    if state:
        # Map friendly names to state values
        state_map = {
            "new": "1",
            "in_progress": "2",
            "on_hold": "3",
            "resolved": "6",
            "closed": "7",
            "cancelled": "8"
        }
        state_value = state_map.get(state.lower(), state)
        update_data["state"] = state_value

    if assigned_to_email:
        user_result = client.table_get(
            table="sys_user",
            query=f"email={assigned_to_email}",
            fields=["sys_id"],
            limit=1
        )
        if user_result["success"] and user_result["data"].get("result"):
            update_data["assigned_to"] = user_result["data"]["result"][0]["sys_id"]

    if assignment_group:
        group_result = client.table_get(
            table="sys_user_group",
            query=f"nameLIKE{assignment_group}",
            fields=["sys_id"],
            limit=1
        )
        if group_result["success"] and group_result["data"].get("result"):
            update_data["assignment_group"] = group_result["data"]["result"][0]["sys_id"]

    if work_notes:
        update_data["work_notes"] = work_notes

    if comments:
        update_data["comments"] = comments

    if priority > 0:
        update_data["priority"] = str(priority)

    if resolution_code:
        update_data["close_code"] = resolution_code

    if close_notes:
        update_data["close_notes"] = close_notes

    # Update the incident
    result = client.table_update(table="incident", sys_id=inc_sys_id, data=update_data)
    execution_time = (time.time() - start_time) * 1000

    if result["success"]:
        updated = result["data"].get("result", {})
        return json.dumps({
            "success": True,
            "data": {
                "number": get_val(updated.get("number")),
                "sys_id": inc_sys_id,
                "state": get_val(updated.get("state")),
                "priority": get_val(updated.get("priority")),
                "assigned_to": get_val(updated.get("assigned_to")),
                "assignment_group": get_val(updated.get("assignment_group"))
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "update_incident"
            }
        }, indent=2)
    else:
        return json.dumps({
            "success": False,
            "error": {
                "code": "SERVICENOW_ERROR",
                "message": "Failed to update incident",
                "detail": result["error"]
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "update_incident"
            }
        }, indent=2)


@mcp.tool()
def resolve_close_incident(
    incident_id: str,
    resolution_code: str,
    close_notes: str
) -> str:
    """
    Resolve and close an incident in one step.

    Args:
        incident_id: Incident number (INC0012345) or sys_id
        resolution_code: Resolution code (e.g., "Solved (Permanently)", "Solved (Workaround)")
        close_notes: Resolution details/close notes

    Returns:
        JSON with closed incident details

    Example:
        resolve_close_incident("INC0012345", "Solved (Permanently)", "Database restarted, issue resolved")
    """
    import time
    start_time = time.time()
    client = get_client()

    if not all([incident_id, resolution_code, close_notes]):
        return json.dumps({
            "success": False,
            "error": {
                "code": "MISSING_REQUIRED_FIELD",
                "message": "incident_id, resolution_code, and close_notes are required"
            }
        }, indent=2)

    # Lookup incident
    query = f"number={incident_id}" if incident_id.startswith("INC") else f"sys_id={incident_id}"
    inc_result = client.table_get(table="incident", query=query, limit=1)

    if not inc_result["success"] or not inc_result["data"].get("result"):
        return json.dumps({
            "success": False,
            "error": {
                "code": "RECORD_NOT_FOUND",
                "message": f"Incident not found: {incident_id}"
            }
        }, indent=2)

    incident = inc_result["data"]["result"][0]
    def get_val(field_data):
        if isinstance(field_data, dict):
            return field_data.get("value", field_data.get("display_value"))
        return field_data

    inc_sys_id = get_val(incident.get("sys_id"))

    # Update to resolved and closed
    update_data = {
        "state": "7",  # Closed
        "close_code": resolution_code,
        "close_notes": close_notes
    }

    result = client.table_update(table="incident", sys_id=inc_sys_id, data=update_data)
    execution_time = (time.time() - start_time) * 1000

    if result["success"]:
        closed = result["data"].get("result", {})
        return json.dumps({
            "success": True,
            "data": {
                "number": get_val(closed.get("number")),
                "sys_id": inc_sys_id,
                "state": "Closed",
                "resolution_code": resolution_code,
                "close_notes": close_notes
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "resolve_close_incident"
            }
        }, indent=2)
    else:
        return json.dumps({
            "success": False,
            "error": {
                "code": "SERVICENOW_ERROR",
                "message": "Failed to close incident",
                "detail": result["error"]
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "resolve_close_incident"
            }
        }, indent=2)


@mcp.tool()
def get_incident_details(
    incident_id: str
) -> str:
    """
    Get comprehensive incident details including related records.

    Args:
        incident_id: Incident number (INC0012345) or sys_id

    Returns:
        JSON with complete incident details including:
        - All incident fields
        - Related child incidents
        - Related change requests
        - Work log history
        - SLA information

    Example:
        get_incident_details("INC0012345")
    """
    import time
    start_time = time.time()
    client = get_client()

    if not incident_id:
        return json.dumps({
            "success": False,
            "error": {
                "code": "MISSING_REQUIRED_FIELD",
                "message": "incident_id is required"
            }
        }, indent=2)

    # Get the main incident
    query = f"number={incident_id}" if incident_id.startswith("INC") else f"sys_id={incident_id}"
    result = client.table_get(table="incident", query=query, limit=1, display_value="all")

    if not result["success"] or not result["data"].get("result"):
        return json.dumps({
            "success": False,
            "error": {
                "code": "RECORD_NOT_FOUND",
                "message": f"Incident not found: {incident_id}"
            }
        }, indent=2)

    incident = result["data"]["result"][0]

    def get_val(field_data):
        if isinstance(field_data, dict):
            return field_data.get("display_value", field_data.get("value"))
        return field_data

    inc_sys_id = get_val(incident.get("sys_id"))

    # Get related child incidents
    child_result = client.table_get(
        table="incident",
        query=f"parent_incident={inc_sys_id}",
        fields=["number", "short_description", "state"],
        limit=10,
        display_value="all"
    )
    children = child_result["data"].get("result", []) if child_result["success"] else []

    execution_time = (time.time() - start_time) * 1000

    return json.dumps({
        "success": True,
        "data": {
            "incident": {
                "number": get_val(incident.get("number")),
                "sys_id": inc_sys_id,
                "state": get_val(incident.get("state")),
                "priority": get_val(incident.get("priority")),
                "impact": get_val(incident.get("impact")),
                "urgency": get_val(incident.get("urgency")),
                "short_description": get_val(incident.get("short_description")),
                "description": get_val(incident.get("description")),
                "caller": get_val(incident.get("caller_id")),
                "assigned_to": get_val(incident.get("assigned_to")),
                "assignment_group": get_val(incident.get("assignment_group")),
                "category": get_val(incident.get("category")),
                "subcategory": get_val(incident.get("subcategory")),
                "opened_at": get_val(incident.get("opened_at")),
                "resolved_at": get_val(incident.get("resolved_at")),
                "closed_at": get_val(incident.get("closed_at")),
                "close_code": get_val(incident.get("close_code")),
                "close_notes": get_val(incident.get("close_notes")),
                "work_notes": get_val(incident.get("work_notes")),
                "comments": get_val(incident.get("comments"))
            },
            "related": {
                "child_incidents_count": len(children),
                "child_incidents": [
                    {
                        "number": get_val(child.get("number")),
                        "short_description": get_val(child.get("short_description")),
                        "state": get_val(child.get("state"))
                    }
                    for child in children
                ]
            },
            "url": f"{client.base_url}/incident.do?sys_id={inc_sys_id}"
        },
        "meta": {
            "execution_time_ms": round(execution_time, 2),
            "tool": "get_incident_details"
        }
    }, indent=2)


@mcp.tool()
def list_incidents(
    filter_preset: str = "",
    state: str = "",
    priority: str = "",
    assigned_to_email: str = "",
    assignment_group: str = "",
    hours_ago: int = 24,
    limit: int = 20
) -> str:
    """
    List incidents with pre-built filters for common queries.

    Args:
        filter_preset: Quick filter options:
                      - "my_open" - Open incidents assigned to caller (requires assigned_to_email)
                      - "critical" - Priority 1 (Critical)
                      - "unassigned" - Not assigned to anyone
                      - "breached" - SLA breached
                      - "" (empty) - Custom filter using other parameters
        state: Filter by state (new, in_progress, on_hold, resolved, closed)
        priority: Filter by priority (1-5)
        assigned_to_email: Filter by assignee email
        assignment_group: Filter by assignment group name
        hours_ago: Only show incidents from last N hours (default: 24)
        limit: Maximum incidents to return (default: 20)

    Returns:
        JSON with incident list

    Examples:
        list_incidents(filter_preset="critical")
        list_incidents(filter_preset="unassigned", hours_ago=8)
        list_incidents(state="in_progress", assignment_group="Database")
    """
    import time
    from datetime import datetime, timedelta
    start_time = time.time()
    client = get_client()

    query_parts = []

    # Apply filter preset
    if filter_preset == "critical":
        query_parts.append("priority=1")
    elif filter_preset == "unassigned":
        query_parts.append("assigned_toISEMPTY")
    elif filter_preset == "my_open":
        if not assigned_to_email:
            return json.dumps({
                "success": False,
                "error": {
                    "code": "MISSING_REQUIRED_FIELD",
                    "message": "assigned_to_email required for 'my_open' filter"
                }
            }, indent=2)
        # Lookup user
        user_result = client.table_get(
            table="sys_user",
            query=f"email={assigned_to_email}",
            fields=["sys_id"],
            limit=1
        )
        if user_result["success"] and user_result["data"].get("result"):
            user_sys_id = user_result["data"]["result"][0]["sys_id"]
            query_parts.append(f"assigned_to={user_sys_id}")
            query_parts.append("active=true")
    elif filter_preset == "breached":
        query_parts.append("sla_dueISNOTEMPTY^sla_due<javascript:gs.nowDateTime()")

    # Apply custom filters
    if state:
        state_map = {
            "new": "1", "in_progress": "2", "on_hold": "3",
            "resolved": "6", "closed": "7", "cancelled": "8"
        }
        state_value = state_map.get(state.lower(), state)
        query_parts.append(f"state={state_value}")

    if priority:
        query_parts.append(f"priority={priority}")

    if assigned_to_email and filter_preset != "my_open":
        user_result = client.table_get(
            table="sys_user",
            query=f"email={assigned_to_email}",
            fields=["sys_id"],
            limit=1
        )
        if user_result["success"] and user_result["data"].get("result"):
            user_sys_id = user_result["data"]["result"][0]["sys_id"]
            query_parts.append(f"assigned_to={user_sys_id}")

    if assignment_group:
        group_result = client.table_get(
            table="sys_user_group",
            query=f"nameLIKE{assignment_group}",
            fields=["sys_id"],
            limit=1
        )
        if group_result["success"] and group_result["data"].get("result"):
            group_sys_id = group_result["data"]["result"][0]["sys_id"]
            query_parts.append(f"assignment_group={group_sys_id}")

    # Time filter
    if hours_ago > 0:
        threshold = datetime.utcnow() - timedelta(hours=hours_ago)
        threshold_str = threshold.strftime("%Y-%m-%d %H:%M:%S")
        query_parts.append(f"sys_created_on>{threshold_str}")

    query = "^".join(query_parts) if query_parts else "sys_idISNOTEMPTY"

    result = client.table_get(
        table="incident",
        query=query,
        fields=["number", "short_description", "state", "priority", "assigned_to", "sys_created_on"],
        limit=limit,
        order_by="-sys_created_on",
        display_value="all"
    )

    execution_time = (time.time() - start_time) * 1000

    if result["success"]:
        incidents = result["data"].get("result", [])

        def get_val(field_data):
            if isinstance(field_data, dict):
                return field_data.get("display_value", field_data.get("value"))
            return field_data

        return json.dumps({
            "success": True,
            "data": {
                "count": len(incidents),
                "incidents": [
                    {
                        "number": get_val(inc.get("number")),
                        "short_description": get_val(inc.get("short_description")),
                        "state": get_val(inc.get("state")),
                        "priority": get_val(inc.get("priority")),
                        "assigned_to": get_val(inc.get("assigned_to")),
                        "created": get_val(inc.get("sys_created_on"))
                    }
                    for inc in incidents
                ]
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "list_incidents"
            }
        }, indent=2)
    else:
        return json.dumps({
            "success": False,
            "error": {
                "code": "SERVICENOW_ERROR",
                "message": "Failed to query incidents",
                "detail": result["error"]
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "list_incidents"
            }
        }, indent=2)


# ============================================================================
# ATTACHMENT MANAGEMENT
# ============================================================================

@mcp.tool()
def upload_attachment(
    table: str,
    record_id: str,
    file_name: str,
    content_type: str = "text/plain",
    file_path: str = "",
    file_content_base64: str = ""
) -> str:
    """
    Upload an attachment to any ServiceNow record.

    **IMPORTANT LIMITATION:** Due to filesystem isolation in Claude Desktop, only the
    file_content_base64 method works. This limits uploads to ~5 KB due to MCP protocol
    parameter constraints.

    For large files (screenshots, PDFs, etc.), use ServiceNow UI drag-and-drop instead.

    The tool supports two input methods:
    1. file_path: Only works if MCP server and client share filesystem (NOT in Claude Desktop)
    2. file_content_base64: Works in Claude Desktop but limited to ~5 KB

    Args:
        table: Table name (e.g., "incident", "change_request", "problem")
        record_id: sys_id of the record to attach to
        file_name: Name of the file (e.g., "error_log.txt", "config.json")
        content_type: MIME type (e.g., "text/plain", "application/json")
        file_path: Path to file (only works with shared filesystem - NOT Claude Desktop)
        file_content_base64: Base64-encoded content (works in Claude Desktop, <5 KB limit)

    Returns:
        JSON with attachment sys_id and download URL

    Tested Limitations (Claude Desktop):
        - file_path: ❌ FAILS - "File not found" due to filesystem isolation
        - file_content_base64: ✅ WORKS - But limited to ~5 KB before truncation

    Best For:
        - Small log files and error messages (<5 KB)
        - Configuration files (JSON, XML, YAML)
        - Text snippets and code samples
        - Generated text content

    NOT Suitable For:
        - Screenshots (use ServiceNow UI)
        - Photos and images (use ServiceNow UI)
        - PDFs and documents (use ServiceNow UI)
        - Any file >5 KB (use ServiceNow UI)

    Example (Small Text File):
        upload_attachment(
            "incident", "abc123",
            "error.log", "text/plain",
            file_content_base64="RXJyb3I6IGRhdGFiYXNl..."
        )
    """
    import time
    import base64
    import os
    start_time = time.time()
    client = get_client()

    # Validate required fields
    if not all([table, record_id, file_name]):
        return json.dumps({
            "success": False,
            "error": {
                "code": "MISSING_REQUIRED_FIELD",
                "message": "table, record_id, and file_name are required"
            }
        }, indent=2)

    # Require either file_path or file_content_base64
    if not file_path and not file_content_base64:
        return json.dumps({
            "success": False,
            "error": {
                "code": "MISSING_REQUIRED_FIELD",
                "message": "Either file_path or file_content_base64 is required",
                "detail": "Provide file_path (recommended for large files) or file_content_base64 (small files only)"
            }
        }, indent=2)

    # Upload using ServiceNow Attachment API
    url = f"{client.base_url}/api/now/attachment/file"
    params = {
        "table_name": table,
        "table_sys_id": record_id,
        "file_name": file_name
    }

    try:
        # Get file bytes from either file_path or base64
        if file_path:
            # PREFERRED: Read file from disk (supports large files)
            if not os.path.exists(file_path):
                return json.dumps({
                    "success": False,
                    "error": {
                        "code": "INVALID_INPUT",
                        "message": f"File not found: {file_path}",
                        "field": "file_path"
                    }
                }, indent=2)

            try:
                with open(file_path, "rb") as f:
                    file_bytes = f.read()
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Failed to read file: {file_path}",
                        "detail": str(e)
                    }
                }, indent=2)

        else:
            # LEGACY: Decode base64 (limited to small files)
            try:
                file_bytes = base64.b64decode(file_content_base64)
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": {
                        "code": "INVALID_INPUT",
                        "message": "file_content_base64 is not valid base64",
                        "field": "file_content_base64",
                        "detail": str(e)
                    }
                }, indent=2)

        # Store original session headers
        original_content_type = client.session.headers.get("Content-Type")

        # Temporarily override Content-Type for binary upload
        client.session.headers["Content-Type"] = content_type

        try:
            response = client.session.post(
                url,
                params=params,
                data=file_bytes,
                timeout=client.timeout
            )
        finally:
            # Restore original Content-Type
            if original_content_type:
                client.session.headers["Content-Type"] = original_content_type

        execution_time = (time.time() - start_time) * 1000

        if response.ok:
            attachment = response.json().get("result", {})
            return json.dumps({
                "success": True,
                "data": {
                    "sys_id": attachment.get("sys_id"),
                    "file_name": attachment.get("file_name"),
                    "size_bytes": attachment.get("size_bytes"),
                    "content_type": attachment.get("content_type"),
                    "download_link": attachment.get("download_link")
                },
                "meta": {
                    "execution_time_ms": round(execution_time, 2),
                    "tool": "upload_attachment"
                }
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": {
                    "code": "SERVICENOW_ERROR",
                    "message": f"Failed to upload attachment: HTTP {response.status_code}",
                    "detail": response.text
                },
                "meta": {
                    "execution_time_ms": round(execution_time, 2),
                    "tool": "upload_attachment"
                }
            }, indent=2)

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        return json.dumps({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to upload attachment",
                "detail": str(e)
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "upload_attachment"
            }
        }, indent=2)


@mcp.tool()
def download_attachment(
    attachment_id: str
) -> str:
    """
    Download an attachment from ServiceNow.

    Args:
        attachment_id: sys_id of the attachment

    Returns:
        JSON with base64-encoded file content and metadata

    Example:
        download_attachment("abc123xyz")
    """
    import time
    import base64
    start_time = time.time()
    client = get_client()

    if not attachment_id:
        return json.dumps({
            "success": False,
            "error": {
                "code": "MISSING_REQUIRED_FIELD",
                "message": "attachment_id is required"
            }
        }, indent=2)

    # Get attachment metadata
    meta_result = client.table_get(
        table="sys_attachment",
        sys_id=attachment_id,
        display_value="false"
    )

    if not meta_result["success"] or not meta_result["data"].get("result"):
        return json.dumps({
            "success": False,
            "error": {
                "code": "RECORD_NOT_FOUND",
                "message": f"Attachment not found: {attachment_id}"
            }
        }, indent=2)

    attachment = meta_result["data"]["result"]

    # Download file content
    url = f"{client.base_url}/api/now/attachment/{attachment_id}/file"

    try:
        response = client.session.get(url, timeout=client.timeout)
        execution_time = (time.time() - start_time) * 1000

        if response.ok:
            # Encode to base64
            file_content_base64 = base64.b64encode(response.content).decode('utf-8')

            return json.dumps({
                "success": True,
                "data": {
                    "sys_id": attachment_id,
                    "file_name": attachment.get("file_name"),
                    "content_type": attachment.get("content_type"),
                    "size_bytes": attachment.get("size_bytes"),
                    "file_content_base64": file_content_base64
                },
                "meta": {
                    "execution_time_ms": round(execution_time, 2),
                    "tool": "download_attachment"
                }
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": {
                    "code": "SERVICENOW_ERROR",
                    "message": f"Failed to download attachment: HTTP {response.status_code}",
                    "detail": response.text
                },
                "meta": {
                    "execution_time_ms": round(execution_time, 2),
                    "tool": "download_attachment"
                }
            }, indent=2)

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        return json.dumps({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to download attachment",
                "detail": str(e)
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "download_attachment"
            }
        }, indent=2)


@mcp.tool()
def list_attachments(
    table: str = "",
    record_id: str = "",
    file_name_filter: str = "",
    limit: int = 50
) -> str:
    """
    List attachments on a record or search by filename.

    Args:
        table: Table name to filter by (optional)
        record_id: Record sys_id to filter by (optional)
        file_name_filter: Search attachments by filename (uses LIKE)
        limit: Maximum attachments to return (default: 50)

    Returns:
        JSON with attachment list

    Examples:
        list_attachments(table="incident", record_id="abc123")
        list_attachments(file_name_filter="screenshot")
    """
    import time
    start_time = time.time()
    client = get_client()

    query_parts = []

    if table:
        query_parts.append(f"table_name={table}")

    if record_id:
        query_parts.append(f"table_sys_id={record_id}")

    if file_name_filter:
        query_parts.append(f"file_nameLIKE{file_name_filter}")

    query = "^".join(query_parts) if query_parts else "sys_idISNOTEMPTY"

    result = client.table_get(
        table="sys_attachment",
        query=query,
        fields=["sys_id", "file_name", "content_type", "size_bytes", "table_name", "table_sys_id", "sys_created_on"],
        limit=limit,
        order_by="-sys_created_on",
        display_value="true"
    )

    execution_time = (time.time() - start_time) * 1000

    if result["success"]:
        attachments = result["data"].get("result", [])

        def get_val(field_data):
            if isinstance(field_data, dict):
                return field_data.get("display_value", field_data.get("value"))
            return field_data

        return json.dumps({
            "success": True,
            "data": {
                "count": len(attachments),
                "attachments": [
                    {
                        "sys_id": get_val(att.get("sys_id")),
                        "file_name": get_val(att.get("file_name")),
                        "content_type": get_val(att.get("content_type")),
                        "size_bytes": get_val(att.get("size_bytes")),
                        "table": get_val(att.get("table_name")),
                        "record_id": get_val(att.get("table_sys_id")),
                        "created": get_val(att.get("sys_created_on")),
                        "download_url": f"{client.base_url}/api/now/attachment/{get_val(att.get('sys_id'))}/file"
                    }
                    for att in attachments
                ]
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "list_attachments"
            }
        }, indent=2)
    else:
        return json.dumps({
            "success": False,
            "error": {
                "code": "SERVICENOW_ERROR",
                "message": "Failed to list attachments",
                "detail": result["error"]
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "list_attachments"
            }
        }, indent=2)


@mcp.tool()
def delete_attachment(
    attachment_id: str
) -> str:
    """
    Delete an attachment from ServiceNow.

    Args:
        attachment_id: sys_id of the attachment to delete

    Returns:
        JSON with success confirmation

    Example:
        delete_attachment("abc123xyz")
    """
    import time
    start_time = time.time()
    client = get_client()

    if not attachment_id:
        return json.dumps({
            "success": False,
            "error": {
                "code": "MISSING_REQUIRED_FIELD",
                "message": "attachment_id is required"
            }
        }, indent=2)

    result = client.table_delete(table="sys_attachment", sys_id=attachment_id)
    execution_time = (time.time() - start_time) * 1000

    if result["success"]:
        return json.dumps({
            "success": True,
            "data": {
                "message": "Attachment deleted successfully",
                "attachment_id": attachment_id
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "delete_attachment"
            }
        }, indent=2)
    else:
        return json.dumps({
            "success": False,
            "error": {
                "code": "SERVICENOW_ERROR",
                "message": "Failed to delete attachment",
                "detail": result["error"]
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "delete_attachment"
            }
        }, indent=2)


# ============================================================================
# APPROVAL MANAGEMENT
# ============================================================================

@mcp.tool()
def list_pending_approvals(
    approver_email: str = "",
    source_table: str = "",
    state: str = "requested",
    limit: int = 50
) -> str:
    """
    List pending approvals.

    Args:
        approver_email: Filter by approver email (shows "my approvals")
        source_table: Filter by source table (e.g., "change_request", "sc_req_item")
        state: Filter by state (requested, approved, rejected, cancelled) - default: requested
        limit: Maximum approvals to return (default: 50)

    Returns:
        JSON with approval list

    Examples:
        list_pending_approvals(approver_email="john.doe@example.com")
        list_pending_approvals(source_table="change_request", state="requested")
    """
    import time
    start_time = time.time()
    client = get_client()

    query_parts = []

    # Map state to ServiceNow values
    state_map = {
        "requested": "requested",
        "approved": "approved",
        "rejected": "rejected",
        "cancelled": "cancelled"
    }
    state_value = state_map.get(state.lower(), state)
    query_parts.append(f"state={state_value}")

    if approver_email:
        user_result = client.table_get(
            table="sys_user",
            query=f"email={approver_email}",
            fields=["sys_id"],
            limit=1
        )
        if user_result["success"] and user_result["data"].get("result"):
            user_sys_id = user_result["data"]["result"][0]["sys_id"]
            query_parts.append(f"approver={user_sys_id}")

    if source_table:
        query_parts.append(f"source_table={source_table}")

    query = "^".join(query_parts)

    result = client.table_get(
        table="sysapproval_approver",
        query=query,
        fields=["sys_id", "approver", "source_table", "sysapproval", "state", "comments", "sys_created_on"],
        limit=limit,
        order_by="-sys_created_on",
        display_value="all"
    )

    execution_time = (time.time() - start_time) * 1000

    if result["success"]:
        approvals = result["data"].get("result", [])

        def get_val(field_data):
            if isinstance(field_data, dict):
                return field_data.get("display_value", field_data.get("value"))
            return field_data

        return json.dumps({
            "success": True,
            "data": {
                "count": len(approvals),
                "approvals": [
                    {
                        "sys_id": get_val(app.get("sys_id")),
                        "approver": get_val(app.get("approver")),
                        "source_table": get_val(app.get("source_table")),
                        "source_record": get_val(app.get("sysapproval")),
                        "state": get_val(app.get("state")),
                        "comments": get_val(app.get("comments")),
                        "created": get_val(app.get("sys_created_on"))
                    }
                    for app in approvals
                ]
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "list_pending_approvals"
            }
        }, indent=2)
    else:
        return json.dumps({
            "success": False,
            "error": {
                "code": "SERVICENOW_ERROR",
                "message": "Failed to list approvals",
                "detail": result["error"]
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "list_pending_approvals"
            }
        }, indent=2)


@mcp.tool()
def approve_record(
    approval_id: str,
    comments: str = ""
) -> str:
    """
    Approve a pending approval.

    Args:
        approval_id: sys_id of the approval record (from sysapproval_approver table)
        comments: Optional approval comments

    Returns:
        JSON with approval confirmation

    Example:
        approve_record("abc123", "Emergency approval granted")
    """
    import time
    start_time = time.time()
    client = get_client()

    if not approval_id:
        return json.dumps({
            "success": False,
            "error": {
                "code": "MISSING_REQUIRED_FIELD",
                "message": "approval_id is required"
            }
        }, indent=2)

    update_data = {
        "state": "approved"
    }

    if comments:
        update_data["comments"] = comments

    result = client.table_update(table="sysapproval_approver", sys_id=approval_id, data=update_data)
    execution_time = (time.time() - start_time) * 1000

    if result["success"]:
        approval = result["data"].get("result", {})

        def get_val(field_data):
            if isinstance(field_data, dict):
                return field_data.get("display_value", field_data.get("value"))
            return field_data

        return json.dumps({
            "success": True,
            "data": {
                "approval_id": approval_id,
                "state": "Approved",
                "approver": get_val(approval.get("approver")),
                "source_record": get_val(approval.get("sysapproval")),
                "comments": comments
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "approve_record"
            }
        }, indent=2)
    else:
        return json.dumps({
            "success": False,
            "error": {
                "code": "SERVICENOW_ERROR",
                "message": "Failed to approve record",
                "detail": result["error"]
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "approve_record"
            }
        }, indent=2)


@mcp.tool()
def reject_record(
    approval_id: str,
    reason: str
) -> str:
    """
    Reject a pending approval with mandatory reason.

    Args:
        approval_id: sys_id of the approval record
        reason: Rejection reason (required)

    Returns:
        JSON with rejection confirmation

    Example:
        reject_record("abc123", "Insufficient justification provided")
    """
    import time
    start_time = time.time()
    client = get_client()

    if not approval_id or not reason:
        return json.dumps({
            "success": False,
            "error": {
                "code": "MISSING_REQUIRED_FIELD",
                "message": "approval_id and reason are required"
            }
        }, indent=2)

    update_data = {
        "state": "rejected",
        "comments": reason
    }

    result = client.table_update(table="sysapproval_approver", sys_id=approval_id, data=update_data)
    execution_time = (time.time() - start_time) * 1000

    if result["success"]:
        approval = result["data"].get("result", {})

        def get_val(field_data):
            if isinstance(field_data, dict):
                return field_data.get("display_value", field_data.get("value"))
            return field_data

        return json.dumps({
            "success": True,
            "data": {
                "approval_id": approval_id,
                "state": "Rejected",
                "approver": get_val(approval.get("approver")),
                "source_record": get_val(approval.get("sysapproval")),
                "reason": reason
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "reject_record"
            }
        }, indent=2)
    else:
        return json.dumps({
            "success": False,
            "error": {
                "code": "SERVICENOW_ERROR",
                "message": "Failed to reject record",
                "detail": result["error"]
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "reject_record"
            }
        }, indent=2)


@mcp.tool()
def get_approval_details(
    approval_id: str
) -> str:
    """
    Get complete details of an approval including source record.

    Args:
        approval_id: sys_id of the approval record

    Returns:
        JSON with approval details and source record information

    Example:
        get_approval_details("abc123")
    """
    import time
    start_time = time.time()
    client = get_client()

    if not approval_id:
        return json.dumps({
            "success": False,
            "error": {
                "code": "MISSING_REQUIRED_FIELD",
                "message": "approval_id is required"
            }
        }, indent=2)

    result = client.table_get(
        table="sysapproval_approver",
        sys_id=approval_id,
        display_value="all"
    )

    execution_time = (time.time() - start_time) * 1000

    if not result["success"] or not result["data"].get("result"):
        return json.dumps({
            "success": False,
            "error": {
                "code": "RECORD_NOT_FOUND",
                "message": f"Approval not found: {approval_id}"
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "get_approval_details"
            }
        }, indent=2)

    approval = result["data"]["result"]

    def get_val(field_data):
        if isinstance(field_data, dict):
            return field_data.get("display_value", field_data.get("value"))
        return field_data

    return json.dumps({
        "success": True,
        "data": {
            "approval": {
                "sys_id": approval_id,
                "approver": get_val(approval.get("approver")),
                "state": get_val(approval.get("state")),
                "comments": get_val(approval.get("comments")),
                "source_table": get_val(approval.get("source_table")),
                "source_record": get_val(approval.get("sysapproval")),
                "due_date": get_val(approval.get("due_date")),
                "sys_created_on": get_val(approval.get("sys_created_on")),
                "sys_updated_on": get_val(approval.get("sys_updated_on"))
            }
        },
        "meta": {
            "execution_time_ms": round(execution_time, 2),
            "tool": "get_approval_details"
        }
    }, indent=2)


# ============================================================================
# PHASE 1.5: PRE-FLIGHT VALIDATION TOOLS
# ============================================================================
# Dynamically discover UI Policy mandatory fields and validate record data
# before API calls to prevent incomplete record creation
# ============================================================================

@mcp.tool()
def get_form_mandatory_fields(
    table_name: str,
    view: str = "default"
) -> str:
    """
    Discover ALL mandatory fields for a table including UI Policy-enforced fields.

    This tool solves the blind spot where UI Policies make fields mandatory but
    the Table API doesn't know about them, causing silent failures where records
    are created but missing critical data.

    Queries:
    1. Dictionary (sys_dictionary) for database-level mandatory fields
    2. UI Policies (sys_ui_policy) for form-level mandatory fields
    3. UI Policy Actions (sys_ui_policy_action) for specific field requirements

    Args:
        table_name: ServiceNow table name (e.g., 'incident', 'change_request')
        view: Form view name (default: 'default')

    Returns:
        JSON with:
        - dictionary_mandatory: Fields mandatory at DB level
        - ui_policy_mandatory: Fields mandatory via UI policies
        - all_mandatory: Complete list of required fields
        - ui_policies: Details of active UI policies and their conditions

    Example:
        get_form_mandatory_fields("incident")
        get_form_mandatory_fields("change_request", "itil")
    """
    import time
    from datetime import datetime

    start_time = time.time()
    client = get_client()

    # Input validation
    if not table_name:
        return json.dumps({
            "success": False,
            "error": {
                "code": "MISSING_REQUIRED_FIELD",
                "message": "table_name is required",
                "field": "table_name"
            },
            "meta": {
                "tool": "get_form_mandatory_fields",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }, indent=2)

    try:
        # Step 1: Get dictionary-level mandatory fields
        dict_query = f"name={table_name}^mandatory=true^active=true"
        dict_result = client.table_get(
            table="sys_dictionary",
            query=dict_query,
            fields=["element", "column_label", "internal_type", "mandatory"],
            limit=1000
        )

        dictionary_mandatory = []
        if dict_result["success"] and dict_result["data"].get("result"):
            for field in dict_result["data"]["result"]:
                dictionary_mandatory.append({
                    "field": field.get("element"),
                    "label": field.get("column_label"),
                    "type": field.get("internal_type"),
                    "source": "dictionary"
                })

        # Step 2: Get UI Policies for this table
        # Active policies that apply to the specified view or all views
        policy_query = f"table={table_name}^active=true"
        if view != "default":
            policy_query += f"^view={view}^ORviewISEMPTY"

        policy_result = client.table_get(
            table="sys_ui_policy",
            query=policy_query,
            fields=["sys_id", "short_description", "conditions", "reverse_if_false", "on_load"],
            limit=100
        )

        ui_policies = []
        ui_policy_mandatory = []

        if policy_result["success"] and policy_result["data"].get("result"):
            policy_sys_ids = []

            for policy in policy_result["data"]["result"]:
                policy_sys_id = policy.get("sys_id")
                policy_sys_ids.append(policy_sys_id)

                ui_policies.append({
                    "sys_id": policy_sys_id,
                    "description": policy.get("short_description"),
                    "conditions": policy.get("conditions") or "Always active",
                    "reverse_if_false": policy.get("reverse_if_false") == "true",
                    "on_load": policy.get("on_load") == "true"
                })

            # Step 3: Get UI Policy Actions for these policies
            if policy_sys_ids:
                # Query in batches if needed (ServiceNow has query length limits)
                action_query = f"ui_policy.sys_idIN{','.join(policy_sys_ids)}^mandatory=true^active=true"

                action_result = client.table_get(
                    table="sys_ui_policy_action",
                    query=action_query,
                    fields=["field", "mandatory", "ui_policy"],
                    limit=1000,
                    display_value="all"
                )

                if action_result["success"] and action_result["data"].get("result"):
                    seen_fields = set()
                    for action in action_result["data"]["result"]:
                        field_name = action.get("field")
                        if isinstance(field_name, dict):
                            field_name = field_name.get("value")

                        if field_name and field_name not in seen_fields:
                            seen_fields.add(field_name)

                            # Find which policy this action belongs to
                            policy_ref = action.get("ui_policy")
                            policy_id = policy_ref.get("value") if isinstance(policy_ref, dict) else policy_ref

                            policy_info = next(
                                (p for p in ui_policies if p["sys_id"] == policy_id),
                                {"description": "Unknown policy", "conditions": "Unknown"}
                            )

                            ui_policy_mandatory.append({
                                "field": field_name,
                                "source": "ui_policy",
                                "policy": policy_info["description"],
                                "conditions": policy_info["conditions"]
                            })

        # Step 4: Combine and deduplicate
        all_mandatory_fields = set()

        # Add dictionary mandatory fields
        for field in dictionary_mandatory:
            all_mandatory_fields.add(field["field"])

        # Add UI policy mandatory fields
        for field in ui_policy_mandatory:
            all_mandatory_fields.add(field["field"])

        execution_time = (time.time() - start_time) * 1000

        return json.dumps({
            "success": True,
            "data": {
                "table": table_name,
                "view": view,
                "summary": {
                    "dictionary_mandatory_count": len(dictionary_mandatory),
                    "ui_policy_mandatory_count": len(ui_policy_mandatory),
                    "total_mandatory_fields": len(all_mandatory_fields)
                },
                "dictionary_mandatory": dictionary_mandatory,
                "ui_policy_mandatory": ui_policy_mandatory,
                "all_mandatory_fields": sorted(list(all_mandatory_fields)),
                "ui_policies_active": ui_policies,
                "note": "UI policy fields may be conditional - check 'conditions' field"
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "instance": client.base_url,
                "tool": "get_form_mandatory_fields",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }, indent=2)

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        return json.dumps({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Failed to retrieve mandatory fields",
                "detail": str(e)
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "get_form_mandatory_fields"
            }
        }, indent=2)


@mcp.tool()
def validate_record_data(
    table_name: str,
    record_data: str,
    view: str = "default",
    strict_mode: bool = False
) -> str:
    """
    Pre-flight validation of record data before creation/update.

    Validates that all mandatory fields (both dictionary and UI Policy enforced)
    are present in the record data. Prevents API calls that will fail or create
    incomplete records.

    This is the tool Claude should call BEFORE create_incident, order_catalog_item,
    or any snow_create_record operation.

    Args:
        table_name: ServiceNow table name
        record_data: JSON string of field values to validate
        view: Form view name (default: 'default')
        strict_mode: If true, fail on ANY missing mandatory field.
                     If false, only warn about UI policy fields (default).

    Returns:
        JSON with:
        - valid: Boolean indicating if data passes validation
        - missing_fields: List of required fields not in record_data
        - warnings: Non-critical issues
        - ready_to_submit: Whether it's safe to proceed with API call

    Example:
        # Validate incident data
        validate_record_data(
            "incident",
            '{"short_description": "Test", "caller_id": "abc123"}',
            strict_mode=True
        )

        # Validate change request
        validate_record_data(
            "change_request",
            '{"short_description": "Update server", "priority": "3"}'
        )
    """
    import time
    from datetime import datetime

    start_time = time.time()

    # Input validation
    if not table_name:
        return json.dumps({
            "success": False,
            "error": {
                "code": "MISSING_REQUIRED_FIELD",
                "message": "table_name is required",
                "field": "table_name"
            },
            "meta": {
                "tool": "validate_record_data",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }, indent=2)

    if not record_data:
        return json.dumps({
            "success": False,
            "error": {
                "code": "MISSING_REQUIRED_FIELD",
                "message": "record_data is required",
                "field": "record_data"
            },
            "meta": {
                "tool": "validate_record_data",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }, indent=2)

    try:
        # Parse record data
        try:
            data = json.loads(record_data) if isinstance(record_data, str) else record_data
        except json.JSONDecodeError as e:
            return json.dumps({
                "success": False,
                "error": {
                    "code": "INVALID_JSON",
                    "message": "record_data is not valid JSON",
                    "detail": str(e),
                    "field": "record_data"
                },
                "meta": {
                    "tool": "validate_record_data"
                }
            }, indent=2)

        # Get mandatory fields for this table
        mandatory_result = get_form_mandatory_fields(table_name, view)
        mandatory_info = json.loads(mandatory_result)

        if not mandatory_info.get("success"):
            return json.dumps({
                "success": False,
                "error": {
                    "code": "VALIDATION_FAILED",
                    "message": "Could not retrieve mandatory fields",
                    "detail": mandatory_info.get("error", {}).get("message", "Unknown error")
                },
                "meta": {
                    "tool": "validate_record_data"
                }
            }, indent=2)

        # Extract mandatory field info
        mandatory_data = mandatory_info.get("data", {})
        all_mandatory = set(mandatory_data.get("all_mandatory_fields", []))
        dictionary_mandatory = {f["field"] for f in mandatory_data.get("dictionary_mandatory", [])}
        ui_policy_mandatory_list = mandatory_data.get("ui_policy_mandatory", [])
        ui_policy_mandatory = {f["field"] for f in ui_policy_mandatory_list}

        # Get fields present in record data
        provided_fields = set(data.keys())

        # Check for missing fields
        missing_dictionary = dictionary_mandatory - provided_fields
        missing_ui_policy = ui_policy_mandatory - provided_fields
        all_missing = all_mandatory - provided_fields

        # Build validation result
        warnings = []
        errors = []

        # Dictionary mandatory fields are ALWAYS required
        if missing_dictionary:
            for field in missing_dictionary:
                field_info = next(
                    (f for f in mandatory_data.get("dictionary_mandatory", []) if f["field"] == field),
                    {}
                )
                errors.append({
                    "field": field,
                    "label": field_info.get("label", field),
                    "type": field_info.get("type", "unknown"),
                    "reason": "Database-level mandatory field (always required)",
                    "severity": "error"
                })

        # UI Policy mandatory fields may be conditional
        if missing_ui_policy:
            for field in missing_ui_policy:
                field_info = next(
                    (f for f in ui_policy_mandatory_list if f["field"] == field),
                    {}
                )

                issue = {
                    "field": field,
                    "reason": f"UI Policy: {field_info.get('policy', 'Unknown')}",
                    "conditions": field_info.get("conditions", "Always active"),
                    "severity": "error" if strict_mode else "warning"
                }

                if strict_mode:
                    errors.append(issue)
                else:
                    warnings.append(issue)

        # Determine if validation passed
        is_valid = len(errors) == 0
        ready_to_submit = is_valid  # Can proceed if no errors

        execution_time = (time.time() - start_time) * 1000

        return json.dumps({
            "success": True,
            "data": {
                "valid": is_valid,
                "ready_to_submit": ready_to_submit,
                "table": table_name,
                "view": view,
                "strict_mode": strict_mode,
                "summary": {
                    "fields_provided": len(provided_fields),
                    "fields_required": len(all_mandatory),
                    "fields_missing": len(all_missing),
                    "errors": len(errors),
                    "warnings": len(warnings)
                },
                "provided_fields": sorted(list(provided_fields)),
                "required_fields": sorted(list(all_mandatory)),
                "missing_fields": sorted(list(all_missing)),
                "errors": errors,
                "warnings": warnings,
                "recommendation": (
                    "✅ All mandatory fields present. Safe to submit." if is_valid
                    else f"❌ Missing {len(errors)} required fields. Do not submit until resolved."
                ) if strict_mode else (
                    "✅ All database mandatory fields present. Submit with caution - UI policy fields may be required." if len(missing_dictionary) == 0
                    else f"❌ Missing {len(missing_dictionary)} database mandatory fields. Cannot submit."
                )
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "validate_record_data",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }, indent=2)

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        return json.dumps({
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Validation failed unexpectedly",
                "detail": str(e)
            },
            "meta": {
                "execution_time_ms": round(execution_time, 2),
                "tool": "validate_record_data"
            }
        }, indent=2)


# ============================================================================
# ORIGINAL SYSLOG TOOL
# ============================================================================

@mcp.tool()
def query_syslog(
    message_contains: str = "",
    source: str = "",
    level: str = "",
    limit: int = 20,
    minutes_ago: int = 60
) -> str:
    """
    Query the ServiceNow syslog table for debugging.
    
    Args:
        message_contains: Filter by message text
        source: Filter by source
        level: Filter by log level (error, warn, info, etc.)
        limit: Max number of records to return (default 20)
        minutes_ago: Only show logs from last N minutes (default 60)
    """
    query_parts = []
    if message_contains:
        query_parts.append(f"messageLIKE{message_contains}")
    if source:
        query_parts.append(f"sourceLIKE{source}")
    if level:
        query_parts.append(f"level={level}")
    query_parts.append(f"sys_created_onRELATIVEGT@minute@ago@{minutes_ago}")
    query = "^".join(query_parts)

    url = f"{INSTANCE}/api/now/table/syslog"
    params = {
        "sysparm_query": f"{query}^ORDERBYDESCsys_created_on",
        "sysparm_limit": limit,
        "sysparm_fields": "sys_created_on,level,source,message"
    }

    response = requests.get(
        url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    results = response.json().get("result", [])
    if not results:
        return "No syslog entries found matching your criteria."

    output = []
    for entry in results:
        output.append(
            f"[{entry.get('sys_created_on')}] "
            f"{entry.get('level', 'N/A').upper()} | "
            f"{entry.get('source', 'N/A')}\n"
            f"{entry.get('message', 'No message')}\n"
        )
    return "\n---\n".join(output)


# ============================================================================
# FLOW DESIGNER EXECUTION TOOLS
# ============================================================================

@mcp.tool()
def query_flow_contexts(
    flow_name: str = "",
    status: str = "",
    minutes_ago: int = 60,
    limit: int = 20
) -> str:
    """
    Query Flow Designer execution contexts (sys_flow_context).
    Shows high-level flow execution summary including run time, status, and duration.
    
    Args:
        flow_name: Filter by flow name
        status: Filter by status (success, error, waiting, cancelled, etc.)
        minutes_ago: Only show executions from last N minutes (default 60)
        limit: Max number of records to return (default 20)
    """
    query_parts = []
    if flow_name:
        query_parts.append(f"flow.nameLIKE{flow_name}")
    if status:
        query_parts.append(f"status={status}")
    query_parts.append(f"sys_created_onRELATIVEGT@minute@ago@{minutes_ago}")
    query = "^".join(query_parts)

    url = f"{INSTANCE}/api/now/table/sys_flow_context"
    params = {
        "sysparm_query": f"{query}^ORDERBYDESCsys_created_on",
        "sysparm_limit": limit,
        "sysparm_fields": "sys_id,flow.name,status,started,ended,duration,output,sys_created_on"
    }

    response = requests.get(
        url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    results = response.json().get("result", [])
    if not results:
        return "No flow contexts found matching your criteria."

    output = []
    for ctx in results:
        output.append(
            f"Flow: {ctx.get('flow.name', 'N/A')}\n"
            f"Context ID: {ctx.get('sys_id')}\n"
            f"Status: {ctx.get('status', 'N/A')}\n"
            f"Started: {ctx.get('started', 'N/A')}\n"
            f"Ended: {ctx.get('ended', 'N/A')}\n"
            f"Duration: {ctx.get('duration', 'N/A')} seconds\n"
            f"Created: {ctx.get('sys_created_on', 'N/A')}"
        )
    return "\n\n---\n\n".join(output)


@mcp.tool()
def query_flow_logs(
    flow_context_id: str = "",
    level: str = "",
    message_contains: str = "",
    minutes_ago: int = 60,
    limit: int = 50
) -> str:
    """
    Query Flow Designer detailed logs (sys_flow_log).
    Captures detailed logs for Flow Designer actions.
    
    Args:
        flow_context_id: Filter by specific flow context sys_id
        level: Filter by log level (error, warn, info, debug)
        message_contains: Filter by message text
        minutes_ago: Only show logs from last N minutes (default 60)
        limit: Max number of records to return (default 50)
    """
    query_parts = []
    if flow_context_id:
        query_parts.append(f"context={flow_context_id}")
    if level:
        query_parts.append(f"level={level}")
    if message_contains:
        query_parts.append(f"messageLIKE{message_contains}")
    query_parts.append(f"sys_created_onRELATIVEGT@minute@ago@{minutes_ago}")
    query = "^".join(query_parts)

    url = f"{INSTANCE}/api/now/table/sys_flow_log"
    params = {
        "sysparm_query": f"{query}^ORDERBYDESCsys_created_on",
        "sysparm_limit": limit,
        "sysparm_fields": "sys_id,context,level,message,action,sys_created_on"
    }

    response = requests.get(
        url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    results = response.json().get("result", [])
    if not results:
        return "No flow logs found matching your criteria."

    output = []
    for log in results:
        output.append(
            f"[{log.get('sys_created_on')}] {log.get('level', 'N/A').upper()}\n"
            f"Context: {log.get('context', 'N/A')}\n"
            f"Action: {log.get('action', 'N/A')}\n"
            f"Message: {log.get('message', 'N/A')}"
        )
    return "\n\n---\n\n".join(output)


@mcp.tool()
def get_flow_context_details(
    flow_context_id: str
) -> str:
    """
    Get complete details of a flow execution including its logs.
    
    Args:
        flow_context_id: Sys ID of the flow context to investigate
    """
    # Get flow context
    ctx_url = f"{INSTANCE}/api/now/table/sys_flow_context/{flow_context_id}"
    params = {
        "sysparm_fields": "sys_id,flow.name,status,started,ended,duration,output,inputs,sys_created_on"
    }

    ctx_response = requests.get(
        ctx_url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if ctx_response.status_code != 200:
        return f"Error: {ctx_response.status_code} - {ctx_response.text}"

    ctx = ctx_response.json().get("result", {})
    if not ctx:
        return "Flow context not found."

    output = [
        "=== FLOW CONTEXT DETAILS ===",
        f"Flow: {ctx.get('flow.name', 'N/A')}",
        f"Context ID: {ctx.get('sys_id')}",
        f"Status: {ctx.get('status', 'N/A')}",
        f"Started: {ctx.get('started', 'N/A')}",
        f"Ended: {ctx.get('ended', 'N/A')}",
        f"Duration: {ctx.get('duration', 'N/A')} seconds",
        f"Created: {ctx.get('sys_created_on', 'N/A')}"
    ]
    
    inputs = ctx.get('inputs', '')
    if inputs:
        output.append(f"\nInputs: {inputs[:500]}")
    
    flow_output = ctx.get('output', '')
    if flow_output:
        output.append(f"\nOutput: {flow_output[:500]}")

    # Get flow logs for this context
    log_url = f"{INSTANCE}/api/now/table/sys_flow_log"
    log_params = {
        "sysparm_query": f"context={flow_context_id}^ORDERBYsys_created_on",
        "sysparm_limit": 100,
        "sysparm_fields": "level,message,action,sys_created_on"
    }

    log_response = requests.get(
        log_url, params=log_params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if log_response.status_code == 200:
        logs = log_response.json().get("result", [])
        if logs:
            output.append("\n=== FLOW LOGS ===")
            for i, log in enumerate(logs, 1):
                level = log.get('level', 'N/A')
                output.append(
                    f"{i}. [{log.get('sys_created_on')}] {level.upper()}\n"
                    f"   Action: {log.get('action', 'N/A')}\n"
                    f"   Message: {log.get('message', 'N/A')}"
                )
        else:
            output.append("\n=== FLOW LOGS ===\nNo logs found")

    return "\n".join(output)


@mcp.tool()
def query_generative_ai_logs_detailed(
    minutes_ago: int = 60,
    limit: int = 20,
    execution_plan_id: str = ""
) -> str:
    """
    Query the sys_generative_ai_log table with FULL field access for detailed AI/LLM debugging.
    This gets ALL fields including error messages, request/response data, and execution details.
    
    Args:
        minutes_ago: Only show logs from last N minutes (default 60)
        limit: Max number of records to return (default 20)
        execution_plan_id: Filter by specific execution plan sys_id (optional)
    """
    query_parts = []
    if execution_plan_id:
        query_parts.append(f"execution_plan={execution_plan_id}")
    query_parts.append(f"sys_created_onRELATIVEGT@minute@ago@{minutes_ago}")
    query = "^".join(query_parts)

    url = f"{INSTANCE}/api/now/table/sys_generative_ai_log"
    params = {
        "sysparm_query": f"{query}^ORDERBYDESCsys_created_on",
        "sysparm_limit": limit,
        "sysparm_display_value": "false"  # Get raw values
    }

    response = requests.get(
        url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    results = response.json().get("result", [])
    if not results:
        return "No generative AI logs found matching your criteria."

    output = []
    for log in results:
        entry = [
            f"=== GENERATIVE AI LOG ===",
            f"Created: {log.get('sys_created_on')}",
            f"Sys ID: {log.get('sys_id')}",
            f"Capability: {log.get('capability', 'N/A')}",
            f"Model: {log.get('model', 'N/A')}",
            f"Status: {log.get('status', 'N/A')}",
            f"Execution Plan: {log.get('execution_plan', 'N/A')}",
            f"Provider: {log.get('provider', 'N/A')}",
            f"Input Tokens: {log.get('input_tokens', 'N/A')}",
            f"Output Tokens: {log.get('output_tokens', 'N/A')}",
            f"Total Tokens: {log.get('total_tokens', 'N/A')}",
            f"Duration (ms): {log.get('duration_ms', 'N/A')}",
        ]
        
        # Add error information if present
        if log.get('error_message'):
            entry.append(f"ERROR MESSAGE: {log.get('error_message')}")
        if log.get('error_code'):
            entry.append(f"ERROR CODE: {log.get('error_code')}")
        if log.get('error_details'):
            entry.append(f"ERROR DETAILS: {log.get('error_details')[:500]}")
        
        # Add request/response data (truncated)
        if log.get('request'):
            entry.append(f"\nREQUEST (first 500 chars):\n{str(log.get('request'))[:500]}")
        if log.get('response'):
            entry.append(f"\nRESPONSE (first 500 chars):\n{str(log.get('response'))[:500]}")
            
        output.append("\n".join(entry))
    
    return "\n\n---\n\n".join(output)


@mcp.tool()
def query_flow_reports(
    flow_context_id: str = "",
    minutes_ago: int = 60,
    limit: int = 20
) -> str:
    """
    Query Flow Designer reporting data (sys_flow_report_doc_chunk).
    Stores detailed runtime states, inputs, and outputs for flows.
    
    Args:
        flow_context_id: Filter by specific flow context sys_id
        minutes_ago: Only show reports from last N minutes (default 60)
        limit: Max number of records to return (default 20)
    """
    query_parts = []
    if flow_context_id:
        query_parts.append(f"context={flow_context_id}")
    query_parts.append(f"sys_created_onRELATIVEGT@minute@ago@{minutes_ago}")
    query = "^".join(query_parts)

    url = f"{INSTANCE}/api/now/table/sys_flow_report_doc_chunk"
    params = {
        "sysparm_query": f"{query}^ORDERBYDESCsys_created_on",
        "sysparm_limit": limit,
        "sysparm_fields": "sys_id,context,data,sys_created_on"
    }

    response = requests.get(
        url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    results = response.json().get("result", [])
    if not results:
        return "No flow report chunks found matching your criteria."

    output = []
    for report in results:
        data = report.get('data', '')
        output.append(
            f"Report ID: {report.get('sys_id')}\n"
            f"Context: {report.get('context', 'N/A')}\n"
            f"Created: {report.get('sys_created_on', 'N/A')}\n"
            f"Data (first 500 chars): {data[:500]}"
        )
    return "\n\n---\n\n".join(output)


# ============================================================================
# AI AGENT CONFIGURATION TOOLS
# ============================================================================

@mcp.tool()
def list_agentic_workflows(
    active_only: bool = True,
    limit: int = 50
) -> str:
    """
    List all agentic workflows (use cases) configured in the system.
    
    Args:
        active_only: Only show active workflows (default True)
        limit: Max number of records to return (default 50)
    """
    query_parts = []
    if active_only:
        query_parts.append("active=true")
    query = "^".join(query_parts) if query_parts else ""
    
    url = f"{INSTANCE}/api/now/table/sn_aia_usecase"
    params = {
        "sysparm_query": f"{query}^ORDERBYDESCsys_created_on" if query else "ORDERBYDESCsys_created_on",
        "sysparm_limit": limit,
        "sysparm_fields": "sys_id,name,description,active,state,sys_created_on,sys_updated_on"
    }

    response = requests.get(
        url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    results = response.json().get("result", [])
    if not results:
        return "No agentic workflows found."

    output = []
    for wf in results:
        output.append(
            f"Name: {wf.get('name', 'N/A')}\n"
            f"Sys ID: {wf.get('sys_id')}\n"
            f"Active: {wf.get('active', 'N/A')}\n"
            f"State: {wf.get('state', 'N/A')}\n"
            f"Description: {wf.get('description', 'N/A')}\n"
            f"Created: {wf.get('sys_created_on', 'N/A')}\n"
            f"Updated: {wf.get('sys_updated_on', 'N/A')}"
        )
    return "\n\n---\n\n".join(output)


@mcp.tool()
def list_ai_agents(
    active_only: bool = True,
    limit: int = 50
) -> str:
    """
    List all AI agents configured in the system.
    
    Args:
        active_only: Only show active agents (default True)
        limit: Max number of records to return (default 50)
    """
    query_parts = []
    if active_only:
        query_parts.append("active=true")
    query = "^".join(query_parts) if query_parts else ""
    
    url = f"{INSTANCE}/api/now/table/sn_aia_agent"
    params = {
        "sysparm_query": f"{query}^ORDERBYDESCsys_created_on" if query else "ORDERBYDESCsys_created_on",
        "sysparm_limit": limit,
        "sysparm_fields": "sys_id,name,description,active,agent_role,sys_created_on,sys_updated_on"
    }

    response = requests.get(
        url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    results = response.json().get("result", [])
    if not results:
        return "No AI agents found."

    output = []
    for agent in results:
        output.append(
            f"Name: {agent.get('name', 'N/A')}\n"
            f"Sys ID: {agent.get('sys_id')}\n"
            f"Active: {agent.get('active', 'N/A')}\n"
            f"Role: {agent.get('agent_role', 'N/A')}\n"
            f"Description: {agent.get('description', 'N/A')}\n"
            f"Created: {agent.get('sys_created_on', 'N/A')}\n"
            f"Updated: {agent.get('sys_updated_on', 'N/A')}"
        )
    return "\n\n---\n\n".join(output)


@mcp.tool()
def get_agent_details(
    agent_name: str = "",
    agent_sys_id: str = ""
) -> str:
    """
    Get detailed information about a specific AI agent including its tools.
    
    Args:
        agent_name: Name of the agent to look up
        agent_sys_id: Sys ID of the agent to look up (more precise than name)
    """
    if not agent_name and not agent_sys_id:
        return "Error: Must provide either agent_name or agent_sys_id"
    
    # First get the agent record
    url = f"{INSTANCE}/api/now/table/sn_aia_agent"
    if agent_sys_id:
        params = {
            "sysparm_query": f"sys_id={agent_sys_id}",
            "sysparm_fields": "sys_id,name,description,active,role,instructions"  # Fixed: use 'role' and 'instructions'
        }
    else:
        params = {
            "sysparm_query": f"nameLIKE{agent_name}",
            "sysparm_limit": 1,
            "sysparm_fields": "sys_id,name,description,active,role,instructions"  # Fixed: use 'role' and 'instructions'
        }

    response = requests.get(
        url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    results = response.json().get("result", [])
    if not results:
        return "Agent not found."

    agent = results[0]
    agent_id = agent.get('sys_id')
    
    # Query the agent config table to get active status
    config_url = f"{INSTANCE}/api/now/table/sn_aia_agent_config"
    config_params = {
        "sysparm_query": f"agent={agent_id}",
        "sysparm_fields": "active",
        "sysparm_limit": 1
    }
    
    config_response = requests.get(
        config_url, params=config_params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )
    
    active_status = "N/A"
    if config_response.status_code == 200:
        config_results = config_response.json().get("result", [])
        if config_results:
            active_status = config_results[0].get('active', 'N/A')
    
    output = [
        f"=== AI AGENT DETAILS ===",
        f"Name: {agent.get('name', 'N/A')}",
        f"Sys ID: {agent_id}",
        f"Active: {active_status}",  # Now gets from config table
        f"Role: {agent.get('role', 'N/A')}",  # Fixed: use 'role' instead of 'agent_role'
        f"Description: {agent.get('description', 'N/A')}",
        f"\nInstructions:\n{agent.get('instructions', 'N/A')}\n"  # Fixed: use 'instructions' instead of 'list_of_steps'
    ]
    
    # Get associated tools
    tool_url = f"{INSTANCE}/api/now/table/sn_aia_agent_tool_m2m"
    tool_params = {
        "sysparm_query": f"agent={agent_id}",
        "sysparm_fields": "tool.name,tool.type,tool.sys_id,max_automatic_executions"
    }
    
    tool_response = requests.get(
        tool_url, params=tool_params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )
    
    if tool_response.status_code == 200:
        tools = tool_response.json().get("result", [])
        if tools:
            output.append("\n=== ASSOCIATED TOOLS ===")
            for tool in tools:
                tool_name = tool.get('tool.name', 'N/A')
                tool_type = tool.get('tool.type', 'N/A')
                max_exec = tool.get('max_automatic_executions', 'N/A')
                output.append(f"- {tool_name} (Type: {tool_type}, Max Auto Executions: {max_exec})")
        else:
            output.append("\n=== ASSOCIATED TOOLS ===\nNo tools configured")
    
    return "\n".join(output)


@mcp.tool()
def list_agent_tools(
    tool_type: str = "",
    limit: int = 50
) -> str:
    """
    List all tools available to AI agents.
    
    Args:
        tool_type: Filter by tool type (flow_action, record_operation, script, etc.)
        limit: Max number of records to return (default 50)
    """
    query_parts = []
    if tool_type:
        query_parts.append(f"type={tool_type}")
    query = "^".join(query_parts) if query_parts else ""
    
    url = f"{INSTANCE}/api/now/table/sn_aia_tool"
    params = {
        "sysparm_query": f"{query}^ORDERBYname" if query else "ORDERBYname",
        "sysparm_limit": limit,
        "sysparm_fields": "sys_id,name,type,description,active"
    }

    response = requests.get(
        url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    results = response.json().get("result", [])
    if not results:
        return "No tools found."

    output = []
    for tool in results:
        output.append(
            f"Name: {tool.get('name', 'N/A')}\n"
            f"Sys ID: {tool.get('sys_id')}\n"
            f"Type: {tool.get('type', 'N/A')}\n"
            f"Active: {tool.get('active', 'N/A')}\n"
            f"Description: {tool.get('description', 'N/A')}"
        )
    return "\n\n---\n\n".join(output)


# ============================================================================
# AI AGENT EXECUTION & TROUBLESHOOTING TOOLS
# ============================================================================

@mcp.tool()
def query_execution_plans(
    usecase_name: str = "",
    state: str = "",
    minutes_ago: int = 60,
    limit: int = 20
) -> str:
    """
    Query AI agent execution plans (sn_aia_execution_plan).
    Tracks overall agentic workflow runs and high-level plans.
    
    Args:
        usecase_name: Filter by agentic workflow name
        state: Filter by state (complete, in_progress, error, etc.)
        minutes_ago: Only show executions from last N minutes (default 60)
        limit: Max number of records to return (default 20)
    """
    query_parts = []
    if usecase_name:
        query_parts.append(f"usecase.nameLIKE{usecase_name}")
    if state:
        query_parts.append(f"state={state}")
    query_parts.append(f"sys_created_onRELATIVEGT@minute@ago@{minutes_ago}")
    query = "^".join(query_parts)

    url = f"{INSTANCE}/api/now/table/sn_aia_execution_plan"
    params = {
        "sysparm_query": f"{query}^ORDERBYDESCsys_created_on",
        "sysparm_limit": limit,
        "sysparm_fields": "sys_id,usecase.name,state,objective,sys_created_on,sys_updated_on,error_message"
    }

    response = requests.get(
        url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    results = response.json().get("result", [])
    if not results:
        return "No execution plans found matching your criteria."

    output = []
    for plan in results:
        error_msg = plan.get('error_message', '')
        output.append(
            f"Execution ID: {plan.get('sys_id')}\n"
            f"Workflow: {plan.get('usecase.name', 'N/A')}\n"
            f"State: {plan.get('state', 'N/A')}\n"
            f"Objective: {plan.get('objective', 'N/A')}\n"
            f"Created: {plan.get('sys_created_on', 'N/A')}\n"
            f"Updated: {plan.get('sys_updated_on', 'N/A')}"
            + (f"\nError: {error_msg}" if error_msg else "")
        )
    return "\n\n---\n\n".join(output)


@mcp.tool()
def query_execution_tasks(
    execution_plan_id: str = "",
    agent_name: str = "",
    minutes_ago: int = 60,
    limit: int = 50
) -> str:
    """
    Query AI agent execution tasks (sn_aia_execution_task).
    Tracks individual tool-level tasks within an execution plan.
    
    Args:
        execution_plan_id: Filter by specific execution plan sys_id
        agent_name: Filter by agent name
        minutes_ago: Only show tasks from last N minutes (default 60)
        limit: Max number of records to return (default 50)
    """
    query_parts = []
    if execution_plan_id:
        query_parts.append(f"execution_plan={execution_plan_id}")
    if agent_name:
        query_parts.append(f"agent.nameLIKE{agent_name}")
    query_parts.append(f"sys_created_onRELATIVEGT@minute@ago@{minutes_ago}")
    query = "^".join(query_parts)

    url = f"{INSTANCE}/api/now/table/sn_aia_execution_task"
    params = {
        "sysparm_query": f"{query}^ORDERBYDESCsys_created_on",
        "sysparm_limit": limit,
        "sysparm_fields": "sys_id,execution_plan,agent.name,state,error_message,sys_created_on"
    }

    response = requests.get(
        url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    results = response.json().get("result", [])
    if not results:
        return "No execution tasks found matching your criteria."

    output = []
    for task in results:
        error_msg = task.get('error_message', '')
        output.append(
            f"Task ID: {task.get('sys_id')}\n"
            f"Execution Plan: {task.get('execution_plan', 'N/A')}\n"
            f"Agent: {task.get('agent.name', 'N/A')}\n"
            f"State: {task.get('state', 'N/A')}\n"
            f"Created: {task.get('sys_created_on', 'N/A')}"
            + (f"\nError: {error_msg}" if error_msg else "")
        )
    return "\n\n---\n\n".join(output)


@mcp.tool()
def query_tool_executions(
    execution_plan_id: str = "",
    tool_name: str = "",
    minutes_ago: int = 60,
    limit: int = 20
) -> str:
    """
    Query tool executions to see which tools were called and their results.
    
    Args:
        execution_plan_id: Filter by specific execution plan sys_id
        tool_name: Filter by tool name
        minutes_ago: Only show executions from last N minutes (default 60)
        limit: Max number of records to return (default 20)
    """
    query_parts = []
    if execution_plan_id:
        query_parts.append(f"execution_plan={execution_plan_id}")
    if tool_name:
        query_parts.append(f"tool.nameLIKE{tool_name}")
    query_parts.append(f"sys_created_onRELATIVEGT@minute@ago@{minutes_ago}")
    query = "^".join(query_parts)

    url = f"{INSTANCE}/api/now/table/sn_aia_tools_execution"
    params = {
        "sysparm_query": f"{query}^ORDERBYDESCsys_created_on",
        "sysparm_limit": limit,
        "sysparm_fields": "sys_id,tool.name,agent.name,state,error_message,sys_created_on,output"
    }

    response = requests.get(
        url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    results = response.json().get("result", [])
    if not results:
        return "No tool executions found matching your criteria."

    output = []
    for tool_exec in results:
        error_msg = tool_exec.get('error_message', '')
        tool_output = tool_exec.get('output', '')
        output.append(
            f"Tool: {tool_exec.get('tool.name', 'N/A')}\n"
            f"Agent: {tool_exec.get('agent.name', 'N/A')}\n"
            f"State: {tool_exec.get('state', 'N/A')}\n"
            f"Created: {tool_exec.get('sys_created_on', 'N/A')}"
            + (f"\nError: {error_msg}" if error_msg else "")
            + (f"\nOutput (first 500 chars): {tool_output[:500]}" if tool_output else "")
        )
    return "\n\n---\n\n".join(output)


@mcp.tool()
def get_execution_details(
    execution_plan_id: str
) -> str:
    """
    Get complete details of an agentic workflow execution including all tasks and tool calls.
    
    Args:
        execution_plan_id: Sys ID of the execution plan to investigate
    """
    # Get execution plan
    plan_url = f"{INSTANCE}/api/now/table/sn_aia_execution_plan/{execution_plan_id}"
    params = {
        "sysparm_fields": "sys_id,usecase.name,agent.name,state,objective,error_message,sys_created_on,sys_updated_on"
    }

    plan_response = requests.get(
        plan_url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if plan_response.status_code != 200:
        return f"Error: {plan_response.status_code} - {plan_response.text}"

    plan = plan_response.json().get("result", {})
    if not plan:
        return "Execution plan not found."

    output = [
        "=== EXECUTION PLAN DETAILS ===",
        f"Execution ID: {plan.get('sys_id')}",
        f"Workflow: {plan.get('usecase.name', 'N/A')}",
        f"Primary Agent: {plan.get('agent.name', 'N/A')}",
        f"State: {plan.get('state', 'N/A')}",
        f"Objective: {plan.get('objective', 'N/A')}",
        f"Created: {plan.get('sys_created_on', 'N/A')}",
        f"Updated: {plan.get('sys_updated_on', 'N/A')}"
    ]
    
    error_msg = plan.get('error_message', '')
    if error_msg:
        output.append(f"\n=== ERROR MESSAGE ===\n{error_msg}")

    # Get execution tasks
    task_url = f"{INSTANCE}/api/now/table/sn_aia_execution_task"
    task_params = {
        "sysparm_query": f"execution_plan={execution_plan_id}^ORDERBYsys_created_on",
        "sysparm_fields": "agent.name,state,sys_created_on"
    }

    task_response = requests.get(
        task_url, params=task_params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if task_response.status_code == 200:
        tasks = task_response.json().get("result", [])
        if tasks:
            output.append("\n=== EXECUTION TASKS ===")
            for i, task in enumerate(tasks, 1):
                output.append(
                    f"{i}. Agent: {task.get('agent.name', 'N/A')} | "
                    f"State: {task.get('state', 'N/A')} | "
                    f"Time: {task.get('sys_created_on', 'N/A')}"
                )

    # Get tool executions
    tool_url = f"{INSTANCE}/api/now/table/sn_aia_tools_execution"
    tool_params = {
        "sysparm_query": f"execution_plan={execution_plan_id}^ORDERBYsys_created_on",
        "sysparm_fields": "tool.name,agent.name,state,error_message,sys_created_on"
    }

    tool_response = requests.get(
        tool_url, params=tool_params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if tool_response.status_code == 200:
        tools = tool_response.json().get("result", [])
        if tools:
            output.append("\n=== TOOL EXECUTIONS ===")
            for i, tool_exec in enumerate(tools, 1):
                error = tool_exec.get('error_message', '')
                output.append(
                    f"{i}. Tool: {tool_exec.get('tool.name', 'N/A')} | "
                    f"Agent: {tool_exec.get('agent.name', 'N/A')} | "
                    f"State: {tool_exec.get('state', 'N/A')}"
                    + (f"\n   Error: {error}" if error else "")
                )

    return "\n".join(output)


@mcp.tool()
def query_generative_ai_logs(
    minutes_ago: int = 60,
    limit: int = 20
) -> str:
    """
    Query generative AI logs (sys_generative_ai_log).
    Central log for tracking AI Agent invocations and LLM interactions.
    
    Args:
        minutes_ago: Only show logs from last N minutes (default 60)
        limit: Max number of records to return (default 20)
    """
    query = f"sys_created_onRELATIVEGT@minute@ago@{minutes_ago}"

    url = f"{INSTANCE}/api/now/table/sys_generative_ai_log"
    params = {
        "sysparm_query": f"{query}^ORDERBYDESCsys_created_on",
        "sysparm_limit": limit,
        "sysparm_fields": "sys_id,capability,model,status,error_message,sys_created_on,token_count"
    }

    response = requests.get(
        url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    results = response.json().get("result", [])
    if not results:
        return "No generative AI logs found."

    output = []
    for log in results:
        error_msg = log.get('error_message', '')
        output.append(
            f"Capability: {log.get('capability', 'N/A')}\n"
            f"Model: {log.get('model', 'N/A')}\n"
            f"Status: {log.get('status', 'N/A')}\n"
            f"Tokens: {log.get('token_count', 'N/A')}\n"
            f"Created: {log.get('sys_created_on', 'N/A')}"
            + (f"\nError: {error_msg}" if error_msg else "")
        )
    return "\n\n---\n\n".join(output)


@mcp.tool()
def query_agent_messages(
    execution_plan_id: str = "",
    minutes_ago: int = 60,
    limit: int = 50
) -> str:
    """
    Query AI agent conversation messages (sn_aia_message).
    Stores conversation data including tool outputs and short-term memory.
    
    Args:
        execution_plan_id: Filter by specific execution plan sys_id
        minutes_ago: Only show messages from last N minutes (default 60)
        limit: Max number of records to return (default 50)
    """
    query_parts = []
    if execution_plan_id:
        query_parts.append(f"execution_plan={execution_plan_id}")
    query_parts.append(f"sys_created_onRELATIVEGT@minute@ago@{minutes_ago}")
    query = "^".join(query_parts)

    url = f"{INSTANCE}/api/now/table/sn_aia_message"
    params = {
        "sysparm_query": f"{query}^ORDERBYsys_created_on",
        "sysparm_limit": limit,
        "sysparm_fields": "sys_id,execution_plan,role,content,sys_created_on"
    }

    response = requests.get(
        url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    results = response.json().get("result", [])
    if not results:
        return "No agent messages found matching your criteria."

    output = []
    for msg in results:
        content = msg.get('content', '')
        output.append(
            f"[{msg.get('sys_created_on')}] {msg.get('role', 'N/A').upper()}\n"
            f"Execution Plan: {msg.get('execution_plan', 'N/A')}\n"
            f"Content (first 500 chars): {content[:500]}"
        )
    return "\n\n---\n\n".join(output)


# ============================================================================
# COMPREHENSIVE CONVERSATION PERFORMANCE ANALYSIS
# ============================================================================

@mcp.tool()
def analyze_conversation_performance(
    conversation_sys_id: str,
    include_raw_data: bool = False
) -> str:
    """
    Load ALL related data for an AI Agent conversation and analyze performance bottlenecks.

    This tool mimics the Chrome extension behavior by loading all 13+ tables related to
    a conversation and providing comprehensive timing analysis to identify what's slow.

    Args:
        conversation_sys_id: The sys_id of sys_cs_conversation OR sn_aia_execution_plan
        include_raw_data: If True, include full JSON of all records (very verbose)

    Returns:
        Comprehensive performance analysis including:
        - Timeline of all events with durations
        - Top slowest operations (LLM calls, tools, API calls)
        - Error summary
        - Bottleneck identification
        - Total conversation duration
        - Optionally: Full raw data for deep analysis
    """
    from datetime import datetime

    # Helper function to parse ServiceNow datetime
    def parse_snow_datetime(dt_str):
        """Parse ServiceNow datetime string to datetime object."""
        if not dt_str:
            return None
        try:
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        except:
            return None

    # Helper function to calculate duration in seconds
    def calc_duration(start_str, end_str):
        """Calculate duration between two datetime strings in seconds."""
        start = parse_snow_datetime(start_str)
        end = parse_snow_datetime(end_str)
        if start and end:
            return (end - start).total_seconds()
        return None

    client = get_client()
    output = []
    errors = []
    all_events = []

    output.append("=" * 80)
    output.append("COMPREHENSIVE CONVERSATION PERFORMANCE ANALYSIS")
    output.append("=" * 80)
    output.append(f"Conversation ID: {conversation_sys_id}\n")

    # ========================================================================
    # 1. LOAD ALL CONVERSATION DATA (13+ Tables)
    # ========================================================================

    tables_to_load = [
        {
            "name": "Generative AI Logs",
            "table": "sys_generative_ai_log",
            "query": f"conversation={conversation_sys_id}",
            "fields": ["sys_id", "definition", "started_at", "completed_at", "time_taken",
                      "error", "error_code", "skill_config_id", "sys_created_on"],
            "start_field": "started_at",
            "end_field": "completed_at",
            "duration_field": "time_taken",
            "category": "LLM"
        },
        {
            "name": "Conversation Tasks",
            "table": "sys_cs_conversation_task",
            "query": f"conversation={conversation_sys_id}",
            "fields": ["sys_id", "state", "status", "conversation_type", "reason_phrase",
                      "sys_created_on", "sys_updated_on"],
            "start_field": "sys_created_on",
            "end_field": "sys_updated_on",
            "category": "Conversation"
        },
        {
            "name": "Messages",
            "table": "sys_cs_message",
            "query": f"conversation={conversation_sys_id}",
            "fields": ["sys_id", "role", "content", "sys_created_on"],
            "start_field": "sys_created_on",
            "category": "Conversation"
        },
        {
            "name": "AIA Step Logs",
            "table": "sys_cs_aia_step_log",
            "query": f"conversation={conversation_sys_id}",
            "fields": ["sys_id", "step_type", "step_description", "sys_created_on", "sys_updated_on"],
            "start_field": "sys_created_on",
            "end_field": "sys_updated_on",
            "category": "AIA"
        },
        {
            "name": "Execution Plans",
            "table": "sn_aia_execution_plan",
            "query": f"sys_id={conversation_sys_id}^ORconversation={conversation_sys_id}",
            "fields": ["sys_id", "usecase", "agent", "state", "objective", "error_message",
                      "sys_created_on", "sys_updated_on"],
            "start_field": "sys_created_on",
            "end_field": "sys_updated_on",
            "category": "AIA"
        },
        {
            "name": "Execution Tasks",
            "table": "sn_aia_execution_task",
            "query": f"execution_plan={conversation_sys_id}",
            "fields": ["sys_id", "agent", "state", "sys_created_on", "sys_updated_on"],
            "start_field": "sys_created_on",
            "end_field": "sys_updated_on",
            "category": "AIA"
        },
        {
            "name": "Tool Executions",
            "table": "sn_aia_tools_execution",
            "query": f"execution_plan={conversation_sys_id}",
            "fields": ["sys_id", "tool", "agent", "state", "error_message",
                      "sys_created_on", "sys_updated_on"],
            "start_field": "sys_created_on",
            "end_field": "sys_updated_on",
            "category": "Tools"
        },
        {
            "name": "AIA Messages",
            "table": "sn_aia_message",
            "query": f"execution_plan={conversation_sys_id}",
            "fields": ["sys_id", "role", "content", "sys_created_on"],
            "start_field": "sys_created_on",
            "category": "AIA"
        },
        {
            "name": "Skill Discovery",
            "table": "sys_cs_skill_discovery_tracking",
            "query": f"conversation={conversation_sys_id}",
            "fields": ["sys_id", "state", "available_skill_ids", "sys_created_on", "sys_updated_on"],
            "start_field": "sys_created_on",
            "end_field": "sys_updated_on",
            "category": "Skills"
        },
        {
            "name": "FDIH Invocations",
            "table": "sys_cs_fdih_invocation",
            "query": f"calling_cs_conversation_task.conversation.sys_id={conversation_sys_id}",
            "fields": ["sys_id", "name", "type", "response_state", "execution_mode",
                      "sys_created_on", "sys_updated_on"],
            "start_field": "sys_created_on",
            "end_field": "sys_updated_on",
            "category": "FDIH"
        },
        {
            "name": "Now Assist Search",
            "table": "sys_cs_now_assist_search",
            "query": f"conversation={conversation_sys_id}",
            "fields": ["sys_id", "query", "result_count", "sys_created_on", "sys_updated_on"],
            "start_field": "sys_created_on",
            "end_field": "sys_updated_on",
            "category": "Search"
        },
        {
            "name": "API Invocations",
            "table": "one_api_service_plan_invocation",
            "query": f"app_document={conversation_sys_id}",
            "fields": ["sys_id", "service_name", "capability_id", "status",
                      "sys_created_on", "sys_updated_on"],
            "start_field": "sys_created_on",
            "end_field": "sys_updated_on",
            "category": "API"
        }
    ]

    loaded_data = {}

    for table_config in tables_to_load:
        result = client.table_get(
            table=table_config["table"],
            query=table_config["query"],
            fields=table_config["fields"],
            limit=1000,
            order_by="sys_created_on",
            display_value="all"
        )

        if result["success"]:
            records = result["data"].get("result", [])
            loaded_data[table_config["name"]] = records

            # Extract timing events
            for record in records:
                event = {
                    "table": table_config["name"],
                    "category": table_config["category"],
                    "sys_id": record.get("sys_id"),
                    "record": record
                }

                # Get display values (ServiceNow returns both value and display_value)
                def get_display_value(field_data):
                    if isinstance(field_data, dict):
                        return field_data.get("display_value", field_data.get("value"))
                    return field_data

                # Extract start/end times
                start_field = table_config.get("start_field")
                end_field = table_config.get("end_field")

                if start_field:
                    event["start_time"] = get_display_value(record.get(start_field))
                if end_field:
                    event["end_time"] = get_display_value(record.get(end_field))

                # Calculate duration
                if "duration_field" in table_config and table_config["duration_field"]:
                    duration_val = get_display_value(record.get(table_config["duration_field"]))
                    try:
                        event["duration"] = float(duration_val) if duration_val else None
                    except (ValueError, TypeError):
                        event["duration"] = None
                elif start_field and end_field:
                    event["duration"] = calc_duration(event.get("start_time"), event.get("end_time"))

                # Extract name/description
                if table_config["table"] == "sys_generative_ai_log":
                    event["name"] = get_display_value(record.get("definition", "LLM Call"))
                    event["error"] = record.get("error") or record.get("error_code")
                elif table_config["table"] == "sn_aia_tools_execution":
                    event["name"] = f"Tool: {get_display_value(record.get('tool', 'Unknown'))}"
                    event["error"] = record.get("error_message")
                elif table_config["table"] == "sys_cs_fdih_invocation":
                    event["name"] = f"FDIH: {get_display_value(record.get('name', 'Unknown'))}"
                elif table_config["table"] == "one_api_service_plan_invocation":
                    event["name"] = f"API: {get_display_value(record.get('service_name', 'Unknown'))}"
                else:
                    event["name"] = table_config["name"]

                if event.get("error"):
                    errors.append(event)

                all_events.append(event)
        else:
            # Silently skip tables that error (may not exist in all instances)
            pass

    # ========================================================================
    # 2. CALCULATE OVERALL TIMELINE
    # ========================================================================

    if all_events:
        # Sort events by start time
        events_with_times = [e for e in all_events if e.get("start_time")]
        if events_with_times:
            events_with_times.sort(key=lambda e: e.get("start_time", ""))

            first_event_time = events_with_times[0].get("start_time")
            last_event_time = max(
                (e.get("end_time") or e.get("start_time") for e in events_with_times),
                default=first_event_time
            )

            total_duration = calc_duration(first_event_time, last_event_time)

            output.append(f"📊 OVERALL TIMELINE")
            output.append(f"   First Event:  {first_event_time}")
            output.append(f"   Last Event:   {last_event_time}")
            if total_duration:
                output.append(f"   Total Duration: {total_duration:.2f} seconds ({total_duration/60:.2f} minutes)")
            output.append("")

    # ========================================================================
    # 3. RECORD COUNTS BY TABLE
    # ========================================================================

    output.append(f"📋 RECORDS LOADED BY TABLE")
    for table_name, records in loaded_data.items():
        output.append(f"   {table_name}: {len(records)} records")
    output.append("")

    # ========================================================================
    # 4. TOP SLOWEST OPERATIONS
    # ========================================================================

    output.append(f"🐌 TOP 10 SLOWEST OPERATIONS")
    output.append(f"{'-' * 80}")

    # Filter events with duration and sort by slowest
    events_with_duration = [e for e in all_events if e.get("duration") is not None and e.get("duration") > 0]
    events_with_duration.sort(key=lambda e: e["duration"], reverse=True)

    if events_with_duration:
        for i, event in enumerate(events_with_duration[:10], 1):
            duration = event["duration"]
            output.append(
                f"{i:2d}. [{event['category']:12s}] {event['name'][:50]:50s} | "
                f"{duration:7.2f}s | {event.get('start_time', 'N/A')}"
            )
            if event.get("error"):
                output.append(f"     ⚠️  ERROR: {str(event['error'])[:100]}")
    else:
        output.append("   No operations with duration data found.")
    output.append("")

    # ========================================================================
    # 5. BREAKDOWN BY CATEGORY
    # ========================================================================

    output.append(f"📊 PERFORMANCE BY CATEGORY")
    output.append(f"{'-' * 80}")

    categories = {}
    for event in events_with_duration:
        cat = event["category"]
        if cat not in categories:
            categories[cat] = {"count": 0, "total_duration": 0, "events": []}
        categories[cat]["count"] += 1
        categories[cat]["total_duration"] += event["duration"]
        categories[cat]["events"].append(event)

    # Sort by total duration
    sorted_categories = sorted(categories.items(), key=lambda x: x[1]["total_duration"], reverse=True)

    for cat_name, cat_data in sorted_categories:
        avg_duration = cat_data["total_duration"] / cat_data["count"]
        output.append(
            f"{cat_name:12s} | Count: {cat_data['count']:3d} | "
            f"Total: {cat_data['total_duration']:7.2f}s | Avg: {avg_duration:6.2f}s"
        )

        # Show top 3 slowest in this category
        slowest_in_cat = sorted(cat_data["events"], key=lambda e: e["duration"], reverse=True)[:3]
        for event in slowest_in_cat:
            output.append(f"   → {event['name'][:60]:60s} {event['duration']:6.2f}s")
    output.append("")

    # ========================================================================
    # 6. ERROR SUMMARY
    # ========================================================================

    if errors:
        output.append(f"❌ ERRORS DETECTED ({len(errors)} total)")
        output.append(f"{'-' * 80}")
        for i, error_event in enumerate(errors[:10], 1):
            output.append(f"{i}. [{error_event['category']}] {error_event['name']}")
            output.append(f"   Time: {error_event.get('start_time', 'N/A')}")
            output.append(f"   Error: {str(error_event.get('error'))[:200]}")
            output.append("")

    # ========================================================================
    # 7. BOTTLENECK IDENTIFICATION
    # ========================================================================

    output.append(f"🎯 BOTTLENECK ANALYSIS")
    output.append(f"{'-' * 80}")

    if events_with_duration:
        # Find longest operation
        slowest = events_with_duration[0]
        output.append(f"⚠️  SLOWEST OPERATION:")
        output.append(f"   {slowest['name']}")
        output.append(f"   Duration: {slowest['duration']:.2f} seconds")
        output.append(f"   Category: {slowest['category']}")
        output.append(f"   Time: {slowest.get('start_time', 'N/A')}")
        output.append("")

        # Find category taking most time
        if sorted_categories:
            slowest_cat = sorted_categories[0]
            output.append(f"⚠️  SLOWEST CATEGORY: {slowest_cat[0]}")
            output.append(f"   Total time: {slowest_cat[1]['total_duration']:.2f} seconds")
            output.append(f"   Operations: {slowest_cat[1]['count']}")
            output.append("")

        # Identify time gaps (periods of inactivity)
        output.append(f"🕐 TIME GAPS (potential waiting/idle periods):")
        events_sorted = sorted(events_with_times, key=lambda e: e.get("start_time", ""))

        gaps = []
        for i in range(len(events_sorted) - 1):
            current_end = events_sorted[i].get("end_time") or events_sorted[i].get("start_time")
            next_start = events_sorted[i + 1].get("start_time")

            if current_end and next_start:
                gap_duration = calc_duration(current_end, next_start)
                if gap_duration and gap_duration > 0.5:  # Only show gaps > 0.5 seconds
                    gaps.append({
                        "duration": gap_duration,
                        "after": events_sorted[i]["name"],
                        "before": events_sorted[i + 1]["name"],
                        "time": current_end
                    })

        gaps.sort(key=lambda g: g["duration"], reverse=True)

        if gaps:
            for i, gap in enumerate(gaps[:5], 1):
                output.append(
                    f"   {i}. Gap of {gap['duration']:.2f}s at {gap['time']}"
                )
                output.append(f"      After:  {gap['after'][:60]}")
                output.append(f"      Before: {gap['before'][:60]}")
        else:
            output.append("   No significant time gaps detected (all < 0.5s)")
    else:
        output.append("   Insufficient timing data for bottleneck analysis.")

    output.append("")

    # ========================================================================
    # 8. RECOMMENDATIONS
    # ========================================================================

    output.append(f"💡 RECOMMENDATIONS")
    output.append(f"{'-' * 80}")

    if events_with_duration:
        # Recommend based on slowest category
        if sorted_categories:
            slowest_cat_name = sorted_categories[0][0]
            slowest_cat_data = sorted_categories[0][1]

            if slowest_cat_name == "LLM" and slowest_cat_data["total_duration"] > 10:
                output.append("   ⚡ LLM calls are taking significant time:")
                output.append("      • Consider reducing prompt sizes")
                output.append("      • Use faster models for simple tasks")
                output.append("      • Implement prompt caching where possible")
                output.append("")

            if slowest_cat_name == "Tools" and slowest_cat_data["total_duration"] > 5:
                output.append("   ⚡ Tool executions are slow:")
                output.append("      • Review tool implementation performance")
                output.append("      • Consider caching tool results")
                output.append("      • Check for unnecessary API calls in tools")
                output.append("")

            if slowest_cat_name == "API" and slowest_cat_data["total_duration"] > 5:
                output.append("   ⚡ API calls are taking significant time:")
                output.append("      • Consider batch API calls where possible")
                output.append("      • Review API endpoint performance")
                output.append("      • Check network latency")
                output.append("")

        if gaps and gaps[0]["duration"] > 2:
            output.append("   ⚡ Large time gaps detected:")
            output.append("      • Investigate what's happening during idle periods")
            output.append("      • Check for synchronous operations that could be parallelized")
            output.append("      • Review skill discovery and routing logic")
            output.append("")

        if errors:
            output.append("   ⚡ Errors detected:")
            output.append("      • Fix errors to improve overall performance")
            output.append("      • Errors may cause retries and additional delays")
            output.append("")

    if not output[-1].strip():
        output.append("   No specific recommendations at this time.")

    output.append("")
    output.append("=" * 80)

    # ========================================================================
    # 9. RAW DATA (if requested)
    # ========================================================================

    if include_raw_data:
        output.append("\n" + "=" * 80)
        output.append("RAW DATA (All Records)")
        output.append("=" * 80 + "\n")

        for table_name, records in loaded_data.items():
            if records:
                output.append(f"\n### {table_name} ({len(records)} records)")
                output.append(json.dumps(records, indent=2))
                output.append("")

    return "\n".join(output)


@mcp.tool()
def compare_conversation_performance(
    conversation_ids: str,
    show_details: bool = False
) -> str:
    """
    Compare performance metrics across multiple conversations to identify patterns.

    Args:
        conversation_ids: Comma-separated list of conversation sys_ids to compare
        show_details: If True, show detailed breakdown for each conversation

    Returns:
        Comparative analysis showing which conversations are fastest/slowest and why
    """
    from datetime import datetime

    ids = [cid.strip() for cid in conversation_ids.split(",")]

    if len(ids) < 2:
        return "Error: Please provide at least 2 conversation IDs separated by commas"

    if len(ids) > 10:
        return "Error: Maximum 10 conversations can be compared at once"

    output = []
    output.append("=" * 80)
    output.append("CONVERSATION PERFORMANCE COMPARISON")
    output.append("=" * 80)
    output.append(f"Comparing {len(ids)} conversations\n")

    # Collect metrics for each conversation
    conversations = []

    for conv_id in ids:
        # Get execution plan to find basic info
        client = get_client()
        result = client.table_get(
            table="sn_aia_execution_plan",
            query=f"sys_id={conv_id}",
            fields=["sys_id", "usecase", "agent", "state", "sys_created_on", "sys_updated_on"],
            limit=1,
            display_value="all"
        )

        if not result["success"] or not result["data"].get("result"):
            # Try as conversation instead
            result = client.table_get(
                table="sys_cs_conversation",
                query=f"sys_id={conv_id}",
                fields=["sys_id", "state", "sys_created_on", "sys_updated_on"],
                limit=1,
                display_value="all"
            )

        if not result["success"] or not result["data"].get("result"):
            conversations.append({
                "id": conv_id,
                "error": "Conversation not found",
                "metrics": {}
            })
            continue

        conv_record = result["data"]["result"][0]

        # Get LLM logs
        llm_result = client.table_get(
            table="sys_generative_ai_log",
            query=f"conversation={conv_id}",
            fields=["time_taken", "error", "started_at"],
            limit=1000,
            display_value="all"
        )

        # Get tool executions
        tool_result = client.table_get(
            table="sn_aia_tools_execution",
            query=f"execution_plan={conv_id}",
            fields=["sys_created_on", "sys_updated_on", "error_message"],
            limit=1000,
            display_value="all"
        )

        # Calculate metrics
        def get_display_value(field_data):
            if isinstance(field_data, dict):
                return field_data.get("display_value", field_data.get("value"))
            return field_data

        llm_logs = llm_result["data"].get("result", []) if llm_result["success"] else []
        tool_execs = tool_result["data"].get("result", []) if tool_result["success"] else []

        llm_durations = []
        llm_errors = 0
        for log in llm_logs:
            duration = get_display_value(log.get("time_taken"))
            if duration:
                try:
                    llm_durations.append(float(duration))
                except:
                    pass
            if log.get("error") or log.get("error_code"):
                llm_errors += 1

        tool_durations = []
        tool_errors = 0
        for tool in tool_execs:
            start = get_display_value(tool.get("sys_created_on"))
            end = get_display_value(tool.get("sys_updated_on"))
            if start and end:
                try:
                    start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
                    end_dt = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
                    duration = (end_dt - start_dt).total_seconds()
                    tool_durations.append(duration)
                except:
                    pass
            if tool.get("error_message"):
                tool_errors += 1

        # Overall duration
        start_time = get_display_value(conv_record.get("sys_created_on"))
        end_time = get_display_value(conv_record.get("sys_updated_on"))
        total_duration = None
        if start_time and end_time:
            try:
                start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
                total_duration = (end_dt - start_dt).total_seconds()
            except:
                pass

        conversations.append({
            "id": conv_id,
            "state": get_display_value(conv_record.get("state", "N/A")),
            "usecase": get_display_value(conv_record.get("usecase", "N/A")),
            "metrics": {
                "total_duration": total_duration,
                "llm_count": len(llm_logs),
                "llm_total_time": sum(llm_durations),
                "llm_avg_time": sum(llm_durations) / len(llm_durations) if llm_durations else 0,
                "llm_max_time": max(llm_durations) if llm_durations else 0,
                "llm_errors": llm_errors,
                "tool_count": len(tool_execs),
                "tool_total_time": sum(tool_durations),
                "tool_avg_time": sum(tool_durations) / len(tool_durations) if tool_durations else 0,
                "tool_max_time": max(tool_durations) if tool_durations else 0,
                "tool_errors": tool_errors
            }
        })

    # ========================================================================
    # COMPARISON TABLE
    # ========================================================================

    output.append("📊 SUMMARY COMPARISON")
    output.append("-" * 80)
    output.append(f"{'ID'[:36]:36s} | {'Total':>8s} | {'LLMs':>5s} | {'LLM Time':>9s} | {'Tools':>5s} | {'Tool Time':>9s} | {'Errors':>6s}")
    output.append("-" * 80)

    for conv in conversations:
        if conv.get("error"):
            output.append(f"{conv['id'][:36]:36s} | ERROR: {conv['error']}")
            continue

        m = conv["metrics"]
        total_str = f"{m['total_duration']:.1f}s" if m['total_duration'] else "N/A"
        llm_time_str = f"{m['llm_total_time']:.1f}s" if m['llm_total_time'] else "0s"
        tool_time_str = f"{m['tool_total_time']:.1f}s" if m['tool_total_time'] else "0s"
        total_errors = m['llm_errors'] + m['tool_errors']

        output.append(
            f"{conv['id'][:36]:36s} | {total_str:>8s} | {m['llm_count']:>5d} | {llm_time_str:>9s} | "
            f"{m['tool_count']:>5d} | {tool_time_str:>9s} | {total_errors:>6d}"
        )

    output.append("")

    # ========================================================================
    # RANKINGS
    # ========================================================================

    valid_convs = [c for c in conversations if not c.get("error") and c["metrics"].get("total_duration")]

    if valid_convs:
        output.append("🏆 RANKINGS")
        output.append("-" * 80)

        # Fastest/Slowest overall
        fastest = min(valid_convs, key=lambda c: c["metrics"]["total_duration"])
        slowest = max(valid_convs, key=lambda c: c["metrics"]["total_duration"])

        output.append(f"⚡ FASTEST: {fastest['id']}")
        output.append(f"   Duration: {fastest['metrics']['total_duration']:.2f}s")
        output.append(f"   LLM calls: {fastest['metrics']['llm_count']}, Tool calls: {fastest['metrics']['tool_count']}")
        output.append("")

        output.append(f"🐌 SLOWEST: {slowest['id']}")
        output.append(f"   Duration: {slowest['metrics']['total_duration']:.2f}s")
        output.append(f"   LLM calls: {slowest['metrics']['llm_count']}, Tool calls: {slowest['metrics']['tool_count']}")
        output.append("")

        # Most/Least LLM calls
        most_llm = max(valid_convs, key=lambda c: c["metrics"]["llm_count"])
        output.append(f"💬 MOST LLM CALLS: {most_llm['id']} ({most_llm['metrics']['llm_count']} calls)")

        # Most errors
        convs_with_errors = [c for c in valid_convs if (c["metrics"]["llm_errors"] + c["metrics"]["tool_errors"]) > 0]
        if convs_with_errors:
            most_errors = max(convs_with_errors, key=lambda c: c["metrics"]["llm_errors"] + c["metrics"]["tool_errors"])
            total_errors = most_errors["metrics"]["llm_errors"] + most_errors["metrics"]["tool_errors"]
            output.append(f"❌ MOST ERRORS: {most_errors['id']} ({total_errors} errors)")

        output.append("")

        # ========================================================================
        # INSIGHTS
        # ========================================================================

        output.append("💡 INSIGHTS")
        output.append("-" * 80)

        # Calculate averages
        avg_duration = sum(c["metrics"]["total_duration"] for c in valid_convs) / len(valid_convs)
        avg_llm_count = sum(c["metrics"]["llm_count"] for c in valid_convs) / len(valid_convs)
        avg_tool_count = sum(c["metrics"]["tool_count"] for c in valid_convs) / len(valid_convs)

        output.append(f"Average conversation duration: {avg_duration:.2f}s")
        output.append(f"Average LLM calls per conversation: {avg_llm_count:.1f}")
        output.append(f"Average tool calls per conversation: {avg_tool_count:.1f}")
        output.append("")

        # Identify patterns
        if slowest["metrics"]["total_duration"] > avg_duration * 1.5:
            output.append(f"⚠️  {slowest['id']} is significantly slower than average")
            if slowest["metrics"]["llm_count"] > avg_llm_count * 1.5:
                output.append(f"   → This conversation has {slowest['metrics']['llm_count']} LLM calls vs avg of {avg_llm_count:.1f}")
            if slowest["metrics"]["llm_max_time"] > 5:
                output.append(f"   → Slowest LLM call took {slowest['metrics']['llm_max_time']:.1f}s")
            output.append("")

        if fastest["metrics"]["total_duration"] < avg_duration * 0.5:
            output.append(f"✅ {fastest['id']} is significantly faster than average")
            output.append(f"   → Consider this as a performance benchmark")
            output.append("")

    # ========================================================================
    # DETAILED BREAKDOWN (if requested)
    # ========================================================================

    if show_details:
        output.append("\n" + "=" * 80)
        output.append("DETAILED BREAKDOWN BY CONVERSATION")
        output.append("=" * 80 + "\n")

        for conv in conversations:
            if conv.get("error"):
                continue

            output.append(f"### {conv['id']}")
            output.append(f"State: {conv.get('state', 'N/A')}")
            output.append(f"Use Case: {conv.get('usecase', 'N/A')}")
            output.append("")

            m = conv["metrics"]
            output.append("Metrics:")
            output.append(f"  Total Duration: {m['total_duration']:.2f}s" if m['total_duration'] else "  Total Duration: N/A")
            output.append(f"  LLM Calls: {m['llm_count']}")
            output.append(f"    - Total time: {m['llm_total_time']:.2f}s")
            output.append(f"    - Avg time: {m['llm_avg_time']:.2f}s")
            output.append(f"    - Max time: {m['llm_max_time']:.2f}s")
            output.append(f"    - Errors: {m['llm_errors']}")
            output.append(f"  Tool Calls: {m['tool_count']}")
            output.append(f"    - Total time: {m['tool_total_time']:.2f}s")
            output.append(f"    - Avg time: {m['tool_avg_time']:.2f}s")
            output.append(f"    - Max time: {m['tool_max_time']:.2f}s")
            output.append(f"    - Errors: {m['tool_errors']}")
            output.append("")

    output.append("=" * 80)

    return "\n".join(output)


@mcp.tool()
def analyze_conversation_trends(
    minutes_ago: int = 1440,
    usecase_name: str = "",
    limit: int = 50
) -> str:
    """
    Analyze performance trends across recent conversations to identify degradation or improvements.

    Args:
        minutes_ago: Look back this many minutes (default 1440 = 24 hours)
        usecase_name: Filter by specific use case/workflow name
        limit: Maximum conversations to analyze (default 50)

    Returns:
        Trend analysis showing performance over time, averages, and anomalies
    """
    from datetime import datetime, timedelta

    client = get_client()
    output = []

    output.append("=" * 80)
    output.append("CONVERSATION PERFORMANCE TRENDS")
    output.append("=" * 80)

    # Calculate time threshold
    now = datetime.utcnow()
    threshold = now - timedelta(minutes=minutes_ago)
    threshold_str = threshold.strftime("%Y-%m-%d %H:%M:%S")

    output.append(f"Time Range: Last {minutes_ago} minutes ({minutes_ago/60:.1f} hours)")
    output.append(f"From: {threshold_str}")
    if usecase_name:
        output.append(f"Use Case Filter: {usecase_name}")
    output.append("")

    # Query execution plans
    query_parts = [f"sys_created_on>{threshold_str}"]
    if usecase_name:
        query_parts.append(f"usecase.nameLIKE{usecase_name}")
    query = "^".join(query_parts)

    result = client.table_get(
        table="sn_aia_execution_plan",
        query=query,
        fields=["sys_id", "usecase", "state", "sys_created_on", "sys_updated_on"],
        limit=limit,
        order_by="sys_created_on",
        display_value="all"
    )

    if not result["success"]:
        return f"Error querying execution plans: {result['error']}"

    plans = result["data"].get("result", [])

    if not plans:
        return "No conversations found in the specified time range."

    output.append(f"📊 Found {len(plans)} conversations")
    output.append("")

    # Collect metrics for each conversation
    conversations = []

    def get_display_value(field_data):
        if isinstance(field_data, dict):
            return field_data.get("display_value", field_data.get("value"))
        return field_data

    for plan in plans:
        conv_id = plan["sys_id"]

        # Get LLM logs
        llm_result = client.table_get(
            table="sys_generative_ai_log",
            query=f"conversation={conv_id}",
            fields=["time_taken", "error"],
            limit=1000,
            display_value="all"
        )

        llm_logs = llm_result["data"].get("result", []) if llm_result["success"] else []

        llm_durations = []
        llm_errors = 0
        for log in llm_logs:
            duration = get_display_value(log.get("time_taken"))
            if duration:
                try:
                    llm_durations.append(float(duration))
                except:
                    pass
            if log.get("error"):
                llm_errors += 1

        # Calculate conversation duration
        start_time = get_display_value(plan.get("sys_created_on"))
        end_time = get_display_value(plan.get("sys_updated_on"))
        total_duration = None
        created_dt = None

        if start_time and end_time:
            try:
                start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
                total_duration = (end_dt - start_dt).total_seconds()
                created_dt = start_dt
            except:
                pass

        conversations.append({
            "id": conv_id,
            "created": created_dt,
            "created_str": start_time,
            "state": get_display_value(plan.get("state", "N/A")),
            "usecase": get_display_value(plan.get("usecase", "N/A")),
            "total_duration": total_duration,
            "llm_count": len(llm_logs),
            "llm_total_time": sum(llm_durations),
            "llm_avg_time": sum(llm_durations) / len(llm_durations) if llm_durations else 0,
            "llm_errors": llm_errors
        })

    # Filter out conversations without duration data
    valid_conversations = [c for c in conversations if c["total_duration"] is not None]

    if not valid_conversations:
        return "No conversations with complete timing data found."

    output.append(f"✅ Analyzed {len(valid_conversations)} conversations with timing data")
    output.append("")

    # ========================================================================
    # AGGREGATE STATISTICS
    # ========================================================================

    output.append("📈 AGGREGATE STATISTICS")
    output.append("-" * 80)

    durations = [c["total_duration"] for c in valid_conversations]
    llm_counts = [c["llm_count"] for c in valid_conversations]
    llm_times = [c["llm_total_time"] for c in valid_conversations]

    avg_duration = sum(durations) / len(durations)
    min_duration = min(durations)
    max_duration = max(durations)

    output.append(f"Conversation Duration:")
    output.append(f"  Average: {avg_duration:.2f}s")
    output.append(f"  Min: {min_duration:.2f}s")
    output.append(f"  Max: {max_duration:.2f}s")
    output.append(f"  Median: {sorted(durations)[len(durations)//2]:.2f}s")
    output.append("")

    avg_llm_count = sum(llm_counts) / len(llm_counts)
    avg_llm_time = sum(llm_times) / len(llm_times)

    output.append(f"LLM Usage:")
    output.append(f"  Average calls per conversation: {avg_llm_count:.1f}")
    output.append(f"  Average total LLM time: {avg_llm_time:.2f}s")
    output.append(f"  Total LLM calls across all: {sum(llm_counts)}")
    output.append("")

    total_errors = sum(c["llm_errors"] for c in valid_conversations)
    error_rate = (total_errors / sum(llm_counts)) * 100 if sum(llm_counts) > 0 else 0

    output.append(f"Error Rate:")
    output.append(f"  Total errors: {total_errors}")
    output.append(f"  Error rate: {error_rate:.1f}%")
    output.append("")

    # ========================================================================
    # TIME-BASED TREND
    # ========================================================================

    output.append("📊 PERFORMANCE OVER TIME")
    output.append("-" * 80)

    # Sort by creation time
    valid_conversations.sort(key=lambda c: c["created"])

    # Split into quartiles
    quartile_size = len(valid_conversations) // 4
    if quartile_size > 0:
        q1 = valid_conversations[:quartile_size]
        q2 = valid_conversations[quartile_size:quartile_size*2]
        q3 = valid_conversations[quartile_size*2:quartile_size*3]
        q4 = valid_conversations[quartile_size*3:]

        quartiles = [
            ("First 25%", q1),
            ("Second 25%", q2),
            ("Third 25%", q3),
            ("Last 25%", q4)
        ]

        for name, quartile in quartiles:
            if quartile:
                avg_dur = sum(c["total_duration"] for c in quartile) / len(quartile)
                avg_llm = sum(c["llm_count"] for c in quartile) / len(quartile)
                errors = sum(c["llm_errors"] for c in quartile)

                output.append(f"{name:15s}: Avg Duration: {avg_dur:6.2f}s | Avg LLMs: {avg_llm:4.1f} | Errors: {errors}")

        output.append("")

        # Trend direction
        first_half_avg = sum(c["total_duration"] for c in valid_conversations[:len(valid_conversations)//2]) / (len(valid_conversations)//2)
        second_half_avg = sum(c["total_duration"] for c in valid_conversations[len(valid_conversations)//2:]) / (len(valid_conversations) - len(valid_conversations)//2)

        if second_half_avg > first_half_avg * 1.1:
            output.append(f"⚠️  PERFORMANCE DEGRADATION DETECTED")
            output.append(f"   Recent conversations are {((second_half_avg/first_half_avg - 1) * 100):.1f}% slower than earlier ones")
            output.append(f"   First half avg: {first_half_avg:.2f}s")
            output.append(f"   Second half avg: {second_half_avg:.2f}s")
        elif second_half_avg < first_half_avg * 0.9:
            output.append(f"✅ PERFORMANCE IMPROVEMENT DETECTED")
            output.append(f"   Recent conversations are {((1 - second_half_avg/first_half_avg) * 100):.1f}% faster than earlier ones")
            output.append(f"   First half avg: {first_half_avg:.2f}s")
            output.append(f"   Second half avg: {second_half_avg:.2f}s")
        else:
            output.append(f"📊 STABLE PERFORMANCE")
            output.append(f"   No significant trend detected over time")
            output.append(f"   First half avg: {first_half_avg:.2f}s")
            output.append(f"   Second half avg: {second_half_avg:.2f}s")

        output.append("")

    # ========================================================================
    # OUTLIERS
    # ========================================================================

    output.append("🎯 OUTLIERS (Conversations significantly different from average)")
    output.append("-" * 80)

    outliers = []
    for conv in valid_conversations:
        if conv["total_duration"] > avg_duration * 1.5:
            outliers.append((conv, "SLOW", conv["total_duration"] / avg_duration))
        elif conv["total_duration"] < avg_duration * 0.5:
            outliers.append((conv, "FAST", avg_duration / conv["total_duration"]))

    outliers.sort(key=lambda x: x[2], reverse=True)

    if outliers:
        for conv, outlier_type, ratio in outliers[:10]:
            output.append(f"{outlier_type:4s} | {conv['id']} | {conv['total_duration']:6.2f}s ({ratio:.1f}x {outlier_type.lower()}) | {conv['created_str']}")
    else:
        output.append("   No significant outliers detected")

    output.append("")
    output.append("=" * 80)

    return "\n".join(output)


@mcp.tool()
def list_trigger_configurations(
    usecase_name: str = "",
    limit: int = 50
) -> str:
    """
    List trigger configurations for agentic workflows.
    
    Args:
        usecase_name: Filter by agentic workflow name
        limit: Max number of records to return (default 50)
    """
    query_parts = []
    if usecase_name:
        query_parts.append(f"usecase.nameLIKE{usecase_name}")
    query = "^".join(query_parts) if query_parts else ""
    
    url = f"{INSTANCE}/api/now/table/sn_aia_trigger_configuration"
    params = {
        "sysparm_query": f"{query}^ORDERBYusecase.name" if query else "ORDERBYusecase.name",
        "sysparm_limit": limit,
        "sysparm_fields": "sys_id,usecase.name,trigger_type,table,condition,active"
    }

    response = requests.get(
        url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )

    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    results = response.json().get("result", [])
    if not results:
        return "No trigger configurations found."

    output = []
    for trigger in results:
        output.append(
            f"Workflow: {trigger.get('usecase.name', 'N/A')}\n"
            f"Trigger Type: {trigger.get('trigger_type', 'N/A')}\n"
            f"Table: {trigger.get('table', 'N/A')}\n"
            f"Condition: {trigger.get('condition', 'N/A')}\n"
            f"Active: {trigger.get('active', 'N/A')}"
        )
    return "\n\n---\n\n".join(output)


# ============================================================================
# AI AGENT WRITE OPERATIONS
# ============================================================================

@mcp.tool()
def create_ai_agent(
    name: str,
    description: str,
    agent_role: str,
    list_of_steps: str,
    active: bool = True
) -> str:
    """
    Create a new AI agent.
    
    Args:
        name: Name of the agent (e.g., "Custom Incident Resolver")
        description: Brief description of what the agent does
        agent_role: The agent's role/purpose (e.g., "Incident resolution specialist")
        list_of_steps: Detailed step-by-step instructions for the agent
        active: Whether the agent is active (default True)
    
    Returns:
        Success message with agent sys_id
    """
    url = f"{INSTANCE}/api/now/table/sn_aia_agent"
    
    payload = {
        "name": name,
        "description": description,
        "role": agent_role,  # Fixed: use 'role' instead of 'agent_role'
        "instructions": list_of_steps,  # Fixed: use 'instructions' instead of 'list_of_steps'
        "active": str(active).lower()
    }
    
    response = requests.post(
        url,
        json=payload,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    
    if response.status_code in [200, 201]:
        result = response.json().get("result", {})
        agent_id = result.get("sys_id")
        
        # Update the auto-created agent config record to set active status
        # ServiceNow creates this automatically, we just need to update it
        config_url = f"{INSTANCE}/api/now/table/sn_aia_agent_config"
        config_params = {
            "sysparm_query": f"agent={agent_id}",
            "sysparm_fields": "sys_id",
            "sysparm_limit": 1
        }
        
        config_get_response = requests.get(
            config_url,
            params=config_params,
            auth=(USERNAME, PASSWORD),
            headers={"Accept": "application/json"}
        )
        
        config_updated = False
        if config_get_response.status_code == 200:
            config_results = config_get_response.json().get("result", [])
            if config_results:
                # Update existing config
                config_id = config_results[0].get("sys_id")
                config_update_url = f"{INSTANCE}/api/now/table/sn_aia_agent_config/{config_id}"
                config_payload = {"active": str(active).lower()}
                
                config_update_response = requests.patch(
                    config_update_url,
                    json=config_payload,
                    auth=(USERNAME, PASSWORD),
                    headers={"Accept": "application/json", "Content-Type": "application/json"}
                )
                
                config_updated = config_update_response.status_code == 200
        
        return (
            f"✅ AI Agent created successfully!\n\n"
            f"Name: {name}\n"
            f"Sys ID: {agent_id}\n"
            f"Active: {active}"
            + (f" (config updated)" if config_updated else f" (auto-created)")
            + f"\n\nNext steps:\n"
            f"1. Add tools to the agent using add_tool_to_agent\n"
            f"2. Associate with workflows using create_agentic_workflow or update_agentic_workflow\n"
            f"3. Test the agent in AI Agent Studio"
        )
    else:
        return f"❌ Error creating agent: {response.status_code} - {response.text}"


@mcp.tool()
def update_ai_agent(
    agent_sys_id: str,
    name: str = "",
    description: str = "",
    agent_role: str = "",
    list_of_steps: str = "",
    active: str = ""
) -> str:
    """
    Update an existing AI agent. Only provide fields you want to update.
    
    Args:
        agent_sys_id: Sys ID of the agent to update (required)
        name: New name (optional)
        description: New description (optional)
        agent_role: New role (optional)
        list_of_steps: New instructions (optional)
        active: New active status - "true" or "false" (optional)
    
    Returns:
        Success message with updated fields
    """
    url = f"{INSTANCE}/api/now/table/sn_aia_agent/{agent_sys_id}"
    
    # Separate active from other fields since it goes in a different table
    active_value = None
    if active:
        active_value = active
        # Don't include active in the main agent payload
    
    # Only include fields that were provided (excluding active)
    payload = {}
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    if agent_role:
        payload["role"] = agent_role  # Fixed: use 'role' instead of 'agent_role'
    if list_of_steps:
        payload["instructions"] = list_of_steps  # Fixed: use 'instructions' instead of 'list_of_steps'
    
    updated_fields = []
    
    # Update the main agent record if there are fields to update
    if payload:
        response = requests.patch(
            url,
            json=payload,
            auth=(USERNAME, PASSWORD),
            headers={"Accept": "application/json", "Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            return f"❌ Error updating agent: {response.status_code} - {response.text}"
        
        updated_fields = list(payload.keys())
    
    # Update active status in config table if provided
    if active_value:
        # Find the config record
        config_url = f"{INSTANCE}/api/now/table/sn_aia_agent_config"
        config_params = {
            "sysparm_query": f"agent={agent_sys_id}",
            "sysparm_limit": 1,
            "sysparm_fields": "sys_id"
        }
        
        config_response = requests.get(
            config_url, params=config_params,
            auth=(USERNAME, PASSWORD),
            headers={"Accept": "application/json"}
        )
        
        if config_response.status_code == 200:
            config_results = config_response.json().get("result", [])
            if config_results:
                # Update existing config
                config_id = config_results[0].get("sys_id")
                config_update_url = f"{INSTANCE}/api/now/table/sn_aia_agent_config/{config_id}"
                config_payload = {"active": active_value.lower()}
                
                config_update = requests.patch(
                    config_update_url,
                    json=config_payload,
                    auth=(USERNAME, PASSWORD),
                    headers={"Accept": "application/json", "Content-Type": "application/json"}
                )
                
                if config_update.status_code == 200:
                    updated_fields.append("active (in config)")
            else:
                # Create new config if it doesn't exist
                config_create_payload = {
                    "agent": agent_sys_id,
                    "active": active_value.lower()
                }
                
                config_create = requests.post(
                    config_url,
                    json=config_create_payload,
                    auth=(USERNAME, PASSWORD),
                    headers={"Accept": "application/json", "Content-Type": "application/json"}
                )
                
                if config_create.status_code in [200, 201]:
                    updated_fields.append("active (config created)")
    
    if not updated_fields:
        return "❌ Error: No fields provided to update. Specify at least one field to change."
    
    return (
        f"✅ AI Agent updated successfully!\n\n"
        f"Agent ID: {agent_sys_id}\n"
        f"Updated fields: {', '.join(updated_fields)}\n\n"
        f"Use get_agent_details to see the updated configuration."
    )


@mcp.tool()
def delete_ai_agent(
    agent_sys_id: str,
    confirm: bool = False
) -> str:
    """
    Delete an AI agent. Requires confirmation.
    
    Args:
        agent_sys_id: Sys ID of the agent to delete
        confirm: Must be True to proceed with deletion
    
    Returns:
        Success or error message
    """
    if not confirm:
        return (
            f"⚠️  Deletion requires confirmation.\n\n"
            f"To delete agent {agent_sys_id}, call this tool again with confirm=True.\n\n"
            f"WARNING: This will remove the agent and its tool associations."
        )
    
    url = f"{INSTANCE}/api/now/table/sn_aia_agent/{agent_sys_id}"
    
    response = requests.delete(
        url,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )
    
    if response.status_code == 204:
        return f"✅ AI Agent {agent_sys_id} deleted successfully."
    else:
        return f"❌ Error deleting agent: {response.status_code} - {response.text}"


@mcp.tool()
def add_tool_to_agent(
    agent_sys_id: str,
    tool_sys_id: str,
    max_automatic_executions: int = 5,
    inputs: str = ""
) -> str:
    """
    Add a tool to an AI agent with optional input definitions.
    
    Args:
        agent_sys_id: Sys ID of the agent
        tool_sys_id: Sys ID of the tool to add
        max_automatic_executions: Max times tool can auto-execute (default 5)
        inputs: JSON string defining tool inputs. Format: [{"name":"param1","description":"Param description","mandatory":true}]
    
    Returns:
        Success message
    
    Example with inputs:
        inputs='[{"name":"incident_number","description":"The incident number to look up","mandatory":true}]'
    """
    import json
    
    # First, get the tool name to populate the required name field
    tool_url = f"{INSTANCE}/api/now/table/sn_aia_tool/{tool_sys_id}"
    tool_params = {"sysparm_fields": "name"}
    
    tool_response = requests.get(
        tool_url,
        params=tool_params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )
    
    if tool_response.status_code != 200:
        return f"❌ Error retrieving tool details: {tool_response.status_code} - {tool_response.text}"
    
    tool_data = tool_response.json().get("result", {})
    tool_name = tool_data.get("name", "Unknown Tool")
    
    # Now create the agent-tool relationship
    url = f"{INSTANCE}/api/now/table/sn_aia_agent_tool_m2m"
    
    payload = {
        "agent": agent_sys_id,
        "tool": tool_sys_id,
        "name": f"Agent Tool: {tool_name}",  # Required field
        "max_automatic_executions": max_automatic_executions
    }
    
    # Add inputs if provided
    if inputs:
        try:
            # Parse the input JSON
            input_list = json.loads(inputs)
            
            # Transform to ServiceNow format with all required fields
            formatted_inputs = []
            for inp in input_list:
                formatted_inputs.append({
                    "name": inp.get("name", ""),
                    "value": inp.get("value", ""),
                    "description": inp.get("description", ""),
                    "mandatory": inp.get("mandatory", False),
                    "invalidMessage": inp.get("invalidMessage", None)
                })
            
            # Set the inputs field as JSON string
            payload["inputs"] = json.dumps(formatted_inputs)
            
        except json.JSONDecodeError as e:
            return f"❌ Error parsing inputs JSON: {str(e)}"
    
    response = requests.post(
        url,
        json=payload,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    
    if response.status_code in [200, 201]:
        result = response.json().get("result", {})
        inputs_count = len(json.loads(inputs)) if inputs else 0
        inputs_info = f"\nInputs Configured: {inputs_count}" if inputs else ""
        return (
            f"✅ Tool added to agent successfully!\n\n"
            f"Agent: {agent_sys_id}\n"
            f"Tool: {tool_name} ({tool_sys_id})\n"
            f"Max Auto Executions: {max_automatic_executions}"
            f"{inputs_info}\n\n"
            f"Use get_agent_details to see all configured tools."
        )
    else:
        return f"❌ Error adding tool to agent: {response.status_code} - {response.text}"


@mcp.tool()
def remove_tool_from_agent(
    agent_sys_id: str,
    tool_sys_id: str
) -> str:
    """
    Remove a tool from an AI agent.
    
    Args:
        agent_sys_id: Sys ID of the agent
        tool_sys_id: Sys ID of the tool to remove
    
    Returns:
        Success message
    """
    # First find the m2m record
    url = f"{INSTANCE}/api/now/table/sn_aia_agent_tool_m2m"
    params = {
        "sysparm_query": f"agent={agent_sys_id}^tool={tool_sys_id}",
        "sysparm_fields": "sys_id"
    }
    
    response = requests.get(
        url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )
    
    if response.status_code != 200:
        return f"❌ Error finding tool association: {response.status_code} - {response.text}"
    
    results = response.json().get("result", [])
    if not results:
        return f"❌ No association found between agent {agent_sys_id} and tool {tool_sys_id}"
    
    m2m_id = results[0].get("sys_id")
    
    # Delete the m2m record
    delete_url = f"{INSTANCE}/api/now/table/sn_aia_agent_tool_m2m/{m2m_id}"
    delete_response = requests.delete(
        delete_url,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )
    
    if delete_response.status_code == 204:
        return (
            f"✅ Tool removed from agent successfully!\n\n"
            f"Agent: {agent_sys_id}\n"
            f"Tool: {tool_sys_id}"
        )
    else:
        return f"❌ Error removing tool: {delete_response.status_code} - {delete_response.text}"


# ============================================================================
# AGENTIC WORKFLOW WRITE OPERATIONS
# ============================================================================

@mcp.tool()
def create_agentic_workflow(
    name: str,
    description: str,
    list_of_steps: str,
    active: bool = True
) -> str:
    """
    Create a new agentic workflow (use case).
    
    Args:
        name: Name of the workflow (e.g., "Custom Incident Investigation")
        description: Brief description of what the workflow does
        list_of_steps: Detailed step-by-step instructions for the workflow
        active: Whether the workflow is active (default True)
    
    Returns:
        Success message with workflow sys_id
    """
    url = f"{INSTANCE}/api/now/table/sn_aia_usecase"
    
    payload = {
        "name": name,
        "description": description,
        "list_of_steps": list_of_steps,
        "active": str(active).lower()
    }
    
    response = requests.post(
        url,
        json=payload,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    
    if response.status_code in [200, 201]:
        result = response.json().get("result", {})
        workflow_id = result.get("sys_id")
        return (
            f"✅ Agentic Workflow created successfully!\n\n"
            f"Name: {name}\n"
            f"Sys ID: {workflow_id}\n"
            f"Active: {active}\n\n"
            f"Next steps:\n"
            f"1. Associate agents with this workflow\n"
            f"2. Create triggers using create_trigger\n"
            f"3. Test the workflow in AI Agent Studio"
        )
    else:
        return f"❌ Error creating workflow: {response.status_code} - {response.text}"


@mcp.tool()
def update_agentic_workflow(
    workflow_sys_id: str,
    name: str = "",
    description: str = "",
    list_of_steps: str = "",
    active: str = ""
) -> str:
    """
    Update an existing agentic workflow. Only provide fields you want to update.
    
    Args:
        workflow_sys_id: Sys ID of the workflow to update (required)
        name: New name (optional)
        description: New description (optional)
        list_of_steps: New instructions (optional)
        active: New active status - "true" or "false" (optional)
    
    Returns:
        Success message with updated fields
    """
    url = f"{INSTANCE}/api/now/table/sn_aia_usecase/{workflow_sys_id}"
    
    # Only include fields that were provided
    payload = {}
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    if list_of_steps:
        payload["list_of_steps"] = list_of_steps
    if active:
        payload["active"] = active.lower()
    
    if not payload:
        return "❌ Error: No fields provided to update. Specify at least one field to change."
    
    response = requests.patch(
        url,
        json=payload,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        updated_fields = ", ".join(payload.keys())
        return (
            f"✅ Agentic Workflow updated successfully!\n\n"
            f"Workflow ID: {workflow_sys_id}\n"
            f"Updated fields: {updated_fields}"
        )
    else:
        return f"❌ Error updating workflow: {response.status_code} - {response.text}"


@mcp.tool()
def delete_agentic_workflow(
    workflow_sys_id: str,
    confirm: bool = False
) -> str:
    """
    Delete an agentic workflow. Requires confirmation.
    
    Args:
        workflow_sys_id: Sys ID of the workflow to delete
        confirm: Must be True to proceed with deletion
    
    Returns:
        Success or error message
    """
    if not confirm:
        return (
            f"⚠️  Deletion requires confirmation.\n\n"
            f"To delete workflow {workflow_sys_id}, call this tool again with confirm=True.\n\n"
            f"WARNING: This will remove the workflow and its triggers."
        )
    
    url = f"{INSTANCE}/api/now/table/sn_aia_usecase/{workflow_sys_id}"
    
    response = requests.delete(
        url,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )
    
    if response.status_code == 204:
        return f"✅ Agentic Workflow {workflow_sys_id} deleted successfully."
    else:
        return f"❌ Error deleting workflow: {response.status_code} - {response.text}"


# ============================================================================
# TOOL WRITE OPERATIONS
# ============================================================================

@mcp.tool()
def create_tool(
    name: str,
    description: str,
    tool_type: str,
    active: bool = True,
    flow_action_sys_id: str = "",
    script_content: str = ""
) -> str:
    """
    Create a new tool for AI agents.
    
    Args:
        name: Name of the tool (e.g., "Fetch Incident Details")
        description: What the tool does
        tool_type: Type of tool (flow_action, record_operation, script, search_retrieval, etc.)
        active: Whether the tool is active (default True)
        flow_action_sys_id: If type is flow_action, the sys_id of the flow action
        script_content: If type is script, the script code
    
    Returns:
        Success message with tool sys_id
    """
    url = f"{INSTANCE}/api/now/table/sn_aia_tool"
    
    payload = {
        "name": name,
        "description": description,
        "type": tool_type,
        "active": str(active).lower()
    }
    
    # Add type-specific fields
    if tool_type == "flow_action" and flow_action_sys_id:
        payload["flow_action"] = flow_action_sys_id
    elif tool_type == "script" and script_content:
        payload["script"] = script_content
    
    response = requests.post(
        url,
        json=payload,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    
    if response.status_code in [200, 201]:
        result = response.json().get("result", {})
        tool_id = result.get("sys_id")
        return (
            f"✅ Tool created successfully!\n\n"
            f"Name: {name}\n"
            f"Type: {tool_type}\n"
            f"Sys ID: {tool_id}\n"
            f"Active: {active}\n\n"
            f"Next step: Use add_tool_to_agent to associate this tool with agents."
        )
    else:
        return f"❌ Error creating tool: {response.status_code} - {response.text}"


@mcp.tool()
def update_tool(
    tool_sys_id: str,
    name: str = "",
    description: str = "",
    active: str = "",
    script_content: str = ""
) -> str:
    """
    Update an existing tool. Only provide fields you want to update.
    
    Args:
        tool_sys_id: Sys ID of the tool to update (required)
        name: New name (optional)
        description: New description (optional)
        active: New active status - "true" or "false" (optional)
        script_content: New script content if type is script (optional)
    
    Returns:
        Success message with updated fields
    """
    url = f"{INSTANCE}/api/now/table/sn_aia_tool/{tool_sys_id}"
    
    # Only include fields that were provided
    payload = {}
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    if active:
        payload["active"] = active.lower()
    if script_content:
        payload["script"] = script_content
    
    if not payload:
        return "❌ Error: No fields provided to update. Specify at least one field to change."
    
    response = requests.patch(
        url,
        json=payload,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        updated_fields = ", ".join(payload.keys())
        return (
            f"✅ Tool updated successfully!\n\n"
            f"Tool ID: {tool_sys_id}\n"
            f"Updated fields: {updated_fields}"
        )
    else:
        return f"❌ Error updating tool: {response.status_code} - {response.text}"


@mcp.tool()
def delete_tool(
    tool_sys_id: str,
    confirm: bool = False
) -> str:
    """
    Delete a tool. Requires confirmation.
    
    Args:
        tool_sys_id: Sys ID of the tool to delete
        confirm: Must be True to proceed with deletion
    
    Returns:
        Success or error message
    """
    if not confirm:
        return (
            f"⚠️  Deletion requires confirmation.\n\n"
            f"To delete tool {tool_sys_id}, call this tool again with confirm=True.\n\n"
            f"WARNING: This will remove the tool from all agents using it."
        )
    
    url = f"{INSTANCE}/api/now/table/sn_aia_tool/{tool_sys_id}"
    
    response = requests.delete(
        url,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )
    
    if response.status_code == 204:
        return f"✅ Tool {tool_sys_id} deleted successfully."
    else:
        return f"❌ Error deleting tool: {response.status_code} - {response.text}"


# ============================================================================
# TRIGGER WRITE OPERATIONS
# ============================================================================

@mcp.tool()
def create_trigger(
    workflow_sys_id: str,
    trigger_type: str,
    table: str = "",
    condition: str = "",
    active: bool = True
) -> str:
    """
    Create a trigger for an agentic workflow.
    
    Args:
        workflow_sys_id: Sys ID of the workflow this trigger starts
        trigger_type: Type of trigger (on_demand, record_created, record_updated, etc.)
        table: Table name if record-based trigger (e.g., "incident")
        condition: Encoded query condition (e.g., "priority=1^state=1")
        active: Whether the trigger is active (default True)
    
    Returns:
        Success message with trigger sys_id
    """
    url = f"{INSTANCE}/api/now/table/sn_aia_trigger_configuration"
    
    payload = {
        "usecase": workflow_sys_id,
        "trigger_type": trigger_type,
        "active": str(active).lower()
    }
    
    # Add optional fields
    if table:
        payload["table"] = table
    if condition:
        payload["condition"] = condition
    
    response = requests.post(
        url,
        json=payload,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    
    if response.status_code in [200, 201]:
        result = response.json().get("result", {})
        trigger_id = result.get("sys_id")
        return (
            f"✅ Trigger created successfully!\n\n"
            f"Trigger ID: {trigger_id}\n"
            f"Workflow: {workflow_sys_id}\n"
            f"Type: {trigger_type}\n"
            f"Table: {table if table else 'N/A'}\n"
            f"Active: {active}\n\n"
            f"The workflow will now execute when this trigger fires."
        )
    else:
        return f"❌ Error creating trigger: {response.status_code} - {response.text}"


@mcp.tool()
def update_trigger(
    trigger_sys_id: str,
    trigger_type: str = "",
    table: str = "",
    condition: str = "",
    active: str = ""
) -> str:
    """
    Update an existing trigger. Only provide fields you want to update.
    
    Args:
        trigger_sys_id: Sys ID of the trigger to update (required)
        trigger_type: New trigger type (optional)
        table: New table (optional)
        condition: New condition (optional)
        active: New active status - "true" or "false" (optional)
    
    Returns:
        Success message with updated fields
    """
    url = f"{INSTANCE}/api/now/table/sn_aia_trigger_configuration/{trigger_sys_id}"
    
    # Only include fields that were provided
    payload = {}
    if trigger_type:
        payload["trigger_type"] = trigger_type
    if table:
        payload["table"] = table
    if condition:
        payload["condition"] = condition
    if active:
        payload["active"] = active.lower()
    
    if not payload:
        return "❌ Error: No fields provided to update. Specify at least one field to change."
    
    response = requests.patch(
        url,
        json=payload,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        updated_fields = ", ".join(payload.keys())
        return (
            f"✅ Trigger updated successfully!\n\n"
            f"Trigger ID: {trigger_sys_id}\n"
            f"Updated fields: {updated_fields}"
        )
    else:
        return f"❌ Error updating trigger: {response.status_code} - {response.text}"


@mcp.tool()
def delete_trigger(
    trigger_sys_id: str,
    confirm: bool = False
) -> str:
    """
    Delete a trigger. Requires confirmation.
    
    Args:
        trigger_sys_id: Sys ID of the trigger to delete
        confirm: Must be True to proceed with deletion
    
    Returns:
        Success or error message
    """
    if not confirm:
        return (
            f"⚠️  Deletion requires confirmation.\n\n"
            f"To delete trigger {trigger_sys_id}, call this tool again with confirm=True."
        )
    
    url = f"{INSTANCE}/api/now/table/sn_aia_trigger_configuration/{trigger_sys_id}"
    
    response = requests.delete(
        url,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )
    
    if response.status_code == 204:
        return f"✅ Trigger {trigger_sys_id} deleted successfully."
    else:
        return f"❌ Error deleting trigger: {response.status_code} - {response.text}"


# ============================================================================
# HELPER/UTILITY OPERATIONS
# ============================================================================

@mcp.tool()
def clone_ai_agent(
    source_agent_sys_id: str,
    new_name: str,
    new_description: str = ""
) -> str:
    """
    Clone an existing AI agent with all its tools and configuration.
    
    Args:
        source_agent_sys_id: Sys ID of the agent to clone
        new_name: Name for the new agent
        new_description: Description for the new agent (optional, uses source if not provided)
    
    Returns:
        Success message with new agent sys_id
    """
    # Get the source agent
    source_url = f"{INSTANCE}/api/now/table/sn_aia_agent/{source_agent_sys_id}"
    params = {
        "sysparm_fields": "name,description,agent_role,list_of_steps,active"
    }
    
    source_response = requests.get(
        source_url, params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )
    
    if source_response.status_code != 200:
        return f"❌ Error retrieving source agent: {source_response.status_code} - {source_response.text}"
    
    source = source_response.json().get("result", {})
    if not source:
        return f"❌ Source agent {source_agent_sys_id} not found."
    
    # Create new agent with source configuration
    create_url = f"{INSTANCE}/api/now/table/sn_aia_agent"
    payload = {
        "name": new_name,
        "description": new_description if new_description else source.get("description", ""),
        "agent_role": source.get("agent_role", ""),
        "list_of_steps": source.get("list_of_steps", ""),
        "active": source.get("active", "true")
    }
    
    create_response = requests.post(
        create_url,
        json=payload,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    
    if create_response.status_code not in [200, 201]:
        return f"❌ Error creating cloned agent: {create_response.status_code} - {create_response.text}"
    
    new_agent = create_response.json().get("result", {})
    new_agent_id = new_agent.get("sys_id")
    
    # Get source agent's tools with their inputs
    tools_url = f"{INSTANCE}/api/now/table/sn_aia_agent_tool_m2m"
    tools_params = {
        "sysparm_query": f"agent={source_agent_sys_id}",
        "sysparm_fields": "tool,max_automatic_executions,inputs"  # Include inputs field
    }
    
    tools_response = requests.get(
        tools_url, params=tools_params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )
    
    tools_cloned = 0
    if tools_response.status_code == 200:
        tools = tools_response.json().get("result", [])
        for tool in tools:
            # Get the tool sys_id reference value
            tool_ref = tool.get("tool")
            
            # Extract sys_id from reference if it's a dict
            if isinstance(tool_ref, dict):
                tool_sys_id = tool_ref.get("value")
            else:
                tool_sys_id = tool_ref
            
            # Get tool name for the required name field
            tool_name_response = requests.get(
                f"{INSTANCE}/api/now/table/sn_aia_tool/{tool_sys_id}",
                params={"sysparm_fields": "name"},
                auth=(USERNAME, PASSWORD),
                headers={"Accept": "application/json"}
            )
            
            tool_name = "Tool"
            if tool_name_response.status_code == 200:
                tool_name = tool_name_response.json().get("result", {}).get("name", "Tool")
            
            tool_payload = {
                "agent": new_agent_id,
                "tool": tool_sys_id,
                "name": f"Agent Tool: {tool_name}",  # Required field
                "max_automatic_executions": tool.get("max_automatic_executions", 5)
            }
            
            # Include inputs if they exist in the source
            if tool.get("inputs"):
                tool_payload["inputs"] = tool.get("inputs")
            
            tool_create_response = requests.post(
                f"{INSTANCE}/api/now/table/sn_aia_agent_tool_m2m",
                json=tool_payload,
                auth=(USERNAME, PASSWORD),
                headers={"Accept": "application/json", "Content-Type": "application/json"}
            )
            
            if tool_create_response.status_code in [200, 201]:
                tools_cloned += 1
    
    return (
        f"✅ AI Agent cloned successfully!\n\n"
        f"Source Agent: {source.get('name')}\n"
        f"New Agent: {new_name}\n"
        f"New Agent ID: {new_agent_id}\n"
        f"Tools Cloned: {tools_cloned}\n\n"
        f"The new agent has the same configuration and tools as the source."
    )


# ============================================================================
# AI SEARCH TOOLS
# ============================================================================

@mcp.tool()
def search_servicenow_knowledge(
    query: str,
    max_results: int = 10,
    config_sys_id: str = ""
) -> str:
    """
    Search ServiceNow using AI Search. Returns relevant knowledge articles,
    catalog items, and other content based on natural language queries.

    Requires: Scripted REST API configured at /api/snc/mcp_ai_search_api/search
    (See servicenow_rest_api_setup.md for setup instructions)

    Args:
        query: Natural language search query (e.g., "how to reset password")
        max_results: Maximum number of results to return (default 10, max 50)
        config_sys_id: Optional AI Search config sys_id. If not provided,
                      uses the first available AI Search configuration.

    Returns:
        JSON string with search results including titles, snippets, tables,
        and relevance scores. Also shows if the query was spell-corrected.

    Examples:
        - "how to reset my password"
        - "request a new laptop"
        - "VPN troubleshooting"
        - "create an incident"
    """
    import json

    # Validate max_results
    max_results = max(1, min(max_results, 50))

    # Build request payload
    payload = {
        "query": query,
        "max_results": max_results
    }

    if config_sys_id:
        payload["config_sys_id"] = config_sys_id

    # Call the Scripted REST API
    url = f"{INSTANCE}/api/snc/mcp_ai_search_api/search"

    try:
        response = requests.post(
            url,
            json=payload,
            auth=(USERNAME, PASSWORD),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=30
        )

        if response.status_code != 200:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get('error', response.text)
            except:
                pass

            return json.dumps({
                "success": False,
                "error": f"HTTP {response.status_code}: {error_detail}",
                "setup_required": response.status_code == 404,
                "setup_guide": "See servicenow_rest_api_setup.md for REST API setup instructions"
            }, indent=2)

        response_data = response.json()

        # ServiceNow wraps the response in a 'result' key
        result = response_data.get('result', {})

        if not result.get('success'):
            return json.dumps({
                "success": False,
                "error": result.get('error', 'Unknown error'),
                "query": query
            }, indent=2)

        # Format results for better readability
        results = result.get('results', [])
        corrected = result.get('corrected_query', '')

        output = {
            "success": True,
            "query": query,
            "result_count": len(results),
            "results": []
        }

        if corrected and corrected != query:
            output["corrected_query"] = corrected
            output["note"] = f"Query was corrected from '{query}' to '{corrected}'"

        for r in results:
            output["results"].append({
                "title": r.get('title', 'Untitled'),
                "table": r.get('table', 'unknown'),
                "sys_id": r.get('sys_id', ''),
                "snippet": r.get('snippet', '')[:300],  # Truncate long snippets
                "score": r.get('score', 0),
                "url": f"{INSTANCE}/nav_to.do?uri={r.get('table')}:{r.get('sys_id')}" if r.get('sys_id') else ''
            })

        return json.dumps(output, indent=2)

    except requests.exceptions.Timeout:
        return json.dumps({
            "success": False,
            "error": "Request timeout - AI Search took too long to respond",
            "suggestion": "Try a more specific query or reduce max_results"
        }, indent=2)

    except requests.exceptions.ConnectionError:
        return json.dumps({
            "success": False,
            "error": "Connection error - could not reach ServiceNow instance",
            "instance": INSTANCE
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "query": query
        }, indent=2)


@mcp.tool()
def list_ai_search_profiles() -> str:
    """
    List all available AI Search profiles and configurations on the instance.
    Use this to discover which config_sys_id to use with search_servicenow_knowledge.

    Requires: Scripted REST API configured at /api/snc/mcp_ai_search_api/profiles
    (See servicenow_rest_api_setup.md for setup instructions)

    Returns:
        JSON string with list of AI Search configurations including:
        - Configuration name and sys_id
        - Profile name and sys_id
        - Which applications use each profile
    """
    import json

    url = f"{INSTANCE}/api/snc/mcp_ai_search_api/profiles"

    try:
        response = requests.get(
            url,
            auth=(USERNAME, PASSWORD),
            headers={"Accept": "application/json"},
            timeout=10
        )

        if response.status_code != 200:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get('error', response.text)
            except:
                pass

            return json.dumps({
                "success": False,
                "error": f"HTTP {response.status_code}: {error_detail}",
                "setup_required": response.status_code == 404,
                "setup_guide": "See servicenow_rest_api_setup.md for REST API setup instructions"
            }, indent=2)

        response_data = response.json()

        # ServiceNow wraps the response in a 'result' key
        result = response_data.get('result', {})

        if not result.get('success'):
            return json.dumps({
                "success": False,
                "error": result.get('error', 'Unknown error')
            }, indent=2)

        configs = result.get('configs', [])

        output = {
            "success": True,
            "count": len(configs),
            "profiles": []
        }

        for config in configs:
            output["profiles"].append({
                "config_name": config.get('config_name', 'Unnamed'),
                "config_sys_id": config.get('config_sys_id', ''),
                "profile_name": config.get('profile_name', 'Unnamed Profile'),
                "profile_sys_id": config.get('profile_sys_id', '')
            })

        if len(configs) == 0:
            output["note"] = "No AI Search profiles found. Configure AI Search in ServiceNow first."

        return json.dumps(output, indent=2)

    except requests.exceptions.Timeout:
        return json.dumps({
            "success": False,
            "error": "Request timeout"
        }, indent=2)

    except requests.exceptions.ConnectionError:
        return json.dumps({
            "success": False,
            "error": "Connection error - could not reach ServiceNow instance",
            "instance": INSTANCE
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


# =============================================================================
# SERVICE CATALOG HELPER FUNCTIONS
# =============================================================================

def query_snow_table_sc(table, query="", fields="", limit=100, display_value="false"):
    """Generic ServiceNow table query helper for Service Catalog tools."""
    url = f"{INSTANCE}/api/now/table/{table}"
    params = {
        "sysparm_limit": min(limit, 1000),
        "sysparm_display_value": display_value
    }

    if query:
        params["sysparm_query"] = query
    if fields:
        params["sysparm_fields"] = fields

    try:
        response = requests.get(
            url,
            params=params,
            auth=(USERNAME, PASSWORD),
            headers={"Accept": "application/json"},
            timeout=30
        )

        if response.status_code == 200:
            return {"success": True, "result": response.json().get("result", [])}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text[:200]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_category_path(category_sys_id):
    """Build full category path by walking parent hierarchy."""
    if not category_sys_id:
        return ""

    path = []
    current_id = category_sys_id
    max_depth = 10  # Prevent infinite loops

    for _ in range(max_depth):
        result = query_snow_table_sc(
            "sc_category",
            query=f"sys_id={current_id}",
            fields="title,parent",
            limit=1,
            display_value="all"
        )

        if not result["success"] or not result["result"]:
            break

        category = result["result"][0]
        title = category.get("title", "")

        # Handle dict response from display_value="all"
        if isinstance(title, dict):
            title = title.get("display_value", "") or title.get("value", "")

        if title:
            path.insert(0, title)

        # Get parent
        parent = category.get("parent", {})
        if isinstance(parent, dict):
            parent_id = parent.get("value", "")
        else:
            parent_id = parent

        if not parent_id:
            break

        current_id = parent_id

    return " > ".join(path) if path else ""


def strip_html(html_text):
    """Strip HTML tags and entities from text."""
    if not html_text:
        return ""

    # Handle dict response from display_value="all"
    if isinstance(html_text, dict):
        html_text = html_text.get("value", "") or html_text.get("display_value", "")

    # Ensure we have a string
    if not isinstance(html_text, str):
        return ""

    import re
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html_text)
    # Replace common entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def translate_variable_type(type_code):
    """Translate ServiceNow variable type code to human-readable name."""
    type_map = {
        '1': 'Yes/No',
        '2': 'Multi Line Text',
        '3': 'Multiple Choice',
        '4': 'Numeric Scale',
        '5': 'Select Box',
        '6': 'Single Line Text',
        '7': 'Check Box',
        '8': 'Reference',
        '9': 'Date',
        '10': 'Date/Time',
        '11': 'Label',
        '12': 'Break',
        '14': 'Macro',
        '15': 'UI Page',
        '16': 'Wide Single Line Text',
        '17': 'Masked',
        '18': 'Lookup Select Box',
        '19': 'Container Start',
        '20': 'Container End',
        '21': 'List Collector',
        '22': 'Lookup Multiple Choice',
        '23': 'HTML',
        '24': 'Rich Text',
        '25': 'Email',
        '26': 'URL'
    }
    return type_map.get(str(type_code), f'Unknown Type ({type_code})')


def parse_ui_policy_conditions(conditions_string):
    """
    Parse catalog UI policy conditions into structured format.
    Handles formats like: IO:{var_sys_id}={value} and IO.{var_sys_id}={value}
    """
    if not conditions_string:
        return []

    import re
    parsed = []

    # Remove trailing ^EQ if present
    conditions_string = re.sub(r'\^EQ$', '', conditions_string)

    # Split by ^OR for OR groups
    or_groups = conditions_string.split('^OR')

    for group in or_groups:
        # Find all IO: or IO. patterns
        io_pattern = r'IO[:\.]([a-f0-9]{32})([!=<>]+|IN|LIKE|NOT LIKE|CONTAINS)(.+?)(?:\^|$)'
        matches = re.finditer(io_pattern, group, re.IGNORECASE)

        for match in matches:
            var_sys_id = match.group(1)
            operator = match.group(2).strip()
            value = match.group(3).strip()

            # Resolve variable name from sys_id
            var_name = resolve_variable_name(var_sys_id)

            # Normalize operator
            op_map = {
                '=': 'equals',
                '!=': 'not_equals',
                'IN': 'in',
                'NOT IN': 'not_in',
                'LIKE': 'like',
                'NOT LIKE': 'not_like',
                'CONTAINS': 'contains'
            }
            normalized_op = op_map.get(operator, operator.lower())

            parsed.append({
                "trigger_variable": var_name if var_name else var_sys_id,
                "trigger_variable_sys_id": var_sys_id,
                "operator": normalized_op,
                "trigger_value": value
            })

    return parsed


def resolve_variable_name(var_sys_id):
    """Resolve variable name from sys_id."""
    result = query_snow_table_sc(
        "item_option_new",
        query=f"sys_id={var_sys_id}",
        fields="name",
        limit=1
    )

    if result["success"] and result["result"]:
        return result["result"][0].get("name", "")
    return ""


# =============================================================================
# SECTION: SERVICE CATALOG ORDERING
# =============================================================================

@mcp.tool()
def list_catalog_items(
    limit: int = 50,
    category_sys_id: str = "",
    include_producers: bool = True
) -> str:
    """
    List active ServiceNow catalog items.

    Args:
        limit: Maximum number of items to return (default 50, max 100)
        category_sys_id: Optional category sys_id to filter by specific category
        include_producers: Include record producers (default True)

    Returns:
        JSON with catalog items including sys_id, name, description, category, price

    Examples:
        List all items: list_catalog_items()
        List specific category: list_catalog_items(category_sys_id="abc123...")
        Standard items only: list_catalog_items(include_producers=False)
    """
    try:
        # Build query
        query_parts = ["active=true"]

        if include_producers:
            query_parts.append("sys_class_nameINsc_cat_item,sc_cat_item_producer")
        else:
            query_parts.append("sys_class_name=sc_cat_item")

        if category_sys_id:
            query_parts.append(f"category={category_sys_id}")

        query = "^".join(query_parts)

        # Query catalog items
        result = query_snow_table_sc(
            "sc_cat_item",
            query=query,
            fields="sys_id,name,short_description,description,category,price,recurring_price,sys_class_name",
            limit=min(limit, 100),
            display_value="all"
        )

        if not result["success"]:
            return json.dumps({
                "success": False,
                "error": result["error"]
            }, indent=2)

        items = result["result"]
        output_items = []

        for item in items:
            # Get category path
            category_val = item.get("category", {})
            category_sys_id_val = category_val.get("value", "") if isinstance(category_val, dict) else category_val
            category_path = get_category_path(category_sys_id_val) if category_sys_id_val else ""

            # Strip HTML from description
            description = strip_html(item.get("description", ""))
            if len(description) > 300:
                description = description[:300] + "..."

            output_items.append({
                "sys_id": item.get("sys_id", ""),
                "name": item.get("name", ""),
                "short_description": item.get("short_description", ""),
                "description": description,
                "category": category_path,
                "price": item.get("price", "0"),
                "recurring_price": item.get("recurring_price", "0"),
                "item_type": item.get("sys_class_name", "sc_cat_item")
            })

        return json.dumps({
            "success": True,
            "count": len(output_items),
            "items": output_items
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


@mcp.tool()
def search_catalog_items(
    search_term: str,
    limit: int = 20,
    include_producers: bool = True
) -> str:
    """
    Search ServiceNow catalog items by keyword.

    Args:
        search_term: Keywords to search in name, short_description, and description
        limit: Maximum number of results (default 20, max 100)
        include_producers: Include record producers in results (default True)

    Returns:
        JSON with matching catalog items

    Examples:
        search_catalog_items("laptop")
        search_catalog_items("iphone", limit=10)
        search_catalog_items("incident", include_producers=True)
    """
    try:
        # Input sanitization
        if not search_term:
            return json.dumps({
                "success": False,
                "error": "search_term is required"
            }, indent=2)

        # Trim whitespace
        search_term = search_term.strip()

        if not search_term:
            return json.dumps({
                "success": False,
                "error": "search_term cannot be empty or whitespace only"
            }, indent=2)

        # Build search query - name field only for now
        # Note: OR queries with multi-word search terms have parsing issues in ServiceNow
        # Searching name field covers 95% of use cases and works reliably
        query_parts = ["active=true"]

        if include_producers:
            query_parts.append("sys_class_nameINsc_cat_item,sc_cat_item_producer")
        else:
            query_parts.append("sys_class_name=sc_cat_item")

        # Search name field only - proven to work with multi-word terms
        query_parts.append(f"nameLIKE{search_term}")

        query = "^".join(query_parts)

        # Query catalog items
        result = query_snow_table_sc(
            "sc_cat_item",
            query=query,
            fields="sys_id,name,short_description,description,category,price,recurring_price,sys_class_name",
            limit=min(limit, 100),
            display_value="all"
        )

        if not result["success"]:
            return json.dumps({
                "success": False,
                "error": result["error"]
            }, indent=2)

        items = result["result"]
        output_items = []

        for item in items:
            # Get category path
            category_val = item.get("category", {})
            category_sys_id_val = category_val.get("value", "") if isinstance(category_val, dict) else category_val
            category_path = get_category_path(category_sys_id_val) if category_sys_id_val else ""

            # Strip HTML from description
            description = strip_html(item.get("description", ""))
            if len(description) > 300:
                description = description[:300] + "..."

            output_items.append({
                "sys_id": item.get("sys_id", ""),
                "name": item.get("name", ""),
                "short_description": item.get("short_description", ""),
                "description": description,
                "category": category_path,
                "price": item.get("price", "0"),
                "recurring_price": item.get("recurring_price", "0"),
                "item_type": item.get("sys_class_name", "sc_cat_item")
            })

        return json.dumps({
            "success": True,
            "search_term": search_term,
            "count": len(output_items),
            "items": output_items
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


@mcp.tool()
def get_catalog_item_details(catalog_item_sys_id: str) -> str:
    """
    Get complete catalog item details including variables, pricing, and UI policies.

    This is the primary discovery tool for catalog ordering. It returns all metadata
    needed to understand what information is required to order an item.

    Args:
        catalog_item_sys_id: The sys_id of the catalog item to retrieve

    Returns:
        JSON with complete item details including:
        - Basic info (name, description, type, table_name for producers)
        - Pricing (price, recurring_price, list_price, cost)
        - Variables (direct variables and those in variable sets)
        - Variable metadata (type, question, choices, mandatory, help_text)
        - UI policies (conditional field logic)
        - Price-affecting fields

    Example:
        get_catalog_item_details("abc123...")
    """
    try:
        if not catalog_item_sys_id:
            return json.dumps({"success": False, "error": "catalog_item_sys_id is required"}, indent=2)

        # Step 1: Get catalog item basic info
        item_result = query_snow_table_sc(
            "sc_cat_item",
            query=f"sys_id={catalog_item_sys_id}",
            fields="sys_id,name,short_description,description,sys_class_name,table_name,price,recurring_price,list_price,cost,recurring_frequency",
            limit=1,
            display_value="all"
        )

        if not item_result["success"] or not item_result["result"]:
            return json.dumps({"success": False, "error": "Catalog item not found"}, indent=2)

        item = item_result["result"][0]

        output = {
            "success": True,
            "sys_id": catalog_item_sys_id,
            "name": item.get("name", ""),
            "short_description": item.get("short_description", ""),
            "description": strip_html(item.get("description", "")),
            "item_type": item.get("sys_class_name", "sc_cat_item"),
            "table_name": item.get("table_name", ""),
            "pricing": {
                "has_pricing": False,
                "is_recurring": False,
                "base_price": {"value": "0", "display_value": "$0.00"},
                "recurring_price": {"value": "0", "display_value": "$0.00", "frequency": ""},
                "list_price": {"value": "0", "display_value": "$0.00"},
                "cost": {"value": "0", "display_value": "$0.00"}
            },
            "variables": [],
            "variable_sets": [],
            "ui_policies": [],
            "price_affecting_fields": []
        }

        # Step 2: Extract pricing
        price_val = item.get("price", "0")
        recurring_price_val = item.get("recurring_price", "0")

        if price_val and price_val != "0":
            output["pricing"]["has_pricing"] = True
            output["pricing"]["base_price"] = {
                "value": price_val,
                "display_value": item.get("price", "$0.00") if isinstance(item.get("price"), str) else f"${price_val}"
            }

        if recurring_price_val and recurring_price_val != "0":
            output["pricing"]["is_recurring"] = True
            output["pricing"]["recurring_price"] = {
                "value": recurring_price_val,
                "display_value": item.get("recurring_price", "$0.00") if isinstance(item.get("recurring_price"), str) else f"${recurring_price_val}",
                "frequency": item.get("recurring_frequency", "monthly")
            }

        # Step 3: Get direct variables (not in variable sets)
        vars_result = query_snow_table_sc(
            "item_option_new",
            query=f"cat_item={catalog_item_sys_id}^variable_setISEMPTY",
            fields="sys_id,name,question_text,type,order,mandatory,read_only,default_value,help_text,example_text,reference,reference_qual,max_length",
            limit=200,
            display_value="all"
        )

        if vars_result["success"]:
            for var in vars_result["result"]:
                var_data = {
                    "name": var.get("name", ""),
                    "question": var.get("question_text", ""),
                    "type": translate_variable_type(var.get("type", "")),
                    "type_code": var.get("type", ""),
                    "order": var.get("order", "100"),
                    "mandatory": var.get("mandatory", "false") == "true",
                    "read_only": var.get("read_only", "false") == "true",
                    "default_value": var.get("default_value", ""),
                    "help_text": var.get("help_text", ""),
                    "example_text": var.get("example_text", "")
                }

                # Add type-specific fields
                if var_data["type"] == "Reference":
                    var_data["reference_table"] = var.get("reference", "")
                    var_data["reference_qualifier"] = var.get("reference_qual", "")

                if var_data["type"] in ["Single Line Text", "Multi Line Text", "Wide Single Line Text"]:
                    var_data["max_length"] = var.get("max_length", "")

                # Get choices for select/dropdown fields
                if var_data["type"] in ["Select Box", "Multiple Choice", "Check Box", "Radio"]:
                    var_sys_id = var.get("sys_id", "")
                    choices_result = query_snow_table_sc(
                        "question_choice",
                        query=f"question={var_sys_id}",
                        fields="text,value,order,price,recurring_price",
                        limit=100,
                        display_value="all"
                    )

                    if choices_result["success"]:
                        choices = []
                        for choice in choices_result["result"]:
                            choice_data = {
                                "text": choice.get("text", ""),
                                "value": choice.get("value", ""),
                                "order": choice.get("order", "100")
                            }

                            # Add pricing if present
                            if choice.get("price") and choice.get("price") != "0":
                                choice_data["price"] = choice.get("price", "0")
                                choice_data["price_display"] = f"+${choice.get('price', '0')}"

                            if choice.get("recurring_price") and choice.get("recurring_price") != "0":
                                choice_data["recurring_price"] = choice.get("recurring_price", "0")
                                choice_data["recurring_price_display"] = f"+${choice.get('recurring_price', '0')}/month"

                            choices.append(choice_data)

                        var_data["choices"] = choices

                output["variables"].append(var_data)

        # Step 4: Get variable sets
        varsets_result = query_snow_table_sc(
            "io_set_item",
            query=f"sc_cat_item={catalog_item_sys_id}",
            fields="variable_set",
            limit=50,
            display_value="all"
        )

        if varsets_result["success"]:
            for set_item in varsets_result["result"]:
                varset_val = set_item.get("variable_set", {})
                varset_sys_id = varset_val.get("value", "") if isinstance(varset_val, dict) else varset_val

                if not varset_sys_id:
                    continue

                # Get variable set details
                varset_detail_result = query_snow_table_sc(
                    "item_option_new_set",
                    query=f"sys_id={varset_sys_id}",
                    fields="sys_id,internal_name,title,description,type,max_rows,min_rows",
                    limit=1,
                    display_value="all"
                )

                if varset_detail_result["success"] and varset_detail_result["result"]:
                    varset_detail = varset_detail_result["result"][0]
                    set_type = varset_detail.get("type", "one_to_one")
                    is_multi_row = set_type == "one_to_many"

                    varset_data = {
                        "sys_id": varset_sys_id,
                        "internal_name": varset_detail.get("internal_name", ""),
                        "title": varset_detail.get("title", ""),
                        "description": varset_detail.get("description", ""),
                        "type": set_type,
                        "is_multi_row": is_multi_row,
                        "variables": []
                    }

                    if is_multi_row:
                        varset_data["multi_row_config"] = {
                            "max_rows": varset_detail.get("max_rows", "unlimited"),
                            "min_rows": varset_detail.get("min_rows", "0")
                        }

                    # Get variables in this set (simplified - same structure as direct variables)
                    set_vars_result = query_snow_table_sc(
                        "item_option_new",
                        query=f"variable_set={varset_sys_id}",
                        fields="name,question_text,type,mandatory",
                        limit=100,
                        display_value="all"
                    )

                    if set_vars_result["success"]:
                        for set_var in set_vars_result["result"]:
                            varset_data["variables"].append({
                                "name": set_var.get("name", ""),
                                "question": set_var.get("question_text", ""),
                                "type": translate_variable_type(set_var.get("type", "")),
                                "mandatory": set_var.get("mandatory", "false") == "true"
                            })

                    output["variable_sets"].append(varset_data)

        # Step 5: Get UI policies (simplified)
        policies_result = query_snow_table_sc(
            "catalog_ui_policy",
            query=f"catalog_item={catalog_item_sys_id}^active=true",
            fields="sys_id,short_description,catalog_conditions,on_load,reverse_if_false",
            limit=50,
            display_value="all"
        )

        if policies_result["success"]:
            for policy in policies_result["result"]:
                policy_sys_id = policy.get("sys_id", "")
                conditions_string = policy.get("catalog_conditions", "")

                # Handle dict response from display_value="all"
                if isinstance(conditions_string, dict):
                    conditions_string = conditions_string.get("value", "") or conditions_string.get("display_value", "")
                if not isinstance(conditions_string, str):
                    conditions_string = ""

                policy_data = {
                    "sys_id": policy_sys_id,
                    "short_description": policy.get("short_description", ""),
                    "on_load": policy.get("on_load", "0"),
                    "reverse_if_false": policy.get("reverse_if_false", "0"),
                    "catalog_conditions": conditions_string,
                    "trigger_conditions": parse_ui_policy_conditions(conditions_string),
                    "policy_actions": []
                }

                # Get policy actions
                actions_result = query_snow_table_sc(
                    "catalog_ui_policy_action",
                    query=f"ui_policy={policy_sys_id}",
                    fields="variable,visible,mandatory,read_only,clear_value",
                    limit=50,
                    display_value="all"
                )

                if actions_result["success"]:
                    for action in actions_result["result"]:
                        var_val = action.get("variable", {})
                        var_sys_id = var_val.get("value", "") if isinstance(var_val, dict) else var_val
                        var_name = resolve_variable_name(var_sys_id) if var_sys_id else ""

                        policy_data["policy_actions"].append({
                            "affected_variable": var_name if var_name else var_sys_id,
                            "affected_variable_sys_id": var_sys_id,
                            "makes_visible": action.get("visible", "false") == "true",
                            "makes_mandatory": action.get("mandatory", "false") == "true",
                            "makes_read_only": action.get("read_only", "false") == "true",
                            "clears_value": action.get("clear_value", "false") == "true"
                        })

                output["ui_policies"].append(policy_data)

        return json.dumps(output, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


@mcp.tool()
def lookup_reference_field(
    reference_table: str,
    reference_qualifier: str = "",
    search_term: str = "",
    limit: int = 10
) -> str:
    """
    Query a reference table to get available options for a Reference type variable.

    This tool helps populate Reference fields by querying the target table with
    optional filters and search terms.

    Args:
        reference_table: ServiceNow table to query (e.g., "sys_user", "cmdb_ci", "core_company")
        reference_qualifier: Optional encoded query to filter results (e.g., "active=true")
                           Note: JavaScript qualifiers cannot be evaluated client-side
        search_term: Optional keyword to search in name, number, title fields
        limit: Maximum results to return (default 10, max 100)

    Returns:
        JSON with matching records including sys_id, display_value, and common fields

    Examples:
        lookup_reference_field("sys_user", search_term="beth")
        lookup_reference_field("cmdb_ci_computer", reference_qualifier="install_status=1")
        lookup_reference_field("core_company", limit=20)
    """
    try:
        if not reference_table:
            return json.dumps({
                "success": False,
                "error": "reference_table is required"
            }, indent=2)

        # Build query
        query_parts = []

        # Apply reference qualifier if it's not a javascript: expression
        if reference_qualifier and not reference_qualifier.lower().startswith("javascript:"):
            query_parts.append(reference_qualifier)

        # Apply search term
        if search_term:
            search_parts = [
                f"nameLIKE{search_term}",
                f"numberLIKE{search_term}",
                f"titleLIKE{search_term}",
                f"short_descriptionLIKE{search_term}"
            ]
            query_parts.append("(" + "^OR".join(search_parts) + ")")

        query = "^".join(query_parts) if query_parts else ""

        # Query the reference table
        result = query_snow_table_sc(
            reference_table,
            query=query,
            fields="sys_id,name,number,title,short_description,email,user_name",
            limit=min(limit, 100),
            display_value="all"
        )

        if not result["success"]:
            return json.dumps({
                "success": False,
                "error": result["error"],
                "reference_table": reference_table
            }, indent=2)

        records = result["result"]
        output_records = []

        for record in records:
            # Build display value from available fields
            display_value = (
                record.get("name", "") or
                record.get("number", "") or
                record.get("title", "") or
                record.get("sys_id", "")
            )

            record_data = {
                "sys_id": record.get("sys_id", ""),
                "display_value": display_value
            }

            # Add optional fields if present
            if record.get("number"):
                record_data["number"] = record.get("number", "")
            if record.get("title"):
                record_data["title"] = record.get("title", "")
            if record.get("short_description"):
                record_data["short_description"] = record.get("short_description", "")[:100]
            if record.get("email"):
                record_data["email"] = record.get("email", "")
            if record.get("user_name"):
                record_data["user_name"] = record.get("user_name", "")

            output_records.append(record_data)

        return json.dumps({
            "success": True,
            "reference_table": reference_table,
            "total_count": len(output_records),
            "results": output_records,
            "search_term_used": search_term,
            "reference_qualifier_note": "JavaScript qualifiers cannot be evaluated" if reference_qualifier.lower().startswith("javascript:") else ""
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "reference_table": reference_table
        }, indent=2)


@mcp.tool()
def get_user_context(user_identifier: str) -> str:
    """
    Get user details from ServiceNow for auto-populating order fields.

    This tool retrieves user information that can be used to automatically
    populate fields like requested_for, location, department, etc.

    Args:
        user_identifier: Email address, user_name, or sys_id of the user

    Returns:
        JSON with user details including sys_id, name, email, location, department, manager

    Examples:
        get_user_context("beth.anglin@example.com")
        get_user_context("beth.anglin")
        get_user_context("abc123...")  # sys_id
    """
    try:
        if not user_identifier:
            return json.dumps({
                "success": False,
                "error": "user_identifier is required"
            }, indent=2)

        # Determine query type based on input
        if '@' in user_identifier:
            # Email
            query = f"email={user_identifier}"
        elif len(user_identifier) == 32 and '-' not in user_identifier:
            # Likely sys_id (32 hex characters, no dashes)
            query = f"sys_id={user_identifier}"
        else:
            # User name
            query = f"user_name={user_identifier}"

        # Query sys_user table
        result = query_snow_table_sc(
            "sys_user",
            query=query,
            fields="sys_id,user_name,name,email,title,department,location,manager,phone,mobile_phone",
            limit=1,
            display_value="all"
        )

        if not result["success"]:
            return json.dumps({
                "success": False,
                "error": result["error"]
            }, indent=2)

        if not result["result"]:
            return json.dumps({
                "success": False,
                "error": f"User not found: {user_identifier}"
            }, indent=2)

        user = result["result"][0]

        # Extract display values for reference fields
        def extract_display(field_val):
            if isinstance(field_val, dict):
                return {
                    "sys_id": field_val.get("value", ""),
                    "display_value": field_val.get("display_value", "")
                }
            return field_val

        output = {
            "success": True,
            "user_sys_id": user.get("sys_id", ""),
            "user_name": user.get("user_name", ""),
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "title": user.get("title", ""),
            "department": extract_display(user.get("department", "")),
            "location": extract_display(user.get("location", "")),
            "manager": extract_display(user.get("manager", "")),
            "phone": user.get("phone", ""),
            "mobile_phone": user.get("mobile_phone", "")
        }

        return json.dumps(output, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


# =============================================================================
# SECTION: SERVICE CATALOG ORDERING - PHASE 2 (ORDER SUBMISSION)
# =============================================================================

@mcp.tool()
def order_catalog_item(
    catalog_item_sys_id: str,
    variables: str = "{}",
    requested_for: str = "",
    quantity: int = 1,
    special_instructions: str = ""
) -> str:
    """
    Submit a Service Catalog order.

    IMPORTANT WORKFLOW:
    1. ALWAYS ask who the order is for if not explicitly mentioned
    2. Use get_user_context(email_or_username) to get the user's sys_id
    3. Pass the sys_id as requested_for parameter
    4. Without requested_for, order will default to service account (NOT desired)

    Args:
        catalog_item_sys_id: The sys_id of the catalog item to order
        variables: JSON string of variable values (e.g., '{"color": "green", "storage": "256"}')
        requested_for: User sys_id to order for (REQUIRED - get from get_user_context)
        quantity: Number of items to order (default 1)
        special_instructions: Additional instructions or notes for the request

    Returns:
        JSON with request number (REQ...), request item number (RITM...), and order details

    Workflow Example:
        1. Ask: "Who is this order for?"
        2. Call: get_user_context("beth.anglin@example.com") -> get sys_id
        3. Call: order_catalog_item("abc123...", '{"color": "green"}', requested_for="user_sys_id")
    """
    try:
        if not catalog_item_sys_id:
            return json.dumps({
                "success": False,
                "error": "catalog_item_sys_id is required"
            }, indent=2)

        # Parse variables JSON
        try:
            variables_dict = json.loads(variables)
        except json.JSONDecodeError:
            return json.dumps({
                "success": False,
                "error": f"Invalid JSON in variables parameter: {variables}"
            }, indent=2)

        # Build request body for Service Catalog API
        request_body = {
            "sysparm_quantity": str(quantity)
        }

        # Add variables if provided
        if variables_dict:
            request_body["variables"] = variables_dict

        # Add requested_for if provided
        if requested_for:
            request_body["sysparm_requested_for"] = requested_for

        # Add special instructions if provided
        if special_instructions:
            # Note: special_instructions maps to work_notes or comments depending on API version
            request_body["sysparm_special_instructions"] = special_instructions

        # Call Service Catalog REST API
        url = f"{INSTANCE}/api/sn_sc/servicecatalog/items/{catalog_item_sys_id}/order_now"

        response = requests.post(
            url,
            json=request_body,
            auth=(USERNAME, PASSWORD),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            timeout=30
        )

        if response.status_code not in [200, 201]:
            return json.dumps({
                "success": False,
                "error": f"API error: {response.status_code}",
                "details": response.text
            }, indent=2)

        result = response.json()

        # Extract request and request item information
        request_result = result.get("result", {})

        output = {
            "success": True,
            "order_submitted": True,
            "request_number": request_result.get("request_number", ""),
            "request_sys_id": request_result.get("request_id", ""),
            "request_item_number": "",
            "request_item_sys_id": "",
            "order_status": request_result.get("state", ""),
            "catalog_item": catalog_item_sys_id,
            "quantity": quantity,
            "variables_submitted": variables_dict
        }

        # Extract request item (RITM) info if available
        request_items = request_result.get("request_items", [])
        if request_items and len(request_items) > 0:
            first_item = request_items[0]
            output["request_item_number"] = first_item.get("number", "")
            output["request_item_sys_id"] = first_item.get("sys_id", "")

        return json.dumps(output, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


@mcp.tool()
def get_request_status(request_number: str) -> str:
    """
    Get the status and details of a Service Catalog request.

    Args:
        request_number: The request number (REQ...) or request item number (RITM...)

    Returns:
        JSON with request status, approval status, assigned groups, and fulfillment progress

    Examples:
        get_request_status("REQ0010001")
        get_request_status("RITM0010001")
    """
    try:
        if not request_number:
            return json.dumps({
                "success": False,
                "error": "request_number is required"
            }, indent=2)

        # Determine if this is a request (REQ) or request item (RITM)
        request_number = request_number.strip().upper()

        if request_number.startswith("REQ"):
            # Query sc_request table
            table = "sc_request"
            query = f"number={request_number}"
        elif request_number.startswith("RITM"):
            # Query sc_req_item table
            table = "sc_req_item"
            query = f"number={request_number}"
        else:
            return json.dumps({
                "success": False,
                "error": f"Invalid request number format. Must start with REQ or RITM: {request_number}"
            }, indent=2)

        # Query the appropriate table
        result = query_snow_table_sc(
            table,
            query=query,
            fields="sys_id,number,state,stage,approval,active,opened_at,opened_by,requested_for,short_description,description,assignment_group,assigned_to,work_notes,comments",
            limit=1,
            display_value="all"
        )

        if not result["success"]:
            return json.dumps({
                "success": False,
                "error": result["error"]
            }, indent=2)

        if not result["result"]:
            return json.dumps({
                "success": False,
                "error": f"Request not found: {request_number}"
            }, indent=2)

        record = result["result"][0]

        # Extract display values
        def extract_display(field_val):
            if isinstance(field_val, dict):
                return field_val.get("display_value", "")
            return field_val

        output = {
            "success": True,
            "request_number": record.get("number", ""),
            "sys_id": record.get("sys_id", ""),
            "state": extract_display(record.get("state", "")),
            "stage": extract_display(record.get("stage", "")),
            "approval": extract_display(record.get("approval", "")),
            "active": record.get("active", "true") == "true",
            "opened_at": extract_display(record.get("opened_at", "")),
            "opened_by": extract_display(record.get("opened_by", "")),
            "requested_for": extract_display(record.get("requested_for", "")),
            "short_description": record.get("short_description", ""),
            "description": strip_html(record.get("description", "")),
            "assignment_group": extract_display(record.get("assignment_group", "")),
            "assigned_to": extract_display(record.get("assigned_to", "")),
            "work_notes": record.get("work_notes", ""),
            "comments": record.get("comments", "")
        }

        # If this is a request (REQ), also get associated request items (RITMs)
        if request_number.startswith("REQ"):
            req_sys_id = record.get("sys_id", "")
            items_result = query_snow_table_sc(
                "sc_req_item",
                query=f"request={req_sys_id}",
                fields="sys_id,number,state,stage,short_description",
                limit=20,
                display_value="all"
            )

            if items_result["success"]:
                output["request_items"] = []
                for item in items_result["result"]:
                    output["request_items"].append({
                        "number": item.get("number", ""),
                        "sys_id": item.get("sys_id", ""),
                        "state": extract_display(item.get("state", "")),
                        "stage": extract_display(item.get("stage", "")),
                        "short_description": item.get("short_description", "")
                    })

        return json.dumps(output, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


@mcp.tool()
def list_my_requests(
    requested_for: str = "",
    limit: int = 20,
    active_only: bool = True
) -> str:
    """
    List Service Catalog requests for a specific user.

    Args:
        requested_for: User sys_id, email, or user_name to filter by (optional, returns all if empty)
        limit: Maximum number of requests to return (default 20, max 100)
        active_only: Only show active requests (default True)

    Returns:
        JSON with list of requests including number, state, opened date, items

    Examples:
        list_my_requests("beth.anglin@example.com")
        list_my_requests("user_sys_id", limit=10)
        list_my_requests(active_only=False)  # Show all requests including closed
    """
    try:
        query_parts = []

        # Add active filter
        if active_only:
            query_parts.append("active=true")

        # Add requested_for filter if provided
        if requested_for:
            # First, resolve user identifier to sys_id
            user_result = get_user_context(requested_for)
            user_data = json.loads(user_result)

            if not user_data.get("success"):
                return json.dumps({
                    "success": False,
                    "error": f"Could not find user: {requested_for}"
                }, indent=2)

            user_sys_id = user_data.get("user_sys_id", "")
            if user_sys_id:
                query_parts.append(f"requested_for={user_sys_id}")

        query = "^".join(query_parts) if query_parts else ""

        # Query sc_request table
        result = query_snow_table_sc(
            "sc_request",
            query=query,
            fields="sys_id,number,state,stage,approval,active,opened_at,requested_for,short_description",
            limit=min(limit, 100),
            display_value="all"
        )

        if not result["success"]:
            return json.dumps({
                "success": False,
                "error": result["error"]
            }, indent=2)

        requests_list = []
        for record in result["result"]:
            # Extract display values
            def extract_display(field_val):
                if isinstance(field_val, dict):
                    return field_val.get("display_value", "")
                return field_val

            request_data = {
                "request_number": record.get("number", ""),
                "sys_id": record.get("sys_id", ""),
                "state": extract_display(record.get("state", "")),
                "stage": extract_display(record.get("stage", "")),
                "approval": extract_display(record.get("approval", "")),
                "active": record.get("active", "true") == "true",
                "opened_at": extract_display(record.get("opened_at", "")),
                "requested_for": extract_display(record.get("requested_for", "")),
                "short_description": record.get("short_description", "")
            }

            requests_list.append(request_data)

        return json.dumps({
            "success": True,
            "total_count": len(requests_list),
            "requests": requests_list
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2)


if __name__ == "__main__":
    mcp.run()
# Function to add to server.py for cleaning up duplicate agent configs

@mcp.tool()
def cleanup_agent_configs(
    agent_sys_id: str
) -> str:
    """
    Clean up duplicate agent config records for an agent.
    Keeps the most recent config record and deletes older duplicates.
    
    Args:
        agent_sys_id: Sys ID of the agent to clean up configs for
    
    Returns:
        Success message with cleanup details
    """
    # Query all config records for this agent
    url = f"{INSTANCE}/api/now/table/sn_aia_agent_config"
    params = {
        "sysparm_query": f"agent={agent_sys_id}^ORDERBYDESCsys_created_on",
        "sysparm_fields": "sys_id,active,sys_created_on"
    }
    
    response = requests.get(
        url,
        params=params,
        auth=(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )
    
    if response.status_code != 200:
        return f"❌ Error querying configs: {response.status_code} - {response.text}"
    
    configs = response.json().get("result", [])
    
    if len(configs) <= 1:
        return f"✅ No cleanup needed. Agent has {len(configs)} config record(s)."
    
    # Keep the first one (most recent), delete the rest
    kept_config = configs[0]
    deleted_count = 0
    
    for config in configs[1:]:
        delete_url = f"{INSTANCE}/api/now/table/sn_aia_agent_config/{config.get('sys_id')}"
        delete_response = requests.delete(
            delete_url,
            auth=(USERNAME, PASSWORD),
            headers={"Accept": "application/json"}
        )
        
        if delete_response.status_code == 204:
            deleted_count += 1
    
    return (
        f"✅ Agent config cleanup completed!\n\n"
        f"Agent: {agent_sys_id}\n"
        f"Total configs found: {len(configs)}\n"
        f"Configs deleted: {deleted_count}\n"
        f"Active config kept: {kept_config.get('sys_id')} (Active: {kept_config.get('active')})"
    )
