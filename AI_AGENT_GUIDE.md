# ServiceNow AI Agent Builder Guide

This enhanced MCP server includes comprehensive tools for building, managing, and troubleshooting ServiceNow AI Agents.

## 🤖 What's New - AI Agent Capabilities

### 1. AI Agent Configuration Tools
Create and manage AI Agents programmatically:

- **`list_ai_agents`** - List all AI agents in your instance
- **`get_agent_details`** - Get complete details about a specific agent
- **`create_ai_agent`** - Create a new AI agent with custom instructions
- **`update_ai_agent`** - Update existing agent configuration
- **`delete_ai_agent`** - Remove an agent (with confirmation)
- **`clone_ai_agent`** - Clone an existing agent with all its tools

### 2. Agent Tools Management
Manage tools that agents can use:

- **`list_agent_tools`** - List all available tools for agents
- **`add_tool_to_agent`** - Assign a tool to an agent
- **`remove_tool_from_agent`** - Remove a tool from an agent
- **`create_tool`** - Create a new custom tool for agents

### 3. Agentic Workflows
Create orchestrated workflows:

- **`list_agentic_workflows`** - List all workflows (use cases)
- **`create_agentic_workflow`** - Create a new workflow
- **`update_agentic_workflow`** - Update workflow configuration

### 4. Execution & Troubleshooting
Debug and monitor agent executions:

- **`query_execution_plans`** - Track overall workflow runs
- **`query_execution_tasks`** - Monitor individual tool tasks
- **`query_generative_ai_logs`** - View AI/LLM interactions
- **`query_generative_ai_logs_detailed`** - Get full AI log details
- **`query_agent_messages`** - View agent conversation history
- **`get_execution_plan_full_details`** - Complete execution analysis

### 5. Flow Designer Debugging
Debug Flow Designer actions:

- **`query_flow_contexts`** - Flow execution summaries
- **`query_flow_logs`** - Detailed flow logs
- **`get_flow_context_details`** - Complete flow execution details
- **`query_flow_reports`** - Flow runtime states

### 6. System Debugging
General debugging tools:

- **`query_syslog`** - Query ServiceNow system logs
- **`cleanup_agent_configs`** - Clean up duplicate agent configs

## 📚 How to Build an AI Agent

### Step 1: Create an AI Agent

```
Ask Claude: "Create a new AI agent named 'Incident Resolver' with role 'Incident management specialist' and description 'Helps resolve incidents quickly'"
```

The agent needs detailed instructions. Example:

```
list_of_steps = '''
You are an incident resolution specialist. Your job is to:

1. Analyze the incident details thoroughly
2. Check for similar past incidents and their resolutions
3. Identify the affected configuration items
4. Suggest resolution steps based on:
   - Past incident patterns
   - Knowledge base articles
   - Standard operating procedures
5. Provide clear, actionable recommendations
6. Update the incident with your findings

Always be thorough, accurate, and follow ITIL best practices.
'''
```

### Step 2: Add Tools to Your Agent

First, list available tools:
```
Ask Claude: "List all available agent tools"
```

Then add relevant tools:
```
Ask Claude: "Add the tool [tool_sys_id] to agent [agent_sys_id]"
```

Common useful tools:
- **Record operations** - Query/update incidents, users, etc.
- **Flow actions** - Execute custom Flow Designer flows
- **Search retrieval** - Search knowledge bases
- **Script tools** - Custom JavaScript logic

### Step 3: Create an Agentic Workflow

```
Ask Claude: "Create an agentic workflow named 'Auto Incident Resolution' that uses the Incident Resolver agent"
```

Workflow instructions should define:
- When the workflow triggers
- What the goal is
- How agents should collaborate (if multiple)
- Success criteria

### Step 4: Test Your Agent

```
Ask Claude: "Show me recent execution plans for the Incident Resolver agent"
```

### Step 5: Debug Issues

If your agent has problems:

1. **Check execution plans**: See if workflows are running
   ```
   Ask Claude: "Query execution plans from the last 60 minutes"
   ```

2. **View AI logs**: See what the LLM is doing
   ```
   Ask Claude: "Show detailed generative AI logs"
   ```

3. **Check agent messages**: View conversation history
   ```
   Ask Claude: "Query agent messages for execution plan [sys_id]"
   ```

4. **Review flow logs**: If using Flow Designer tools
   ```
   Ask Claude: "Query flow contexts from the last hour"
   ```

## 🎯 Example Use Cases

### Use Case 1: Incident Auto-Assignment Agent

**Goal**: Automatically assign incidents to the right team based on category and urgency

