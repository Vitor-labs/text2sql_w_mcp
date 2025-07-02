# src/client/interfaces.py
from abc import ABC, abstractmethod
from typing import Any, Protocol

from client.types import Message


class ToolExecutor(Protocol):
    """Protocol defining tool execution interface."""

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool with given arguments."""
        raise NotImplementedError("ToolExecutor.execute_tool not implemented")


class MessageProcessor(ABC):
    """Abstract base class for processing different types of messages."""

    @abstractmethod
    async def can_handle(self, message: str) -> bool:
        """Check if this processor can handle the given message."""
        raise NotImplementedError("MessageProcessor.can_handle not implemented")

    @abstractmethod
    async def process(self, message: str, tool_executor: ToolExecutor) -> str:
        """Process the message and return response."""
        raise NotImplementedError("MessageProcessor.process not implemented")


class ChatSession(ABC):
    """Abstract base class for chat session management."""

    @abstractmethod
    async def add_message(self, message: Message) -> None:
        """Add a message to the session."""
        raise NotImplementedError("ChatSession.add_message not implemented")

    @abstractmethod
    async def get_messages(self) -> list[Message]:
        """Get all messages in the session."""
        raise NotImplementedError("ChatSession.get_messages not implemented")
