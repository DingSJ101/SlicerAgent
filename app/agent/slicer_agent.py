import asyncio
import sys
import re
import json
import sys
import os
import pathlib
from app.logger import logger
from typing import Literal
# sys.path.append("/home/dsj/workspace/LLM/SlicerAgent")
# sys.path.append("/home/dsj/workspace/LLM/SlicerAgent/.venv/lib/python3.9/site-packages")
is_slicer_available = True
is_app_available = True
try:
    # rely on the qt module wrapped in Slicer
    from qt import QLineEdit, QTextEdit, QPushButton, QVBoxLayout, QWidget, QTextCursor, QProcess, Signal, Qt, QEvent, QTimer
    class SlicerAgentProcess(QProcess):
        streaming_output = Signal(str) # 主进程绑定该信号

        def __init__(self):
            super().__init__()
            self._buffer = ""
            self._in_response_string = False  # Tracks if we're inside response string
            self.readyReadStandardOutput.connect(self._handle_stdout)
            self.errorOccurred.connect(lambda: print(f"进程错误: {self.errorString()}"))

        def _handle_stdout(self):
            raw = self.readAllStandardOutput().data().decode()
            if not raw:
                return
            
            self._buffer += raw
            start = 0
            decoder = json.JSONDecoder()
            while True:
                try:
                    # Try to decode a JSON object from the buffer
                    data, index = decoder.raw_decode(self._buffer, start)
                    start = index
                except json.JSONDecodeError:
                    # If decoding fails, break the loop
                    if self._buffer[start:].strip():
                        print("JSON decoding error, buffer:", self._buffer[start:].strip())
                    break
                if data.get("type") == "message":
                    content = data.get("content")
                    if content:
                        self.streaming_output.emit(content)
                elif data.get("type") == "error":
                    content = data.get("content")
                    if content:
                        print(f"Error: {content}")
                elif data.get("type") == "command" and data.get("content"):
                    content = data.get("content").replace("\\n", "\n")
                    if data.get("name") == "create_chat_completion":
                        if self._in_response_string :
                            self.streaming_output.emit(content)
                        else:
                            if "response" in content:
                                self._in_response_string = True
                        continue
                self._in_response_string = False
            # Keep only unprocessed data in buffer
            self._buffer = self._buffer[start:] if start < len(self._buffer) else ""

        def send_messages(self,messages):
            data = {
                "type": "message",
                "content": messages
            }
            with open("/home/dsj/workspace/LLM/SlicerAgent/tmp.log", "a") as fp:
                fp.write("writing:"+messages+"\n")
            messages = json.dumps(data)
            self.write(f"{messages}\n")

        def stop(self):
            self.running = False

        def start_agent(self):
            cmd = "PythonSlicer"

            agent_script_file = __file__
            main_script_file = pathlib.Path(__file__).parent.parent.parent / "main.py"
            script_file = str(main_script_file)
            args = [script_file]
            print("starting ",cmd, args)
            self.start(cmd, args)

except ImportError:
    is_slicer_available = False
    logger.info("PythonQt.QtCore not found, using fallback imports")

from app.agent import BaseAgent, ReActAgent, ToolCallAgent
from app.logger import logger
from app.config import config
from app.tool import Terminate, ToolCollection, WebSearch, CreateChatCompletion
# from app.tool.browser_use_tool import BrowserUseTool
# from app.tool.python_execute import PythonExecute
# from app.tool.str_replace_editor import StrReplaceEditor
from pydantic import Field, model_validator
from app.schema import Payload

SYSTEM_PROMPT = (
    "You are SlicerAgent, an all-capable AI assistant for 3D Slicer, aimed at solving any task presented by the user. You have various tools at your disposal that you can call upon to efficiently complete complex requests."
)

class SlicerAgent(ToolCallAgent):
    """A versatile general-purpose agent for 3D Slicer."""

    name: str = "SlicerAgent"
    description: str = (
        "A versatile agent that can solve various tasks using multiple tools"
    )

    system_prompt: str = SYSTEM_PROMPT

    max_observe: int = 10000
    max_steps: int = 20
    streaming_output:bool = True

    # Add general-purpose tools to the tool collection
    available_tools:ToolCollection = ToolCollection(
        Terminate(), CreateChatCompletion(), WebSearch()
    )

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

    special_tool_names: list[str] = Field(default_factory=lambda: [Terminate().name])

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
                        payload = Payload(content="No question provided.", type="error")
                        payload.write_structed_content()
            except Exception as e:
                payload = Payload(content=f"Error in run_loop: {e}", type="error")
                payload.write_structed_content()

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

