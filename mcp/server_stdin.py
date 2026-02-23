#!/usr/bin/env python3
"""
MCP server via stdin/stdout (JSON-RPC 2.0).
This server reads JSON-RPC requests from stdin and writes responses to stdout.
"""
import sys
import json
import asyncio
import logging
from typing import Dict, Any, Optional

from mcp.core.registry import get_registry, register_all_tools
from mcp.core.executor import ToolExecutor

# Setup logging to stderr (stdout is for JSON-RPC)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Initialize tools
register_all_tools()

executor = ToolExecutor()


class MCPServer:
    """MCP server using stdin/stdout transport."""
    
    def __init__(self):
        self.registry = get_registry()
        self.executor = executor
        self.initialized = False
    
    async def handle_request(self, request: Dict[str, Any], db_session=None) -> Dict[str, Any]:
        """Handle a JSON-RPC request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                result = await self.handle_initialize(params)
                self.initialized = True
            elif method == "tools/list":
                result = await self.handle_tools_list()
            elif method == "tools/call":
                result = await self.handle_tools_call(params, db_session)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
        
        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
    
    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "elma365-mcp-server",
                "version": "1.0.0"
            }
        }
    
    async def handle_tools_list(self) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = self.registry.list_tools()
        return {"tools": tools}
    
    async def handle_tools_call(self, params: Dict[str, Any], db_session) -> Dict[str, Any]:
        """Handle tools/call request."""
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not name:
            raise ValueError("Tool name is required")
        
        result = await self.executor.execute_tool(
            name=name,
            input_data=arguments,
            db_session=db_session
        )
        
        return result
    
    async def run(self):
        """Run the MCP server, reading from stdin and writing to stdout."""
        logger.info("MCP server started (stdin/stdout)")
        
        # Note: For stdin/stdout mode, we typically can't use async database sessions
        # This is a limitation - in production, you might need a different approach
        # For now, we'll handle requests without DB session in stdin mode
        
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    request = json.loads(line)
                    response = await self.handle_request(request, db_session=None)
                    print(json.dumps(response), flush=True)
                
                except json.JSONDecodeError as e:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": f"Parse error: {str(e)}"
                        }
                    }
                    print(json.dumps(error_response), flush=True)
        
        except KeyboardInterrupt:
            logger.info("MCP server stopped")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            sys.exit(1)


async def main():
    """Main entry point."""
    server = MCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())

