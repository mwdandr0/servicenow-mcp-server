"""
Horizon-specific entrypoint for ServiceNow MCP Server

This entrypoint exports an ASGI application for Horizon deployment.
Horizon runs MCP servers over HTTP using ASGI, not stdio.
"""

# Import the mcp server instance from server.py
from server import mcp

# Export ASGI app for Horizon to run
# This uses HTTP transport instead of stdio, avoiding asyncio conflicts
app = mcp.http_app()

__all__ = ['app']
