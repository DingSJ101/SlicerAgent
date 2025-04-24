import asyncio
import sys
import re
import json
import sys
from app.logger import logger
from typing import Literal

from app.agent import BaseAgent, ReActAgent, ToolCallAgent
from app.logger import logger
from app.config import config
from app.tool import Terminate, ToolCollection, WebSearch, CreateChatCompletion
from pydantic import Field, model_validator
from app.schema import Payload

SLICER_SYSTEM_PROMPT = (
    "You are SlicerAgent, an all-capable AI assistant for 3D Slicer, aimed at solving any task presented by the user. You have various tools at your disposal that you can call upon to efficiently complete complex requests."
)

class SlicerBaseAgent(BaseAgent):
    """A base agent class for 3D Slicer with stdio communication.
    
    Methods:
        load_message_from_main_process() -> dict: Reads a line from stdin and parses it as JSON.
        write_message_to_main_process(message: str, type: str = "message") -> None: Writes a message to the main process.
        run_loop() -> None: Main loop for the agent to process messages. 
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

    def write_message_to_main_process(self, message: str, type:str = "message") -> None:
        payload = Payload(content=message, type=type)
        payload.write_structed_content()

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
                        self.write_message_to_main_process("No content in message", type="error")
            except Exception as e:
                self.write_message_to_main_process(f"Error in run_loop: {e}", type="error")

class SlicerAgent(SlicerBaseAgent, ToolCallAgent):
    """A versatile general-purpose agent for 3D Slicer."""

    name: str = "SlicerAgent"
    description: str = "A versatile agent that can solve various tasks using multiple tools"

    system_prompt: str = SLICER_SYSTEM_PROMPT

    max_observe: int = 10000
    max_steps: int = 20
    streaming_output:bool = True

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

