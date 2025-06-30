from dataclasses import dataclass
from enum import Enum


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    role: MessageRole
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"author": self.role.value, "content": self.content}
