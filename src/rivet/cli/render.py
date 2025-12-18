import logging

from rich.layout import Layout
from rich.panel import Panel
from rich.spinner import Spinner
from rich.syntax import Syntax

logger = logging.getLogger(__name__)


def update_on_event(layout: Layout, event: dict):
    logger.info(f"TUI Event received: {list(event.keys())}")
    logger.info(f"Full Event data: {event}")

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

    elif "slice_node" in event:
        layout["body"].update(
            Panel(
                Spinner(
                    "dots",
                    text="🔪 Spec sliced successfully.\n\n🧠 Generating SDK code (Calling LLM)...",
                ),
                title="Step 2: Code Generation",
                border_style="yellow",
            )
        )
        layout["footer"].update(
            Panel("✅ Slice complete. Starting LLM Generation...", style="green")
        )

    elif "generate_sdk" in event:
        logger.info("Processing generate_sdk event")
        data = event["generate_sdk"]

        logger.info(f"generate_sdk data: {data}")

        # Show retry count if applicable
        retry_count = data.get("sdk_retry_count", 0)
        retry_msg = f" (Retry {retry_count}/3)" if retry_count > 0 else ""

        if "error" in data and data["error"]:
            layout["footer"].update(
                Panel(
                    f"[red]❌ SDK Generation Failed{retry_msg}:[/red] {data['error']}",
                    style="bold red",
                )
            )
        else:
            code = data.get("sdk_code", "# Generating...")
            syntax = Syntax(code[:1000] + "\n...", "python", theme="monokai", line_numbers=True)
            layout["body"].update(
                Panel(
                    syntax, title=f"Generated SDK Code{retry_msg} (Snippet)", border_style="green"
                )
            )
            layout["footer"].update(
                Panel(
                    Spinner("runner", text="🔍 Validating SDK syntax..."),
                    title="Step 3: Validation",
                    style="cyan",
                )
            )
            logger.info(f"Updated layout['body']. Layout ID: {id(layout)}")

    elif "validate_sdk" in event:
        data = event["validate_sdk"]
        retry_count = data.get("sdk_retry_count", 0)
        retry_msg = f" (Retry {retry_count}/3)" if retry_count > 0 else ""

        if "error" in data and data["error"]:
            layout["footer"].update(
                Panel(f"[red]❌ SDK Validation Failed.[/red]{data['error']}", style="bold red")
            )
        else:
            code = data.get("sdk_code", "# Generating...")
            syntax = Syntax(code[:1000] + "\n...", "python", theme="monokai", line_numbers=True)
            # layout["body"].update(
            #     Panel(
            #         syntax,
            #         title=f"Generated SDK Code{retry_msg} (Snippet)",
            #         border_style="green"
            #     )
            # )
            layout["footer"].update(
                Panel(
                    Spinner(
                        "runner",
                        text="✅ SDK Validated Successfully!\n⚒️ Moving to Tests Generation...",
                    ),
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
