# MCP Package for Agent2
# This package contains the COMMON and ATLAS MCP servers

from .common_tools import mcp as common_mcp
from .atlas_tools import mcp as atlas_mcp

__all__ = ["common_mcp", "atlas_mcp"]
