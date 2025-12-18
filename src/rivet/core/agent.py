import ast
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
from rivet.utils.errors import get_error_analysis
from rivet.utils.prompts import (
    get_code_sys_prompt,
    get_code_usr_prompt,
    get_fix_sdk_sys_prompt,
    get_fix_sdk_usr_prompt,
    get_fix_test_sys_prompt,
    get_fix_test_usr_prompt,
    get_test_sys_prompt,
    get_test_usr_prompt,
)

console = Console()
logger = logging.getLogger(__name__)

# This belongs in RunnableConfig.configurable,
# But we will make do with this for now.
MAX_SDK_RETRIES = 5
MAX_TEST_RETRIES = 5


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


# SDK GENERATION AND VALIDATION


async def generate_sdk(state: AgentState, config: RunnableConfig):
    config_params = config.get("configurable", {})
    output_dir = config_params.get("output_dir", "./output")

    error_context = None
    if state.error_analysis:
        analysis = state.error_analysis
        if analysis.get("is_sdk_error"):
            error_context = analysis.get("suggestion")
            logger.warning(f"⚠️ Regenerating SDK due to: {error_context}")

    logger.info("🔧 Generating SDK code...")
    raw_sdk_code = await direct_chat_completion(
        config=config,
        sys_msg_content=get_code_sys_prompt(),
        usr_msg_content=get_code_usr_prompt(
            swagger_spec=json.dumps(state.required_spec),
            docs_text=state.doc_text,
            user_requirements=state.requirement or None,
            error=error_context,
        ),
    )

    generated_sdk_code = clean_code(raw_sdk_code)

    if not generated_sdk_code:
        logger.error("❌ LLM failed to generate SDK code")
        return {
            "status": "error",
            "error": "LLM failed to generate SDK code.",
        }

    try:
        with open(f"{output_dir}/client.py", "w") as f:
            f.write(generated_sdk_code)
        logger.info("✅ SDK code generated and saved")
    except Exception as e:
        logger.error(f"❌ Failed to save SDK code: {str(e)}")
        return {"status": "error", "error": f"Failed to save SDK: {str(e)}"}

    return {
        "status": "sdk_generated",
        "sdk_code": generated_sdk_code,
        "error": None,
        "error_analysis": {},  # Clear previous error
    }


async def validate_sdk(state: AgentState, config: RunnableConfig):
    sdk_code = state.sdk_code

    if not sdk_code:
        return {
            "status": "sdk_invalid",
            "error": "No SDK code to validate",
        }

    logger.info("🔍 Validating SDK syntax...")

    try:
        compile(sdk_code, "<string>", "exec")

        ast.parse(sdk_code)

        validation_issues = []

        if "import httpx" not in sdk_code and "from httpx" not in sdk_code:
            validation_issues.append("Warning: 'httpx' library not imported")

        if "class " not in sdk_code:
            validation_issues.append("Warning: No class definitions found")

        if validation_issues:
            logger.warning(f"⚠️ SDK validation warnings: {validation_issues}")

        logger.info("✅ SDK syntax is valid")
        return {
            "status": "sdk_valid",
        }

    except SyntaxError as e:
        logger.error(f"❌ SDK syntax error: {str(e)}")
        error_msg = f"SyntaxError: {str(e)} at line {e.lineno}"
        return {
            "status": "sdk_invalid",
            "error": error_msg,
            "error_analysis": {
                "category": "sdk_syntax",
                "is_sdk_error": True,
                "severity": "critical",
                "suggestion": f"Fix syntax error at line {e.lineno}: {str(e)}",
            },
        }

    except Exception as e:
        logger.error(f"❌ SDK validation failed: {str(e)}")
        return {
            "status": "sdk_invalid",
            "error": str(e),
            "error_analysis": {
                "category": "sdk_syntax",
                "is_sdk_error": True,
                "severity": "high",
                "suggestion": f"Validation error: {str(e)}",
            },
        }


# TEST GENERATION


