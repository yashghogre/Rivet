def clean_code(code: str):
    if code.startswith("```python"):
        code = code[len("```python") :]
    elif code.startswith("```"):
        code = code[len("```") :]

    if code.endswith("```"):
        code = code[: -len("```")]

    return code.strip()
