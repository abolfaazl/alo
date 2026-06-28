import typer
from pathlib import Path
from alo.ui.console import console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from datetime import datetime
from alo.models import OnboardingProfile, ExperienceLevel, PrivacyPreference
from alo import config as alo_config, state_manager, assessment, workspace

app = typer.Typer(help="ALO - Agentic Learning OS")

@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    no_interactive: bool = typer.Option(False, "--no-interactive", help="Run dashboard in non-interactive mode")
):
    if ctx.invoked_subcommand is None:
        from alo.ui.dashboard import show_dashboard
        show_dashboard(interactive=not no_interactive)

@app.command()
def home(no_interactive: bool = typer.Option(False, "--no-interactive", help="Run dashboard in non-interactive mode")):
    """Shows the ALO home dashboard."""
    from alo.ui.dashboard import show_dashboard
    show_dashboard(interactive=not no_interactive)

@app.command()
def config():
    """Manage ALO global configuration."""
    from alo.services.config_service import get_current_config, save_new_config
    cfg = get_current_config()
    console.print(Panel("[bold cyan]ALO Configuration[/bold cyan]"))
    
    provider_choice = IntPrompt.ask("LLM provider:\n1. openai\n2. openai-compatible\nChoose one", choices=["1", "2"], default=1 if cfg.llm_provider == "openai" else 2)
    cfg.llm_provider = "openai" if provider_choice == 1 else "openai-compatible"
    
    cfg.model = Prompt.ask("Model name", default=cfg.model)
    
    if cfg.llm_provider == "openai-compatible":
        base_url = Prompt.ask("Base URL", default=cfg.base_url or "")
        while not base_url.strip():
            console.print("[red]Base URL is required for openai-compatible providers.[/red]")
            base_url = Prompt.ask("Base URL")
        cfg.base_url = base_url.strip().rstrip("/")
    else:
        base_url = Prompt.ask("Base URL (optional for openai)", default=cfg.base_url or "")
        cfg.base_url = base_url.strip().rstrip("/") if base_url.strip() else None
        
    console.print("\n[yellow]Set your API key in your shell environment, for example:[/yellow]")
    console.print("PowerShell: $env:OPENAI_API_KEY=\"...\"")
    console.print("Bash/Zsh: export OPENAI_API_KEY=\"...\"\n")
    
    cfg.api_key_env_var = Prompt.ask("API key environment variable name", default=cfg.api_key_env_var)
    cfg.default_language = Prompt.ask("Default Language", default=cfg.default_language)
    cfg.safe_mode = Confirm.ask("Safe Mode", default=cfg.safe_mode)
    cfg.auto_push = Confirm.ask("Auto Push Git", default=cfg.auto_push)
    
    save_new_config(cfg)
    console.print("[green]Configuration saved![/green]")

@app.command()
def init(
    allow_source_repo: bool = typer.Option(False, "--allow-source-repo", help="Allow initializing in ALO source repository")
):
    """Initializes ALO in the current directory as a learning workspace."""
    cwd = Path.cwd()
    
    if workspace.is_alo_source_repo(cwd) and not allow_source_repo:
        console.print("[red]Error: You are inside the ALO source repository.[/red]")
        console.print("Please run `alo init` in a separate learning folder.")
        raise typer.Exit(1)
        
    workspace.ensure_git_repo(cwd)
    state_manager.ensure_state_files(cwd)

    lp_path = cwd / "learning-profile.md"
    sm_path = cwd / "skill-map.md"
    
    lp_exists = state_manager.has_user_content(lp_path, state_manager.REQUIRED_FILES["learning-profile.md"])
    sm_exists = state_manager.has_user_content(sm_path, state_manager.REQUIRED_FILES["skill-map.md"])
    
    if lp_exists or sm_exists:
        console.print("Existing learning profile detected.", style="yellow")
        do_overwrite = Confirm.ask("Overwrite it with new onboarding answers?", default=False)
        if not do_overwrite:
            console.print("Onboarding aborted. Existing files preserved.", style="blue")
            return

    console.print(Panel("[bold cyan]ALO Workspace Setup[/bold cyan]"))
    
    subject = Prompt.ask("What is this learning project about? (e.g. English grammar, Java Spring Boot)")
    background = Prompt.ask("What do you already know about this subject?")
    
    exp_levels = [e.value for e in ExperienceLevel]
    console.print("Experience Level:")
    for i, level in enumerate(exp_levels, 1):
        console.print(f"{i}. {level}")
    exp_choice = IntPrompt.ask("Choose one", choices=[str(i) for i in range(1, len(exp_levels)+1)], default=1)
    experience_level = ExperienceLevel(exp_levels[exp_choice-1])
    
    goal = Prompt.ask("What do you want to achieve?")
    assess_now = Confirm.ask("Do you want ALO to assess your current level now?", default=False)
    privacy_confirm = Confirm.ask("May ALO store private project, company, client, or repository names if you mention them?", default=False)
    privacy_preference = PrivacyPreference.store if privacy_confirm else PrivacyPreference.generalize
    
    profile = OnboardingProfile(
        subject=subject,
        background=background,
        experience_level=experience_level,
        goal=goal,
        assess_now=assess_now,
        privacy_preference=privacy_preference,
        date=datetime.now().strftime("%Y-%m-%d")
    )
    
    state_manager.save_onboarding_profile(cwd, profile, overwrite=True)
    state_manager.append_onboarding_progress(cwd, profile)
    
    connect_remote = Confirm.ask("Do you want to connect a remote Git repository?", default=False)
    if connect_remote:
        remote_url = Prompt.ask("Enter remote URL")
        workspace.set_git_remote(cwd, remote_url)
        
    console.print("Workspace setup complete.", style="green")
    
    if assess_now:
        if alo_config.config_exists():
            console.print("\nNext step: Run `alo assess` to start your assessment.", style="bold cyan")
        else:
            console.print("\nNext step: Run `alo config` to setup LLM, then `alo assess`.", style="bold cyan")
    else:
        console.print("\nNext step: Generate a learning path later.", style="bold cyan")

    # Removed due to rewrite

