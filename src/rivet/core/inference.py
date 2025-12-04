from typing import Dict, List

from litellm import acompletion
from rich.console import Console

from rivet.core.schema import Message

console = Console()


async def chat_completion(config: Dict, msgs: List[Message]):
    llm_api_key = config.get("llm_api_key")
    llm_base_url = config.get("llm_base_url")
    llm_name = config.get("llm_name")

    if not llm_api_key or not llm_base_url or not llm_name:
        console.print(
            "❌ LLM Configuration not set! Please make sure LLM's API key, Base URL and the Model Name is set properly."
        )
        raise ValueError("LLM Configuration not set.")

    response = await acompletion(
        model=llm_name,
        base_url=llm_base_url,
        api_key=llm_api_key,
        messages=[msg.model_dump() for msg in msgs],
    )

    return response.choices[0].message.content
