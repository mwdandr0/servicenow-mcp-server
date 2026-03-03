# ServiceNow MCP Server with AI Agent Builder

A comprehensive Model Context Protocol (MCP) server for interacting with ServiceNow instances, including full support for building and managing AI Agents, debugging workflows, and troubleshooting ServiceNow integrations using the REST API with basic authentication.

## Setup Instructions

### 1. Configure Your Credentials

Copy the `.env.template` file to `.env` and fill in your ServiceNow credentials:

```bash
cp .env.template .env
```

Then edit `.env` with your actual credentials:
- `SERVICENOW_INSTANCE`: Your ServiceNow instance name (e.g., 'dev12345' or 'dev12345.service-now.com')
- `SERVICENOW_USERNAME`: Your ServiceNow username
- `SERVICENOW_PASSWORD`: Your ServiceNow password

### 2. Dependencies

The following Python packages are required:
- `mcp` - Model Context Protocol SDK
- `requests` - HTTP library for API calls
- `python-dotenv` - Environment variable management

These will be installed automatically during setup.

## Available Tools

The server provides comprehensive MCP tools for ServiceNow operations:

### 🤖 AI Agent Building & Management (NEW!)
Build, configure, and manage ServiceNow AI Agents:
- `list_ai_agents` - List all AI agents
- `get_agent_details` - Get complete agent configuration
- `create_ai_agent` - Create new AI agents with custom instructions
- `update_ai_agent` - Modify existing agents
- `delete_ai_agent` - Remove agents
- `clone_ai_agent` - Clone agents with all tools
- `list_agent_tools` - View available tools for agents
- `add_tool_to_agent` - Assign tools to agents
- `remove_tool_from_agent` - Remove tools from agents
- `create_tool` - Create custom tools

### 🔄 Agentic Workflows
Orchestrate multi-agent workflows:
- `list_agentic_workflows` - List all workflows (use cases)
- `create_agentic_workflow` - Create new workflows
- `update_agentic_workflow` - Update workflow configuration

### 🔍 Execution & Troubleshooting
Debug and monitor AI Agent executions:
- `query_execution_plans` - Track workflow runs
- `query_execution_tasks` - Monitor tool tasks
- `query_generative_ai_logs` - View AI/LLM logs
- `query_generative_ai_logs_detailed` - Full AI log details
- `query_agent_messages` - View conversation history
- `get_execution_plan_full_details` - Complete execution analysis

### 📊 **Performance Analysis (NEW!)**
Comprehensive conversation performance analysis tools (mimics Chrome extension):
- `analyze_conversation_performance` - Load ALL tables for a conversation and identify bottlenecks
- `compare_conversation_performance` - Compare 2-10 conversations side-by-side
- `analyze_conversation_trends` - Track performance over time, detect degradation

**See [PERFORMANCE_ANALYSIS_GUIDE.md](PERFORMANCE_ANALYSIS_GUIDE.md) for detailed usage examples**

### 🌊 Flow Designer Debugging
Debug Flow Designer actions:
- `query_flow_contexts` - Flow execution summaries
- `query_flow_logs` - Detailed flow logs
- `get_flow_context_details` - Complete flow details
- `query_flow_reports` - Flow runtime states

### 🛠️ System Debugging
General debugging tools:
- `query_syslog` - Query ServiceNow system logs
- `cleanup_agent_configs` - Clean up duplicate configs

### 🔍 AI Search (NEW!)
Natural language search powered by ServiceNow AI Search:
- `search_servicenow_knowledge` - Search using natural language queries
- `list_ai_search_profiles` - View available search configurations

**Note:** Requires Scripted REST API setup in ServiceNow. See [AI_SEARCH_QUICKSTART.md](AI_SEARCH_QUICKSTART.md)

### 📊 Generic Table Operations
Standard CRUD operations:
- `snow_query` - Query records from any table
- `snow_get_record` - Get a single record by sys_id
- `snow_create_record` - Create new records
- `snow_update_record` - Update existing records
- `snow_delete_record` - Delete records
- `snow_aggregate` - Perform aggregate queries

