import os

import keyring
from rich.console import Console
from rich.prompt import Prompt

SERVICE_NAME = "rivet-tool"
USERNAME = "api_key"

console = Console()


def get_api_key() -> str:
    env_key = os.getenv("RIVET_API_KEY")
    if env_key:
        return env_key

    try:
        stored_key = keyring.get_password(SERVICE_NAME, USERNAME)
        if stored_key:
            return stored_key

    except Exception:
        pass

    console.print("[yellow]⚠️ API Key not found![/yellow]")
    new_key = Prompt.ask("🔑 Please paste your API Key", password=True)

    try:
        keyring.set_password(SERVICE_NAME, USERNAME, new_key)
        console.print("[green]✅ Key saved securely to OS Keyring[/green]")

    except Exception:
        console.print("[red]Could not save to Keyring. Please paste the key next time![/red]")

    return new_key


def reset_api_key():
    try:
        keyring.delete_password(SERVICE_NAME, USERNAME)
        console.print("[green]🗑️ API key removed from secured storage.[/green]")

    except keyring.errors.PasswordDeleteError:
        console.print("[yellow]⚠️ No Key was stored!")
