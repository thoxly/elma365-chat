from typing import Dict, Any, Optional
import aiohttp
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for interacting with MCP server."""
    
    def __init__(self, base_url: Optional[str] = None, transport: str = "http"):
        """
        Initialize MCP client.
        
        Args:
            base_url: Base URL for HTTP transport (default: from settings)
            transport: Transport type ("http" or "stdin")
        """
        self.transport = transport
        if base_url:
            self.base_url = base_url
        else:
            # Default to local FastAPI server
            self.base_url = "http://localhost:8000"
    
    async def list_tools(self) -> list:
        """List all available tools."""
        if self.transport == "http":
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/mcp/tools/list") as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    return data.get("tools", [])
        else:
            raise NotImplementedError("stdin transport not implemented for client")
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool.
        
        Args:
            name: Tool name (e.g., "elma365.search_docs")
            arguments: Tool arguments
        
        Returns:
            Tool execution result
        """
        if self.transport == "http":
            async with aiohttp.ClientSession() as session:
                payload = {
                    "name": name,
                    "arguments": arguments
                }
                async with session.post(
                    f"{self.base_url}/mcp/tools/call",
                    json=payload
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    return data
        else:
            raise NotImplementedError("stdin transport not implemented for client")

