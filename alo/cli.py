import typer
from typing import Optional
from pathlib import Path
from alo.ui.console import console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm, IntPrompt
from alo.models import ExperienceLevel, PrivacyPreference
from alo import config as alo_config, assessment

app = typer.Typer(help="ALO - Agentic Learning OS")

def version_callback(value: bool):
    if value:
        from alo import __version__
        console.print(f"ALO Agentic Learning OS\nVersion: {__version__}")
        raise typer.Exit()

@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    no_interactive: bool = typer.Option(False, "--no-interactive", help="Run dashboard in non-interactive mode"),
    version: Optional[bool] = typer.Option(None, "--version", callback=version_callback, is_eager=True, help="Show the version and exit.")
):
    if ctx.invoked_subcommand is None:
        from alo.ui.dashboard import show_dashboard
        show_dashboard(interactive=not no_interactive)

@app.command()
def version():
    """Show the ALO version."""
    from alo import __version__
    console.print(f"ALO Agentic Learning OS\nVersion: {__version__}")

@app.command()
def home(no_interactive: bool = typer.Option(False, "--no-interactive", help="Run dashboard in non-interactive mode")):
    """Shows the ALO home dashboard."""
    from alo.ui.dashboard import show_dashboard
    show_dashboard(interactive=not no_interactive)

@app.command()
def config():
    """Configure the LLM provider and securely store your API key."""
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
        
    console.print("\n[bold cyan]API Key Storage Mode[/bold cyan]")
    storage_choice = IntPrompt.ask("1. Store API key securely in OS keyring\n2. Use environment variable name\nChoose one", choices=["1", "2"], default=1 if cfg.api_key_storage == "keyring" else 2)
    cfg.api_key_storage = "keyring" if storage_choice == 1 else "env"
    
    if cfg.api_key_storage == "keyring":
        import keyring
        raw_key = Prompt.ask("Paste API key", password=True)
        key_name = "ALO_" + cfg.llm_provider.upper().replace("-", "_") + "_API_KEY"
        try:
            if raw_key:
                keyring.set_password("alo", key_name, raw_key)
            cfg.api_key_name = key_name
            cfg.api_key_env_var = None
            console.print("[green]API Key saved securely to OS keyring.[/green]")
        except Exception as e:
            console.print(f"[red]Secure OS keyring is unavailable. (Error: {e})[/red]")
            console.print("[yellow]Falling back to environment-variable mode.[/yellow]")
            cfg.api_key_storage = "env"
            
    if cfg.api_key_storage == "env":
        console.print("\n[yellow]Set your API key in your shell environment, for example:[/yellow]")
        console.print("PowerShell: $env:OPENAI_API_KEY=\"...\"")
        console.print("Bash/Zsh: export OPENAI_API_KEY=\"...\"\n")
        cfg.api_key_env_var = Prompt.ask("API key environment variable name", default=cfg.api_key_env_var or "OPENAI_API_KEY")
        cfg.api_key_name = None
    cfg.default_language = Prompt.ask("Default Language", default=cfg.default_language)
    cfg.safe_mode = Confirm.ask("Safe Mode", default=cfg.safe_mode)
    cfg.auto_push = Confirm.ask("Auto Push Git", default=cfg.auto_push)
    
    save_new_config(cfg)
    console.print("[green]Configuration saved![/green]")

