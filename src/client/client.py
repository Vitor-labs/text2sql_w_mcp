# src/client/client.py
import traceback
from asyncio import TimeoutError, wait_for
from contextlib import asynccontextmanager

from google.genai import Client
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from client.interfaces import Message, MessageProcessor
from client.processors import (
    SchemaRequestProcessor,
    SqlQueryProcessor,
    TableAnalysisProcessor,
)
from client.session import InMemoryChatSession
from client.tool_executor import MCPToolExecutor
from client.types import MessageRole
from config.config import ChatConfig
from config.logger import logger


class Chat:
    """Enhanced SQL chat client following SOLID principles."""

    def __init__(
        self,
        genai_client: Client,
        server_params: StdioServerParameters,
        config: ChatConfig | None = None,
    ) -> None:
        """Initialize enhanced chat client."""
        self._genai_client = genai_client
        self._server_params = server_params
        self._config = config or ChatConfig()
        self._session = InMemoryChatSession()
        self._tool_executor: MCPToolExecutor | None = None
        self._processors: list[MessageProcessor] = [
            SchemaRequestProcessor(),
            SqlQueryProcessor(),
            TableAnalysisProcessor(),
        ]

    async def _initialize_mcp_session(
        self, session: ClientSession, in_test_mode: bool = False
    ) -> bool:
        """Initialize MCP session and tools."""
        try:
            await wait_for(session.initialize(), timeout=self._config.session_timeout)
            logger.info("MCP session initialized successfully")

            mcp_tools = await session.list_tools()
            logger.info(f"Retrieved {len(mcp_tools.tools)} tools from MCP server")

            self._tool_executor = MCPToolExecutor(session)

            if not in_test_mode:
                for tool in mcp_tools.tools:
                    logger.info(f"\nAvailable tool: {tool.name} - {tool.description}")

            return len(mcp_tools.tools) > 0

        except TimeoutError:
            logger.error(
                f"Session initialization timed out after {self._config.session_timeout} seconds"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to initialize MCP session: {e}")
            logger.error(f"Exception details: {traceback.format_exc()}")
            return False

    async def _process_with_ai(self, user_query: str) -> str:
        """Generate AI response for user query."""
        try:
            await self._session.add_message(Message(MessageRole.USER, user_query))
            response = self._genai_client.models.generate_content(
                model=self._config.model_name,
                contents=self._session.convert_to_llm_content("gemini"),
                config={
                    "temperature": self._config.temperature,
                    "max_output_tokens": self._config.max_output_tokens,
                },
            ).text
            return "No response from the AI model" if not response else response

        except Exception as e:
            error_msg = f"Error generating AI response: {str(e)}"
            logger.error(error_msg)
            return error_msg

    async def _process_commands(self, ai_response: str) -> str:
        """Process AI response for commands using registered processors."""
        try:
            if not self._tool_executor:
                return ai_response

            for processor in self._processors:
                if await processor.can_handle(ai_response):
                    # Execute the tool and get the direct result
                    tool_result = await processor.process(
                        ai_response, self._tool_executor
                    )
                    # Add the tool's output to the session history
                    await self._session.add_message(
                        Message(MessageRole.TOOL, tool_result)
                    )
                    # Directly return the tool's result to the user
                    return tool_result

            return ai_response  # No special commands found, return original response

        except Exception as e:
            error_msg = f"Error processing commands: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Command processing traceback: {traceback.format_exc()}")
            return error_msg

    async def process_query(self, query: str) -> str:
        """Process user query with full pipeline."""
        try:
            # First, get the AI's response (which might be a tool call)
            # Second, execute any tools the AI requested and get the final result
            final_response = await self._process_commands(
                await self._process_with_ai(query)
            )
            await self._session.add_message(
                Message(MessageRole.ASSISTANT, final_response)
            )
            return final_response

        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            logger.error(f"{error_msg}\ntraceback: {traceback.format_exc()}")
            await self._session.add_message(Message(MessageRole.ASSISTANT, error_msg))
            return error_msg

    async def start_interactive_chat(self) -> None:
        """Start interactive chat loop."""
        print("""
        🤖 Enhanced SQL Assistant ready! Type 'quit' to exit.
        💡 You can ask me to analyze data, run queries, or explore the database schema.
        📊 Example: 'Show me all tables' or 'What are the top 10 customers by sales?'
        """)

        while True:
            try:
                if not (query := input("\n💬 Query: ").strip()):
                    continue

                if query.lower() in ["quit", "exit", "bye", "q"]:
                    print("👋 Goodbye!")
                    break

                print("🔄 Processing...")
                print(f"\n🤖 Assistant:\n{await self.process_query(query)}")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                logger.error(f"Chat loop error: {traceback.format_exc()}")

    @asynccontextmanager
    async def test_context(self):
        """Context manager for running tests with persistent MCP session."""
        logger.info(
            f"Starting server for tests: {self._server_params.command} {' '.join(self._server_params.args)}"
        )
        async with stdio_client(self._server_params) as (read, write):
            async with ClientSession(read, write) as session:
                if not await self._initialize_mcp_session(session, in_test_mode=True):
                    logger.warning(
                        "No tools available - the assistant will have limited functionality"
                    )
                else:
                    logger.info("Tools are available and ready for testing")
                try:
                    yield self
                finally:
                    self._tool_executor = None

    async def run(self) -> None:
        """Main run method with comprehensive error handling."""
        try:
            logger.info(
                f"Starting server: {self._server_params.command} {' '.join(self._server_params.args)}"
            )

            async with stdio_client(self._server_params) as (read, write):
                logger.info("STDIO client established")

                async with ClientSession(read, write) as session:
                    if not await self._initialize_mcp_session(session):
                        logger.warning(
                            "No tools available - the assistant will have limited functionality"
                        )
                    else:
                        logger.info("Tools are available and ready")

                    await self.start_interactive_chat()

        except Exception as e:
            logger.error(
                f"{type(e).__name__}: Failed to start chat: {e}\ntraceback: {traceback.format_exc()}"
            )
            raise e
