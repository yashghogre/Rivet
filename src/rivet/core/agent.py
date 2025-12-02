import asyncio

from langchain_core.runnables import RunnableConfig
from rich.console import Console

from rivet.core.schema import AgentState
from rivet.tools.scrape import ingest_resource

console = Console()


class MockGraph:
    """
    A fake LangGraph that just yields events to test the UI.
    """

    async def astream(self, initial_state: dict):
        """
        Simulates the AI thinking process with delays.
        """
        url = initial_state.get("url", "https://api.example.com")

        # --- Step 1: Ingest (The Crawler) ---
        # Simulates fetching the docs
        await asyncio.sleep(1.0)
        yield {"node_ingest": {"url": url, "status": "fetching_spec"}}
        await asyncio.sleep(1.5)  # Fake network delay

        # --- Step 2: Code Gen (The Writer) ---
        # Simulates the AI typing out code (streaming effect)
        boilerplate = [
            "import requests",
            "from pydantic import BaseModel",
            "\nclass User(BaseModel):\n    id: int\n    name: str",
            "\nclass APIClient:\n    def __init__(self, base_url: str):",
            "        self.base_url = base_url",
            "    def get_user(self, uid: int):",
            "        return requests.get(f'{self.base_url}/users/{uid}')",
        ]

        current_code = ""
        for line in boilerplate:
            current_code += line + "\n"
            await asyncio.sleep(0.3)  # Simulate typing speed
            yield {"node_codegen": {"partial_code": current_code}}

        # --- Step 3: Testing (The Sandbox) ---
        # Simulates running pytest in Docker
        await asyncio.sleep(0.5)
        yield {"node_test": {"status": "running"}}
        await asyncio.sleep(2.0)  # Fake test duration

        # --- Step 4: Failure (The Self-Healing) ---
        # Simulates a crash to show off your error handling UI
        yield {"node_fix": {"error": "ImportError: module 'requests' not found", "attempt": 1}}
        await asyncio.sleep(1.5)  # Fake "thinking about the fix" time

        # --- Step 5: Success (The Fix) ---
        # Simulates the fixed code
        current_code = "# FIXED: Added imports\n" + current_code
        yield {"node_codegen": {"partial_code": current_code}}
        await asyncio.sleep(1.0)

        # Final success state (optional, usually handled by completion)
        yield {"node_success": {"path": "./output/sdk"}}


def build_graph():
    """
    Returns the mock graph instead of the real LangGraph.
    """
    return MockGraph()


# Starting the actual graph here ->


async def ingest_node(state: AgentState, config: RunnableConfig):
    url = state.url

    try:
        spec_json, docs_text = await ingest_resource(url)
        return {
            "spec_json": spec_json,
            "docs_text": docs_text,
            "status": "ingested",
        }

    except ValueError as e:
        return {"error": str(e)}


# async def generate_code(state: AgentState, configuration: RunnableConfig):
# config = configuration.get("configurable", {})
# llm_api_key = config.get("llm_api_key")
# llm_base_url = config.get("llm_base_url")
# llm_name = config.get("llm_name")

# requirement = state.requirement
