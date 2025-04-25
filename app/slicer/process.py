import json

import pathlib
from app.logger import logger

try:
    # rely on the qt module wrapped in Slicer through PythonQt
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
            messages = json.dumps(data)
            self.write(f"{messages}\n")

        def stop(self):
            self.running = False

        def start_agent(self):
            # cmd = "PythonSlicer"
            cmd = "/home/dsj/workspace/LLM/SlicerAgent/.venv/bin/python" # TODO: use PythonSlicer

            main_script_file = pathlib.Path(__file__).parent.parent.parent / "main.py"
            script_file = str(main_script_file)
            args = [script_file]
            print("starting ",cmd, args)
            self.start(cmd, args)

except ImportError:
    logger.info("PythonQt.QtCore not found, you may not be in Slicer environment")