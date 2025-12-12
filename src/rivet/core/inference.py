import logging
from typing import List

from langchain_core.runnables import RunnableConfig
from openai import AsyncOpenAI
from rich.console import Console

from rivet.core.schema import Message

console = Console()
logger = logging.getLogger(__name__)


async def chat_completion(config: RunnableConfig, msgs: List[Message]) -> str:
    config_params = config.get("configurable", {})
    llm_api_key = config_params.get("llm_api_key")
    llm_base_url = config_params.get("llm_base_url")
    llm_name = config_params.get("llm_name")

    if not llm_api_key or not llm_base_url or not llm_name:
        logger.error("❌ LLM Configuration not set!")
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
        logger.error(f"❌ Failed to create chat completion: {str(e)}")
        console.print(f"❌ Failed to create chat completion: {str(e)}")
        raise


async def direct_chat_completion(
    config: RunnableConfig,
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
        logger.error(f"❌ Failed to create chat completion: {str(e)}")
        console.print(f"❌ Failed to create chat completion: {str(e)}")
        raise