async def generate_tests(state: AgentState, config: RunnableConfig):
    config_params = config.get("configurable", {})
    output_dir = config_params.get("output_dir", "./output")

    sdk_code = state.sdk_code

    error_context = None
    if state.error_analysis:
        analysis = state.error_analysis
        if not analysis.get("is_sdk_error"):
            error_context = analysis.get("suggestion")
            logger.warning(f"⚠️ Regenerating tests due to: {error_context}")

    logger.info("🧪 Generating test code...")
    raw_test_code = await direct_chat_completion(
        config=config,
        sys_msg_content=get_test_sys_prompt(),
        usr_msg_content=get_test_usr_prompt(
            swagger_spec=json.dumps(state.required_spec),
            generated_code=sdk_code,
            user_requirements=state.requirement or None,
            error=error_context,
        ),
    )

    generated_test_code = clean_code(raw_test_code)

    if not generated_test_code:
        logger.error("❌ LLM failed to generate test code")
        return {
            "status": "error",
            "error": "LLM failed to generate test code.",
        }

    try:
        with open(f"{output_dir}/test_client.py", "w") as f:
            f.write(generated_test_code)
        logger.info("✅ Test code generated and saved")
    except Exception as e:
        logger.error(f"❌ Failed to save test code: {str(e)}")
        return {"status": "error", "error": f"Failed to save tests: {str(e)}"}

    return {
        "status": "tests_generated",
        "test_code": generated_test_code,
        "error": None,
        "error_analysis": {},
    }


# TEST EXECUTION AND ANALYSIS


async def test_code(state: AgentState, config: RunnableConfig):
    sdk_code = state.sdk_code
    test_code = state.test_code
    config_params = config.get("configurable", {})
    output_dir = config_params.get("output_dir", "./output")

    logger.info("🧪 Running tests...")
    passed, logs = await run_safe_test(sdk_code, test_code)

    # Save test logs
    try:
        with open(f"{output_dir}/logs.txt", "w") as f:
            f.write(logs)
    except Exception as e:
        logger.warning(f"⚠️ Failed to save logs: {str(e)}")

    if passed:
        logger.info("✅ All tests passed!")
        return {
            "status": "success",
            "error": None,
            "error_analysis": {},
        }

    logger.info("❌ Tests failed, analyzing errors...")

    analysis = get_error_analysis(logs)

    if not analysis:
        logger.error("❌ Could not analyze test failure")
        return {
            "status": "error",
            "error": logs,
            "error_analysis": {
                "category": "unknown",
                "is_sdk_error": True,
                "severity": "high",
                "suggestion": "Could not categorize error. Check logs manually.",
            },
        }

    logger.info("📊 Error Analysis:")
    logger.info(f"   Category: {analysis.category.value}")
    logger.info(f"   Type: {analysis.error_type}")
    logger.info(f"   Severity: {analysis.severity}")
    logger.info(f"   SDK Error: {analysis.is_sdk_error}")
    logger.info(f"   Suggestion: {analysis.suggested_action}")

    return {
        "status": "test_failed",
        "error": logs,
        "error_analysis": {
            "category": analysis.category.value,
            "is_sdk_error": analysis.is_sdk_error,
            "severity": analysis.severity,
            "suggestion": analysis.suggested_action,
            "error_type": analysis.error_type,
            "error_message": analysis.error_message,
            "file_path": analysis.file_path,
            "line_number": analysis.line_number,
        },
    }


# TARGETED FIX NODES


async def fix_sdk_targeted(state: AgentState, config: RunnableConfig):
    analysis = state.error_analysis
    current_sdk = state.sdk_code
    error_logs = state.error

    sdk_retry_count = state.sdk_retry_count + 1
    logger.info(f"🔧 Fixing SDK (attempt {sdk_retry_count}/3)...")

    error_category = analysis.get("category", "unknown")
    error_suggestion = analysis.get("suggestion", "Fix the error")
    error_message = analysis.get("error_message", "")
    file_path = analysis.get("file_path", "")
    line_number = analysis.get("line_number", "")

    fix_prompt = get_fix_sdk_usr_prompt(
        current_sdk=current_sdk,
        error_logs=error_logs,
        error_category=error_category,
        error_suggestion=error_suggestion,
        error_message=error_message,
        file_path=file_path,
        line_number=line_number,
    )

    config_params = config.get("configurable", {})
    output_dir = config_params.get("output_dir", "./output")

    fixed_sdk_code = await direct_chat_completion(
        config=config,
        sys_msg_content=get_fix_sdk_sys_prompt(),
        usr_msg_content=fix_prompt,
    )

    fixed_sdk_code = clean_code(fixed_sdk_code)

    if not fixed_sdk_code:
        logger.error("❌ Failed to fix SDK code")
        return {
            "status": "error",
            "error": "Failed to generate fixed SDK code",
        }

    try:
        with open(f"{output_dir}/client.py", "w") as f:
            f.write(fixed_sdk_code)
        logger.info("✅ SDK fix applied and saved")
    except Exception as e:
        logger.error(f"❌ Failed to save fixed SDK: {str(e)}")

    return {
        "sdk_code": fixed_sdk_code,
        "sdk_retry_count": sdk_retry_count,
        "status": "sdk_fixed",
        "error": None,
    }


