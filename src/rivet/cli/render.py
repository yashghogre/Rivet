from rich.layout import Layout
from rich.panel import Panel
from rich.spinner import Spinner
from rich.syntax import Syntax


def update_on_event(layout: Layout, event: dict):
    if "ingest_node" in event:
        data = event["ingest_node"]
        url = data.get("url", "url")
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

    elif "generate_sdk" in event:
        data = event["generate_sdk"]
        if "error" in data and data["error"]:
            layout["footer"].update(
                Panel(f"[red]❌ Code Generation Failed.[/red]{data['error']}", style="bold red")
            )
        else:
            code = data.get("sdk_code", "# Generating...")
            syntax = Syntax(code[:1000] + "\n...", "python", theme="monokai", line_numbers=True)
            layout["body"].update(
                Panel(syntax, title="Generated SDK Code (Snippet)", border_style="green")
            )
            layout["footer"].update(
                Panel(
                    Spinner("runner", text="🧪 Moving to SDK Validation..."),
                    title="Verification",
                )
            )

    elif "validate_sdk" in event:
        data = event["validate_sdk"]
        if "error" in data and data["error"]:
            layout["footer"].update(
                Panel(f"[red]❌ SDK Validation Failed.[/red]{data['error']}", style="bold red")
            )
        else:
            layout["body"].update(Panel(Spinner("dots", text="✅ SDK Validated Successfully!")))
            layout["footer"].update(
                Panel(
                    Spinner("runner", text="⚒️ Moving to Tests Generation..."),
                    title="Generation",
                )
            )

    elif "generate_tests" in event:
        data = event["generate_tests"]
        if "error" in data and data["error"]:
            layout["footer"].update(
                Panel(f"[red]❌ Tests Generation Failed.[/red]{data['error']}", style="bold red")
            )
        else:
            code = data.get("test_code", "# Generating...")
            syntax = Syntax(code[:1000] + "\n...", "python", theme="monokai", line_numbers=True)
            layout["body"].update(
                Panel(syntax, title="Generated Tests Code (Snippet)", border_style="green")
            )
            layout["footer"].update(
                Panel(
                    Spinner("runner", text="🧪 Moving to Code Testing..."),
                    title="Verification",
                )
            )

    elif "fix_sdk" in event:
        data = event["fix_sdk"]
        if "error" in data and data["error"]:
            layout["footer"].update(
                Panel(f"[red]❌ SDK Fixing Failed.[/red]{data['error']}", style="bold red")
            )
        else:
            code = data.get("sdk_code", "# Generating...")
            syntax = Syntax(code[:1000] + "\n...", "python", theme="monokai", line_numbers=True)
            layout["body"].update(
                Panel(syntax, title="Fixed SDK Code (Snippet)", border_style="green")
            )
            layout["footer"].update(
                Panel(
                    Spinner("runner", text="🧪 Moving to SDK Validation..."),
                    title="Verification",
                )
            )

    elif "fix_tests" in event:
        data = event["fix_tests"]
        if "error" in data and data["error"]:
            layout["footer"].update(
                Panel(f"[red]❌ Tests Fixing Failed.[/red]{data['error']}", style="bold red")
            )
        else:
            code = data.get("test_code", "# Generating...")
            syntax = Syntax(code[:1000] + "\n...", "python", theme="monokai", line_numbers=True)
            layout["body"].update(
                Panel(syntax, title="Fixed Test Code (Snippet)", border_style="green")
            )
            layout["footer"].update(
                Panel(
                    Spinner("runner", text="🧪 Moving to Code Testing..."),
                    title="Verification",
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
                    f"[red]❌ Test Failed:[/red] {error_log[-200:]}\n[green]🔧 Self-Healing Active...[/green]",
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