**Tools Needed**:
- Query incident table
- Query assignment group table
- Update incident record

**Instructions**:
```
Analyze the incoming incident:
1. Check the category and subcategory
2. Check the urgency and impact
3. Look up the appropriate assignment group based on category
4. Consider team workload and availability
5. Assign the incident to the best group
6. Add a work note explaining the assignment logic
```

### Use Case 2: Knowledge Article Suggester

**Goal**: Suggest relevant knowledge articles for incidents

**Tools Needed**:
- Query incident table
- Search knowledge base
- Update incident record

**Instructions**:
```
For each incident:
1. Extract key terms from the short description and description
2. Search the knowledge base for relevant articles
3. Rank articles by relevance
4. Add the top 3 articles as recommendations in work notes
5. If confidence is high, suggest closing with a solution
```

### Use Case 3: Change Risk Assessor

**Goal**: Assess risk level for change requests

**Tools Needed**:
- Query change request table
- Query CMDB for affected CIs
- Query past change history
- Update change record

**Instructions**:
```
Assess change risk by:
1. Analyzing affected configuration items
2. Checking CI criticality and dependencies
3. Reviewing historical changes to similar CIs
4. Evaluating the change window timing
5. Considering any recent incidents on affected CIs
6. Calculating a risk score (1-5)
7. Providing detailed risk assessment notes
```

## 🔍 Troubleshooting Tips

### Agent Not Executing

1. Check if agent is active:
   ```
   Ask Claude: "Get details for agent [name or sys_id]"
   ```

2. Verify workflow is active and has triggers

3. Check execution plan logs for errors

### Agent Giving Wrong Results

1. Review agent instructions - be more specific
2. Check AI logs to see what the LLM is seeing/thinking
3. Verify the agent has access to correct tools
4. Ensure tool inputs are properly defined

### Performance Issues

1. Check token usage in generative AI logs
2. Reduce the number of tools if too many
3. Optimize agent instructions for clarity
4. Consider setting max_automatic_executions limits

### Debugging Flow Actions

If an agent is calling Flow Designer actions:

1. Query flow contexts to see execution status
2. Check flow logs for detailed error messages
3. Use get_flow_context_details for complete analysis
4. Review flow report chunks for runtime data

## 🛠️ Best Practices

### Writing Good Agent Instructions

1. **Be Specific**: Clear, step-by-step instructions work best
2. **Define Success**: Explain what a good outcome looks like
3. **Handle Errors**: Tell the agent what to do if tools fail
4. **Set Boundaries**: Define what the agent should NOT do
5. **Use Examples**: Include example scenarios when helpful

### Tool Configuration

1. **Start Small**: Begin with 2-3 essential tools
2. **Test Incrementally**: Add tools one at a time
3. **Define Inputs**: Always specify required tool inputs
4. **Set Limits**: Use max_automatic_executions to prevent loops

### Monitoring & Maintenance

1. **Regular Reviews**: Check execution logs weekly
2. **Token Monitoring**: Watch AI log token usage
3. **Performance Metrics**: Track success rates
4. **Update Instructions**: Refine based on actual behavior

## 📊 Key Tables Reference

- **sn_aia_agent** - AI Agent definitions
- **sn_aia_agent_config** - Agent configuration settings
- **sn_aia_tool** - Available tools
- **sn_aia_agent_tool_m2m** - Agent-tool associations
- **sn_aia_usecase** - Agentic workflows
- **sn_aia_execution_plan** - Workflow execution tracking
- **sn_aia_execution_task** - Individual tool task tracking
- **sn_aia_message** - Agent conversation history
- **sys_generative_ai_log** - AI/LLM interaction logs
- **sys_flow_context** - Flow Designer execution contexts
- **sys_flow_log** - Flow Designer detailed logs

## 🚀 Quick Start Commands

Try these commands in Claude Desktop after restarting:

```
# List existing agents
"Show me all AI agents in ServiceNow"

# Get details about a specific agent
"Get details for the Virtual Agent Routing agent"

# Create a new agent
"Create an AI agent for managing incidents"

# View recent AI activity
"Show me generative AI logs from the last hour"

# Check execution status
"Query execution plans to see what's running"

# Debug a specific execution
"Get full details for execution plan [sys_id]"
```

## 💡 Tips for Success

1. **Start with OOB Agents**: Examine out-of-box agents to learn patterns
2. **Use Templates**: Clone existing agents as starting points
3. **Test in Sub-Prod**: Always test in dev/test before production
4. **Document Everything**: Keep notes on what works
5. **Iterate**: Agents improve with refinement over time

---

**Ready to build?** Restart Claude Desktop and start creating your AI agents!
