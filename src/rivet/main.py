import asyncio
import logging
import os

import typer
from rich.console import Console
from rich.live import Live
from rich.prompt import Prompt

from rivet.cli.render import update_on_event
from rivet.cli.ui import create_layout
from rivet.core.agent import build_graph
from rivet.core.schema import AgentState
from rivet.tools.url_processor import check_url_validity
from rivet.utils.config import CREDENTIALS_FILE, get_llm_credentials
from rivet.utils.logging import setup_logging

app = typer.Typer(no_args_is_help=True)
console = Console()
logger = logging.getLogger("rivet.main")


@app.command()
def generate(
    url: str = typer.Argument(None, help="Target API URL"),
    requirement: str = typer.Option(
        None, "--req", "-r", help="Specific feature to generate (e.g: 'Payments')"
    ),
    output: str = typer.Option("./output", help="Save directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show debug logs in console"),
):
    log_path = setup_logging(verbose)
    logger.info(f"🚀 Rivet started. Logs: {log_path}")

    os.makedirs(output, exist_ok=True)
    asyncio.run(async_generate(url, requirement, output))


async def async_generate(url: str, requirement: str, output: str):
    llm_base_url, llm_api_key, llm_name = get_llm_credentials()
    console.print(
        f"[dim]💡 LLM configuration stored at {CREDENTIALS_FILE}. Check that file to change the configurations.[/dim]"
    )

    if not url:
        console.print("Welcome to Rivet!", style="bold blue")
        url = Prompt.ask("Paste the [bold blue]API Swagger/OpenAPI/Docs URL[/bold blue]")
        if not check_url_validity(url):
            console.print("[red]Please input a valid URL![/red]")
            return

    if not requirement:
        if (
            Prompt.ask(
                "Do you want to slice the spec for a specific feature?",
                choices=["y", "n"],
                default="n",
            )
            == "y"
        ):
            requirement = Prompt.ask("What feature do you need?")
        else:
            requirement = "full_sdk"

    layout = create_layout()
    graph = build_graph()

    run_config = {
        "configurable": {
            "llm_api_key": llm_api_key,
            "llm_base_url": llm_base_url,
            "llm_name": llm_name,
            "user_id": "local_user",
            "output_dir": output,
        },
    }

    initial_state = AgentState(
        url=url,
        requirement=requirement,
    )

    logger.info(f"Starting the agent with state: {initial_state.model_dump_json(indent=2)}")

    with Live(layout, refresh_per_second=4, console=console):
        async for event in graph.astream(initial_state, config=run_config):
            update_on_event(layout, event)

    console.print(f"[bold green]Done! SDK saved to: {output}[/bold green]")


if __name__ == "__main__":
    app()
