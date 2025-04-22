import asyncio
import sys
import re
import json
import sys
import os
import pathlib
from app.logger import logger
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
            self.readyReadStandardOutput.connect(self._handle_stdout)
            self.errorOccurred.connect(lambda: print(f"进程错误: {self.errorString()}"))


        def _handle_stdout(self):
            raw = self.readAllStandardOutput().data().decode()
            if raw is None:
                return
            
            self._buffer += raw
            # with open("/home/dsj/workspace/LLM/SlicerAgent/tmp.log", "a") as fp:
            #     fp.write(f"main process received (buffer size: {len(self._buffer)}): {raw}\n")
            start = 0
            while start < len(self._buffer):
                try:
                    # Find the next complete JSON object
                    end = self._buffer.index('}', start) + 1
                    json_str = self._buffer[start:end]
                    data = json.loads(json_str)
                    
                    if data.get("type") == "message":
                        content = data.get("content")
                        if content:
                            self.streaming_output.emit(content)
                    
                    start = end  # Move to next potential JSON
                except (ValueError, json.JSONDecodeError):
                    # No complete JSON found, keep remaining data in buffer
                    break
            
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
from app.tool import Terminate, ToolCollection
# from app.tool.browser_use_tool import BrowserUseTool
# from app.tool.python_execute import PythonExecute
# from app.tool.str_replace_editor import StrReplaceEditor
from pydantic import Field, model_validator
from app.schema import Payload

SYSTEM_PROMPT = (
    "You are OpenManus, an all-capable AI assistant, aimed at solving any task presented by the user. You have various tools at your disposal that you can call upon to efficiently complete complex requests. Whether it's programming, information retrieval, file processing, or web browsing, you can handle it all."
    "The initial directory is: {directory}"
)

NEXT_STEP_PROMPT = """
Based on user needs, proactively select the most appropriate tool or combination of tools. For complex tasks, you can break down the problem and use different tools step by step to solve it. After using each tool, clearly explain the execution results and suggest the next steps.

If you want to stop the interaction at any point, use the `terminate` tool/function call.
"""


class SlicerAgent(ToolCallAgent):
    """A versatile general-purpose agent for 3D Slicer."""

    name: str = "SlicerAgent"
    description: str = (
        "A versatile agent that can solve various tasks using multiple tools"
    )

    system_prompt: str = SYSTEM_PROMPT.format(directory=config.workspace_root)
    next_step_prompt: str = NEXT_STEP_PROMPT

    max_observe: int = 10000
    max_steps: int = 20
    streaming_output:bool = True

    # Add general-purpose tools to the tool collection
    # available_tools: ToolCollection = Field(
    #     default_factory=lambda: ToolCollection(
    #         PythonExecute(), BrowserUseTool(), StrReplaceEditor(), Terminate()
    #     )
    # )

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

    def write_structed_content(self, content: str, content_type: str = "message"):
        """
        Write structured information to stdout.

        Format:
            {
                "type": "message"|"command"|"info"|"error", \n
                "content": str
            }

        """
        data = {
                "type": "default",
                "content": None
            }
        if content_type in ["message", "command", "info", "error"]:
            data["type"] = content_type
            data["content"] = content
        
        json.dump(data, sys.stdout)
        sys.stdout.flush()
    
    def echo_message(self, message: str):
        self.write_structed_content(message, "message")

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
                        if self.streaming_output:
                            await self.run(question)
                            # async for chunk in self.run_stream(question):
                            #     self.write_structed_content(chunk,"message")
                        else:
                            response = await self.run(question)
                            self.write_structed_content(response, "message")
                    else:
                        self.write_structed_content("No question provided.", "error")
            except Exception as e:
                self.write_structed_content(f"Error processing task: {e}", "error")

    # async def run_stream(self, question: str):
    #     """流式执行任务并生成结果"""
    #     async for result in self.run(question):
    #         yield result
