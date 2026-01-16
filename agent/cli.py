"""Command-line interface for the data agent."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.markdown import Markdown
from rich.table import Table
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
    console.print(Text(BANNER, style="bold purple4"))
    console.print("  [dim]Ad-hoc analytics powered by AI[/dim]\n")


def show_loading(task_name: str = "Thinking"):
    """Show a loading bar animation."""
    with Progress(
        TextColumn("[bold purple4]{task.description}"),
        BarColumn(bar_width=40, style="purple4", complete_style="bold purple4"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(task_name, total=100)
        while not progress.finished:
            progress.update(task, advance=2)
            import time
            time.sleep(0.02)


@click.group()
def cli():
    """Data platform CLI agent for ad-hoc analysis."""
    pass


@cli.command()
def schema():
    """Show the warehouse schema."""
    show_banner()
    warehouse = get_default_warehouse()
    console.print(Panel(warehouse.get_schema_summary(["raw", "staging", "marts"]), 
                        title="[bold]Database Schema[/bold]", 
                        border_style="purple4"))
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
    show_loading("Analyzing")
    response = agent.chat(question)
    
    console.print(Panel(Markdown(response), title="[bold]Answer[/bold]", border_style="green"))


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
    show_loading("Generating SQL")
    sql_query = agent.generate_sql(question)
    
    console.print(Panel(sql_query, title="[bold]Generated SQL[/bold]", border_style="yellow"))


@cli.command()
def repl():
    """Start an interactive session."""
    show_banner()
    console.print("[dim]Type your questions below. Commands: 'exit' to quit, 'schema' to see tables[/dim]")
    console.print("─" * 60 + "\n")
    
    agent = Agent()
    
    while True:
        try:
            question = console.input("[bold purple4]You >[/bold purple4] ")
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
            console.print(Panel(agent.schema_summary, title="[bold]Schema[/bold]", border_style="magenta"))
            continue
        
        show_loading("Analyzing")
        response = agent.chat(question)
        console.print()
        console.print(Panel(Markdown(response), title="[bold]Answer[/bold]", border_style="green"))
        console.print()


def main():
    cli()


if __name__ == "__main__":
    main()