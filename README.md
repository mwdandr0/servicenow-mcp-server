# ServiceNow MCP Server

A comprehensive Model Context Protocol (MCP) server for interacting with ServiceNow instances. Includes 80 tools covering AI Agent management and invocation, performance analytics, incident/ITSM operations, service catalog ordering, flow designer debugging, app management, and more.

## Setup

### 1. Configure Credentials

Copy `.env.template` to `.env` and fill in your credentials:

```bash
cp .env.template .env
```

```
SERVICENOW_INSTANCE=your-instance.service-now.com
SERVICENOW_USERNAME=your.username
SERVICENOW_PASSWORD=your-password
```

Supports both `SERVICENOW_*` and `SNOW_*` variable names, and accepts instance names in any format (`dev12345`, `dev12345.service-now.com`, or full URL).

### 2. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Add to Claude Desktop

```json
{
  "mcpServers": {
    "servicenow": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/server.py"],
      "env": {
        "SERVICENOW_INSTANCE": "your-instance.service-now.com",
        "SERVICENOW_USERNAME": "your.username",
        "SERVICENOW_PASSWORD": "your-password"
      }
    }
  }
}
```

---

## Available Tools (80)

### 🤖 AI Agent Management
Build, configure, and manage ServiceNow AI Agents:
- `list_ai_agents` - List all AI agents
- `get_agent_details` - Get complete agent configuration
- `create_ai_agent` - Create new Chat or Voice AI agents
- `update_ai_agent` - Modify existing agents
- `delete_ai_agent` - Remove agents
- `clone_ai_agent` - Clone an agent with all its tools
- `list_agent_tools` - View tools assigned to an agent
- `add_tool_to_agent` - Assign tools to agents
- `remove_tool_from_agent` - Remove tools from agents
- `create_tool` - Create custom tools
- `update_tool` - Update tool definitions
- `delete_tool` - Remove tools
- `cleanup_agent_configs` - Clean up duplicate agent config records

### ▶️ AI Agent Invocation (Run Agents)
Invoke AI Agents and get responses:
- `run_ai_agent` - Invoke an AI Agent via the OOB `AiAgentRuntimeUtil` API
  - Accepts agent name or sys_id
  - Supports context records (e.g. target incident)
  - Back-and-forth conversations via `context_memory`
  - Polls execution plan until completed and returns response

  **Prerequisite:** Uses the OOB Scripted REST API at `/api/snc/ai_agent_invoker_api/start_conversation`

### 🔄 Agentic Workflows
Orchestrate multi-agent workflows:
- `list_agentic_workflows` - List all workflows (use cases)
- `create_agentic_workflow` - Create new workflows
- `update_agentic_workflow` - Update workflow configuration
- `delete_agentic_workflow` - Remove workflows
- `list_trigger_configurations` - List workflow triggers
- `create_trigger` - Create workflow triggers
- `update_trigger` - Update triggers
- `delete_trigger` - Remove triggers
- `find_va_agent_execution_plan` - Find execution plans for Virtual Agent conversations

### 📊 Performance Analysis
Analyze AI Agent conversation performance:
- `analyze_conversation_performance` - Full bottleneck analysis: LLM time, tool execution, user wait time
- `compare_conversation_performance` - Compare 2–10 conversations side-by-side
- `analyze_conversation_trends` - Track performance trends over time

### 🔍 Execution Monitoring
Monitor and debug agent executions:
- `query_execution_plans` - List agent execution runs
- `query_execution_tasks` - View individual task steps
- `query_tool_executions` - Track tool calls within executions
- `get_execution_details` - Full execution details with timeline
- `query_generative_ai_logs` - View AI/LLM request logs
- `query_generative_ai_logs_detailed` - Full LLM request/response details
- `query_agent_messages` - View conversation message history

