from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.messages.base import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from rich.console import Console

console = Console()


async def chat_completion(config: RunnableConfig, msgs: List[BaseMessage]) -> str:
    configurable = config.get("configurable", {})
    llm_api_key = configurable.get("llm_api_key")
    llm_base_url = configurable.get("llm_base_url")
    llm_name = configurable.get("llm_name")

    if not llm_api_key or not llm_base_url or not llm_name:
        console.print(
            "❌ LLM Configuration not set! Please make sure LLM's API key, Base URL and the Model Name is set properly."
        )
        raise ValueError("LLM Configuration not set.")

    try:
        llm = ChatOpenAI(
            model=llm_name,
            openai_api_base=llm_base_url,
            openai_api_key=llm_api_key,
        )
        response = await llm.ainvoke(msgs, config=config)
        return response.content

    except Exception as e:
        console.print(f"❌ Failed to create chat completion: {str(e)}")
        raise


async def direct_chat_completion(
    config: Dict,
    sys_msg_content: str,
    usr_msg_content: str,
) -> str:
    try:
        final_msgs = []
        final_msgs.append(SystemMessage(content=sys_msg_content))
        final_msgs.append(HumanMessage(content=usr_msg_content))
        return await chat_completion(config, final_msgs)

    except Exception as e:
        console.print(f"❌ Failed to create chat completion: {str(e)}")
        raise
