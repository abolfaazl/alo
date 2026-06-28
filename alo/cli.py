import sys
import typer
import shutil
import os
from pathlib import Path
from alo.ui.console import console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from datetime import datetime
from alo.models import OnboardingProfile, ExperienceLevel, LearningGoalMode, LearningStyle, PrivacyPreference
from alo import config, state_manager

app = typer.Typer(help="ALO - Agentic Learning OS")

@app.command()
def init(
    no_onboarding: bool = typer.Option(False, "--no-onboarding", help="Skip interactive onboarding"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing onboarding files")
):
    """Initializes ALO in a learning repository."""
    cwd = Path.cwd()
    state_manager.ensure_state_files(cwd)
    
    if no_onboarding:
        console.print("Phase 2 state initialization complete.", style="green")
        console.print("Onboarding skipped due to --no-onboarding.", style="yellow")
        return

    lp_path = cwd / "learning-profile.md"
    sm_path = cwd / "skill-map.md"
    
    lp_exists = state_manager.has_user_content(lp_path, state_manager.REQUIRED_FILES["learning-profile.md"])
    sm_exists = state_manager.has_user_content(sm_path, state_manager.REQUIRED_FILES["skill-map.md"])
    
    if (lp_exists or sm_exists) and not force:
        console.print("Existing learning profile detected.", style="yellow")
        do_overwrite = Confirm.ask("Overwrite it with new onboarding answers?", default=False)
        if not do_overwrite:
            console.print("Onboarding aborted. Existing files preserved.", style="blue")
            return
        force = True

    console.print(Panel("[bold cyan]ALO Onboarding[/bold cyan] - Let's set up your learning profile!"))
    
    declared_skills = Prompt.ask("What skills do you already have? Mention languages, tools, frameworks, workflows, and areas you feel confident in")
    
    exp_levels = [e.value for e in ExperienceLevel]
    console.print("Experience Level:")
    for i, level in enumerate(exp_levels, 1):
        console.print(f"{i}. {level}")
    exp_choice = IntPrompt.ask("Choose one", choices=[str(i) for i in range(1, len(exp_levels)+1)], default=1)
    experience_level = ExperienceLevel(exp_levels[exp_choice-1])
    
    goal_modes = [e.value for e in LearningGoalMode]
    console.print("Do you already know what you want to learn, or should ALO recommend learning paths later?")
    for i, mode in enumerate(goal_modes, 1):
        console.print(f"{i}. {mode}")
    mode_choice = IntPrompt.ask("Choose one", choices=[str(i) for i in range(1, len(goal_modes)+1)], default=1)
    goal_mode = LearningGoalMode(goal_modes[mode_choice-1])
    
    specific_goal = None
    if goal_mode == LearningGoalMode.know:
        specific_goal = Prompt.ask("What do you want to learn next?")
        
    styles = [e.value for e in LearningStyle]
    console.print("How do you prefer to learn?")
    for i, style in enumerate(styles, 1):
        console.print(f"{i}. {style}")
    style_choice = IntPrompt.ask("Choose one", choices=[str(i) for i in range(1, len(styles)+1)], default=1)
    learning_style = LearningStyle(styles[style_choice-1])
    
    time_per_session = Prompt.ask("How much time can you spend per learning session?")
    sessions_per_week = Prompt.ask("How many sessions per week do you realistically want?")
    
    privacy_confirm = Confirm.ask("May ALO store private project, company, client, or repository names if you mention them?", default=False)
    privacy_preference = PrivacyPreference.store if privacy_confirm else PrivacyPreference.generalize
    
    profile = OnboardingProfile(
        declared_skills=declared_skills,
        experience_level=experience_level,
        goal_mode=goal_mode,
        specific_goal=specific_goal,
        learning_style=learning_style,
        time_per_session=time_per_session,
        sessions_per_week=sessions_per_week,
        privacy_preference=privacy_preference,
        date=datetime.now().strftime("%Y-%m-%d")
    )
    
    state_manager.save_onboarding_profile(cwd, profile, overwrite=True)
    state_manager.append_onboarding_progress(cwd, profile)
    
    console.print("Onboarding complete. Learning profile and skill map generated.", style="green")

@app.command()
def status():
    """Shows current learning state."""
    cwd = Path.cwd()
    summary = state_manager.get_state_summary(cwd)
    
    console.print(Panel("[bold cyan]ALO Status[/bold cyan] - Checking learning state..."))
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("File")
    table.add_column("Status")
    
    for file_status in summary.files:
        status_text = "[green]Found[/green]" if file_status.exists else "[red]Missing[/red]"
        table.add_row(file_status.name, status_text)
        
    console.print(table)
    
    # Check config
    config_exists = config.config_exists()
    console.print(f"Local Config: {'[green]Exists[/green]' if config_exists else '[yellow]Missing[/yellow]'}")
    
    # Check git repo
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
    
    console.print(f"Inside Git Repo: {'[green]Yes[/green]' if is_git_repo else '[yellow]No[/yellow]'}")
    console.print(f"Working Directory: {cwd}")

@app.command()
def assess():
    """Runs a standalone assessment."""
    console.print("This command will be implemented in Phase 4.", style="yellow")

@app.command()
def paths():
    """Suggests 3 learning paths based on current profile."""
    console.print("This command will be implemented in Phase 5.", style="yellow")

@app.command()
def roadmap():
    """Generates or updates the roadmap for a selected path or user-defined goal."""
    console.print("This command will be implemented in Phase 6.", style="yellow")

@app.command()
def learn():
    """Runs one learning session."""
    console.print("This command will be implemented in Phase 7.", style="yellow")

@app.command()
def review():
    """Focuses only on weaknesses and previously failed topics."""
    console.print("This command will be implemented in Phase 8.", style="yellow")

@app.command()
def sync():
    """Safely commits and pushes learning state."""
    console.print("This command will be implemented in Phase 9.", style="yellow")

@app.command()
def doctor():
    """Checks environment health."""
    console.print(Panel("[bold cyan]ALO Doctor[/bold cyan] - Checking environment health..."))
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")

    # 1. Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    table.add_row("Python Version", "[green]OK[/green]" if sys.version_info >= (3, 10) else "[red]Fail[/red]", py_version)

    # 2. Current working directory
    cwd = Path.cwd()
    table.add_row("Working Directory", "[green]OK[/green]", str(cwd))

    # 3. Whether Git is available
    git_path = shutil.which("git")
    table.add_row("Git Installed", "[green]Yes[/green]" if git_path else "[red]No[/red]", git_path or "Not found in PATH")

    # 4. Whether the current directory is inside a Git repository
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

    # 5. Whether local ALO config exists
    # 6. The expected local config path
    config_path = config.get_config_path()
    config_exists = config.config_exists()
    table.add_row("Local Config", "[green]Exists[/green]" if config_exists else "[yellow]Missing[/yellow]", str(config_path))

    # 7. Whether required environment variables exist
    openai_key = "OPENAI_API_KEY" in os.environ
    anthropic_key = "ANTHROPIC_API_KEY" in os.environ
    keys_status = "[green]Found[/green]" if openai_key or anthropic_key else "[yellow]None[/yellow]"
    keys_details = "OPENAI_API_KEY: " + ("Yes" if openai_key else "No") + ", ANTHROPIC_API_KEY: " + ("Yes" if anthropic_key else "No")
    table.add_row("Env Variables", keys_status, keys_details)

    # 8. Whether the project package can be imported
    try:
        import alo  # noqa: F401
        alo_imported = True
    except ImportError:
        alo_imported = False
    table.add_row("Package Importable", "[green]Yes[/green]" if alo_imported else "[red]No[/red]", "alo package")

    console.print(table)
    
    if not config_exists:
        console.print("[yellow]Warning: Local ALO config does not exist. Run 'alo init' or create it manually.[/yellow]")

if __name__ == "__main__":
    app()
