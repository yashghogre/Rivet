import typer
from rich.console import Console
from rich.live import Live
from rich.prompt import Prompt

from rivet.cli.render import update_on_event
from rivet.cli.ui import create_layout
from rivet.core.agent import build_graph
from rivet.utils.config import get_api_key, reset_api_key

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def generate(
    url: str = typer.Argument(None, help="Target API URL"),
    requirement: str = typer.Option(
        None, "--req", "-r", help="Specific feature to generate (e.g: 'Payments')"
    ),
    output: str = typer.Option("./output", help="Save directory"),
):
    api_key = get_api_key()

    if not url:
        console.print("Welcome to Rivet!", style="bold blue")
        url = Prompt.ask("Paste the [bold blue]API Docs URL[/bold blue]")

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
    initial_state = {
        "url": url,
        "requirement": requirement,
        "api_key": api_key,
    }

    with Live(layout, refresh_per_second=4, console=console):
        for event in graph.stream(initial_state):
            update_on_event(layout, event)

    console.print(f"[bold green]Done! SDK saved to: {output}[/bold green]")


@app.command()
def logout():
    reset_api_key()


if __name__ == "__main__":
    app()