@app.command()
def status():
    """Shows current learning state."""
    cwd = Path.cwd()
    from alo.ui import views
    console.print(views.build_status_view(cwd))

@app.command()
def assess(
    mock: bool = typer.Option(False, "--mock", help="Use mock assessment mode for development"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run without updating state files")
):
    """Runs a domain-specific LLM assessment."""
    cwd = Path.cwd()
    from alo.services.assess_service import generate_assessment_service, score_assessment_service
    
    gen_result = generate_assessment_service(cwd, mock=mock)
    if not gen_result.success:
        console.print(f"[red]{gen_result.error}[/red]")
        raise typer.Exit(1)
        
    if gen_result.warning:
        console.print(f"[yellow]{gen_result.warning}[/yellow]")
        
    console.print(Panel(f"[bold cyan]ALO Assessment[/bold cyan] - {gen_result.subject}"))
    
    answers = []
    questions = gen_result.questions
    for i, q in enumerate(questions, 1):
        console.print(f"\n[bold]Question {i}/{len(questions)}[/bold] ({q.domain} - {q.difficulty})")
        console.print(q.question)
        for j, choice in enumerate(q.choices):
            letter = chr(65 + j)
            console.print(f"{letter}) {choice}")
            
        ans_idx = None
        while ans_idx is None:
            raw_ans = Prompt.ask("Your answer (A/B/C/D or 1/2/3/4)")
            ans_idx = assessment.normalize_answer(raw_ans)
            if ans_idx is None or ans_idx >= len(q.choices):
                console.print("[red]Invalid choice. Please try again.[/red]")
                ans_idx = None
                
        answers.append(ans_idx)
        
    score_result = score_assessment_service(cwd, questions, answers, mock=mock, dry_run=dry_run)
    if not score_result.success:
        console.print(f"[red]{score_result.error}[/red]")
        raise typer.Exit(1)
        
    result = score_result.result
    console.print("\n[bold cyan]Assessment Results[/bold cyan]")
    console.print(f"Total Score: {result.score_percent}% ({result.correct_answers}/{result.total_questions})")
    console.print(f"Level: {result.level}")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Domain")
    table.add_column("Score")
    for ds in result.domain_scores:
        table.add_row(ds.domain, f"{ds.score_percent}%")
    console.print(table)
    
    if dry_run:
        console.print("[yellow]Dry run completed. No files were updated.[/yellow]")
        return
        
    console.print("[green]Assessment saved successfully.[/green]")

@app.command()
def paths(mock: bool = False, dry_run: bool = False):
    """Suggests 3 learning paths based on current profile."""
    repo_path = Path.cwd()
    from alo.services.paths_service import get_paths, select_path
    
    res = get_paths(repo_path, mock=mock)
    if not res.success:
        console.print(f"[red]{res.error}[/red]")
        raise typer.Exit(1)
        
    if res.warning:
        console.print(f"[yellow]{res.warning}[/yellow]")
        
    for idx, p in enumerate(res.paths):
        console.print(f"\n[bold blue]{idx + 1}. {p.title}[/bold blue] (Confidence: {p.confidence})")
        console.print(f"   Summary: {p.summary}")
        console.print(f"   Topics: {', '.join(p.core_topics)}")
        console.print(f"   Duration: {p.estimated_duration} | Difficulty: {p.difficulty}")
        
    choice = Prompt.ask("\nSelect a path to continue? [1/2/3/skip]", choices=["1", "2", "3", "skip"], default="skip")
    
    choice_idx = None if choice == "skip" else int(choice) - 1
    msg = select_path(repo_path, res.paths, choice_idx, dry_run=dry_run)
    
    if choice_idx is not None:
        console.print(f"\n[green]{msg}[/green]")
    else:
        console.print(f"\n[yellow]{msg}[/yellow]")

@app.command()
def roadmap(
    mock: bool = False,
    dry_run: bool = False,
    force: bool = False,
    yes: bool = False
):
    """Generates or updates the roadmap for the active path."""
    repo_path = Path.cwd()
    from alo.services.roadmap_service import generate_roadmap_service
    
    if not mock:
        console.print("[cyan]Generating roadmap...[/cyan]")
        
    res = generate_roadmap_service(repo_path, mock=mock, force=force, dry_run=dry_run)
    if not res.success:
        console.print(f"[red]{res.error}[/red]")
        raise typer.Exit(1)
        
    if res.warning:
        console.print(f"[yellow]{res.warning}[/yellow]")
        
    if dry_run:
        console.print(f"\n[yellow]Successfully generated {len(res.items)} roadmap items (dry run).[/yellow]")
    else:
        console.print(f"\n[green]Successfully generated {len(res.items)} roadmap items![/green]")
        
    table = Table(title=f"Roadmap Summary ({res.active_path_id})")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="magenta")
    table.add_column("Level", style="green")
    table.add_column("Status", style="yellow")
    
    for item in res.items:
        table.add_row(item.id, item.title, item.level, item.status)
        
    console.print(table)

