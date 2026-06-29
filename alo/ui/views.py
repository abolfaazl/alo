import sys
import shutil
from pathlib import Path
from rich.table import Table
from rich.panel import Panel
from rich.console import Group
from rich.text import Text

from alo import state_manager, config as alo_config

def truncate_middle(text: str, max_length: int = 40) -> str:
    if len(text) <= max_length:
        return text
    half = (max_length - 3) // 2
    return f"{text[:half]}...{text[-half:]}"

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
    
    cfg = alo_config.load_config()
    readiness = alo_config.validate_config_readiness(cfg)
    
    ready_status = "[green]Ready[/green]" if readiness.llm_ready else "[red]Not ready[/red]"
    
    missing_str = ", ".join([i.label for i in readiness.missing_required])
    if missing_str:
        details = f"Missing: {missing_str}"
    else:
        details = "All required fields configured"
        
    table.add_row("LLM Readiness", ready_status, details)

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
    
    # Actionable Next Steps
    next_steps = []
    
    from alo.services.init_service import detect_init_state
    init_state = detect_init_state(cwd, allow_source_repo=False)
    
    if init_state == "source_repo":
        next_steps.append("[red]This is the ALO development repository.[/red] [bold]Next step:[/bold] Create a separate learning workspace and run `alo init`.")
    elif not git_path:
        next_steps.append("[yellow]Git is not available.[/yellow] Sync will not work until Git is installed.")
    elif not readiness.llm_ready:
        next_steps.append("[bold]Next step:[/bold] Run `alo config` or open the dashboard and type `config`.")
    elif not alo_config.config_exists():
        next_steps.append("[bold]Next step:[/bold] Run `alo init` to initialize this workspace.")
    else:
        next_steps.append("[bold]Next step:[/bold] In a learning workspace, run `alo paths`.")
        
    renderables.append(Panel("\n".join(next_steps), title="Recommendations", border_style="green"))

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
