from rich.layout import Layout
from rich.panel import Panel
from rich.spinner import Spinner
from rich.syntax import Syntax


def update_on_event(layout: Layout, event: dict):
    if "ingest_node" in event:
        data = event["ingest_node"]
        url = data.get("url", "unknown")
        layout["footer"].update(Panel(f"🕷️  Crawling API Documentation at: {url}...", style="blue"))

        if "error" in data and data["error"]:
            layout["footer"].update(
                Panel(f"[red]❌ Ingest failed:[/red]{data['error']}", style="bold red")
            )
        else:
            layout["body"].update(
                Panel(
                    Spinner(
                        "dots",
                        text=f"✅ Ingested: {url}\n\n🧠 Generating SDK code (This may take some time...)",
                    ),
                    title="Step 2: Code Generation",
                    border_style="yellow",
                )
            )

    elif "generate_code" in event:
        data = event["generate_code"]
        if "error" in data and data["error"]:
            layout["footer"].update(
                Panel(f"[red]❌ Code Generation Failed.[/red]{data['error']}", style="bold red")
            )
        else:
            code = data.get("sdk_code", "# Generating...")
            syntax = Syntax(code[:1000] + "\n...", "python", theme="monokai", line_numbers=True)
            layout["body"].update(
                Panel(syntax, title="Generated Code (Snippet)", border_style="green")
            )
            layout["footer"].update(
                Panel(
                    Spinner("runner", text="🧪 Moving to Sandbox Testing..."),
                    title="Step 3: Verification",
                )
            )

    elif "test_code" in event:
        data = event["test_code"]
        status = data.get("status")
        if status == "success":
            layout["footer"].update(
                Panel(
                    "[bold green]✅ All Tests Passed! SDK is ready.[/bold green]", title="Success"
                )
            )
        else:
            error_log = data.get("error", "Unknown Error")
            layout["footer"].update(
                Panel(
                    f"[red]❌ Test Failed:[/red] {error_log}\n[green]🔧 Self-Healing Active...[/green]",
                    title="Self-Healing Active",
                    border_style="red",
                )
            )
            layout["body"].update(
                Panel(
                    Spinner("earth", text="🔧 Agent is analyzing the error and fixing the code..."),
                    title="Self-Healing Loop",
                    border_style="orange1",
                )
            )
