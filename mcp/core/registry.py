from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Definition of an MCP tool."""
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    handler: Callable


class ToolRegistry:
    """Registry for MCP tools."""
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
    
    def register(
        self,
        name: str,
        description: str,
        input_schema: dict,
        output_schema: dict,
        handler: Callable
    ):
        """Register a tool."""
        tool_def = ToolDefinition(
            name=name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            handler=handler
        )
        self._tools[name] = tool_def
        logger.info(f"Registered tool: {name}")
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> list:
        """List all registered tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]
    
    def get_all_tools(self) -> Dict[str, ToolDefinition]:
        """Get all tools."""
        return self._tools.copy()


# Global registry instance
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _registry


def register_all_tools():
    """Register all MCP tools."""
    from mcp.tools import search_docs, get_doc, get_entities, find_examples, find_process_patterns
    
    # Register search_docs
    _registry.register(
        name="elma365.search_docs",
        description="Search ELMA365 documentation by query",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query string"}
            },
            "required": ["query"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {"type": "object"}
                }
            }
        },
        handler=search_docs.search_docs
    )
    
    # Register get_doc
    _registry.register(
        name="elma365.get_doc",
        description="Get a specific document by doc_id",
        input_schema={
            "type": "object",
            "properties": {
                "doc_id": {"type": "string", "description": "Document ID"}
            },
            "required": ["doc_id"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "doc": {"type": "object"}
            }
        },
        handler=get_doc.get_doc
    )
    
    # Register get_entities
    _registry.register(
        name="elma365.get_entities",
        description="Get entities from a document, optionally filtered by type",
        input_schema={
            "type": "object",
            "properties": {
                "doc_id": {"type": "string", "description": "Document ID"},
                "entity_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by entity types: headers, lists, code_blocks, examples, api, special_blocks"
                }
            },
            "required": ["doc_id"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {"type": "object"}
                }
            }
        },
        handler=get_entities.get_entities
    )
    
    # Register find_examples
    _registry.register(
        name="elma365.find_examples",
        description="Find examples in documentation by keywords",
        input_schema={
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords to search for"
                }
            },
            "required": ["keywords"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "examples": {
                    "type": "array",
                    "items": {"type": "object"}
                }
            }
        },
        handler=find_examples.find_examples
    )
    
    # Register find_process_patterns
    _registry.register(
        name="elma365.find_process_patterns",
        description="Find process patterns in documentation (согласование, поручение, регистрация, архивирование, SLA)",
        input_schema={
            "type": "object",
            "properties": {
                "pattern_type": {
                    "type": "string",
                    "description": "Pattern type: согласование, поручение, регистрация, архивирование, SLA"
                }
            },
            "required": ["pattern_type"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "patterns": {
                    "type": "array",
                    "items": {"type": "object"}
                }
            }
        },
        handler=find_process_patterns.find_process_patterns
    )
    
    logger.info(f"Registered {len(_registry._tools)} tools")

