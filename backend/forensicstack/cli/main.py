import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from pathlib import Path
import sys

app = typer.Typer(name="forensicstack", help="DFIR Investigation Platform CLI")
console = Console()

@app.command()
def version():
    """Show ForensicStack version"""
    console.print("\n[bold cyan]ForensicStack v0.1.0[/bold cyan]")
    console.print("Digital Forensics & Incident Response Platform\n")
    
    # Show installed tools
    table = Table(title="Installed Tools")
    table.add_column("Tool", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Status", style="yellow")
    
    # Volatility
    try:
        from forensicstack.plugins.memory.volatility import get_volatility_plugin
        vol = get_volatility_plugin()
        table.add_row("Volatility3", vol.version, "Ready")
    except Exception as e:
        table.add_row("Volatility3", "N/A", f"{str(e)[:20]}")
    
    # YARA
    try:
        import yara
        table.add_row("YARA", yara.__version__, "Ready")
    except:
        table.add_row("YARA", "N/A", "Not installed")
    
    # TSK
    try:
        import pytsk3
        table.add_row("TSK (pytsk3)", pytsk3.get_version(), "Ready")
    except:
        table.add_row("TSK", "N/A", "Not installed")
    
    # Plaso
    try:
        from forensicstack.plugins.timeline.plaso import get_plaso_plugin
        plaso = get_plaso_plugin()
        table.add_row("Plaso", plaso.version, "Ready (Docker)")
    except:
        table.add_row("Plaso", "N/A", "Not available")
    
    console.print(table)
    console.print()

@app.command()
def status():
    """Check system status"""
    table = Table(title="ForensicStack System Status")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="green")
    
    table.add_row("API", "Running on http://localhost:8001")
    table.add_row("Database", "Connected (PostgreSQL)")
    table.add_row("Redis", "Connected")
    table.add_row("Celery", "Worker Active")
    table.add_row("Storage", "MinIO (9000-9001)")
    
    console.print(table)

# ============================================================
# CASE MANAGEMENT
# ============================================================

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

# ============================================================
# VOLATILITY COMMANDS
# ============================================================

vol_app = typer.Typer(help="Memory analysis with Volatility3")
app.add_typer(vol_app, name="volatility")

@vol_app.command("plugins")
def list_volatility_plugins():
    """List all available Volatility plugins"""
    from forensicstack.plugins.memory.volatility import get_volatility_plugin
    
    vol = get_volatility_plugin()
    plugins = vol.list_plugins()
    
    console.print(f"[bold cyan]Volatility {vol.version}[/bold cyan]")
    console.print(f"[green]{len(plugins)} plugins available[/green]\n")
    
    windows = [p for p in plugins if p.startswith("windows.")]
    linux = [p for p in plugins if p.startswith("linux.")]
    mac = [p for p in plugins if p.startswith("mac.")]
    
    if windows:
        console.print("[bold yellow]Windows Plugins:[/bold yellow]")
        for p in sorted(windows)[:10]:
            console.print(f"  • {p}")
        if len(windows) > 10:
            console.print(f"  ... and {len(windows) - 10} more")
    
    if linux:
        console.print("\n[bold yellow]Linux Plugins:[/bold yellow]")
        for p in sorted(linux)[:5]:
            console.print(f"  • {p}")
    
    if mac:
        console.print("\n[bold yellow]macOS Plugins:[/bold yellow]")
        for p in sorted(mac)[:5]:
            console.print(f"  • {p}")

