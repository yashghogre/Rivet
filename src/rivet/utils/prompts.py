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

    ### STRICT OUTPUT FORMATTING
    1. **NO MARKDOWN**: Do not use ```python or ``` blocks.
    2. **NO CONVERSATION**: Do not write "Here is the code" or "I have fixed the error".
    3. **PURE CODE**: The very first character of your response must be an import statement (e.g., `import` or `from`).

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
    4. **Error** - to know what error the generated code in the last round threw.

    **CRITICAL MOCKING RULES (DO NOT IGNORE)**
    1. **NO `with Mock()`**: 
       - NEVER write: `with Mock(...) as m:` (This causes TypeError).
       - ALWAYS write: `mock = AsyncMock(...)` or `with patch(...) as m:`.
    
    2. **MOCKING ASYNC CONTEXT MANAGERS**:
       - The SDK likely uses `async with httpx.AsyncClient() as client:`.
       - To mock this, you MUST set the `__aenter__` return value.
       - **REQUIRED PATTERN**:
         ```python
         # In your fixture:
         mock_client_instance = AsyncMock(spec=httpx.AsyncClient)
         mock_client_instance.__aenter__.return_value = mock_client_instance
         
         # If using patch:
         with patch("httpx.AsyncClient", return_value=mock_client_instance):
             yield mock_client_instance
         ```
    
    3. **ASSERTING AUTH HEADERS**:
       - If you initialize the client with `token="test_token"`, the SDK will generate a header like `Bearer test_token`.
       - When asserting, do not expect `"Bearer mock_token"` unless you passed `"mock_token"` into the constructor.
       - **Check the actual arguments** passed to the constructor in your test setup.

    **TECHNICAL CONSTRAINTS**
        - **Framework:** `pytest` and `pytest-asyncio` (if the SDK is async).
        - **Mocking:** Use `unittest.mock` (standard library) or `pytest-mock`.
        - **Imports:** Assume the SDK is in a file named `client.py`. Import as `from client import ...`.
        - **Pydantic Compatibility:**
           - Check the SDK code.
           - If SDK uses `model_dump()`, your tests MUST use `model_dump()` (Pydantic V2).
           - If SDK uses `dict()`, your tests MUST use `dict()` (Pydantic V1).

    **CORE BEHAVIORS**
        - **Coverage:** If `<user_requirements>` are provided, only test those features. Otherwise, cover all main endpoints.
        - **Edge Cases:** Include at least one test case for an API error (e.g., mocking a 404 or 500 response to ensure the SDK raises the correct exception).

    **STRICT OUTPUT FORMATTING**
    1. **NO MARKDOWN**: Do not use ```python or ``` blocks.
    2. **NO CONVERSATION**: Do not write "Here is the code" or "I have fixed the error".
    3. **PURE CODE**: The very first character of your response must be an import statement (e.g., `import` or `from`).

    **OUTPUT REQUIREMENTS**
    Generate a single Python file named `test_client.py` containing:
    1. **Fixtures:** Pytest fixtures to initialize the SDK Client. Use `pytest_asyncio.fixture` for async setup.
    2. **Model Tests:** Unit tests verifying that the Pydantic models correctly validate data (valid data passes, invalid data raises `ValidationError`).
    3. **Client Tests:** Tests for the API methods.
        - **CRITICAL:** You must MOCK all network requests. Do not allow the tests to hit the real API.
        - Use `unittest.mock` or `pytest-mock` to patch the underlying HTTP client (e.g., `httpx.AsyncClient.request` or `requests.Session.request`) or the SDK methods themselves.
        - Verify that the SDK constructs the correct URLs and payloads based on the method arguments.

    **RESPONSE FORMAT**
    Return only the Python code for the test file.
    Ensure you include: `from unittest.mock import AsyncMock, MagicMock, patch`
    **CRITICAL:** Ensure you import `pytest`, `pytest_asyncio`, `httpx`, and all SDK classes.
    Start with imports.
    """)


def get_test_usr_prompt(
    swagger_spec: str,
    generated_code: str,
    user_requirements: Optional[str] = None,
    error: Optional[str] = None,
):
    prompt = dedent(f"""
    Please generate the `pytest` file for the following SDK.

    <api_specification>
    {swagger_spec}
    </api_specification>

    <generated_sdk_code>
    {generated_code}
    </generated_sdk_code>
    """)

    if user_requirements:
        prompt += dedent(f"""
        <user_requirements>
        {user_requirements}
        </user_requirements>
        """)

    if error:
        prompt += dedent(f"""
        <previous_test_failure>
        The previous test suite FAILED. You must fix the code to resolve this specific error.
        
        ERROR LOG:
        {error}
        
        CORRECTION STRATEGIES:
        1. If `ModuleNotFoundError: No module named 'client'`:
           - Ensure you use `from client import ...` (NOT `from src.client` or `from .client`).
        
        2. If `TypeError: 'Mock' object does not support context manager`:
           - You used `with Mock():`. CHANGE IT to the `__aenter__` pattern defined in the system prompt.
        
        3. If `AssertionError` on headers:
           - You are asserting headers that don't match the setup. Check your fixture initialization.
           
        4. If `AttributeError` on Pydantic models:
           - Check if the SDK uses Pydantic V1 (`dict()`) or V2 (`model_dump()`). Match the SDK's usage.
        </previous_test_failure>
        """)

    prompt += dedent("""
    Instructions:
    1. Analyze the `<generated_sdk_code>` to identify Class names, Method names, and Pydantic models.
    2. Refer to `<api_specification>` to generate realistic mock JSON data for the responses.
    3. Write the `test_client.py` file. Assume the SDK code is located in `client.py`.
    """)

    return prompt


def get_fix_sdk_usr_prompt(
    current_sdk: str,
    error_logs: str,
    error_category: str,
    error_suggestion: str,
    error_message: str,
    file_path: Optional[str] = None,
    line_number: Optional[int] = None,
) -> str:
    # Use the last 2000 chars of logs to capture the actual traceback
    relevant_logs = error_logs[-2000:] if error_logs else "No logs available"

    location_info = f"Line {line_number}" if line_number else "Unknown Line"
    if file_path:
        location_info += f" in {file_path}"

    return dedent(f"""
    The SDK code has a specific error that needs fixing.

    ### 1. DIAGNOSIS
    - **Error Category:** {error_category}
    - **Issue:** {error_suggestion}
    - **Specific Error:** {error_message}
    - **Location:** {location_info}

    ### 2. CURRENT SDK CODE
    ```python
    {current_sdk}
    ```

    ### 3. RELEVANT LOGS (Traceback)
    ```text
    {relevant_logs}
    ```

    ### 4. FIX INSTRUCTIONS
    1. **Identify the missing dependency or logic flaw.**
       - If `NameError: name 'json' is not defined`, add `import json`.
       - If `AttributeError: 'Client' has no attribute 'session'`, add `self.session` initialization.
    2. **Apply the fix surgically.** Do not change logic that isn't broken.
    3. **Verify Imports:** Scan the code to ensure all used types (`List`, `Optional`, `Dict`, `Any`) and libraries (`httpx`, `pydantic`) are imported.

    ### 5. OUTPUT
    Return the **COMPLETE** fixed `client.py` file.
    """).strip()


def get_fix_test_sys_prompt():
    return """### ROLE
