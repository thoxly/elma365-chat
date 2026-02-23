from typing import Dict, Any, Optional
import logging
from mcp.core.registry import get_registry, ToolDefinition

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Executor for MCP tools."""
    
    def __init__(self):
        self.registry = get_registry()
    
    async def execute_tool(
        self,
        name: str,
        input_data: dict,
        db_session: Any = None
    ) -> Dict[str, Any]:
        """
        Execute a tool by name with input data.
        
        Args:
            name: Tool name
            input_data: Input data for the tool
            db_session: Database session (required for most tools)
        
        Returns:
            Tool execution result
        """
        tool = self.registry.get_tool(name)
        
        if not tool:
            raise ValueError(f"Tool '{name}' not found")
        
        try:
            # Validate input data
            # Note: Full validation should be done with Pydantic models
            # For now, we'll pass the data directly to the handler
            
            # Execute the tool handler
            if db_session:
                result = await tool.handler(input_data, db_session)
            else:
                result = await tool.handler(input_data)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": str(result) if not isinstance(result, dict) else result
                    }
                ]
            }
        
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}", exc_info=True)
            raise RuntimeError(f"Tool execution failed: {str(e)}") from e