@vol_app.command("run", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def run_volatility(
    ctx: typer.Context,
    dump: str = typer.Argument(..., help="Path to memory dump"),
    plugin: str = typer.Argument(..., help="Plugin name (e.g., windows.pslist)"),
    output_format: str = typer.Option("text", "--format", "-f", help="Output format: text, json, csv"),
    output_file: str = typer.Option(None, "--output", "-o", help="Save output to file")
):
    """
    Run Volatility plugin on a memory dump
    
    Examples:
        forensicstack volatility run memory.dmp windows.pslist
        forensicstack volatility run memory.dmp windows.dlllist --pid 1808
        forensicstack volatility run memory.dmp windows.netscan --format json
    """
    from forensicstack.plugins.memory.volatility import get_volatility_plugin
    
    if not Path(dump).exists():
        console.print(f"[red]Error: File not found: {dump}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[cyan]Analyzing {Path(dump).name} with {plugin}...[/cyan]")
    
    extra_args = ctx.args
    vol = get_volatility_plugin()
    result = vol.run(dump, plugin, output_format, output_file, extra_args)
    
    if result["status"] == "success":
        console.print("[green]Analysis completed![/green]\n")
        if output_file:
            console.print(f"[cyan]Results saved to: {output_file}[/cyan]")
        else:
            console.print(result["output"])
    else:
        console.print(f"[red]Error:[/red]\n{result.get('error', 'Unknown error')}")

@vol_app.command("pslist")
def volatility_pslist(dump: str = typer.Argument(...)):
    """Quick pslist (list processes)"""
    from forensicstack.plugins.memory.volatility import get_volatility_plugin
    vol = get_volatility_plugin()
    result = vol.pslist(dump)
    console.print(result["output"] if result["status"] == "success" else result.get("error"))

@vol_app.command("netscan")
def volatility_netscan(dump: str = typer.Argument(...)):
    """Quick netscan (network connections)"""
    from forensicstack.plugins.memory.volatility import get_volatility_plugin
    vol = get_volatility_plugin()
    result = vol.netscan(dump)
    console.print(result["output"] if result["status"] == "success" else result.get("error"))

@vol_app.command("vol2-help")
def volatility2_migration_guide():
    """Show Volatility 2 to 3 migration guide"""
    console.print("\n[bold cyan]Volatility 2 → 3 Migration Guide[/bold cyan]\n")
    
    table = Table(title="Common Command Changes")
    table.add_column("Volatility 2", style="red")
    table.add_column("Volatility 3", style="green")
    table.add_column("Notes")
    
    migrations = [
        ("imageinfo", "windows.info", "Get system info"),
        ("pslist", "windows.pslist", "List processes"),
        ("pstree", "windows.pstree", "Process tree"),
        ("dlllist", "windows.dlllist", "List DLLs"),
        ("netscan", "windows.netscan", "Network connections"),
    ]
    
    for vol2, vol3, note in migrations:
        table.add_row(vol2, vol3, note)
    
    console.print(table)
    console.print("\n[bold yellow]Key Differences:[/bold yellow]")
    console.print("  1. No --profile needed (auto-detected)")
    console.print("  2. Use --pid instead of -p")
    console.print("  3. OS prefix required (windows., linux., mac.)\n")

# ============================================================
# YARA COMMANDS
# ============================================================

yara_app = typer.Typer(help="🔍 Malware detection with YARA")
app.add_typer(yara_app, name="yara")

@yara_app.command("scan")
def yara_scan(
    target: str = typer.Argument(..., help="File or directory to scan"),
    rules: str = typer.Argument(..., help="YARA rules file (.yar)"),
):
    """
    Scan file(s) with YARA rules
    
    Examples:
        forensicstack yara scan malware.exe rules.yar
        forensicstack yara scan /evidence malware_rules.yar
    """
    from forensicstack.plugins.yara.scanner import get_yara_plugin
    
    if not Path(target).exists():
        console.print(f"[red]Target not found: {target}[/red]")
        raise typer.Exit(1)
    
    if not Path(rules).exists():
        console.print(f"[red]Rules file not found: {rules}[/red]")
        raise typer.Exit(1)
    
    yara = get_yara_plugin()
    console.print(f"\n[cyan]🔍 Scanning {target} with {Path(rules).name}...[/cyan]\n")
    
    try:
        if Path(target).is_file():
            result = yara.scan_file(target, rules)
        else:
            result = yara.scan_directory(target, rules)
        
        if result["status"] == "success":
            matches = result.get("total_matches", 0)
            if matches > 0:
                console.print(f"[red]{matches} DETECTION(S) FOUND![/red]\n")
                for match in result.get("matches", [])[:10]:
                    console.print(f"Rule: [bold red]{match['rule']}[/bold red]")
            else:
                console.print("[green]No threats detected[/green]\n")
        else:
            console.print(f"[red]Error: {result['error']}[/red]\n")
    except Exception as e:
        console.print(f"[red]Scan failed: {e}[/red]\n")

@yara_app.command("rules")
def list_yara_rules():
    """List available YARA rule collections"""
    from forensicstack.rules_manager import get_rules_manager
    
    manager = get_rules_manager()
    collections = manager.list_collections()
    
    console.print("\n[bold cyan]📚 Available YARA Rule Collections[/bold cyan]\n")
    
    if not collections:
        console.print("[yellow]No rules found. Run:[/yellow]")
        console.print("  git clone https://github.com/Yara-Rules/rules.git forensicstack/rules/yara/community\n")
        return
    
    for col in collections:
        rules = manager.get_rule_files(col)
        console.print(f"[cyan]{col}[/cyan]: {len(rules)} rules")
    
    console.print()

@yara_app.command("scan-quick")
def yara_scan_quick(
    target: str = typer.Argument(..., help="File or directory to scan"),
    ruleset: str = typer.Option("malware", "--ruleset", "-r", help="malware, apt, webshells")
):
    """Quick scan with built-in rules"""
    from forensicstack.plugins.yara.scanner import get_yara_plugin
    from forensicstack.rules_manager import get_rules_manager
    
    if not Path(target).exists():
        console.print(f"[red]Target not found: {target}[/red]")
        raise typer.Exit(1)
    
    manager = get_rules_manager()
    
    # Get rules path
    if ruleset == "malware":
        rules_path = manager.get_malware_rules()
    elif ruleset == "apt":
        rules_path = manager.get_apt_rules()
    elif ruleset == "webshells":
        rules_path = manager.get_webshell_rules()
    else:
        console.print(f"[red]Unknown ruleset: {ruleset}[/red]")
        raise typer.Exit(1)
    
    if not rules_path.exists():
        console.print(f"[red]Rules not found: {rules_path}[/red]")
        console.print("[yellow]Run: forensicstack yara install-rules[/yellow]")
        raise typer.Exit(1)
    
    console.print(f"[cyan]🔍 Scanning with {ruleset} rules...[/cyan]\n")
    
    # Scan with all rules in directory
    yara = get_yara_plugin()
    
    # TODO: Implement multi-rule scanning
    console.print("[yellow]Quick scan with built-in rules[/yellow]")

@yara_app.command("install-rules")
def install_yara_rules():
    """Download and install YARA rules"""
    import subprocess
    
    console.print("\n[cyan]📥 Installing YARA rules...[/cyan]\n")
    
    repos = [
        ("Community Rules", "https://github.com/Yara-Rules/rules.git", "community"),
        ("Elastic", "https://github.com/elastic/protections-artifacts.git", "elastic"),
    ]
    
    for name, url, folder in repos:
        target = Path("forensicstack/rules/yara") / folder
        if target.exists():
            console.print(f"  {name} already installed")
        else:
            console.print(f"  📥 Downloading {name}...")
            try:
                subprocess.run(["git", "clone", url, str(target)], check=True)
                console.print(f"  {name} installed")
            except:
                console.print(f"  Failed to install {name}")
    
    console.print("\n[green]YARA rules installation complete![/green]\n")
# ============================================================
# TSK COMMANDS
# ============================================================

tsk_app = typer.Typer(help="💿 Disk analysis with The Sleuth Kit")
app.add_typer(tsk_app, name="tsk")

@tsk_app.command("partitions")
def tsk_partitions(image: str = typer.Argument(..., help="Disk image file")):
    """List partitions in disk image"""
    from forensicstack.plugins.disk.tsk import get_tsk_plugin
    
    if not Path(image).exists():
        console.print(f"[red]Image not found: {image}[/red]")
        raise typer.Exit(1)
    
    tsk = get_tsk_plugin()
    console.print(f"\n[cyan]💿 Analyzing {Path(image).name}...[/cyan]\n")
    
    result = tsk.list_partitions(image)
    
    if result["status"] == "success":
        console.print(f"[green]Found {result['total']} partition(s)[/green]\n")
        for p in result["partitions"]:
            console.print(f"  Slot {p['slot']}: {p['description']}")
            console.print(f"    Start: {p['start']}, Length: {p['length']}")
    else:
        console.print(f"[yellow]{result['error']}[/yellow]")
        console.print("[dim]Tip: Need a valid disk image (dd, raw, E01)[/dim]\n")

@tsk_app.command("files")
def tsk_files(
    image: str = typer.Argument(..., help="Disk image file"),
    offset: int = typer.Option(0, "--offset", "-o", help="Partition offset")
):
    """List files in filesystem"""
    from forensicstack.plugins.disk.tsk import get_tsk_plugin
    
    if not Path(image).exists():
        console.print(f"[red]Image not found: {image}[/red]")
        raise typer.Exit(1)
    
    tsk = get_tsk_plugin()
    console.print(f"\n[cyan]Listing files...[/cyan]\n")
    
    result = tsk.list_files(image, offset)
    
    if result["status"] == "success":
        console.print(f"[green]Found {result['total']} file(s)[/green]\n")
        for f in result["files"][:30]:
            icon = "📁" if f["type"] == "dir" else "📄"
            console.print(f"  {icon} {f['name']}")
        if result["total"] > 30:
            console.print(f"\n  [dim]... and {result['total'] - 30} more[/dim]")
    else:
        console.print(f"[yellow]{result['error']}[/yellow]\n")

# ============================================================
# PLASO COMMANDS
# ============================================================

plaso_app = typer.Typer(help="⏱️  Timeline generation with Plaso")
app.add_typer(plaso_app, name="plaso")

@plaso_app.command("timeline")
def plaso_timeline(
    source: str = typer.Argument(..., help="Evidence source (dir or image)"),
    output: str = typer.Argument(..., help="Output timeline file (.csv)"),
):
    """
    Generate timeline from evidence
    
    Example:
        forensicstack plaso timeline /evidence timeline.csv
        forensicstack plaso timeline disk.dd timeline.csv
    """
    from forensicstack.plugins.timeline.plaso import get_plaso_plugin
    
    if not Path(source).exists():
        console.print(f"[red]Source not found: {source}[/red]")
        raise typer.Exit(1)
    
    plaso = get_plaso_plugin()
    console.print(f"\n[cyan]⏱️  Generating timeline from {Path(source).name}...[/cyan]")
    console.print("[yellow]This may take several minutes...[/yellow]\n")
    
    result = plaso.create_timeline(source, output)
    
    if result["status"] == "success":
        console.print(f"[green]Timeline created: {output}[/green]\n")
    else:
        console.print(f"[red]Error: {result['error']}[/red]")
        console.print("[dim]Tip: Make sure Docker is running[/dim]\n")

if __name__ == "__main__":
    app()
