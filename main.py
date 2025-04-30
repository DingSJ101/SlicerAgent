import sys

# sys.path.append("/home/dsj/workspace/LLM/SlicerAgent")
# sys.path.append("/home/dsj/workspace/LLM/SlicerAgent/.venv/lib/python3.12/site-packages")

# load slicerwebserver mcp in qprocess instead of threading
# TODO: move mcp to slicer agent extension widget
try:
    import asyncio

    from app.slicer.agent import SlicerAgent, SlicerAgentWithMCP
    from app.slicer.mcp import MCPServer
except ImportError as e:
    print(f"Error information: {e}")

if __name__ == "__main__":
    server = MCPServer(port=6666)
    server.start()
    # agent = SlicerAgent()
    agent = SlicerAgentWithMCP()  # must start Slicer Web Server first
    asyncio.run(agent.run_loop())
    server.stop()

# {"content": "who are you?", "type": "message"}
# {"content": "exit", "type": "command"}
# {"content": "Which nodes are there in the Slicer", "type": "message"}
# {"content": "How many nodes are there in Slicer", "type": "message"}
# {"content": "How to use python code to print these nodes in Slicer?", "type": "message"}
# {"content": "What's the weather of 2025.04.29 in Shanghai?", "type": "message"}
# {"content": "clear", "type": "command"}