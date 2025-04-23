
import sys
# sys.path.append("/home/dsj/workspace/LLM/SlicerAgent")
sys.path.append("/home/dsj/workspace/LLM/SlicerAgent/.venv/lib/python3.9/site-packages")

from app.agent.slicer_agent import SlicerAgent
import asyncio
if __name__ == "__main__":
    agent = SlicerAgent()
    asyncio.run(agent.run_loop())

# {"content": "who are you?", "type": "message"}
