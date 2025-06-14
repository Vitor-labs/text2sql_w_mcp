# src/client/client.py
import logging
from dataclasses import dataclass, field
from typing import Any

from google.genai import Client
from google.genai.types import Content, FunctionDeclaration, Part, Tool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


@dataclass
class Chat:
    """
    Enhanced Chat class with proper MCP tool integration
    """

    genai_client: Client
    server_params: StdioServerParameters
    messages: list[dict[str, str]] = field(
        default_factory=lambda: [
            {
                "author": "system",
                "content": (
                    "You are an expert SQL analyst assistant. Your job is to:\n"
                    "1. Translate natural language queries into SQL statements\n"
                    "2. Execute SQL queries using the available tools\n"
                    "3. Present results in clear, formatted tables\n"
                    "4. Explain your analysis when needed\n\n"
                    "Available tools:\n"
                    "- query_data: Execute SQL queries on the database"
                ),
            }
        ]
    )

    def _convert_messages_to_content(self) -> list[Content]:
        """Convert internal message format to Gemini Content format"""
        return [
            Content(
                role="user" if msg["author"] in ["system", "user"] else "model",
                parts=[Part.from_text(text=msg["content"])],
            )
            for msg in self.messages
        ]

    async def _get_available_tools(self, session: ClientSession) -> list[Tool]:
        """Fetch available tools from MCP server and convert to Gemini Tool format"""
        try:
            gemini_tools = []

            for tool in (await session.list_tools()).tools:
                # Convert MCP tool to Gemini Tool format
                gemini_tools.append(
                    Tool(
                        function_declarations=[
                            FunctionDeclaration(
                                name=tool.name,
                                description=tool.description,
                                parameters={
                                    "type": "object",
                                    "properties": tool.inputSchema.get(
                                        "properties", {}
                                    ),
                                    "required": tool.inputSchema.get("required", []),
                                },
                            )
                        ]
                    )
                )
            logger.info(f"Found {len(gemini_tools)} available tools")
            return gemini_tools

        except Exception as e:
            logger.error(f"Failed to get tools: {e}")
            return []

    async def _execute_tool_call(
        self, session: ClientSession, tool_name: str, arguments: dict[str, Any]
    ) -> str:
        """Execute a tool call through MCP"""
        try:
            logger.info(f"Executing tool: {tool_name} with args: {arguments}")
            result = await session.call_tool(tool_name, arguments)

            if result.isError:
                return f"Tool execution failed: {result.content[0].text if result.content else 'Unknown error'}"

            return (
                result.content[0].text
                if result.content
                else "Tool executed successfully (no output)"
            )
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return f"Error executing tool {tool_name}: {str(e)}"

    async def process_query(self, session: ClientSession, query: str) -> str:
        """Process user query with tool integration"""
        try:
            self.messages.append({"author": "user", "content": query})
            response = self.genai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=self._convert_messages_to_content(),
                tools=tools
                if (tools := await self._get_available_tools(session))
                else None,
            )

            assistant_response = ""

            # Handle tool calls if present
            if hasattr(response.candidates[0].content, "parts"):
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        # Execute the function call
                        func_call = part.function_call
                        tool_result = await self._execute_tool_call(
                            session, func_call.name, dict(func_call.args)
                        )

                        # Add tool result to context and get final response
                        self.messages.append(
                            {
                                "author": "tool",
                                "content": f"Tool {func_call.name} result: {tool_result}",
                            }
                        )

                        # Generate final response incorporating tool results
                        assistant_response = self.genai_client.models.generate_content(
                            model="gemini-2.0-flash",
                            contents=self._convert_messages_to_content(),
                        ).text

                    elif hasattr(part, "text"):
                        assistant_response += part.text
            else:
                assistant_response = response.text

            # Store assistant response
            self.messages.append({"author": "assistant", "content": assistant_response})

            return assistant_response

        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            logger.error(error_msg)
            self.messages.append({"author": "assistant", "content": error_msg})
            return error_msg

    async def chat_loop(self, session: ClientSession) -> None:
        """Interactive chat loop for CLI usage"""
        print("🤖 SQL Assistant ready! Type 'quit' to exit.")

        while True:
            try:
                if not (query := input("\n💬 Query: ").strip()):
                    continue

                if query.lower() in ["quit", "exit", "bye"]:
                    print("👋 Goodbye!")
                    break

                print("🔄 Processing...")
                print(f"\n🤖 Assistant: {await self.process_query(session, query)}")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

    async def run(self) -> None:
        """Run the chat client"""
        try:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    logger.info("MCP session initialized successfully")
                    await self.chat_loop(session)
        except Exception as e:
            logger.error(f"Failed to start chat: {e}")
            raise e