### 🌊 Flow Designer Debugging
Debug ServiceNow Flow Designer workflows:
- `query_flow_contexts` - Flow execution summaries
- `query_flow_logs` - Detailed step-by-step flow logs
- `get_flow_context_details` - Complete execution details with metrics
- `query_flow_reports` - Flow performance reports (success rate, avg duration)

### 🎫 Incident Management
Full incident lifecycle management:
- `create_incident` - Create incidents with caller auto-lookup and validation
- `update_incident` - Update state, work notes, and fields
- `resolve_close_incident` - Resolve/close with resolution code
- `get_incident_details` - Rich retrieval with related records and history
- `list_incidents` - Pre-built filters (critical, unassigned, my_open, breached SLA)

### 📎 Attachment Management
- `upload_attachment` - Attach files to any record (base64, <5KB recommended)
- `download_attachment` - Retrieve attachment content
- `list_attachments` - List attachments by record or filename
- `delete_attachment` - Remove attachments

### ✅ Approvals
- `list_pending_approvals` - Query approvals by state, approver, or source table
- `approve_record` - Approve with comments
- `reject_record` - Reject with mandatory reason
- `get_approval_details` - Full approval details with source record

### ✅ Pre-Flight Validation
Prevent incomplete record creation:
- `get_form_mandatory_fields` - Discover ALL mandatory fields including UI Policy-enforced fields
- `validate_record_data` - Validate data before submission (use before create_incident, order_catalog_item, etc.)

### 🛒 Service Catalog
End-to-end catalog ordering:
- `list_catalog_items` - List active catalog items with pricing
- `search_catalog_items` - Search by keywords across name, description
- `get_catalog_item_details` - Full item metadata, variables, UI policies
- `lookup_reference_field` - Query reference tables for field options
- `get_user_context` - Get user sys_id for `requested_for` parameter
- `order_catalog_item` - Submit orders with variables
- `get_request_status` - Track order status (REQ/RITM numbers)
- `list_my_requests` - View a user's catalog requests

### 📦 App & Plugin Management
- `snow_app_info` - View installed applications and versions
- `snow_app_install` - Install or upgrade an application
- `snow_app_install_status` - Check installation progress
- `snow_plugin_activate` - Activate or deactivate a plugin

### 🔧 System & Debugging
- `snow_run_script` - Execute server-side JavaScript
- `execute_scripted_rest_api` - Call any Scripted REST API (escape hatch for extensibility)
- `query_system_properties` - Query instance configuration settings
- `query_syslog` - Search system error logs
- `health_check` - Connection health check with role/permission verification

### 🔍 AI Search
- `search_servicenow_knowledge` - Natural language knowledge search via AI Search
- `list_ai_search_profiles` - View available search configurations

### 📋 Generic Table Operations
- `snow_query` - Query records from any table
- `snow_get_record` - Get a single record by sys_id
- `snow_create_record` - Create records
- `snow_update_record` - Update records
- `snow_delete_record` - Delete records
- `snow_count` - Count records matching a query
- `snow_aggregate` - Aggregate queries (sum, avg, group by)
- `snow_table_schema` - Get table field definitions
- `snow_test_connection` - Test connectivity

---

## MCP Resources

Access ServiceNow data as context in conversations:

| URI | Description |
|-----|-------------|
| `snow://schema/{table}` | Table schema with all field definitions |
| `snow://record/{table}/{sys_id}` | Full record content formatted as markdown |
| `snow://tables` | Reference list of common ServiceNow tables |

---

## MCP Prompts

Reusable guided workflows:

| Prompt | Description |
|--------|-------------|
| `analyze_agent` | Step-by-step guide for analyzing AI Agent performance |
| `troubleshoot_workflow` | Structured workflow debugging process |
| `create_incident` | Guided incident creation collecting all required fields |
| `order_catalog_item` | Service Catalog ordering workflow |

---

## Security Notes

- Never commit your `.env` file to version control
- Use service accounts with minimum required permissions
- Consider OAuth instead of basic auth for production use
