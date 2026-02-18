"""
Horizon-specific entrypoint for ServiceNow MCP Server

This file simply re-exports the mcp instance from server.py.
Horizon handles all the runtime configuration automatically.
"""

# Import and re-export the mcp server instance
from server import mcp

__all__ = ['mcp']
