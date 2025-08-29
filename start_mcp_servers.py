#!/usr/bin/env python3
"""
Start MCP Servers for Langie Agent
This script starts the COMMON and ATLAS MCP servers on separate ports.
"""

import asyncio
import uvicorn
import os
import sys
from pathlib import Path


from mcp_servers.common_tools import mcp as common_mcp
from mcp_servers.atlas_tools import mcp as atlas_mcp


sys.path.append(str(Path(__file__).parent))

async def start_common_server():
    """Start the COMMON MCP server on port 5001."""
    from mcp_servers.common_tools import mcp as common_mcp
    
    print("Starting COMMON MCP Server on port 5001...")
    
    app = common_mcp.http_app()
    
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=5001,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


async def start_atlas_server():
    """Start the ATLAS MCP server on port 5002."""
    
    print("Starting ATLAS MCP Server on port 5002...")

    app = atlas_mcp.http_app()
    
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=5002,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Start both MCP servers concurrently."""
    print("Starting MCP Servers for Agent...")
    print("COMMON Server: http://localhost:5001/mcp/")
    print("ATLAS Server: http://localhost:5002/mcp/")
    print("Starting servers...")
    

    await asyncio.gather(
        start_common_server(),
        start_atlas_server()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nMCP Servers stopped by user.")
    except Exception as e:
        print(f"Error starting MCP servers: {e}")
        sys.exit(1)
