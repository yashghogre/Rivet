import re


def clean_code(code: str):
    code_block_pattern = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL)
    match = code_block_pattern.search(code)
    if match:
        return match.group(1).strip()

    code = code.strip()
    if code.startswith("```python"):
        code = code[len("```python") :]
    elif code.startswith("```"):
        code = code[len("```") :]

    if code.endswith("```"):
        code = code[: -len("```")]

    return code.strip()
