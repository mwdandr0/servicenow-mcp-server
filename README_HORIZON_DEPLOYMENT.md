# Horizon Deployment Instructions

## Configuration

**Entrypoint:** `server.py:mcp`

Point directly to the main server file. Horizon will automatically handle:
- Loading the FastMCP instance
- Running it with HTTP transport
- Managing the async event loop

## Steps

1. In Horizon settings, set entrypoint to: `server.py:mcp`
2. Deploy
3. Your server will be available at: `https://wicked-lavender-toucan.fastmcp.app/mcp`

## Environment Variables

These are already configured in Horizon:
- `SERVICENOW_INSTANCE`
- `SERVICENOW_USERNAME`  
- `SERVICENOW_PASSWORD`

## Notes

- Don't use `horizon_entrypoint.py` - it's not needed
- Horizon handles all the HTTP/ASGI setup automatically
- The asyncio event loop is managed by Horizon's infrastructure
