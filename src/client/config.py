from dataclasses import dataclass


@dataclass
class ChatConfig:
    """Configuration for chat client."""

    model_name: str = "gemini-2.0-flash"
    temperature: float = 0.1
    max_output_tokens: int = 8192
    session_timeout: float = 15.0
