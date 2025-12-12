import json
import logging
from typing import Any, Dict, List, Optional, Set

from langchain_core.runnables import RunnableConfig
from rich.console import Console

from rivet.core.inference import direct_chat_completion

console = Console()
logger = logging.getLogger(__name__)


def _extract_refs(obj: Any, refs: Set[str]):
    if isinstance(obj, Dict):
        for k, v in obj.items():
            if k == "$ref" and isinstance(v, str):
                refs.add(v)
            else:
                _extract_refs(v, refs)
    elif isinstance(obj, List):
        for item in obj:
            _extract_refs(item, refs)


def _resolve_dependencies(full_spec: Dict, target_paths: List[str]) -> Dict:
    mini_spec = {
        "openapi": full_spec.get("openapi", "3.0.0"),
        "info": full_spec.get("info", {}),
        "servers": full_spec.get("servers", []),
        "paths": {},
        "components": {
            "schemas": {},
            "securitySchemes": full_spec.get("components", {}).get("securitySchemes", {}),
            "parameters": {},
        },
    }

    ref_queue = set()
    for path in target_paths:
        if path in full_spec.get("paths", {}):
            path_item = full_spec["paths"][path]
            mini_spec["paths"][path] = path_item
            _extract_refs(path_item, ref_queue)

    processed_refs = set()
    while ref_queue:
        ref = ref_queue.pop()
        if ref in processed_refs or not ref.startswith("#/"):
            continue
        processed_refs.add(ref)

        parts = ref.lstrip("#/").split("/")

        curr = full_spec
        valid = True
        for part in parts:
            if isinstance(curr, dict) and part in curr:
                curr = curr[part]
            else:
                valid = False
                break

        if valid:
            category, name = parts[1], parts[2]
            if category not in mini_spec["components"]:
                mini_spec["components"][category] = {}

            mini_spec["components"][category][name] = curr
            _extract_refs(curr, ref_queue)

    logger.info("✅ Spec sliced successfully!")
    console.print("[green]✅ Spec sliced successfully![/green]")
    return mini_spec


def _get_api_menu(full_spec: Dict) -> str:
    lines = []
    for path, methods in full_spec.get("paths", {}).items():
        for method, details in methods.items():
            if method.lower() in ["get", "post", "put", "delete", "patch"]:
                summary = details.get("summary") or details.get("description") or ""
                summary = summary.replace("\n", " ")[:80]
                lines.append(f"{method.upper()} {path} : {summary}")
    # return "\n".join(lines[:500]) # Limit to 500 endpoints to save tokens
    return "\n".join(lines)


async def slice_spec(
    full_spec: Dict,
    config: RunnableConfig,
    requirement: Optional[str] = None,
) -> dict:
    if not requirement or requirement == "full_sdk":
        return full_spec

    api_menu = _get_api_menu(full_spec)
    prompt = f"""
    AVAILABLE ENDPOINTS:
    {api_menu}

    USER REQUIREMENT: "{requirement}"

    TASK: Return a JSON list of paths (strings) that match the requirement.
    - If user wants "Get and Delete Posts", select BOTH the GET and DELETE paths.
    - Return strictly JSON. Example: ["/posts", "/posts/{{id}}"]
    """

    response = await direct_chat_completion(
        config=config,
        sys_msg_content="You are an API Architect. Return JSON string list only.",
        usr_msg_content=prompt,
    )

    try:
        clean_json = response.replace("```json", "").replace("```", "").strip()
        target_paths = json.loads(clean_json)
        if not isinstance(target_paths, list):
            raise ValueError

    except Exception as e:
        logger.error(f"⚠️ Slicing failed. Using full spec. Error: {str(e)}")
        console.print(f"[yellow]⚠️ Slicing failed. Using full spec. Error: {str(e)}[/yellow]")
        return full_spec

    return _resolve_dependencies(full_spec, target_paths)
