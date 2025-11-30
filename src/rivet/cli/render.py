from rich.panel import Panel
from rich.layout import Layout
from rich.syntax import Syntax

def update_on_event(layout: Layout, event: dict):
    if "node_ingest" in event:
        url = event["node_ingest"].get("url", "unknown")
        layout["body"].update(Panel(f"🕷️  Crawling API Documentation at: {url}...", style="blue"))

    elif "node_codegen" in event:
        code = event["node_codegen"].get("partial_code", "# Generating...")
        # Use Syntax to make code look colorful
        syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
        layout["body"].update(Panel(syntax, title="Writing Python Code", border_style="yellow"))

    elif "node_fix" in event:
        error_msg = event["node_fix"].get("error")
        layout["footer"].update(Panel(f"[red]❌ Test Failed:[/red] {error_msg}\n[green]🔧 Applying Fix...[/green]", title="Self-Healing Active"))