### 🛒 Service Catalog Ordering (NEW!)
Complete end-to-end catalog ordering workflow:

**Discovery Tools:**
- `list_catalog_items` - List all active catalog items with pricing and categories
- `search_catalog_items` - Search catalog items by keywords (multi-field search)
- `get_catalog_item_details` - Get complete item metadata including variables, pricing, UI policies
- `lookup_reference_field` - Query reference tables for dropdown/lookup options
- `get_user_context` - Get user details for auto-populating order fields

**Order Submission Tools:**
- `order_catalog_item` - Submit catalog orders with variables
- `get_request_status` - Track order fulfillment and approval status
- `list_my_requests` - View user's catalog requests

**Features:**
- Full catalog item discovery with pricing information
- Variable metadata (types, questions, choices, mandatory fields)
- UI policy support (conditional field logic)
- Reference field lookups with filtering
- Multi-row variable set support
- Record producer support
- Complete order submission and tracking
- Multi-field search across name, short_description, and description

### 🔧 **Platform Utilities (NEW!)**
Essential tools for instance administration and debugging:
- `query_system_properties` - Query instance configuration settings (timeouts, feature flags, etc.)
- `health_check` - Comprehensive connection health check with role/permission verification
- `execute_scripted_rest_api` - **ESCAPE HATCH** - Execute ANY Scripted REST API for infinite extensibility

**See [ERROR_HANDLING_STANDARD.md](ERROR_HANDLING_STANDARD.md) for standardized error response format**

### 🎫 **ITSM Core Tools (NEW!)**
Purpose-built tools for incident, attachment, and approval management:

**Incident Management:**
- `create_incident` - Create incidents with auto-lookup (caller, assignment group) and validation
- `update_incident` - Update with state transition validation and work notes
- `resolve_close_incident` - Combined resolve/close with mandatory resolution code
- `get_incident_details` - Rich retrieval including related records and history
- `list_incidents` - Pre-built filters (critical, unassigned, my_open, breached SLA)

**Attachment Management:**
- `upload_attachment` - Attach files to any record (base64 encoding)
- `download_attachment` - Retrieve attachment content
- `list_attachments` - List/search attachments by record or filename
- `delete_attachment` - Remove attachments

**Approval Management:**
- `list_pending_approvals` - Query approvals by state, approver, or source table
- `approve_record` - Approve with comments
- `reject_record` - Reject with mandatory reason
- `get_approval_details` - Full approval details with source record

### ✅ **Pre-Flight Validation (NEW!)**
Dynamic validation tools to prevent incomplete record creation:

**Mandatory Field Discovery:**
- `get_form_mandatory_fields` - Discover ALL mandatory fields including UI Policy-enforced fields
  - Queries sys_dictionary for database-level mandatory fields
  - Queries sys_ui_policy and sys_ui_policy_action for form-level requirements
  - Returns complete list with conditions and sources
  - Solves the "blind spot" where UI Policies make fields mandatory but Table API doesn't know

**Pre-Flight Validation:**
- `validate_record_data` - Validate record data BEFORE API submission
  - Checks dictionary mandatory fields (always required)
  - Checks UI Policy mandatory fields (may be conditional)
  - Returns validation results with missing fields and recommendations
  - Prevents API failures from missing required fields
  - Use BEFORE create_incident, order_catalog_item, or any snow_create_record

**Why These Matter:**
ServiceNow has 3 layers of validation that can cause silent failures:
1. **Dictionary mandatory** - Enforced by database
2. **UI Policy mandatory** - Enforced by form (invisible to REST API)
3. **Business rules** - Custom validation logic

The Table API only validates layer 1, meaning records can be created via API with missing data that would be caught in the UI. These tools expose all 3 layers before you submit.

## 📚 AI Agent Builder Guide

See **[AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)** for a complete guide on building ServiceNow AI Agents, including:
- Step-by-step agent creation
- Tool configuration
- Workflow orchestration
- Debugging techniques
- Best practices
- Example use cases

## Security Notes

- Never commit your `.env` file to version control
- Use service accounts with appropriate permissions
- Consider using OAuth instead of basic auth for production use
