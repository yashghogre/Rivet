from textwrap import dedent
from typing import Optional


def get_code_sys_prompt(error: Optional[str] = None) -> str:
    base_prompt = """### ROLE
You are a Senior Python API Architect specializing in generating production-grade SDKs. Your task is to analyze an OpenAPI/Swagger specification and generate a robust, strictly typed Python SDK."""

    fix_instruction = ""
    if error:
        fix_instruction = """
### ⚠️ CRITICAL: ERROR RECOVERY MODE
The previous code generation failed to execute. You are now in FIX MODE.
1. **Analyze the `<previous_error>` block** in the user message carefully.
2. **Identify the root cause** (e.g., circular imports, invalid Pydantic v2 syntax, undefined variables).
3. **Refactor the code** specifically to resolve this error.
4. **Do NOT** simply output the same code again. You must change the logic to fix the crash.
"""

    return dedent(f"""
    {base_prompt}
    {fix_instruction}
    ### OUTPUT REQUIREMENTS
    You must generate a single, self-contained Python file (or a clear sequence of code blocks) containing:
    1.  **Configuration:** A base `Client` class handling authentication, base URL, and session management.
    2.  **Data Models:** Pydantic `BaseModel` classes for schemas.
    3.  **Methods:** API endpoint methods with snake_case naming and full docstrings.
    4.  **Error Handling:** Custom exception classes.

    ### SCOPE & FILTERING
    - **Critical:** Pay close attention to the `<user_requirements>` section in the prompt.
    - If requirements are present, **filter** the Swagger spec and only implement the requested methods.
    - If requirements are missing, generate the **entire** SDK.

    ### TECHNICAL CONSTRAINTS
    - **Library:** Use `httpx` (async) or `requests`. Default to `httpx`.
    - **Validation:** Use `pydantic` (v2).
    - **Style:** PEP 8.
    - **Ambiguity:** If the spec is ambiguous, mark code with `# TODO: Ambiguous spec`.

    ### RESPONSE FORMAT
    Return only the Python code. Start with imports.
    """).strip()


def get_code_usr_prompt(
    swagger_spec: str,
    docs_text: str,
    user_requirements: Optional[str] = None,
    error: Optional[str] = None,
) -> str:
    requirements_block = ""
    if user_requirements:
        requirements_block = f"""
    <user_requirements>
    {user_requirements}
    </user_requirements>
    """

    error_block = ""
    error_instruction = ""

    if error:
        error_block = f"""
    <previous_error>
    {error}
    </previous_error>
    """
        error_instruction = """
    4. **FIX COMPILATION ERROR:** The previous code generation failed. 
       - Review the trace in `<previous_error>`.
       - Identify the root cause (e.g., circular import, invalid Pydantic syntax).
       - Ensure the new code strictly avoids this specific failure mode."""

    return dedent(f"""
    Please generate the Python SDK based on the following context.

    <api_specification>
    {swagger_spec}
    </api_specification>

    <documentation>
    {docs_text}
    </documentation>
    {requirements_block}{error_block}
    Instructions:
    1. Analyze the `<api_specification>` to build the core logic.
    2. Check `<user_requirements>`.
        - **If provided:** Generate ONLY the SDK components (models, methods, clients) requested by the user, plus any necessary dependencies.
        - **If empty/absent:** Generate the FULL SDK for the entire API specification.
    3. Use `<documentation>` to enhance docstrings and understand edge cases.{error_instruction}
    {5 if error else 4}. Generate the full Python SDK code now.
    """).strip()


def get_test_sys_prompt():
    return dedent("""
    **ROLE**
    You are a Lead QA Automation Engineer. Your task is to write a comprehensive `pytest` test suite for a provided Python SDK.

    **INPUTS**
    You will be provided with:
    1. **The API Specification** (OpenAPI/Swagger) - to understand valid data examples.
    2. **The Generated SDK Code** - to know exactly which class names and method signatures to test.
    3. **User Requirements** - to know which specific parts to focus on (if any).

    **OUTPUT REQUIREMENTS**
    Generate a single Python file named `test_client.py` containing:
    1. **Fixtures:** Pytest fixtures to initialize the SDK Client.
    2. **Model Tests:** Unit tests verifying that the Pydantic models correctly validate data (valid data passes, invalid data raises `ValidationError`).
    3. **Client Tests:** Tests for the API methods.
        - **CRITICAL:** You must MOCK all network requests. Do not allow the tests to hit the real API.
        - Use `unittest.mock` or `pytest-mock` to patch the underlying HTTP client (e.g., `httpx.AsyncClient.request` or `requests.Session.request`) or the SDK methods themselves.
        - Verify that the SDK constructs the correct URLs and payloads based on the method arguments.

    **TECHNICAL CONSTRAINTS**
        - **Framework:** `pytest` and `pytest-asyncio` (if the SDK is async).
        - **Mocking:** Use `unittest.mock` (standard library) or `pytest-mock`.
        - **Imports:** Assume the SDK is in a file named `client.py`. Import as `from client import ...`.

    **CORE BEHAVIORS**
        - **Coverage:** If `<user_requirements>` are provided, only test those features. Otherwise, cover all main endpoints.
        - **Edge Cases:** Include at least one test case for an API error (e.g., mocking a 404 or 500 response to ensure the SDK raises the correct exception).

    **RESPONSE FORMAT**
    Return only the Python code for the test file. Start with imports.
    """)


def get_test_usr_prompt(swagger_spec: str, generated_code: str, user_requirements: str):
    return dedent(f"""
    Please generate the `pytest` file for the following SDK.

    <api_specification>
    {swagger_spec}
    </api_specification>

    <generated_sdk_code>
    {generated_code}
    </generated_sdk_code>

    <user_requirements>
    {user_requirements}
    </user_requirements>

    Instructions:
    1. Analyze the `<generated_sdk_code>` to identify Class names, Method names, and Pydantic models.
    2. Refer to `<api_specification>` to generate realistic mock JSON data for the responses.
    3. Check `<user_requirements>`:
        - If present, only generate tests for the requested features.
        - If absent, generate a comprehensive test suite.
    4. Write the `test_client.py` file. Assume the SDK code is located in `client.py`.
    """)
