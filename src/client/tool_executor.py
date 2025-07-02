# src/client/tool_executor.py
import traceback
from typing import Any

from mcp import ClientSession

from client.interfaces import ToolExecutor
from config.logger import logger


class MCPToolExecutor(ToolExecutor):
    """MCP-based tool executor implementation."""

    def __init__(self, session: ClientSession) -> None:
        """Initialize with MCP session."""
        self._session = session

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool through MCP session."""
        try:
            logger.info(f"Executing tool: {tool_name} with args: {arguments}")
            result = await self._session.call_tool(tool_name, arguments)

            if not result.content:
                return "Tool executed successfully (no output)"

            content_item = result.content[0]
            if hasattr(content_item, "text"):
                logger.info(f"Tool {tool_name} executed successfully")
                return content_item.text
            else:
                return f"Tool {tool_name} executed but returned unexpected content type"

        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {str(e)}"
            logger.error(
                f"{error_msg}\nTool execution traceback: {traceback.format_exc()}"
            )
            return error_msg
