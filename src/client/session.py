# src/client/session.py
from typing import Literal

from google.genai.types import Content, Part

from client.interfaces import ChatSession, Message
from client.types import MessageRole
from config.logger import logger


class InMemoryChatSession(ChatSession):
    """In-memory implementation of chat session."""

    def __init__(self) -> None:
        """Initialize chat session with system message."""
        self._messages: list[Message] = [
            Message(
                MessageRole.SYSTEM,
                """You are an expert SQL analyst assistant. Your job is to:
                1. Analyze natural language queries and translate them into SQL
                2. Execute SQL queries using available tools
                3. Present results in clear, formatted tables
                4. Explain your analysis when needed
                5. Always check database schema first if unsure about table structure

                Available commands:
                - GET_SCHEMA: Get database schema
                - EXECUTE_SQL: your_sql_query_here
                - ANALYZE_TABLE: table_name
                """,
            )
        ]

    async def add_message(self, message: Message) -> None:
        """Add a message to the session."""
        self._messages.append(message)
        logger.debug(f"Added {message.role.value} message to session")

    async def get_messages(self) -> list[Message]:
        """Get all messages in the session."""
        return self._messages.copy()

    def convert_to_llm_content(
        self, model: Literal["openai", "gemini", "claude"]
    ) -> list[Content]:
        """Convert messages to Gemini Content format."""
        try:
            if model == "gemini":
                return [
                    Content(
                        role=(
                            "user"
                            if msg.role in [MessageRole.SYSTEM, MessageRole.USER]
                            else "model"
                        ),
                        parts=[
                            Part.from_text(
                                text=f"{'[SYSTEM] ' if msg.role == MessageRole.SYSTEM else ''}{msg.content}"
                            )
                        ],
                    )
                    for msg in self._messages
                ]
            else:
                raise NotImplementedError("Calma ae chefia, ainda não está pronto")
        except Exception as e:
            logger.error(f"Error converting messages to content: {e}")
            return []
