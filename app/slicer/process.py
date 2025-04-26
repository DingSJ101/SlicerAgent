import json

import pathlib

try:
    # rely on the qt module wrapped in Slicer through PythonQt
    from qt import QLineEdit, QTextEdit, QPushButton, QVBoxLayout, QWidget, QTextCursor, QProcess, Signal, Qt, QEvent, QTimer, QProcessEnvironment
    class SlicerAgentProcess(QProcess):
        streaming_output = Signal(str) # 主进程绑定该信号

        def __init__(self):
            super().__init__()
            self._buffer = ""
            self._in_response_string = False  # Tracks if we're inside response string
            self._last_chunk_type = None
            self.readyReadStandardOutput.connect(self._handle_stdout)
            self.errorOccurred.connect(lambda: print(f"进程错误: {self.errorString()}"))
            self.finished.connect(lambda: print(f"进程结束: {self.exitCode()}"))

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
                    self._handle_messages(data)
                elif data.get("type") == "error":
                    self._handle_error(data)
                elif data.get("type") == "toolcall":
                    self._handle_tools(data)
                self._last_chunk_type = data.get("type")
            # Keep only unprocessed data in buffer
            self._buffer = self._buffer[start:] if start < len(self._buffer) else ""

        def _handle_messages(self, data):
            """Handle incoming messages from the agent process."""
            if "content" in data:
                self.streaming_output.emit(data["content"])
        def _handle_error(self, data):
            """Handle error information from the agent process."""
            if "content" in data:
                print(f"Error: {data['content']}")
        def _handle_request(self, data):
            """Handle human action request from the agent process."""
            ...

        def _handle_tools(self, data):
            """Handle tool call message from the agent process.
            We use create_chat_completion tool to generate response in agent, 
            so we need to extract the content from the tool call message.
            """
            content = data.get("content").replace("\\n", "\n")
            if data.get("name") == "create_chat_completion":
                if self._in_response_string and self._last_chunk_type == "toolcall":
                    self.streaming_output.emit(content)
                else:
                    if "response" in content: # TODO: make it more robust
                        self._in_response_string = True # start streaming after "response" parameter appear 
            else:
                self._in_response_string = False # BUG: can't handle continue create_chat_completion tool call

        def send_messages(self,messages):
            data = {
                "type": "message",
                "content": messages
            }
            messages = json.dumps(data)
            self.write(f"{messages}\n")
            print(f"send message: {messages}")

        def stop(self):
            self.running = False

        def start_agent(self):
            # cmd = "PythonSlicer"
            cmd = "/home/dsj/workspace/LLM/SlicerAgent/.venv/bin/python" # TODO: use PythonSlicer
            env = QProcessEnvironment.systemEnvironment()
            env.remove("PYTHONPATH")
            env.remove("PATH")
            env.remove("PYTHONHOME")
            env.remove("LibraryPaths")
            self.setProcessEnvironment(env)

            main_script_file = pathlib.Path(__file__).parent.parent.parent / "main.py"
            script_file = str(main_script_file)
            args = [script_file]
            print("starting ",cmd, args)
            try:
                self.start(cmd, args)
                self.waitForStarted()
                print("Agent process started")
            except Exception as e:
                print(f"Error starting agent process: {e}")

except ImportError:
    from app.logger import logger
    logger.info("PythonQt.QtCore not found, you may not be in Slicer environment")