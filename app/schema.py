from enum import Enum
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field
import sys
import json

class Role(str, Enum):
    """Message role options"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


ROLE_VALUES = tuple(role.value for role in Role)
ROLE_TYPE = Literal[ROLE_VALUES]  # type: ignore


class ToolChoice(str, Enum):
    """Tool choice options"""

    NONE = "none"
    AUTO = "auto"
    REQUIRED = "required"


TOOL_CHOICE_VALUES = tuple(choice.value for choice in ToolChoice)
TOOL_CHOICE_TYPE = Literal[TOOL_CHOICE_VALUES]  # type: ignore


class AgentState(str, Enum):
    """Agent execution states"""

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    ERROR = "ERROR"


class Function(BaseModel):
    name: Optional[str] = None
    arguments: Optional[str] = None


class ToolCall(BaseModel):
    """Represents a tool/function call in a message"""
    index: int = Field(default=-1)
    id: Optional[str] = None
    type: str = "function"
    function: Optional[Function] = Field(default=None)


class Message(BaseModel):
    """Represents a chat message in the conversation"""

    role: ROLE_TYPE = Field(...)  # type: ignore
    content: Optional[str] = Field(default=None)
    tool_calls: Optional[List[ToolCall]] = Field(default=None)
    name: Optional[str] = Field(default=None)
    tool_call_id: Optional[str] = Field(default=None)
    base64_image: Optional[str] = Field(default=None)

    def __add__(self, other) -> List["Message"]:
        """支持 Message + list 或 Message + Message 的操作"""
        if isinstance(other, list):
            return [self] + other
        elif isinstance(other, Message):
            return [self, other]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(self).__name__}' and '{type(other).__name__}'"
            )

    def __radd__(self, other) -> List["Message"]:
        """支持 list + Message 的操作"""
        if isinstance(other, list):
            return other + [self]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(other).__name__}' and '{type(self).__name__}'"
            )

    def to_dict(self) -> dict:
        """Convert message to dictionary format"""
        message = {"role": self.role}
        if self.content is not None:
            message["content"] = self.content
        if self.tool_calls is not None:
            message["tool_calls"] = [tool_call.dict() for tool_call in self.tool_calls]
        if self.name is not None:
            message["name"] = self.name
        if self.tool_call_id is not None:
            message["tool_call_id"] = self.tool_call_id
        if self.base64_image is not None:
            message["base64_image"] = self.base64_image
        return message

    @classmethod
    def user_message(
        cls, content: str, base64_image: Optional[str] = None
    ) -> "Message":
        """Create a user message"""
        return cls(role=Role.USER, content=content, base64_image=base64_image)

    @classmethod
    def system_message(cls, content: str) -> "Message":
        """Create a system message"""
        return cls(role=Role.SYSTEM, content=content)

    @classmethod
    def assistant_message(
        cls, content: Optional[str] = None, base64_image: Optional[str] = None
    ) -> "Message":
        """Create an assistant message"""
        return cls(role=Role.ASSISTANT, content=content, base64_image=base64_image)

    @classmethod
    def tool_message(
        cls, content: str, name, tool_call_id: str, base64_image: Optional[str] = None
    ) -> "Message":
        """Create a tool message"""
        return cls(
            role=Role.TOOL,
            content=content,
            name=name,
            tool_call_id=tool_call_id,
            base64_image=base64_image,
        )

    @classmethod
    def from_tool_calls(
        cls,
        tool_calls: List[Any],
        content: Union[str, List[str]] = "",
        base64_image: Optional[str] = None,
        **kwargs,
    ):
        """Create ToolCallsMessage from raw tool calls.

        Args:
            tool_calls: Raw tool calls from LLM
            content: Optional message content
            base64_image: Optional base64 encoded image
        """
        formatted_calls = None
        if tool_calls:
            formatted_calls = [
                {"id": call.id, "function": call.function.model_dump(), "type": "function"}
                for call in tool_calls
            ]
        return cls(
            role=Role.ASSISTANT,
            content=content,
            tool_calls=formatted_calls,
            base64_image=base64_image,
            **kwargs,
        )

class MessageChunk(Message):
    type: str = Literal["message","toolcall"]
    def __init__(self,content = "",**kwargs):
        super().__init__(role = Role.ASSISTANT)
        self.content = content
        self.type = "message"
        self.tool_calls = kwargs.get("tool_calls", None)
    def __add__(self, other) -> List["MessageChunk"]:
        if not isinstance(other, MessageChunk):
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(self).__name__}' and '{type(other).__name__}'"
            )
        new_content = self.content + other.content
        if other.tool_calls is None:
            new_tool_calls = self.tool_calls
        else:
            if self.tool_calls is None:
                new_tool_calls = []
            else:
                new_tool_calls = list(self.tool_calls)
            for delta in other.tool_calls:
                i = delta.index
                while len(new_tool_calls) <= i:
                    new_tool_calls.append(None)
                if new_tool_calls[i] is None:
                    new_tool_calls[i] = ToolCall(
                        index=delta.index,
                        id=delta.id,
                        type=delta.type,
                        function=delta.function.model_dump(),
                    )
                else:
                    existing = new_tool_calls[i]
                    if delta.id is not None:
                        existing.id = delta.id
                    if delta.type is not None:
                        existing.type = delta.type
                    if delta.function is not None:
                        if delta.function.name is not None:
                            existing.function.name = delta.function.name
                        if delta.function.arguments is not None:
                            existing.function.arguments += delta.function.arguments
        return self.__class__(content=new_content, tool_calls=new_tool_calls)

        


class Memory(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    max_messages: int = Field(default=100)

    def add_message(self, message: Message) -> None:
        """Add a message to memory"""
        self.messages.append(message)
        # Optional: Implement message limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def add_messages(self, messages: List[Message]) -> None:
        """Add multiple messages to memory"""
        self.messages.extend(messages)
        # Optional: Implement message limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def clear(self) -> None:
        """Clear all messages"""
        self.messages.clear()

    def get_recent_messages(self, n: int) -> List[Message]:
        """Get n most recent messages"""
        return self.messages[-n:]

    def to_dict_list(self) -> List[dict]:
        """Convert messages to list of dicts"""
        return [msg.to_dict() for msg in self.messages]

class Payload(BaseModel):
    content: str
    type: str = Literal["message","image","info","error",\
                        "command","system","toolcall","functioncall"]
    name: Optional[str] = None
    def __init__(self, content: str, type: str = "message",name = None):
        super().__init__(content=content, type=type, name=name)

    def model_dump(self):
        if self.name is not None:
            return {
                "type": self.type,
                "content": self.content,
                "name": self.name
            }
        else:
            return {
                "type": self.type,
                "content": self.content
            }

    def write_structed_content(self):
        """
        Write structured information to stdout.
        """
        json.dump(self.model_dump(), sys.stdout)
        sys.stdout.flush()
    
    @staticmethod
    def write_message(content:str, type:str = "message"):
        data = {
                "type": type,
                "content": content
            }
        json.dump(data, sys.stdout)
        sys.stdout.flush()

    @classmethod
    def from_message(cls,message:Message) -> "Payload":
        content = message.content
        return cls(content=content,type = "message")
