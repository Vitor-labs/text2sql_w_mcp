# src/client/client.py
import traceback
from asyncio import TimeoutError, wait_for
from dataclasses import dataclass, field
from typing import Any

from google.genai import Client
from google.genai.types import Content, FunctionDeclaration, Part, Schema, Tool, Type
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from client.types import Message, MessageRole
from config.logger import logger


@dataclass
class Chat:
    """
    Enhanced Chat class with proper MCP tool integration
    """

    genai_client: Client
    server_params: StdioServerParameters
    tools: list[Tool] = field(default_factory=list)
    messages: list[Message] = field(
        default_factory=lambda: [
            Message(
                MessageRole.SYSTEM,
                (
                    "You are an expert SQL analyst assistant. Your job is to:\n"
                    "1. Analyze natural language queries and translate them into appropriate SQL statements\n"
                    "2. Execute SQL queries using the available tools\n"
                    "3. Present results in clear, formatted tables\n"
                    "4. Explain your analysis when needed\n"
                    "5. Always check the database schema first if you're unsure about table structure\n\n"
                    "Available tools:\n"
                    "- query_data: Execute SQL queries on the database\n"
                    "- get_schema: Get database schema information\n\n"
                    "When a user asks a question:\n"
                    "1. If you need to understand the database structure, use get_schema first\n"
                    "2. Then construct and execute the appropriate SQL query\n"
                    "3. Present the results in a clear, readable format"
                ),
            )
        ]
    )

    def _convert_messages_to_content(self) -> list[Content]:
        """Convert internal message format to Gemini Content format"""
        try:
            contents = []
            for msg in self.messages:
                if msg.role == MessageRole.SYSTEM:
                    contents.append(
                        Content(
                            role="user",
                            parts=[Part.from_text(text=f"[SYSTEM] {msg.content}")],
                        )
                    )
                elif msg.role == MessageRole.USER:
                    contents.append(
                        Content(
                            role="user",
                            parts=[Part.from_text(text=msg.content)],
                        )
                    )
                elif msg.role == MessageRole.ASSISTANT:
                    contents.append(
                        Content(
                            role="model",
                            parts=[Part.from_text(text=msg.content)],
                        )
                    )
                elif msg.role == MessageRole.TOOL:
                    contents.append(
                        Content(
                            role="model",
                            parts=[Part.from_text(text=msg.content)],
                        )
                    )
            return contents
        except Exception as e:
            logger.error(f"Error converting messages to content: {e}")
            return []

    async def _get_available_tools(self, session: ClientSession) -> list[Tool]:
        """Fetch available tools from MCP server and convert to Gemini Tool format"""
        try:
            logger.info("Requesting tools from MCP server...")
            mcp_tools = await session.list_tools()
            logger.info(f"Retrieved {len(mcp_tools.tools)} tools from MCP server")

            gemini_tools = []
            for tool in mcp_tools.tools:
                try:
                    logger.info(f"Converting tool: {tool.name}")

                    # Simple conversion - just use string parameters for now
                    gemini_tool = Tool(
                        function_declarations=[
                            FunctionDeclaration(
                                name=tool.name,
                                description=tool.description or f"Execute {tool.name}",
                                parameters=Schema(
                                    type=Type.OBJECT,
                                    properties={
                                        "sql": {
                                            "type": Type.STRING,
                                            "description": "SQL query to execute",
                                        }
                                    }
                                    if tool.name == "query_data"
                                    else {
                                        "table_name": {
                                            "type": Type.STRING,
                                            "description": "Name of the table to analyze",
                                        }
                                    }
                                    if tool.name == "analyze_table"
                                    else {},
                                    required=["sql"]
                                    if tool.name == "query_data"
                                    else ["table_name"]
                                    if tool.name == "analyze_table"
                                    else [],
                                ),
                            )
                        ]
                    )
                    gemini_tools.append(gemini_tool)
                    logger.info(f"Successfully converted tool: {tool.name}")
                except Exception as e:
                    logger.error(f"Failed to convert tool {tool.name}: {e}")
                    continue

            logger.info(f"Successfully converted {len(gemini_tools)} tools")
            return gemini_tools

        except Exception as e:
            logger.error(f"Failed to get tools: {e}")
            logger.error(f"Exception details: {traceback.format_exc()}")
            return []

    async def _execute_tool_call(
        self, session: ClientSession, tool_name: str, arguments: dict[str, Any]
    ) -> str:
        """Execute a tool call through MCP"""
        try:
            logger.info(f"Executing tool: {tool_name} with args: {arguments}")
            result = await session.call_tool(tool_name, arguments)

            if not result.content:
                return "Tool executed successfully (no output)"

            # Handle different content types
            content_item = result.content[0]
            if hasattr(content_item, "text"):
                tool_output = content_item.text
                logger.info(f"Tool {tool_name} executed successfully")
                return tool_output
            else:
                return f"Tool {tool_name} executed but returned unexpected content type"

        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Tool execution traceback: {traceback.format_exc()}")
            return error_msg

    async def process_query(self, session: ClientSession, query: str) -> str:
        """Process user query with tool integration"""
        try:
            self.messages.append(Message(MessageRole.USER, query))

            # Generate content with tools available

            response = self.genai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=self._convert_messages_to_content(),
                config={"temperature": 0.1, "max_output_tokens": 8192},
            )

            assistant_response = ""
            tool_calls_made = False

            # Handle the response
            if response.candidates and response.candidates[0].content:
                content = response.candidates[0].content

                for part in content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        # Execute the function call
                        func_call = part.function_call
                        tool_calls_made = True

                        logger.info(f"AI requested tool call: {func_call.name}")
                        tool_result = await self._execute_tool_call(
                            session, func_call.name, dict(func_call.args)
                        )

                        # Add tool result to context
                        self.messages.append(
                            Message(
                                MessageRole.TOOL,
                                f"Tool '{func_call.name}' result:\n{tool_result}",
                            )
                        )

                    elif hasattr(part, "text") and part.text:
                        assistant_response += part.text

            # If tool calls were made, generate a final response with the tool results
            if tool_calls_made:
                final_response = self.genai_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=self._convert_messages_to_content(),
                    config={"temperature": 0.1, "max_output_tokens": 8192},
                )

                if final_response.text:
                    assistant_response = final_response.text
                else:
                    assistant_response = "I've executed the requested operations. Please see the results above."

            # If no response was generated, use the original response text
            if not assistant_response and response.text:
                assistant_response = response.text
            elif not assistant_response:
                assistant_response = "I understand your request, but I need more information to provide a helpful response."

            self.messages.append(Message(MessageRole.ASSISTANT, assistant_response))
            return assistant_response

        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Query processing traceback: {traceback.format_exc()}")
            self.messages.append(Message(MessageRole.ASSISTANT, error_msg))
            return error_msg

    async def chat_loop(self, session: ClientSession) -> None:
        """Interactive chat loop for CLI usage"""
        print("🤖 SQL Assistant ready! Type 'quit' to exit.")
        print(
            "💡 You can ask me to analyze data, run queries, or explore the database schema."
        )
        print(
            "📊 Example: 'Show me all tables' or 'What are the top 10 customers by sales?'"
        )

        while True:
            try:
                query = input("\n💬 Query: ").strip()
                if not query:
                    continue

                if query.lower() in ["quit", "exit", "bye", "q"]:
                    print("👋 Goodbye!")
                    break

                print("🔄 Processing...")
                response = await self.process_query(session, query)
                print(f"\n🤖 Assistant:\n{response}")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                logger.error(f"Chat loop error: {traceback.format_exc()}")

    async def run(self) -> None:
        """Main run method with comprehensive error handling"""
        server_process = None
        try:
            logger.info(
                f"Starting server: {self.server_params.command} {' '.join(self.server_params.args)}"
            )

            # Test server connectivity first
            async with stdio_client(self.server_params) as (read, write):
                logger.info("STDIO client established")

                async with ClientSession(read, write) as session:
                    try:
                        # Initialize session with timeout
                        logger.info("Initializing MCP session...")
                        await wait_for(session.initialize(), timeout=30.0)
                        logger.info("MCP session initialized successfully")

                        # Get available tools and store them
                        logger.info("Loading available tools...")
                        self.tools = await self._get_available_tools(session)
                        if not self.tools:
                            logger.warning(
                                "No tools available - the assistant will have limited functionality"
                            )
                        else:
                            logger.info(f"Loaded {len(self.tools)} tools successfully")
                            for tool in self.tools:
                                for func_decl in tool.function_declarations:
                                    logger.info(
                                        f"  - {func_decl.name}: {func_decl.description}"
                                    )

                        # Start the chat loop
                        await self.chat_loop(session)

                    except TimeoutError:
                        logger.error(
                            "Session initialization timed out after 30 seconds"
                        )
                        raise Exception("MCP session initialization timeout")
                    except Exception as e:
                        logger.error(f"Session error: {e}")
                        logger.error(f"Session traceback: {traceback.format_exc()}")
                        raise

        except Exception as e:
            logger.error(f"Failed to start chat: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            if hasattr(e, "__cause__") and e.__cause__:
                logger.error(f"Caused by: {e.__cause__}")
            raise e
