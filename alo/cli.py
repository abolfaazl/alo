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
def status(
    json_output: bool = typer.Option(False, "--json", help="Output status as JSON")
):
    """Shows current learning state."""
    cwd = Path.cwd()
    from alo.services.status_service import compute_workspace_status
    
    status_obj = compute_workspace_status(cwd)
    
    if json_output:
        print(status_obj.model_dump_json(indent=2))
        return

    if status_obj.is_source_repo:
        console.print("[yellow]This is the ALO development repository.[/yellow]")
        console.print("Do not treat it as a learning workspace.")
        console.print("Next step: Create a separate learning workspace using `alo init` in a new directory.")
        raise typer.Exit(0)
        
    if not status_obj.is_workspace:
        console.print("[red]Not an ALO workspace. Missing learning-profile.md.[/red]")
        console.print("Next step: Run `alo init`")
        raise typer.Exit(1)
        
    from rich.panel import Panel
    from rich.console import Group
    from rich.text import Text
    import sys
    
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    from alo import __version__
    
    renderables = []
    
    # Workspace block
    ws_text = "[bold]Workspace[/bold]\n"
    ws_text += f"- Path: {status_obj.workspace_path}\n"
    ws_text += f"- Subject: {status_obj.subject}\n"
    ws_text += f"- Python: {py_version}\n"
    ws_text += f"- ALO version: {__version__}\n"
    renderables.append(Text.from_markup(ws_text))
    
    # Learning Stats
    stats = status_obj.stats
    st_text = "[bold]Learning Stats[/bold]\n"
    st_text += f"- Lessons completed: {stats.lessons_completed}\n"
    st_text += f"- Reviews completed: {stats.reviews_completed}\n"
    st_text += f"- Practice sessions: {stats.practice_sessions}\n"
    st_text += f"- Active days: {stats.active_learning_days}\n"
    st_text += f"- Current streak: {stats.current_streak_days} days\n"
    st_text += f"- Roadmap completion: {stats.roadmap_completion_percent}%\n"
    renderables.append(Text.from_markup(st_text))
    
    # Gamification
    gam = status_obj.gamification
    earned_badges = sum(1 for b in gam.badges if b.earned)
    total_badges = len(gam.badges)
    gm_text = "[bold]Learning Momentum[/bold]\n"
    gm_text += f"- XP: {gam.xp}\n"
    gm_text += f"- Level: {gam.level}\n"
    gm_text += f"- Weekly goal: {gam.weekly_goal_progress} / {gam.weekly_goal_target} days\n"
    gm_text += f"- Earned badges: {earned_badges} / {total_badges}\n"
    renderables.append(Text.from_markup(gm_text))
    
    # Portfolio
    port = status_obj.portfolio
    pt_text = "[bold]Portfolio[/bold]\n"
    pt_text += f"- README.md: {'exists' if port.readme_exists else 'missing'}\n"
    pt_text += f"- Charts: {port.charts_existing} / {port.charts_total} generated\n"
    for c_name, exists in port.chart_files.items():
        pt_text += f"- assets/{c_name}: {'exists' if exists else 'missing'}\n"
    renderables.append(Text.from_markup(pt_text))
    
    # Git
    git = status_obj.git
    gt_text = "[bold]Git Sync[/bold]\n"
    gt_text += f"- Git repo: {'yes' if git.is_git_repo else 'no'}\n"
    gt_text += f"- Remote configured: {'yes' if git.remote_configured else 'no'}\n"
    gt_text += f"- Safe generated files: {'ready' if port.readme_exists else 'not ready'}\n"
    gt_text += f"- Unsafe staged files: {'none' if git.unsafe_staged_count == 0 else str(git.unsafe_staged_count)}\n"
    renderables.append(Text.from_markup(gt_text))
    
    # Next Steps
    ns_text = "[bold]Next Step[/bold]\n"
    for step in status_obj.next_steps:
        ns_text += f"- {step}\n"
    renderables.append(Text.from_markup(ns_text))
    
    panel = Panel(Group(*renderables), title="[bold cyan]ALO Workspace Status[/bold cyan]", border_style="cyan")
    console.print(panel)

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
    
    if force and not yes and (repo_path / "roadmap.md").exists():
        do_overwrite = Confirm.ask("roadmap.md already exists. Regenerating will overwrite it. Continue?", default=False)
        if not do_overwrite:
            console.print("[yellow]Roadmap generation cancelled.[/yellow]")
            raise typer.Exit(0)
            
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
    
    from alo.services.practice_session_service import parse_practice_items
    items = parse_practice_items(session.practice_question)
    
    if len(items) == 1:
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
    else:
        # Multi-item flow
        passed = 0
        failed = 0
        console.print(f"[bold magenta]Multi-part Practice ({len(items)} items)[/bold magenta]")
        for idx, item_obj in enumerate(items):
            console.print(f"\n[bold green]Practice Question {idx+1} / {len(items)}[/bold green]")
            console.print(Panel(item_obj.prompt, style="green"))
            
            answer = Prompt.ask("Your answer")
            if not answer.strip():
                answer = Prompt.ask("Your answer (cannot be empty)")
                if not answer.strip():
                    console.print("[yellow]Session cancelled midway.[/yellow]")
                    break
                    
            if not mock:
                console.print("[cyan]Evaluating answer...[/cyan]")
                
            # Temporarily replace the practice_question for evaluation context
            original_question = session_ctx.session.practice_question
            session_ctx.session.practice_question = item_obj.prompt
            
            eval_res = evaluate_answer(repo_path, session_ctx, answer, mock=mock, dry_run=dry_run)
            
            session_ctx.session.practice_question = original_question
            
            if not eval_res.success:
                console.print(f"[red]{eval_res.error}[/red]")
                continue
                
            evaluation = eval_res.evaluation
            if evaluation.result == "pass":
                passed += 1
                eval_color = "green"
            else:
                failed += 1
                eval_color = "yellow" if evaluation.result == "partial" else "red"
                
            console.print(Panel(f"Result: {evaluation.result.upper()} (Score: {evaluation.score})", style=eval_color))
            console.print(Markdown(evaluation.feedback))
            
            # Show correct answer if failed and available in mock/etc, but LLM usually includes it in feedback.
            # We don't have a rigid expected_answer field natively in the Evaluation schema. The prompt feedback is enough.

        console.print(Panel(f"Practice Complete\nScore: {passed} / {len(items)}\nPassed: {passed}\nFailed: {failed}", title="Summary", style="blue"))


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