async def fix_tests_targeted(state: AgentState, config: RunnableConfig):
    analysis = state.error_analysis
    current_tests = state.test_code
    sdk_code = state.sdk_code
    error_logs = state.error

    test_retry_count = state.test_retry_count + 1
    logger.info(f"🧪 Fixing tests (attempt {test_retry_count}/3)...")

    error_category = analysis.get("category", "unknown")
    error_suggestion = analysis.get("suggestion", "Fix the error")
    error_message = analysis.get("error_message", "")

    fix_prompt = get_fix_test_usr_prompt(
        current_tests=current_tests,
        sdk_code=sdk_code,
        error_logs=error_logs,
        error_category=error_category,
        error_suggestion=error_suggestion,
        error_message=error_message,
    )

    config_params = config.get("configurable", {})
    output_dir = config_params.get("output_dir", "./output")

    fixed_test_code = await direct_chat_completion(
        config=config,
        sys_msg_content=get_fix_test_sys_prompt(),
        usr_msg_content=fix_prompt,
    )

    fixed_test_code = clean_code(fixed_test_code)

    if not fixed_test_code:
        logger.error("❌ Failed to fix test code")
        return {
            "status": "error",
            "error": "Failed to generate fixed test code",
        }

    try:
        with open(f"{output_dir}/test_client.py", "w") as f:
            f.write(fixed_test_code)
        logger.info("✅ Test fix applied and saved")
    except Exception as e:
        logger.error(f"❌ Failed to save fixed tests: {str(e)}")

    return {
        "test_code": fixed_test_code,
        "test_retry_count": test_retry_count,
        "status": "tests_fixed",
        "error": None,
    }


# ROUTING FUNCTIONS


def route_after_sdk_validation(state: AgentState) -> str:
    if state.status == "sdk_valid":
        return "generate_tests"

    sdk_retry_count = state.sdk_retry_count

    if sdk_retry_count >= MAX_SDK_RETRIES:
        logger.error(f"❌ Max SDK retry limit reached ({MAX_SDK_RETRIES})")
        return "end"

    logger.info(f"🔄 Retrying SDK fix ({sdk_retry_count + 1}/{MAX_SDK_RETRIES})")
    return "fix_sdk"


def route_after_test(state: AgentState) -> str:
    if state.status == "success":
        return "end"

    analysis = state.error_analysis

    if not analysis:
        logger.error("❌ No error analysis available, ending workflow")
        return "end"

    sdk_retry_count = state.sdk_retry_count
    test_retry_count = state.test_retry_count

    if analysis.get("is_sdk_error"):
        if sdk_retry_count >= MAX_SDK_RETRIES:
            logger.error(f"❌ Max SDK retry limit reached ({MAX_SDK_RETRIES})")
            return "end"

        logger.info(f"🔄 Routing to SDK fix ({sdk_retry_count + 1}/{MAX_SDK_RETRIES})")
        return "fix_sdk"
    else:
        if test_retry_count >= MAX_TEST_RETRIES:
            logger.error(f"❌ Max test retry limit reached ({MAX_TEST_RETRIES})")
            return "end"

        logger.info(f"🔄 Routing to test fix ({test_retry_count + 1}/{MAX_TEST_RETRIES})")
        return "fix_tests"


# GRAPH CONSTRUCTION


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("ingest_node", ingest_node)
    workflow.add_node("slice_node", slice_node)
    workflow.add_node("generate_sdk", generate_sdk)
    workflow.add_node("validate_sdk", validate_sdk)
    workflow.add_node("generate_tests", generate_tests)
    workflow.add_node("test_code", test_code)
    workflow.add_node("fix_sdk", fix_sdk_targeted)
    workflow.add_node("fix_tests", fix_tests_targeted)

    workflow.set_entry_point("ingest_node")

    workflow.add_edge("ingest_node", "slice_node")
    workflow.add_edge("slice_node", "generate_sdk")
    workflow.add_edge("generate_sdk", "validate_sdk")

    workflow.add_conditional_edges(
        "validate_sdk",
        route_after_sdk_validation,
        {
            "generate_tests": "generate_tests",
            "fix_sdk": "fix_sdk",
            "end": END,
        },
    )

    workflow.add_edge("fix_sdk", "validate_sdk")

    workflow.add_edge("generate_tests", "test_code")

    workflow.add_conditional_edges(
        "test_code",
        route_after_test,
        {
            "end": END,
            "fix_sdk": "fix_sdk",
            "fix_tests": "fix_tests",
        },
    )

    workflow.add_edge("fix_tests", "test_code")

    return workflow.compile()
