"""Command-line interface for the data agent."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from .agent import Agent
from .db import get_default_warehouse

console = Console()

BANNER = """
██████╗  █████╗ ████████╗ █████╗      █████╗  ██████╗ ███████╗███╗   ██╗████████╗
██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
██║  ██║███████║   ██║   ███████║    ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   
██║  ██║██╔══██║   ██║   ██╔══██║    ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   
██████╔╝██║  ██║   ██║   ██║  ██║    ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   
╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   
"""


def show_banner():
    """Display the welcome banner."""
    console.print(Text(BANNER, style="bold medium_purple"))
    console.print("  [dim]Ad-hoc analytics powered by AI[/dim]\n")


def show_loading():
    """Show a simple horizontal loading bar."""
    from rich.progress import Progress, BarColumn
    import time
    
    with Progress(
        BarColumn(bar_width=50, style="dim white", complete_style="medium_purple", finished_style="medium_purple"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("", total=100)
        while not progress.finished:
            progress.update(task, advance=4)
            time.sleep(0.02)


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Data platform CLI agent for ad-hoc analysis."""
    if ctx.invoked_subcommand is None:
        # No subcommand = run interactive mode
        run_repl()


@cli.command()
def schema():
    """Show the warehouse schema."""
    show_banner()
    warehouse = get_default_warehouse()
    console.print(Panel(warehouse.get_schema_summary(["raw", "staging", "marts"]), 
                        title="[bold]Database Schema[/bold]", 
                        border_style="medium_purple"))
    warehouse.close()


@cli.command()
@click.argument("question")
def ask(question: str):
    """Ask a question about the data.
    
    Examples:
        agent ask "How much revenue did we do last quarter?"
        agent ask "What are the top 5 products by sales?"
    """
    show_banner()
    console.print(f"[bold]Question:[/bold] {question}\n")
    
    agent = Agent()
    show_loading()
    response = agent.chat(question)
    
    console.print(Panel(Markdown(response), title="[bold]Answer[/bold]", border_style="medium_purple"))


@cli.command()
@click.argument("question")
def sql(question: str):
    """Generate SQL for a question (without executing).
    
    Examples:
        agent sql "Show me monthly revenue trends"
    """
    show_banner()
    console.print(f"[bold]Question:[/bold] {question}\n")
    
    agent = Agent()
    show_loading()
    sql_query = agent.generate_sql(question)
    
    console.print(Panel(sql_query, title="[bold]Generated SQL[/bold]", border_style="medium_purple"))


def run_repl():
    """Run the interactive REPL session."""
    show_banner()
    console.print("[dim]Ask questions about your data. Press [bold]Ctrl+C[/bold] to quit.[/dim]")
    console.print("[dim]Commands: [bold]schema[/bold] - view tables, [bold]exit[/bold] - quit[/dim]")
    console.print("─" * 60 + "\n")
    
    agent = Agent()
    
    while True:
        try:
            question = console.input("[bold medium_purple]You >[/bold medium_purple] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break
        
        question = question.strip()
        
        if not question:
            continue
        if question.lower() in ("exit", "quit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break
        if question.lower() == "schema":
            console.print(Panel(agent.schema_summary, title="[bold]Schema[/bold]", border_style="medium_purple"))
            continue
        if question.lower() == "help":
            console.print("[dim]Commands: [bold]schema[/bold] - view tables, [bold]exit[/bold] - quit[/dim]")
            console.print("[dim]Or just type a question about your data![/dim]")
            continue
        
        show_loading()
        response = agent.chat(question)
        console.print()
        console.print(Panel(Markdown(response), title="[bold]Answer[/bold]", border_style="medium_purple"))
        console.print()


@cli.command()
def repl():
    """Start an interactive session."""
    run_repl()


def main():
    cli()


if __name__ == "__main__":
    main()
