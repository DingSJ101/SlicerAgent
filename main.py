
import sys
# sys.path.append("/home/dsj/workspace/LLM/SlicerAgent")
sys.path.append("/home/dsj/workspace/LLM/SlicerAgent/.venv/lib/python3.12/site-packages")

# load slicerwebserver mcp in qprocess instead of threading
# TODO: move mcp to slicer agent extension widget
from app.slicer.mcp import MCPServer

from app.slicer.agent import SlicerAgent, SlicerAgentWithMCP
import asyncio
if __name__ == "__main__":
    server = MCPServer(port=6666)
    server.start()
    agent = SlicerAgent()
    agent = SlicerAgentWithMCP() # must start Slicer Web Server first
    asyncio.run(agent.run_loop())
    server.stop()

# {"content": "who are you?", "type": "message"}
# {"content": "exit", "type": "command"}
# {"content": "Which nodes are there in the Slicer", "type": "message"}

