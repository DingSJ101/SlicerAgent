
import sys
# sys.path.append("/home/dsj/workspace/LLM/SlicerAgent")
sys.path.append("/home/dsj/workspace/LLM/SlicerAgent/.venv/lib/python3.12/site-packages")

from app.slicer.agent import SlicerAgent
import asyncio
if __name__ == "__main__":
    agent = SlicerAgent()
    asyncio.run(agent.run_loop())

# {"content": "who are you?", "type": "message"}
