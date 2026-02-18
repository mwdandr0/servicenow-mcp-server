"""
Horizon-specific entrypoint for ServiceNow MCP Server

This entrypoint is designed specifically for Prefect Horizon deployments.
It simply imports and exports the mcp instance without trying to run it.
"""

# Import the mcp server instance from server.py
from server import mcp

# Horizon will handle running the server
# No need to call mcp.run() here - that's what causes the asyncio conflict

__all__ = ['mcp']
