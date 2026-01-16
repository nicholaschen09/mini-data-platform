"""Command-line interface for the data agent."""

import click
from .agent import Agent
from .db import get_default_warehouse


@click.group()
def cli():
    """Data platform CLI agent for ad-hoc analysis."""
    pass


@cli.command()
def schema():
    """Show the warehouse schema."""
    warehouse = get_default_warehouse()
    click.echo(warehouse.get_schema_summary(["raw", "staging", "marts"]))
    warehouse.close()


@cli.command()
@click.argument("question")
def ask(question: str):
    """Ask a question about the data.
    
    Examples:
        agent ask "How much revenue did we do last quarter?"
        agent ask "What are the top 5 products by sales?"
    """
    agent = Agent()
    response = agent.chat(question)
    click.echo(response)


@cli.command()
@click.argument("question")
def sql(question: str):
    """Generate SQL for a question (without executing).
    
    Examples:
        agent sql "Show me monthly revenue trends"
    """
    agent = Agent()
    sql_query = agent.generate_sql(question)
    click.echo(sql_query)


@cli.command()
def repl():
    """Start an interactive session."""
    click.echo("Data Agent REPL (type 'exit' to quit, 'schema' to see tables)")
    click.echo("-" * 50)
    
    agent = Agent()
    
    while True:
        try:
            question = click.prompt("\nYou", prompt_suffix="> ")
        except (EOFError, KeyboardInterrupt):
            click.echo("\nGoodbye!")
            break
        
        question = question.strip()
        
        if not question:
            continue
        if question.lower() in ("exit", "quit", "q"):
            click.echo("Goodbye!")
            break
        if question.lower() == "schema":
            click.echo(agent.schema_summary)
            continue
        
        click.echo("\nThinking...\n")
        response = agent.chat(question)
        click.echo(response)


def main():
    cli()


if __name__ == "__main__":
    main()
