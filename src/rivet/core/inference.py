from typing import Dict, List

from openai import AsyncOpenAI
from rich.console import Console

from rivet.core.schema import Message

console = Console()


async def chat_completion(config: Dict, msgs: List[Message]) -> str:
    llm_api_key = config.get("llm_api_key")
    llm_base_url = config.get("llm_base_url")
    llm_name = config.get("llm_name")

    if not llm_api_key or not llm_base_url or not llm_name:
        console.print(
            "❌ LLM Configuration not set! Please make sure LLM's API key, Base URL and the Model Name is set properly."
        )
        raise ValueError("LLM Configuration not set.")

    try:
        client = AsyncOpenAI(
            base_url=llm_base_url,
            api_key=llm_api_key,
        )
        response = await client.chat.completions.create(
            model=llm_name,
            messages=[msg.model_dump() for msg in msgs],
        )
        return response.choices[0].message.content

    except Exception as e:
        console.print(f"❌ Failed to create chat completion: {str(e)}")
        raise


async def direct_chat_completion(
    config: Dict,
    sys_msg_content: str,
    usr_msg_content: str,
) -> str:
    try:
        sys_msg = Message(
            role="system",
            content=sys_msg_content,
        )
        usr_msg = Message(
            role="user",
            content=usr_msg_content,
        )
        final_msgs = [sys_msg, usr_msg]
        return await chat_completion(config, final_msgs)

    except Exception as e:
        console.print(f"❌ Failed to create chat completion: {str(e)}")
        raise