@app.command(name="readme")
@app.command(name="portfolio", hidden=True)
def readme(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview generated README without writing"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing README.md"),
    output: Path = typer.Option(None, "--output", help="Optional output path"),
    include_charts: bool = typer.Option(False, "--include-charts", help="Generate and embed local progress SVGs"),
    include_gamification: bool = typer.Option(False, "--include-gamification", help="Include gamification stats and badges"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompts")
):
    """Generate a learning workspace README."""
    cwd = Path.cwd()
    from alo.services.readme_service import write_workspace_readme, generate_workspace_readme
    
    target_out = output or (cwd / "README.md")
    if force and not yes and target_out.exists():
        do_overwrite = Confirm.ask(f"{target_out.name} already exists. Regenerating will overwrite it. Continue?", default=False)
        if not do_overwrite:
            console.print("[yellow]README generation cancelled.[/yellow]")
            raise typer.Exit(0)
    
    if dry_run:
        from alo.services.git_service import is_alo_source_repo
        if is_alo_source_repo(cwd):
            console.print("[red]Cannot generate README in the ALO source repository.[/red]")
            raise typer.Exit(1)
        if not (cwd / "learning-profile.md").exists():
            console.print("[red]Not an ALO workspace. Run `alo init` first.[/red]")
            raise typer.Exit(1)
            
        content = generate_workspace_readme(cwd, include_charts=include_charts, include_gamification=include_gamification)
        console.print(content)
        
        if include_charts:
            from alo.services.chart_service import generate_workspace_charts
            charts_data = generate_workspace_charts(cwd)
            console.print("\n[yellow]Charts that would be generated:[/yellow]")
            for name in charts_data.keys():
                console.print(f"  - assets/{name}")
        return

    result = write_workspace_readme(cwd, output_path=output, force=force, include_charts=include_charts, include_gamification=include_gamification)
    
    if not result.written:
        if "already exists" in result.message:
            console.print(f"[yellow]{result.message}[/yellow]")
        else:
            console.print(f"[red]{result.message}[/red]")
        raise typer.Exit(1)
        
    console.print(f"[green]{result.message}[/green]")
    if include_charts:
        console.print("[green]Generated 4 SVG charts in assets/[/green]")

