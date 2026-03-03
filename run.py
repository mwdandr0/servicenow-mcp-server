#!/usr/bin/env python3
"""
Entrypoint for ServiceNow MCP Server

This file handles starting the MCP server in different environments:
- Local development: Creates its own asyncio event loop
- Horizon/Prefect: Uses existing event loop
"""

import sys
import asyncio

# Import the FastMCP server instance
from server import mcp

def main():
    """Main entrypoint that handles asyncio properly."""
    try:
        # Check if we're already in an async context
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context (Horizon), just return the mcp instance
            print("Running in async context (Horizon mode)", file=sys.stderr)
            return mcp
        except RuntimeError:
            # No running loop, we can create one (local mode)
            print("Starting in local mode with new event loop", file=sys.stderr)
            mcp.run()
    except Exception as e:
        print(f"Error starting MCP server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
