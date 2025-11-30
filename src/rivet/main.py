import typer
from rich.live import Live
from rich.console import Console

from rivet.cli.ui import create_layout
from rivet.cli.render import update_on_event
from rivet.core.agent import build_graph


app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def generate(
    url: str = typer.Argument(..., help="Target API URL"),
    output: str = typer.Option("./output", help="Save directory"),
):
    layout = create_layout()
    graph = build_graph()
    initial_state = {"url": url}

    with Live(layout, refresh_per_second=4, console=console):
        for event in graph.stream(initial_state):
            update_on_event(layout, event)

    console.print(f"[bold green]Done! SDK saved to: {output}[/bold green]")

if __name__ == "__main__":
    app()
