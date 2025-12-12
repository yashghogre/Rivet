import json
import logging

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from rich.console import Console

from rivet.core.inference import direct_chat_completion
from rivet.core.schema import AgentState
from rivet.tools.sandbox import run_safe_test
from rivet.tools.scrape import ingest_resource
from rivet.tools.slicer import slice_spec
from rivet.utils.code_cleaner import clean_code
from rivet.utils.prompts import (
    get_code_sys_prompt,
    get_code_usr_prompt,
    get_test_sys_prompt,
    get_test_usr_prompt,
)

console = Console()
logger = logging.getLogger(__name__)


async def ingest_node(state: AgentState, config: RunnableConfig):
    url = state.url

    try:
        spec_json, docs_text = await ingest_resource(url)
        logger.info("✅ Spec ingested successfully!")
        return {
            "spec_json": spec_json,
            "docs_text": docs_text,
            "status": "ingested",
        }

    except ValueError as e:
        logger.error(f"❌ Error while ingesting spec: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
        }


async def slice_node(state: AgentState, config: RunnableConfig):
    try:
        sliced = await slice_spec(state.spec_json, config, state.requirement)

        if not sliced["paths"]:
            return {"status": "error", "error": "No matching endpoints found."}

        logger.info("✅ Spec sliced successfully.")
        return {
            "required_spec": sliced,
            "status": "sliced",
        }

    except Exception as e:
        logger.error(f"❌ Error while slicing spec: {str(e)}")
        return {"status": "error", "error": f"Slicing error: {str(e)}"}


async def generate_code(state: AgentState, config: RunnableConfig):
    config_params = config.get("configurable", {})
    output_dir = config_params.get("output_dir", "./output")
    error = state.error
    generated_test_code = state.test_code

    generated_sdk_code = await direct_chat_completion(
        config=config,
        sys_msg_content=get_code_sys_prompt(),
        usr_msg_content=get_code_usr_prompt(
            swagger_spec=json.dumps(state.required_spec),
            docs_text=state.doc_text,
            user_requirements=state.requirement or None,
            error=error or None,
        ),
    )
    cleaned_generated_sdk_code = clean_code(generated_sdk_code)

    if generated_sdk_code:
        with open(f"{output_dir}/client.py", "w") as f:
            f.write(cleaned_generated_sdk_code)
    else:
        return {
            "status": "error",
            "error": "LLM failed to generate SDK code.",
        }

    generated_test_code = await direct_chat_completion(
        config=config,
        sys_msg_content=get_test_sys_prompt(),
        usr_msg_content=get_test_usr_prompt(
            swagger_spec=json.dumps(state.required_spec),
            generated_code=generated_sdk_code,
            user_requirements=state.requirement or None,
            error=error,
        ),
    )
    cleaned_generated_test_code = clean_code(generated_test_code)

    if generated_test_code:
        with open(f"{output_dir}/test_client.py", "w") as f:
            f.write(cleaned_generated_test_code)
    else:
        return {"status": "error", "error": "LLM failed to generate test code."}

    logger.info("✅ SDK and test code generated successfully!")
    return {
        "status": "generated_code",
        "sdk_code": cleaned_generated_sdk_code,
        "test_code": cleaned_generated_test_code,
        "error": None,
    }


async def test_code(state: AgentState, config: RunnableConfig):
    sdk_code = state.sdk_code
    test_code = state.test_code
    output_dir = config.get("output_dir", "./output")

    passed, logs = await run_safe_test(sdk_code, test_code)
    with open(f"{output_dir}/logs.txt", "w") as f:
        f.write(logs)

    if passed:
        logger.info("✅ Code tests passed!")
        return {
            "status": "success",
            "error": None,
        }
    else:
        logger.info("❌ Code tests failed!")
        return {
            "status": "error",
            "error": logs,
        }


def route_after_test(state: AgentState) -> str:
    if state.status == "success":
        return "end"
    else:
        return "fix"


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("ingest_node", ingest_node)
    workflow.add_node("slice_node", slice_node)
    workflow.add_node("generate_code", generate_code)
    workflow.add_node("test_code", test_code)

    workflow.set_entry_point("ingest_node")

    workflow.add_edge("ingest_node", "slice_node")
    workflow.add_edge("slice_node", "generate_code")
    workflow.add_edge("generate_code", "test_code")

    # TODO: Add a conditional node after "ingest_node", to check
    # if the data has been ingested properly, otherwise END.
    workflow.add_conditional_edges(
        "test_code",
        route_after_test,
        {
            "end": END,
            "fix": "generate_code",
        },
    )

    return workflow.compile()