@app.command()
def learn(
    mock: bool = False,
    dry_run: bool = False,
    item: str = None,
    yes: bool = False
):
    """Runs a single daily learning session based on the current workspace roadmap."""
    repo_path = Path.cwd()
    from alo.services.learn_service import generate_session, evaluate_answer
    
    if not mock:
        console.print("[cyan]Generating learning session...[/cyan]")
        
    gen_res = generate_session(repo_path, mock=mock, item_id=item)
    if not gen_res.success:
        console.print(f"[red]{gen_res.error}[/red]")
        raise typer.Exit(1)
        
    if gen_res.warning:
        console.print(f"[yellow]{gen_res.warning}[/yellow]")
        
    session_ctx = gen_res.context
    session = session_ctx.session
    
    from rich.markdown import Markdown
    console.print(Panel(f"Session: {session.topic} ({session_ctx.target_id})", style="blue"))
    console.print(Markdown(session.short_lesson))
    console.print("\n[bold cyan]Example:[/bold cyan]")
    console.print(Markdown(session.example))
    console.print("\n[bold red]Common Mistake:[/bold red]")
    console.print(Markdown(session.common_mistake))
    
    console.print(Panel(session.practice_question, title="Practice Question", style="green"))
    
    answer = Prompt.ask("Your answer")
    if not answer.strip():
        answer = Prompt.ask("Your answer (cannot be empty)")
        if not answer.strip():
            console.print("[yellow]Session cancelled.[/yellow]")
            raise typer.Exit(0)
            
    if not mock:
        console.print("[cyan]Evaluating answer...[/cyan]")
        
    eval_res = evaluate_answer(repo_path, session_ctx, answer, mock=mock, dry_run=dry_run)
    if not eval_res.success:
        console.print(f"[red]{eval_res.error}[/red]")
        raise typer.Exit(1)
        
    evaluation = eval_res.evaluation
    eval_color = "green" if evaluation.result == "pass" else ("yellow" if evaluation.result == "partial" else "red")
    console.print(Panel(f"Result: {evaluation.result.upper()} (Score: {evaluation.score})", style=eval_color))
    console.print(Markdown(evaluation.feedback))
    console.print(f"\n[bold green]Strengths:[/bold green] {evaluation.strengths}")
    console.print(f"[bold red]Weaknesses:[/bold red] {evaluation.weaknesses}")
    console.print(f"[bold cyan]Next Step:[/bold cyan] {evaluation.recommended_next_step}")
    
    if not dry_run:
        console.print("\n[green]State updated successfully.[/green]")
    else:
        console.print("\n[yellow]State not updated (dry run).[/yellow]")

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
    cwd = Path.cwd()
    from alo.ui import views
    console.print(views.build_doctor_view(cwd))

if __name__ == "__main__":
    app()