@app.command(name="badges")
@app.command(name="badge", hidden=True)
def badges():
    """View local gamification summary and badges."""
    cwd = Path.cwd()
    from alo.services.git_service import is_alo_source_repo
    if is_alo_source_repo(cwd):
        console.print("[red]Cannot run gamification inside the ALO source repository.[/red]")
        raise typer.Exit(1)
    if not (cwd / "learning-profile.md").exists():
        console.print("[red]Not an ALO workspace. Run `alo init` first.[/red]")
        raise typer.Exit(1)
        
    from alo.services.gamification_service import compute_gamification_summary
    
    try:
        summary = compute_gamification_summary(cwd)
        console.print("\n[bold]Learning Gamification[/bold]")
        console.print(f"XP: [yellow]{summary.xp}[/yellow] | Level: [cyan]{summary.level}[/cyan]")
        console.print(f"Current Streak: {summary.current_streak_days} days | Longest: {summary.longest_streak_days} days")
        console.print(f"Weekly Goal: {summary.weekly_goal_progress} / {summary.weekly_goal_target} days")
        console.print(f"Consistency Score: {summary.consistency_score} / 100")
        
        earned = [b for b in summary.badges if b.earned]
        console.print(f"\n[bold]Earned Milestones ({len(earned)})[/bold]")
        if not earned:
            console.print("  (None yet, keep learning!)")
        else:
            for b in earned:
                console.print(f"  [green]✓[/green] [bold]{b.label}[/bold] — {b.description}")
                
        locked = [b for b in summary.badges if not b.earned]
        console.print(f"\n[bold]Locked Milestones ({len(locked)})[/bold]")
        for b in locked:
            console.print(f"  [dim]· {b.label} — {b.description} ({b.progress}/{b.target})[/dim]")
            
    except Exception as e:
        console.print(f"[red]Failed to compute gamification summary:[/red] {e}")
        raise typer.Exit(1)

@app.command(name="charts")
def charts(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview generated charts without writing"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing SVG files"),
    output_dir: Path = typer.Option(None, "--output-dir", help="Optional output directory inside workspace"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompts")
):
    """Generate local SVG progress charts."""
    cwd = Path.cwd()
    from alo.services.chart_service import write_workspace_charts, generate_workspace_charts
    
    target_dir = output_dir or (cwd / "assets")
    if force and not yes and target_dir.exists() and list(target_dir.glob("alo-*.svg")):
        do_overwrite = Confirm.ask(f"Existing SVGs found in {target_dir.name}/. Regenerating will overwrite them. Continue?", default=False)
        if not do_overwrite:
            console.print("[yellow]Charts generation cancelled.[/yellow]")
            raise typer.Exit(0)
    
    if dry_run:
        from alo.services.git_service import is_alo_source_repo
        if is_alo_source_repo(cwd):
            console.print("[red]Cannot generate charts in the ALO source repository.[/red]")
            raise typer.Exit(1)
        if not (cwd / "learning-profile.md").exists():
            console.print("[red]Not an ALO workspace. Run `alo init` first.[/red]")
            raise typer.Exit(1)
            
        charts_data = generate_workspace_charts(cwd)
        console.print("[yellow]Dry run. Planned files:[/yellow]")
        for name in charts_data.keys():
            console.print(f"  - {name}")
        return

    result = write_workspace_charts(cwd, output_dir=output_dir, force=force)
    
    if not result.written:
        if "already exists" in result.message:
            console.print(f"[yellow]{result.message}[/yellow]")
        else:
            console.print(f"[red]{result.message}[/red]")
            raise typer.Exit(1)
    else:
        console.print(f"[green]{result.message}[/green]")
        for f in result.files:
            console.print(f"  - {f}")

if __name__ == "__main__":
    app()
