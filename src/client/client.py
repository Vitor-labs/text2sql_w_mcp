# src/client/client.py
import traceback
from asyncio import TimeoutError, wait_for
from dataclasses import dataclass, field
from typing import Any

from google.genai import Client
from google.genai.types import Content, Part, Tool
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
    session: ClientSession = field(default=None, init=False)
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
                    "Available commands:\n"
                    "- To get database schema: respond with 'GET_SCHEMA'\n"
                    "- To execute SQL: respond with 'EXECUTE_SQL: your_sql_query_here'\n"
                    "- To analyze a table: respond with 'ANALYZE_TABLE: table_name'\n\n"
                    "When a user asks a question:\n"
                    "1. If you need to understand the database structure, use GET_SCHEMA first\n"
                    "2. Then construct and execute the appropriate SQL query with EXECUTE_SQL\n"
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

    async def _get_available_tools(self, session: ClientSession) -> bool:
        """Check if tools are available from MCP server"""
        try:
            logger.info("Checking available tools from MCP server...")
            mcp_tools = await session.list_tools()
            logger.info(f"Retrieved {len(mcp_tools.tools)} tools from MCP server")

            self.session = session  # Store session for later use

            for tool in mcp_tools.tools:
                logger.info(f"Available tool: {tool.name} - {tool.description}")

            return len(mcp_tools.tools) > 0

        except Exception as e:
            logger.error(f"Failed to get tools: {e}")
            logger.error(f"Exception details: {traceback.format_exc()}")
            return False

    async def _execute_tool_call(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> str:
        """Execute a tool call through MCP"""
        try:
            if not self.session:
                return "Error: No active MCP session"

            logger.info(f"Executing tool: {tool_name} with args: {arguments}")
            result = await self.session.call_tool(tool_name, arguments)

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

    async def _parse_and_execute_commands(self, response_text: str) -> str:
        """Parse AI response for commands and execute them"""
        try:
            if not response_text:
                return "No response generated"

            # Check for specific commands
            if "GET_SCHEMA" in response_text:
                logger.info("Executing GET_SCHEMA command")
                schema_result = await self._execute_tool_call("get_schema", {})

                # Add tool result to context
                self.messages.append(
                    Message(MessageRole.TOOL, f"Database Schema:\n{schema_result}")
                )

                # Generate follow-up response
                self.messages.append(
                    Message(
                        MessageRole.USER,
                        "Now please answer the original question using this schema information.",
                    )
                )

                followup_response = self.genai_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=self._convert_messages_to_content(),
                    config={"temperature": 0.1, "max_output_tokens": 8192},
                )

                return (
                    followup_response.text
                    if followup_response.text
                    else "Schema retrieved successfully"
                )

            elif "EXECUTE_SQL:" in response_text:
                # Extract SQL query
                sql_start = response_text.find("EXECUTE_SQL:") + len("EXECUTE_SQL:")
                sql_end = response_text.find("\n", sql_start)
                if sql_end == -1:
                    sql_end = len(response_text)

                sql_query = response_text[sql_start:sql_end].strip()
                logger.info(f"Executing SQL command: {sql_query}")

                sql_result = await self._execute_tool_call(
                    "query_data", {"sql": sql_query}
                )

                # Add tool result to context
                self.messages.append(
                    Message(MessageRole.TOOL, f"SQL Query Result:\n{sql_result}")
                )

                # Generate follow-up response
                self.messages.append(
                    Message(
                        MessageRole.USER,
                        "Please provide a summary and analysis of these results.",
                    )
                )

                followup_response = self.genai_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=self._convert_messages_to_content(),
                    config={"temperature": 0.1, "max_output_tokens": 8192},
                )

                return (
                    followup_response.text
                    if followup_response.text
                    else f"SQL executed successfully:\n{sql_result}"
                )

            elif "ANALYZE_TABLE:" in response_text:
                # Extract table name
                table_start = response_text.find("ANALYZE_TABLE:") + len(
                    "ANALYZE_TABLE:"
                )
                table_end = response_text.find("\n", table_start)
                if table_end == -1:
                    table_end = len(response_text)

                table_name = response_text[table_start:table_end].strip()
                logger.info(f"Analyzing table: {table_name}")

                analysis_result = await self._execute_tool_call(
                    "analyze_table", {"table_name": table_name}
                )

                # Add tool result to context
                self.messages.append(
                    Message(MessageRole.TOOL, f"Table Analysis:\n{analysis_result}")
                )

                # Generate follow-up response
                self.messages.append(
                    Message(
                        MessageRole.USER,
                        "Please provide insights based on this table analysis.",
                    )
                )

                followup_response = self.genai_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=self._convert_messages_to_content(),
                    config={"temperature": 0.1, "max_output_tokens": 8192},
                )

                return (
                    followup_response.text
                    if followup_response.text
                    else f"Table analyzed successfully:\n{analysis_result}"
                )

            else:
                # No special commands, return original response
                return response_text

        except Exception as e:
            error_msg = f"Error parsing/executing commands: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Command execution traceback: {traceback.format_exc()}")
            return error_msg

    async def process_query(self, query: str) -> str:
        """Process user query with tool integration"""
        try:
            self.messages.append(Message(MessageRole.USER, query))

            # Generate content without tools parameter
            generation_config = {
                "temperature": 0.1,
                "max_output_tokens": 8192,
            }

            response = self.genai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=self._convert_messages_to_content(),
                config=generation_config,
            )

            if not response.text:
                return "No response generated from the AI model"

            # Parse response for commands and execute them
            assistant_response = await self._parse_and_execute_commands(response.text)

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
                response = await self.process_query(query)
                print(f"\n🤖 Assistant:\n{response}")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                logger.error(f"Chat loop error: {traceback.format_exc()}")

    async def run(self) -> None:
        """Main run method with comprehensive error handling"""
        try:
            logger.info(
                f"Starting server: {self.server_params.command} {' '.join(self.server_params.args)}"
            )

            async with stdio_client(self.server_params) as (read, write):
                logger.info("STDIO client established")

                async with ClientSession(read, write) as session:
                    try:
                        # Initialize session with timeout
                        logger.info("Initializing MCP session...")
                        await wait_for(session.initialize(), timeout=30.0)
                        logger.info("MCP session initialized successfully")

                        # Check available tools
                        logger.info("Checking available tools...")
                        tools_available = await self._get_available_tools(session)
                        if not tools_available:
                            logger.warning(
                                "No tools available - the assistant will have limited functionality"
                            )
                        else:
                            logger.info("Tools are available and ready")

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
