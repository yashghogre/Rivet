import json
import logging
import os
import stat
from pathlib import Path
from typing import Tuple

import platformdirs
from rich.console import Console
from rich.prompt import Prompt

SERVICE_NAME = "rivet-tool"
USERNAME_LLM_API_KEY = "llm_api_key"
USERNAME_LLM_BASE_URL = "llm_api_url"
USERNAME_LLM_NAME = "llm_name"
CREDENTIALS_FILE = Path(platformdirs.user_config_dir("rivet")) / "credentials.json"

console = Console()
logger = logging.getLogger(__name__)


def _save_to_file_fallback(key: str, value: str):
    try:
        CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}

        if CREDENTIALS_FILE.exists():
            try:
                with open(CREDENTIALS_FILE, "r") as f:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        data = {}
            except Exception:
                data = {}

        data[key] = value

        with open(CREDENTIALS_FILE, "w") as f:
            json.dump(data, f, indent=2)
        os.chmod(CREDENTIALS_FILE, stat.S_IREAD | stat.S_IWRITE)

        logger.info("✅ Saved the LLM config to fallback file successfully!")

    except Exception as e:
        logger.error(f"❌ Could not save to fallback file: {e}")
        console.print(f"[red]❌ Could not save to fallback file: {e}[/red]")


def _load_from_file_fallback(entity: str) -> str | None:
    if not CREDENTIALS_FILE.exists():
        return None
    try:
        with open(CREDENTIALS_FILE, "r") as f:
            data = json.load(f)
            return data.get(entity)
    except Exception:
        logger.error("❌ Failed to load the LLM config from fallback file.")
        return None


def set_llm_api_key() -> str:
    new_key = Prompt.ask("🔑 Please paste your LLM API Key", password=True)
    _save_to_file_fallback(USERNAME_LLM_API_KEY, new_key)
    console.print(f"[green]✅ Key saved securely to {CREDENTIALS_FILE}[/green]")
    return new_key


def get_llm_api_key() -> str:
    file_key = _load_from_file_fallback("llm_api_key")
    if file_key:
        return file_key
    new_key = set_llm_api_key()
    return new_key


def set_llm_api_url() -> str:
    new_key = Prompt.ask("🔗 Please paste your LLM API URL")
    _save_to_file_fallback(USERNAME_LLM_BASE_URL, new_key)
    console.print(f"[green]✅ Key saved securely to {CREDENTIALS_FILE}[/green]")
    return new_key


def get_llm_api_url() -> str:
    file_key = _load_from_file_fallback("llm_api_url")
    if file_key:
        return file_key
    new_key = set_llm_api_url()
    return new_key


def set_llm_name() -> str:
    llm_name = Prompt.ask("🤖 Please enter your LLM Model Name")
    _save_to_file_fallback(USERNAME_LLM_NAME, llm_name)
    console.print(f"[green]✅ LLM Model Name saved securely to {CREDENTIALS_FILE}[/green]")
    return llm_name


def get_llm_name() -> str:
    file_key = _load_from_file_fallback("llm_name")
    if file_key:
        return file_key
    llm_name = set_llm_name()
    return llm_name


def get_llm_credentials() -> Tuple[str, str, str]:
    llm_api_url = get_llm_api_url()
    llm_api_key = get_llm_api_key()
    llm_name = get_llm_name()
    return (llm_api_url, llm_api_key, llm_name)


"""
def reset_api_key():
    try:
        console.print("[green]🗑️ API key removed from secured storage.[/green]")

    except Exception:
        console.print("[yellow]⚠️ No Key was stored!")
"""