@app.command()
def init(
    allow_source_repo: bool = typer.Option(False, "--allow-source-repo", help="Allow initializing in ALO source repository")
):
    """Initialize ALO in the current directory as a new learning workspace."""
    cwd = Path.cwd()
    
    from alo.services.init_service import detect_init_state, prepare_init_plan, create_workspace_state, initialize_git_if_requested
    
    init_state = detect_init_state(cwd, allow_source_repo)
    if init_state == "source_repo":
        console.print("[red]Error: You are inside the ALO source repository.[/red]")
        console.print("Please run `alo init` in a separate learning folder.")
        raise typer.Exit(1)
        
    prepare_init_plan(cwd)
    
    if init_state == "initialized":
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
    
    profile_data = {
        "subject": subject,
        "background": background,
        "experience_level": experience_level.value,
        "goal": goal,
        "assess_now": assess_now,
        "privacy_preference": privacy_preference.value
    }
    
    create_workspace_state(cwd, profile_data)
    
    connect_remote = Confirm.ask("Do you want to connect a remote Git repository?", default=False)
    remote_url = None
    if connect_remote:
        remote_url = Prompt.ask("Enter remote URL")
        
    initialize_git_if_requested(cwd, do_git=True, remote_url=remote_url)
        
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
    """Run a domain-specific LLM assessment to gauge your current knowledge level."""
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
    """Generate learning path options based on your profile and assessment."""
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
    """Generate or update the roadmap for your active learning path."""
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
    """Start a daily learning session based on your current workspace roadmap."""
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
def sync(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be synced without committing."),
    push: Optional[bool] = typer.Option(None, "--push/--no-push", help="Push to remote after commit (overrides auto_push)."),
    message: str = typer.Option("ALO: sync learning state", "--message", "-m", help="Custom commit message."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Automatically confirm prompts (e.g. git init).")
):
    """Safely commit learning-state changes to Git."""
    from alo.services.git_service import SyncOptions, run_sync_service, is_git_repo, is_alo_source_repo
    cwd = Path.cwd()
    
    if is_alo_source_repo(cwd):
        console.print("[red]This looks like the ALO source repository.\nGit sync is only for learning workspaces.[/red]")
        raise typer.Exit(1)
        
    allow_init = yes
    if not is_git_repo(cwd) and not dry_run and not yes:
        allow_init = Confirm.ask("Git is not initialized in this workspace. Do you want to initialize it now?", default=False)
        
    options = SyncOptions(dry_run=dry_run, push=push, message=message, allow_init=allow_init)
    
    with console.status("Syncing..." if not dry_run else "Simulating sync..."):
        result = run_sync_service(cwd, options)
        
    if result.error:
        console.print(f"[red]{result.error}[/red]")
        if not result.success:
            raise typer.Exit(1)
            
    if result.no_changes:
        console.print("[yellow]No safe learning-state changes to sync.[/yellow]")
        return
        
    console.print("\n[bold cyan]Git Sync Summary[/bold cyan]")
    if result.repo_initialized:
        console.print("  [green]Initialized new Git repository.[/green]")
    if result.staged_files:
        console.print("  [green]Safe changes:[/green]")
        for f in result.staged_files:
            console.print(f"    - {f}")
    if result.ignored_files:
        console.print("  [yellow]Ignored files:[/yellow]")
        for f in result.ignored_files:
            console.print(f"    - {f}")
            
    if result.is_dry_run:
        console.print("\n[yellow]Dry run completed. No files were committed.[/yellow]")
        return
        
    if result.commit_hash:
        console.print(f"\n[green]Committed safely ({result.commit_hash}).[/green]")
        
    if result.pushed:
        console.print("[green]Pushed to remote.[/green]")

@app.command()
def doctor():
    """Check environment health and LLM readiness."""
    cwd = Path.cwd()
    from alo.ui import views
    console.print(views.build_doctor_view(cwd))

@app.command()
def review(
    mock: bool = typer.Option(False, "--mock", help="Use mock review content for testing."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not save evaluation results to state."),
    weakness: str = typer.Option(None, "--weakness", help="Specific weakness ID to review."),
    item: str = typer.Option(None, "--item", help="Specific roadmap item ID to review."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip non-destructive confirmations.")
):
    """Review past concepts and update your weaknesses profile."""
    cwd = Path.cwd()
    if not (cwd / "learning-profile.md").exists():
        console.print("[yellow]Not an ALO workspace. Run `alo init` first.[/yellow]")
        raise typer.Exit(1)
        
    from alo.services.review_service import generate_review_service, evaluate_review_service
    
    if not mock:
        console.print("[cyan]Generating review session...[/cyan]")
        
    res = generate_review_service(cwd, mock=mock, weakness_id=weakness, item_id=item)
    
    if not res.success:
        console.print(f"[red]{res.error}[/red]")
        raise typer.Exit(1)
        
    if res.warning:
        console.print(f"[yellow]{res.warning}[/yellow]")
        
    session_ctx = res.context
    session = session_ctx.session
    
    console.print(Panel(f"[bold cyan]Review Session[/bold cyan]: {session.topic} ({session_ctx.target_id})"))
    console.print(Markdown(session.short_review))
    console.print("\n[bold magenta]Why This Matters:[/bold magenta]")
    console.print(Markdown(session.why_this_matters))
    console.print("\n[bold red]Common Mistake:[/bold red]")
    console.print(Markdown(session.common_mistake))
    console.print(Panel(session.review_question, title="Review Question", style="green"))
    
    answer = Prompt.ask("\n[yellow]Your Answer[/yellow]")
    
    if not mock:
        console.print("[cyan]Evaluating answer...[/cyan]")
        
    eval_res = evaluate_review_service(cwd, session_ctx, answer, mock=mock, dry_run=dry_run)
    
    if not eval_res.success:
        console.print(f"[red]{eval_res.error}[/red]")
        raise typer.Exit(1)
        
    evaluation = eval_res.evaluation
    eval_color = "green" if evaluation.result == "pass" else ("yellow" if evaluation.result == "partial" else "red")
    
    console.print(Panel(f"Result: {evaluation.result.upper()} (Score: {evaluation.score})", style=eval_color))
    console.print(Markdown(evaluation.feedback))
    console.print(f"\n[bold green]Strengths:[/bold green] {evaluation.strengths}")
    console.print(f"[bold red]Remaining Gaps:[/bold red] {evaluation.remaining_gaps}")
    console.print(f"[bold cyan]Next Step:[/bold cyan] {evaluation.recommended_next_step}")
    
    if not dry_run:
        console.print("\n[green]State updated successfully.[/green]")
    else:
        console.print("\n[yellow]State not updated (dry run).[/yellow]")

if __name__ == "__main__":
    app()