You are a Senior Python QA Automation Architect specializing in `pytest`, `httpx`, and `asyncio`. 
Your goal is to fix a broken test suite to make it pass against a **verified correct** SDK.

### CRITICAL RULES
1. **SDK IS IMMUTABLE:** Do not modify, assume, or suggest changes to the SDK code. If the Test expects `X` but SDK returns `Y`, change the Test to expect `Y`.
2. **FULL REWRITE:** You must return the **ENTIRE** content of the fixed test file. Do not return snippets or diffs.
3. **IMPORT SAFETY:** You must explicitly ensure `pytest`, `pytest_asyncio`, `httpx`, and all SDK classes are imported.
4. **NO MARKDOWN:** Return ONLY the raw Python code. No conversational filler.
"""


def get_fix_test_usr_prompt(
    current_tests: str,
    sdk_code: str,
    error_logs: str,
    error_category: str,
    error_suggestion: str,
    error_message: str,
) -> str:
    # Use the last 2000 chars to catch the pytest failure summary
    relevant_logs = error_logs[-2000:] if error_logs else "No logs available"

    return dedent(f"""
    We have a test failure. You need to fix `test_client.py` so it passes with the provided `client.py`.

    ### 1. CONTEXT
    - **Error Category:** {error_category}
    - **Issue:** {error_suggestion}
    - **Message:** {error_message}

    ### 2. THE IMMUTABLE SDK (Source of Truth)
    ```python
    {sdk_code}
    ```

    ### 3. THE BROKEN TEST FILE
    ```python
    {current_tests}
    ```

    ### 4. THE ERROR LOGS
    ```text
    {relevant_logs}
    ```

    ### 5. TASK & STRATEGY
    1. **Analyze the Traceback:** Look at the line number in the logs to find the failure.
    2. **Check Mocks (CRITICAL):** - If the error is `TypeError: 'coroutine' object is not iterable`, your mock returned a Coroutine instead of a List/Dict.
       - **Fix:** Ensure you set `.return_value` correctly for async methods. 
       - Example: `mock_client.get.return_value = MagicMock(status_code=200, json=lambda: [...])`
    3. **Check Imports:** Ensure `pytest_asyncio` and `httpx` are imported if used.
    4. **Align Expectations:** If the SDK returns a Pydantic model, ensure the test asserts against model attributes, not dictionary keys.

    ### 6. OUTPUT
    Return the **COMPLETE** fixed `test_client.py` file.
    """).strip()


def get_fix_sdk_sys_prompt() -> str:
    return dedent("""
    ### ROLE
    You are a Senior Python API Developer. You are fixing a specific bug in an existing SDK.

    ### CRITICAL RULES
    1. **SURGICAL FIX:** Only fix the specific error described. Do not refactor working code.
    2. **PRESERVE INTERFACE:** Do not change method signatures or class names unless they are the direct cause of the error.
    3. **FULL REWRITE:** Return the **ENTIRE** corrected `client.py` file. Do not return snippets or diffs.
    4. **DEPENDENCY CHECK:** If the error is `NameError` or `ImportError`, ensure the missing library is added to the top of the file.
    5. **NO MARKDOWN:** Return ONLY the raw Python code. Start with imports.
    """).strip()
