"""Flexible agent that works with task templates."""
from typing import Dict, Any, Optional
from app.database.models import TaskTemplate
from mcp.client import MCPClient
from app.services.knowledge_rules_service import KnowledgeRulesService
import aiohttp
import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class FlexibleAgent:
    """Flexible agent working with templates."""
    
    def __init__(
        self,
        template: TaskTemplate,
        mcp_client: MCPClient,
        rules_service: KnowledgeRulesService
    ):
        self.template = template
        self.mcp_client = mcp_client
        self.rules_service = rules_service
    
    async def execute(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Execute task according to template."""
        # 1. Load rules from DB
        rules_content = {}
        if self.template.knowledge_rules:
            for rule_type in self.template.knowledge_rules:
                rule = await self.rules_service.get_rule(rule_type)
                if rule:
                    rules_content[rule_type] = rule["content"]
        
        # 2. Build prompt from template + rules + context
        system_prompt = self.template.system_prompt or ""
        if rules_content:
            rules_text = "\n\n".join([
                f"## {rule_type}\n{self._format_rule_content(content)}"
                for rule_type, content in rules_content.items()
            ])
            system_prompt = f"{system_prompt}\n\n## Правила ELMA365:\n{rules_text}"
        
        try:
            user_prompt = self.template.prompt.format(
                user_input=user_input,
                context=json.dumps(context or {}, ensure_ascii=False, indent=2)
            )
        except KeyError:
            user_prompt = f"{self.template.prompt}\n\nВвод пользователя:\n{user_input}"
        
        # 3. Execute via LLM with MCP tools access
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Use available tools
        available_tools = []
        if self.template.tools:
            mcp_tools = await self.mcp_client.list_tools()
            available_tools = [
                tool for tool in mcp_tools
                if tool.get("name") in self.template.tools
            ]
        
        # Call LLM (using DeepSeek by default)
        response = await self._call_llm(messages, available_tools)
        
        return response
    
    def _format_rule_content(self, content: Dict[str, Any]) -> str:
        """Format rule content for prompt."""
        if "text" in content:
            return content["text"]
        elif "yaml" in content:
            import yaml
            return yaml.dump(content["yaml"], allow_unicode=True, default_flow_style=False)
        else:
            return str(content)
    
    async def _call_llm(
        self,
        messages: list,
        tools: Optional[list] = None
    ) -> str:
        """Call LLM API."""
        payload = {
            "model": settings.DEEPSEEK_MODEL,
            "messages": messages,
            "temperature": 0.7
        }
        
        if tools:
            payload["tools"] = tools
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"
            }
            
            async with session.post(
                settings.DEEPSEEK_API_URL,
                json=payload,
                headers=headers
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                
                # Extract response content
                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                
                # Handle tool calls if any
                if "tool_calls" in message:
                    # Execute tool calls and continue conversation
                    tool_results = []
                    for tool_call in message["tool_calls"]:
                        tool_name = tool_call["function"]["name"]
                        tool_args = json.loads(tool_call["function"]["arguments"])
                        result = await self.mcp_client.call_tool(tool_name, tool_args)
                        tool_results.append({
                            "role": "tool",
                            "name": tool_name,
                            "content": json.dumps(result, ensure_ascii=False)
                        })
                    
                    # Add tool results and get final response
                    messages.append(message)
                    messages.extend(tool_results)
                    return await self._call_llm(messages)
                
                return message.get("content", "")
