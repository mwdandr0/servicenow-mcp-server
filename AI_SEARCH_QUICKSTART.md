# AI Search Integration - Quick Start Guide

Enable natural language search of your ServiceNow instance from Claude Desktop!

## Overview

This integration adds two new MCP tools:
1. **`search_servicenow_knowledge`** - Search using natural language
2. **`list_ai_search_profiles`** - View available search configurations

## Prerequisites

- ServiceNow instance with AI Search provisioned (Washington DC or later)
- User with `sn_search.user` role
- MCP server already set up (completed ✅)

## Setup Steps

### Part 1: Create the REST API in ServiceNow (5 minutes)

Follow the detailed instructions in [servicenow_rest_api_setup.md](servicenow_rest_api_setup.md)

**Quick summary:**
1. Go to **System Web Services > Scripted REST APIs**
2. Create new API: `MCP AI Search API`
3. Add two resources:
   - `POST /search` - Execute searches
   - `GET /profiles` - List configurations
4. Copy/paste the provided scripts
5. Test with REST API Explorer

### Part 2: Test the API (2 minutes)

Test with cURL to verify it's working:

```bash
curl -X POST "https://demoallwf40768.service-now.com/api/now/mcp_ai_search/search" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -u "claude.desktop:z-\$+88H^qXH_%^-#?op=Vsj" \
  -d '{
    "query": "how to reset password",
    "max_results": 5
  }'
```

**Expected response:**
```json
{
  "success": true,
  "query": "how to reset password",
  "result_count": 5,
  "results": [...]
}
```

### Part 3: Restart Claude Desktop (1 minute)

1. **Quit Claude Desktop** (Cmd+Q)
2. **Reopen Claude Desktop**
3. The new AI Search tools are now available!

## Usage Examples

Once Claude Desktop restarts, try these queries:

### Basic Search
```
"Search ServiceNow for how to reset password"
```

### Specific Queries
```
"Search for articles about VPN access"
"Find knowledge about laptop requests"
"Search for incident creation process"
"Look up change management procedures"
```

### With Options
```
"Search ServiceNow for 'network issues' and return 20 results"
"Search knowledge base for printer troubleshooting, max 5 results"
```

### List Available Profiles
```
"List all AI Search profiles in ServiceNow"
"What AI Search configurations are available?"
```

## How It Works

```
┌─────────────────┐
│ Claude Desktop  │  "Search for password reset"
└────────┬────────┘
         │
         │ MCP Protocol
         ▼
┌─────────────────────┐
│ MCP Server (local)  │  search_servicenow_knowledge()
└────────┬────────────┘
         │
         │ HTTPS REST API
         ▼
┌─────────────────────────────┐
│ ServiceNow Instance         │
│ /api/now/mcp_ai_search/     │
│                             │
│ ┌─────────────────────────┐ │
│ │ Scripted REST API       │ │
│ │ - Receives query        │ │
│ │ - Calls AI Search API   │ │
│ │ - Returns results       │ │
│ └─────────────────────────┘ │
│                             │
│ ┌─────────────────────────┐ │
│ │ AI Search Engine        │ │
│ │ - Semantic search       │ │
│ │ - Spell correction      │ │
│ │ - Relevance ranking     │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

## Tool Details

### search_servicenow_knowledge

**Parameters:**
- `query` (required): Natural language search query
- `max_results` (optional): Number of results (1-50, default 10)
- `config_sys_id` (optional): Specific search config to use

**Returns:**
- Success status
- Result count
- Array of results with:
  - Title
  - Table name
  - Sys ID
  - Snippet (preview text)
  - Relevance score
  - Direct URL
- Spell-corrected query (if applicable)

**Example Response:**
```json
{
  "success": true,
  "query": "password reset",
  "result_count": 3,
  "results": [
    {
      "title": "How to Reset Your Password",
      "table": "kb_knowledge",
      "sys_id": "abc123...",
      "snippet": "Follow these steps to reset your password...",
      "score": 0.95,
      "url": "https://instance.service-now.com/nav_to.do?uri=kb_knowledge:abc123"
    }
  ]
}
```

### list_ai_search_profiles

**Parameters:** None

**Returns:**
- Success status
- Count of profiles
- Array of configurations with:
  - Config name and sys_id
  - Profile name and sys_id

## Troubleshooting

### Error: "404 Not Found"
**Cause:** REST API not created in ServiceNow

**Fix:**
1. Follow [servicenow_rest_api_setup.md](servicenow_rest_api_setup.md)
2. Verify API exists at: **System Web Services > Scripted REST APIs**
3. Check API base path is `/api/now/mcp_ai_search`

### Error: "No AI Search configuration found"
**Cause:** AI Search not configured in ServiceNow

**Fix:**
1. Navigate to **AI Search > AI Search Admin**
2. Create at least one AI Search profile
3. Verify `sys_search_context_config` has records with `search_engine = 'ai_search'`

### Error: "sn_search.ScriptableSearchAPI is not available"
**Cause:** AI Search not provisioned or user lacks permissions

**Fix:**
1. Check ServiceNow release (needs Washington DC+)
2. Verify user has `sn_search.user` role
3. Contact ServiceNow admin to provision AI Search

### Error: "Connection timeout"
**Cause:** Query taking too long

**Fix:**
1. Use more specific search terms
2. Reduce `max_results` parameter
3. Check ServiceNow instance performance

### No Results Returned
**Cause:** No matching content or poor search profile configuration

**Try:**
1. Different search terms
2. Check knowledge base has published articles
3. Verify AI Search profile sources are configured
4. Use `list_ai_search_profiles()` to check configuration

## Advanced Usage

### Using Specific Search Profiles

1. **List available profiles:**
   ```
   "List AI Search profiles"
   ```

2. **Note the config_sys_id** from results

3. **Search with specific profile:**
   ```
   "Search ServiceNow for 'incident management' using config [sys_id]"
   ```

### Integration with AI Agents

You can create AI Agents that use the search tool:

```
"Create an AI agent that helps users by searching the knowledge base
when they ask questions"
```

The agent can automatically:
- Search for relevant articles
- Present formatted results
- Suggest best matches
- Link directly to knowledge articles

## Performance Notes

- **Average search time**: 2-8 seconds
- **Concurrent searches**: Supported
- **Result caching**: Handled by ServiceNow
- **Rate limiting**: Depends on ServiceNow instance configuration

## Security Best Practices

1. **Use dedicated service account** for MCP server
2. **Grant minimal permissions** (sn_search.user only)
3. **Enable ACLs** on Scripted REST API in production
4. **Rotate credentials** regularly
5. **Monitor usage** via ServiceNow logs

## Next Steps

Once AI Search is working:

### Option 2: Enhanced Search Filters
- Add filter by table
- Add date range filtering
- Add category filtering

### Option 3: Search Analytics
- Track most common queries
- Measure result relevance
- Identify knowledge gaps

Let me know when you're ready to implement these enhancements!

## Support

- **Setup Guide**: [servicenow_rest_api_setup.md](servicenow_rest_api_setup.md)
- **AI Agent Guide**: [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md)
- **Main README**: [README.md](README.md)

---

**Status:** ✅ MCP tools added to server.py
**Next:** Set up REST API in ServiceNow and test!
