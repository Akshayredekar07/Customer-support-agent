import asyncio
import uvicorn
import os
from pathlib import Path
from mcp_servers.common_tools import mcp as common_mcp
from mcp_servers.atlas_tools import mcp as atlas_mcp

import sys
sys.path.append(str(Path(__file__).parent))

async def start_common_server():
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
    await asyncio.gather(
        start_common_server(),
        start_atlas_server()
    )

if __name__ == "__main__":
    asyncio.run(main())