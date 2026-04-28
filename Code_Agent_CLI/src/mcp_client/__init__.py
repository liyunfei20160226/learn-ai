"""
MCP (Model Context Protocol) 客户端模块

集成标准 MCP Servers，如 filesystem、github 等。
"""
from .client import MCPClient, MCPTool
from .manager import MCPManager, mcp_manager

__all__ = ["MCPClient", "MCPTool", "MCPManager", "mcp_manager"]
