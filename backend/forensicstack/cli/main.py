import typer
from rich.console import Console
from rich.table import Table
from pathlib import Path

app = typer.Typer(name="forensicstack", help="DFIR Investigation Platform CLI")
console = Console()

@app.command()
def version():
    """Show ForensicStack version"""
    console.print("[bold green]ForensicStack v0.1.0[/bold green]")

@app.command()
def status():
    """Check system status"""
    table = Table(title="ForensicStack Status")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="green")
    table.add_row("API", "Running on http://localhost:8001")
    table.add_row("Database", "Connected")
    table.add_row("Redis", "Connected")
    table.add_row("Celery", "Worker Active")
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
    title: str = typer.Option(..., "--title", "-t"),
    description: str = typer.Option("", "--description", "-d")
):
    """Create a new case"""
    console.print(f"[green]Created case:[/green] {title}")

# Volatility commands
vol_app = typer.Typer(help="Volatility 3 memory analysis")
app.add_typer(vol_app, name="volatility")

@vol_app.command("plugins")
def list_volatility_plugins():
    """List all available Volatility plugins"""
    from forensicstack.plugins.memory.volatility import get_volatility_plugin
    
    vol = get_volatility_plugin()
    plugins = vol.list_plugins()
    
    console.print(f"[bold cyan]Volatility {vol.version}[/bold cyan]")
    console.print(f"[green]{len(plugins)} plugins available[/green]\n")
    
    # Group by OS
    windows = [p for p in plugins if p.startswith("windows.")]
    linux = [p for p in plugins if p.startswith("linux.")]
    mac = [p for p in plugins if p.startswith("mac.")]
    
    if windows:
        console.print("[bold yellow]Windows Plugins:[/bold yellow]")
        for p in windows[:10]:
            console.print(f"  • {p}")
        if len(windows) > 10:
            console.print(f"  ... and {len(windows) - 10} more")
    
    if linux:
        console.print("\n[bold yellow]Linux Plugins:[/bold yellow]")
        for p in linux[:5]:
            console.print(f"  • {p}")
    
    if mac:
        console.print("\n[bold yellow]macOS Plugins:[/bold yellow]")
        for p in mac[:5]:
            console.print(f"  • {p}")

@vol_app.command("run")
def run_volatility(
    dump: str = typer.Argument(..., help="Path to memory dump"),
    plugin: str = typer.Argument(..., help="Plugin name (e.g., windows.pslist)"),
    output_format: str = typer.Option("text", "--format", "-f", help="Output format: text, json, csv"),
    output_file: str = typer.Option(None, "--output", "-o", help="Save output to file")
):
    """
    Run Volatility plugin on a memory dump
    
    Examples:
        forensicstack volatility run memory.dmp windows.pslist
        forensicstack volatility run dump.raw windows.netscan --format json
        forensicstack volatility run memory.dmp linux.pslist --output results.txt
    """
    from forensicstack.plugins.memory.volatility import get_volatility_plugin
    
    if not Path(dump).exists():
        console.print(f"[red]Error: File not found: {dump}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[cyan]Analyzing {dump} with {plugin}...[/cyan]")
    
    vol = get_volatility_plugin()
    result = vol.run(dump, plugin, output_format, output_file)
    
    if result["status"] == "success":
        console.print("[green]Analysis completed![/green]\n")
        if output_file:
            console.print(f"[cyan]Results saved to: {output_file}[/cyan]")
        else:
            console.print(result["output"])
    else:
        console.print(f"[red]Error:[/red] {result.get('error', 'Unknown error')}")

@vol_app.command("pslist")
def volatility_pslist(
    dump: str = typer.Argument(..., help="Path to memory dump")
):
    """Quick pslist (list processes)"""
    from forensicstack.plugins.memory.volatility import get_volatility_plugin
    
    console.print(f"[cyan]Running pslist on {dump}...[/cyan]")
    vol = get_volatility_plugin()
    result = vol.pslist(dump)
    
    if result["status"] == "success":
        console.print(result["output"])
    else:
        console.print(f"[red]Error:[/red] {result.get('error')}")

@vol_app.command("netscan")
def volatility_netscan(
    dump: str = typer.Argument(..., help="Path to memory dump")
):
    """Quick netscan (network connections)"""
    from forensicstack.plugins.memory.volatility import get_volatility_plugin
    
    console.print(f"[cyan]Running netscan on {dump}...[/cyan]")
    vol = get_volatility_plugin()
    result = vol.netscan(dump)
    
    if result["status"] == "success":
        console.print(result["output"])
    else:
        console.print(f"[red]Error:[/red] {result.get('error')}")

if __name__ == "__main__":
    app()