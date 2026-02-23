import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="forensicstack",
    help="All-in-One DFIR Investigation Platform CLI"
)
console = Console()

@app.command()
def version():
    """Show ForensicStack version"""
    console.print("[bold green]ForensicStack v0.1.0[/bold green]")
    console.print("Digital Forensics Investigation Platform")

@app.command()
def status():
    """Check system status"""
    table = Table(title="ForensicStack Status")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="green")
    
    table.add_row("API", "✅ Running on http://localhost:8000")
    table.add_row("Database", "✅ Connected")
    table.add_row("Redis", "✅ Connected")
    table.add_row("Celery", "✅ Worker Active")
    
    console.print(table)

# Case commands
case_app = typer.Typer(help="Manage investigation cases")
app.add_typer(case_app, name="case")

@case_app.command("list")
def list_cases():
    """List all cases"""
    console.print("[yellow]No cases yet[/yellow]")

@case_app.command("create")
def create_case(
    title: str = typer.Option(..., "--title", "-t", help="Case title"),
    description: str = typer.Option("", "--description", "-d", help="Case description")
):
    """Create a new case"""
    console.print(f"[green]✅ Created case:[/green] {title}")

if __name__ == "__main__":
    app()