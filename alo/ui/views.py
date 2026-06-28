import sys
import shutil
import os
from pathlib import Path
from rich.table import Table
from rich.panel import Panel
from rich.console import Group
from rich.text import Text

from alo import state_manager, config as alo_config

def build_status_view(cwd: Path) -> Group:
    summary = state_manager.get_state_summary(cwd)
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("File")
    table.add_column("Status")
    
    for file_status in summary.files:
        status_text = "[green]Found[/green]" if file_status.exists else "[red]Missing[/red]"
        table.add_row(file_status.name, status_text)
        
    config_exists = alo_config.config_exists()
    
    is_git_repo = False
    try:
        import git
        try:
            git.Repo(cwd, search_parent_directories=True)
            is_git_repo = True
        except git.InvalidGitRepositoryError:
            pass
    except ImportError:
        pass
    
    renderables = [
        Panel("[bold cyan]ALO Status[/bold cyan] - Checking learning state..."),
        table,
        Text.from_markup(f"Local Config: {'[green]Exists[/green]' if config_exists else '[yellow]Missing[/yellow]'}"),
        Text.from_markup(f"Inside Git Repo: {'[green]Yes[/green]' if is_git_repo else '[yellow]No[/yellow]'}"),
        Text(f"Working Directory: {cwd}")
    ]
    return Group(*renderables)

def build_doctor_view(cwd: Path) -> Group:
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")

    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    table.add_row("Python Version", "[green]OK[/green]" if sys.version_info >= (3, 10) else "[red]Fail[/red]", py_version)
    table.add_row("Working Directory", "[green]OK[/green]", str(cwd))

    git_path = shutil.which("git")
    table.add_row("Git Installed", "[green]Yes[/green]" if git_path else "[red]No[/red]", git_path or "Not found in PATH")

    is_git_repo = False
    repo_path = "Not in a git repository"
    try:
        import git
        try:
            repo = git.Repo(cwd, search_parent_directories=True)
            is_git_repo = True
            repo_path = str(repo.working_dir)
        except git.InvalidGitRepositoryError:
            pass
    except ImportError:
        repo_path = "GitPython not installed"

    table.add_row("Inside Git Repo", "[green]Yes[/green]" if is_git_repo else "[yellow]No[/yellow]", repo_path)

    config_path = alo_config.get_config_path()
    config_exists = alo_config.config_exists()
    table.add_row("Local Config", "[green]Exists[/green]" if config_exists else "[yellow]Missing[/yellow]", str(config_path))

    openai_key = "OPENAI_API_KEY" in os.environ
    anthropic_key = "ANTHROPIC_API_KEY" in os.environ
    keys_status = "[green]Found[/green]" if openai_key or anthropic_key else "[yellow]None[/yellow]"
    keys_details = "OPENAI_API_KEY: " + ("Yes" if openai_key else "No") + ", ANTHROPIC_API_KEY: " + ("Yes" if anthropic_key else "No")
    table.add_row("Env Variables", keys_status, keys_details)

    try:
        import alo  # noqa: F401
        alo_imported = True
    except ImportError:
        alo_imported = False
    table.add_row("Package Importable", "[green]Yes[/green]" if alo_imported else "[red]No[/red]", "alo package")

    renderables = [
        Panel("[bold cyan]ALO Doctor[/bold cyan] - Checking environment health..."),
        table
    ]
    if not config_exists:
        renderables.append(Text.from_markup("[yellow]Warning: Local ALO config does not exist. Run 'alo init' or create it manually.[/yellow]"))

    return Group(*renderables)

def build_help_view() -> Group:
    return Group(
        Panel("[bold cyan]ALO Command Palette[/bold cyan]", border_style="cyan"),
        Text.from_markup("[bold]/status[/bold]   Show workspace state\n"
                         "[bold]/config[/bold]   Show global config status\n"
                         "[bold]/assess[/bold]   Run assessment\n"
                         "[bold]/paths[/bold]    Generate or show learning paths\n"
                         "[bold]/roadmap[/bold]  Generate or show roadmap\n"
                         "[bold]/learn[/bold]    Start learning session\n"
                         "[bold]/review[/bold]   Review weaknesses\n"
                         "[bold]/doctor[/bold]   Environment health check\n"
                         "[bold]/help[/bold]     Show help\n"
                         "[bold]/clear[/bold]    Clear main panel\n"
                         "[bold]/home[/bold]     Return to home view\n"
                         "[bold]/quit[/bold]     Exit ALO")
    )

def build_home_view(workspace_info: dict) -> Panel:
    subject = workspace_info.get("subject", "Unknown")
    rm_items = workspace_info.get("rm_items", 0)
    
    if rm_items > 0:
        next_cmd = "alo learn"
    elif workspace_info.get("active_path") and workspace_info.get("active_path") != "None":
        next_cmd = "alo roadmap"
    else:
        next_cmd = "alo paths"

    return Panel(
        f"[bold]Subject:[/bold] {subject}\n"
        f"[bold cyan]Suggested next command:[/bold cyan] `{next_cmd}`\n\n"
        "Type [bold]/[/bold] to see available commands.",
        title="ALO Home",
        border_style="green"
    )
