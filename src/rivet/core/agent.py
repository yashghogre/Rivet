import asyncio
import json

from langchain_core.runnables import RunnableConfig
from rich.console import Console

from rivet.core.inference import direct_chat_completion
from rivet.core.schema import AgentState
from rivet.tools.scrape import ingest_resource
from rivet.utils.prompts import (
    get_code_sys_prompt,
    get_code_usr_prompt,
    get_test_sys_prompt,
    get_test_usr_prompt,
)

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


async def generate_code(state: AgentState, configuration: RunnableConfig):
    config = configuration.get("configurable", {})
    output_dir = config.get("output_dir", "./output")
    has_error = state.error

    generated_sdk_code = await direct_chat_completion(
        config=config,
        sys_msg_content=get_code_sys_prompt(),
        usr_msg_content=get_code_usr_prompt(
            swagger_spec=json.dumps(state.spec_json),
            docs_text=state.doc_text,
            user_requirements=state.requirement or None,
            error=state.error or None,
        ),
    )
    if generated_sdk_code is not None:
        with open(f"{output_dir}/client.py", "w") as f:
            f.write(generated_sdk_code)
    else:
        # NOTE: Instead of raising the error here, we should try generating code again.
        raise ValueError("Failed to generate code.")

    if has_error is None:
        generated_test_code = await direct_chat_completion(
            config=config,
            sys_msg_content=get_test_sys_prompt(),
            usr_msg_content=get_test_usr_prompt(
                swagger_spec=json.dumps(state.spec_json),
                generated_code=generated_sdk_code,
                user_requirements=state.requirement or None,
            ),
        )
        if generated_test_code is not None:
            with open(f"{output_dir}/test_client.py", "w") as f:
                f.write(generated_test_code)
        else:
            # NOTE: Same as above.
            raise ValueError("Failed to generate code.")

    return {
        "status": "generated_code",
        "generated_code": generated_sdk_code,
        "generated_test_code": generated_test_code,
    }


# async def test_code(state: AgentState, configuration: RunnableConfig):
