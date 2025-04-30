import asyncio
import json
import sys
from typing import Literal

from pydantic import BaseModel

from app.agent import BaseAgent, MCPAgent, ToolCallAgent
from app.logger import logger
from app.schema import Payload

SLICER_SYSTEM_PROMPT = (
    "You are SlicerAgent, an all-capable AI assistant for 3D Slicer, aimed at solving any task presented by the user. "
    "You have various tools that you can call upon to efficiently complete complex requests."
    "User *Can't* see your tool call, so you can use it to generate a response in the background. "
    "You can *respond* to the user in two ways: "
    "1. By using the `create_chat_completion` tool. "
    "2. By directly responding to the user without any tool call."
)
SLICER_NEXT_STEP_PROMPT = (
    "If you believe the user's initial task has been accomplished in previous *responses*, "
    # "and wish to cease interaction to wait for instruction from user ,"
    "utilize the `terminate` function call *immediately* without any further approval . "
    "Remember, user can't see your tool call, so you may need to make an additional response before `terminate`. "
    "Otherwise, disregard this message and persist in fulfilling the task."
)


class SlicerMessageHandler(BaseModel):
    """A base agent class for 3D Slicer with stdio communication.

    Methods:
        load_message_from_main_process() -> dict: Reads a line from stdin and parses it as JSON.
        write_message_to_main_process(message: str, type: str = "message") -> None: Writes a message to the main process.
    """

    def load_message_from_main_process(self) -> dict:
        """
        Read a line from stdin and parse it as JSON.
        """
        line = sys.stdin.readline().strip()
        if not line:
            return None
        try:
            data = json.loads(line)
            return data
        except:
            logger.error("Error parsing JSON:", line)
            return None

    def write_message_to_main_process(
        self, message: str, type: str = "message"
    ) -> None:
        payload = Payload(content=message, type=type)
        payload.write_structed_content()


class SlicerBaseAgent(SlicerMessageHandler, BaseAgent):
    """You shouldn't instantiate this class because method `step` hasn't been implemented"""

    name: str = "SlicerAgent"
    description: str = (
        "A versatile agent that can solve various tasks using multiple tools"
    )

    system_prompt: str = SLICER_SYSTEM_PROMPT
    next_step_prompt: str = SLICER_NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 20
    streaming_output: bool = True

    async def run_loop(self):
        while True:
            try:
                data = self.load_message_from_main_process()
                if data is None:
                    continue
                if data.get("type") == "message":
                    question = data.get("content")
                    if question:
                        await self.run(question)
                    else:
                        self.write_message_to_main_process(
                            "No content in message", type="info"
                        )
                elif data.get("type") == "command":
                    if data.get("content") == "exit":
                        break
                    elif data.get("content") == "clear":
                        self.current_step = 0
                        self.memory.clear()
                        self.write_message_to_main_process(
                            "Memory cleared", type="info"
                        )
            except Exception as e:
                self.write_message_to_main_process(
                    f"Error in run_loop: {e}", type="error"
                )


class SlicerAgent(SlicerBaseAgent, ToolCallAgent):
    """A versatile general-purpose agent for 3D Slicer."""


class SlicerAgentWithMCP(SlicerBaseAgent, MCPAgent):
    """A versatile general-purpose agent for 3D Slicer."""

    connection_type: Literal["stdio", "sse"] = "sse"

    async def run_loop(self):
        await self.initialize(
            connection_type="sse", server_url="http://localhost:6666/sse"
        )
        await super().run_loop()


if __name__ == "__main__":
    agent = SlicerAgent()
    asyncio.run(agent.run_loop())

# {"content": "who are you?", "type": "message"}

# while SlicerAgent.run_loop():
#     if SlicerAgent.run() > ToolCallAgent.run() > BaseAgent.run() > BaseAgent.run() :
#         while BaseAgent.step() > ReActAgent.step() :
#             ReActAgent.think() > ToolCallAgent.think()
#             if ReActAgent.act() > ToolCallAgent.act():
#                 ToolCallAgent.execute_tool()
