from rich.layout import Layout
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text


def create_layout() -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=10),
    )

    layout["header"].update(Panel(Text("Rivet Factory", justify="center", style="bold green")))
    layout["body"].update(Panel("Waiting for commands...", title="Status"))
    layout["footer"].update(Panel("Logs will appear here", title="Event Log"))

    return layout


def get_spinner(text: str) -> Spinner:
    return Spinner("dots", text=text, style="cyan")
