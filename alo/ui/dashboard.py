from pathlib import Path
import shlex
import argparse
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Input, RichLog, Label
from textual.screen import Screen
from textual.binding import Binding
from textual import work

from alo import workspace, state_manager, config as alo_config
from alo.ui import views
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

class DashboardScreen(Screen):
    """The main dashboard layout."""
    
    BINDINGS = [
        Binding("ctrl+x", "toggle_sidebar", "Toggle Sidebar", show=False)
    ]
    
    def __init__(self, is_workspace: bool, workspace_info: dict, **kwargs):
        super().__init__(**kwargs)
        self.is_workspace = is_workspace
        self.workspace_info = workspace_info
        self.app_state = "idle"
        self.state_data = {}

    def compose(self) -> ComposeResult:
        logo_text = (
            "ALO  Agentic Learning OS\n"
            "Build · 1.0.0"
        )
        
        with Vertical(id="app-container"):
            with Container(id="header"):
                yield Static(logo_text, id="logo")
                
            with Horizontal(id="main-layout"):
                with Vertical(id="chat-pane"):
                    yield RichLog(id="chat-log", markup=True)
                    with Container(id="chat-input-container"):
                        yield Input(placeholder="Type a command or '/' for commands...", id="chat-input")
                
                with Vertical(id="sidebar"):
                    if self.is_workspace:
                        yield Label("Workspace", classes="sidebar-title")
                        yield Label(self.workspace_info.get("cwd", ""), classes="sidebar-text")
                        yield Static("", classes="spacer")
                        yield Label("Subject", classes="sidebar-title")
                        yield Label(self.workspace_info.get("subject", ""), classes="sidebar-text")
                        yield Static("", classes="spacer")
                        yield Label("Active Path", classes="sidebar-title")
                        yield Label(self.workspace_info.get("active_path", ""), classes="sidebar-text")
                        yield Static("", classes="spacer")
                        yield Label("Roadmap Status", classes="sidebar-title")
                        yield Label(f"{self.workspace_info.get('rm_items', 0)} items pending", classes="sidebar-text")
                        yield Static("", classes="spacer")
                        yield Label("LLM Config", classes="sidebar-title")
                        yield Label(self.workspace_info.get("cfg_status", ""), classes="sidebar-text")
                        yield Static("", classes="spacer")
                        yield Label("Git Status", classes="sidebar-title")
                        yield Label(self.workspace_info.get("git_status", "Not tracked"), classes="sidebar-text")
                    else:
                        yield Label("Workspace", classes="sidebar-title")
                        yield Label("Not Initialized", classes="sidebar-text", id="uninitialized-warning")
                    
                    with Vertical(id="sidebar-footer"):
                        yield Label("/*", classes="sidebar-text")
                        yield Label("• ALO 1.0.0", classes="sidebar-text")

    def on_mount(self) -> None:
        self.query_one("#chat-input", Input).focus()
        log = self.query_one("#chat-log", RichLog)
        if self.is_workspace:
            log.write(views.build_home_view(self.workspace_info))
        else:
            log.write(Panel(
                "[yellow]No ALO workspace detected here.[/yellow]\n"
                "Type [bold cyan]init[/bold cyan] to learn how to create one.",
                title="ALO Home", border_style="yellow"
            ))

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar")
        sidebar.display = not sidebar.display

    def on_input_submitted(self, event: Input.Submitted) -> None:
        cmd_raw = event.value.strip()
        self.query_one("#chat-input", Input).value = ""
        log = self.query_one("#chat-log", RichLog)
        
        if not cmd_raw:
            return

        if self.app_state != "idle":
            log.write(f"\n> {cmd_raw}")
            self.handle_state_input(cmd_raw, log)
            return
            
        log.write(f"\n> {cmd_raw}")
        
        try:
            args = shlex.split(cmd_raw)
        except ValueError:
            log.write("[red]Error parsing command.[/red]")
            return
            
        if not args:
            return
            
        cmd = args[0].lstrip("/").lower()
        if cmd == "alo":
            args = args[1:]
            if not args:
                return
            cmd = args[0].lower()
            
        # Aliases & Typos
        if cmd == "path":
            cmd = "paths"
        elif cmd in ["asess", "asses"]: 
            log.write(f"[yellow]Unknown command: {cmd}. Did you mean: assess?[/yellow]")
            return
        elif cmd == "road map":
            cmd = "roadmap"
        elif cmd in ["q", "exit"]:
            cmd = "quit"

        if cmd == "quit":
            self.app.exit()
            return
            
        cwd = Path.cwd()
        
        if cmd_raw == "/":
            self.show_command_menu(log)
        elif cmd == "home":
            if self.is_workspace:
                log.write(views.build_home_view(self.workspace_info))
            else:
                log.write(Panel("Not initialized.", border_style="yellow"))
        elif cmd == "status":
            log.write(views.build_status_view(cwd))
        elif cmd == "doctor":
            log.write(views.build_doctor_view(cwd))
        elif cmd == "help":
            self.show_command_menu(log)
        elif cmd == "clear":
            log.clear()
            if self.is_workspace:
                log.write(views.build_home_view(self.workspace_info))
        elif cmd == "paths":
            self.run_paths_flow(args[1:], log, cwd)
        elif cmd == "roadmap":
            self.run_roadmap_flow(args[1:], log, cwd)
        elif cmd == "learn":
            self.run_learn_flow(args[1:], log, cwd)
        elif cmd == "assess":
            self.run_assess_flow(args[1:], log, cwd)
        elif cmd == "config":
            log.write(Panel("Config interactive flow placeholder. Use `alo config` from CLI for now.", border_style="yellow"))
        elif cmd == "review":
            log.write(Panel("Review mode is not implemented yet. It will be added in Phase 8.", border_style="blue"))
        elif cmd == "init":
            log.write(Panel(
                f"This command is available from the CLI. Inline dashboard execution will be improved later.\n"
                f"Run: [bold cyan]alo {cmd}[/bold cyan]",
                border_style="yellow"
            ))
        else:
            log.write(f"[red]Unknown command: {cmd}.[/red] Type [bold]/[/bold] to see available commands.")

    def show_command_menu(self, log):
        text = (
            "[bold cyan]/init[/bold cyan]      Initialize workspace\n"
            "[bold cyan]/config[/bold cyan]    Configure provider/model/base_url/env var\n"
            "[bold cyan]/status[/bold cyan]    Show workspace status\n"
            "[bold cyan]/assess[/bold cyan]    Run subject-specific assessment\n"
            "[bold cyan]/paths[/bold cyan]     Generate/select learning paths\n"
            "[bold cyan]/roadmap[/bold cyan]   Generate roadmap\n"
            "[bold cyan]/learn[/bold cyan]     Run learning session\n"
            "[bold cyan]/review[/bold cyan]    Review weaknesses\n"
            "[bold cyan]/doctor[/bold cyan]    Environment health\n"
            "[bold cyan]/help[/bold cyan]      Show commands\n"
            "[bold cyan]/clear[/bold cyan]     Clear screen\n"
            "[bold cyan]/quit[/bold cyan]      Exit ALO\n"
        )
        log.write(Panel(text, title="ALO Commands"))

    def handle_state_input(self, text: str, log):
        state = self.app_state
        data = self.state_data
        cwd = Path.cwd()
        
        if state == "paths_selecting":
            choice = text.strip()
            if choice not in ["1", "2", "3", "skip"]:
                log.write("[red]Invalid choice. Select 1, 2, 3, or skip.[/red]")
                return
            
            from alo.services.paths_service import select_path
            choice_idx = None if choice == "skip" else int(choice) - 1
            msg = select_path(cwd, data["paths"], choice_idx, dry_run=data["dry_run"])
            
            if choice_idx is not None:
                log.write(f"\n[green]{msg}[/green]")
            else:
                log.write(f"\n[yellow]{msg}[/yellow]")
            self.app_state = "idle"
            
        elif state == "learn_answering":
            if not text.strip():
                log.write("[red]Your answer cannot be empty.[/red]")
                return
            self.app_state = "idle"
            self.run_learn_evaluate_worker(cwd, data["session_ctx"], text, mock=data["mock"], dry_run=data["dry_run"], log=log)
            
        elif state == "assess_answering":
            from alo import assessment
            ans_idx = assessment.normalize_answer(text)
            q_idx = data["current_q"]
            q = data["questions"][q_idx]
            
            if ans_idx is None or ans_idx >= len(q.choices):
                log.write("[red]Invalid choice. Please answer A/B/C/D or 1/2/3/4.[/red]")
                return
                
            data["answers"].append(ans_idx)
            data["current_q"] += 1
            
            if data["current_q"] < len(data["questions"]):
                self._render_assess_question(log)
            else:
                self.app_state = "idle"
                self.run_assess_score_worker(cwd, data["questions"], data["answers"], mock=data["mock"], dry_run=data["dry_run"], log=log)

    def _parse_args(self, args, log):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--mock", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--yes", action="store_true")
        parser.add_argument("--item", type=str)
        try:
            return parser.parse_known_args(args)[0]
        except SystemExit:
            log.write("[red]Invalid arguments.[/red]")
            return None

    def run_paths_flow(self, args, log, cwd):
        parsed = self._parse_args(args, log)
        if not parsed:
            return
        log.write("[cyan]Generating paths...[/cyan]")
        self.run_paths_worker(cwd, mock=parsed.mock, dry_run=parsed.dry_run, log=log)

    @work(thread=True)
    def run_paths_worker(self, cwd, mock, dry_run, log):
        from alo.services.paths_service import get_paths
        res = get_paths(cwd, mock=mock)
        self.app.call_from_thread(self._on_paths_generated, res, mock, dry_run, log)

    def _on_paths_generated(self, res, mock, dry_run, log):
        if not res.success:
            log.write(f"[red]{res.error}[/red]")
            return
        if res.warning:
            log.write(f"[yellow]{res.warning}[/yellow]")
            
        for idx, p in enumerate(res.paths):
            log.write(f"\n[bold blue]{idx + 1}. {p.title}[/bold blue] (Confidence: {p.confidence})")
            log.write(f"   Summary: {p.summary}")
            log.write(f"   Topics: {', '.join(p.core_topics)}")
            log.write(f"   Duration: {p.estimated_duration} | Difficulty: {p.difficulty}")
            
        log.write("\nSelect a path to continue? [1/2/3/skip]")
        self.app_state = "paths_selecting"
        self.state_data = {"paths": res.paths, "dry_run": dry_run}

    def run_roadmap_flow(self, args, log, cwd):
        parsed = self._parse_args(args, log)
        if not parsed:
            return
        if not parsed.mock:
            log.write("[cyan]Generating roadmap...[/cyan]")
        self.run_roadmap_worker(cwd, mock=parsed.mock, force=parsed.force, dry_run=parsed.dry_run, log=log)

    @work(thread=True)
    def run_roadmap_worker(self, cwd, mock, force, dry_run, log):
        from alo.services.roadmap_service import generate_roadmap_service
        res = generate_roadmap_service(cwd, mock=mock, force=force, dry_run=dry_run)
        self.app.call_from_thread(self._on_roadmap_generated, res, dry_run, log)

    def _on_roadmap_generated(self, res, dry_run, log):
        if not res.success:
            log.write(f"[red]{res.error}[/red]")
            return
        if res.warning:
            log.write(f"[yellow]{res.warning}[/yellow]")
            
        if dry_run:
            log.write(f"\n[yellow]Successfully generated {len(res.items)} roadmap items (dry run).[/yellow]")
        else:
            log.write(f"\n[green]Successfully generated {len(res.items)} roadmap items![/green]")
            
        table = Table(title=f"Roadmap Summary ({res.active_path_id})")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="magenta")
        table.add_column("Level", style="green")
        table.add_column("Status", style="yellow")
        for item in res.items:
            table.add_row(item.id, item.title, item.level, item.status)
        log.write(table)

    def run_learn_flow(self, args, log, cwd):
        parsed = self._parse_args(args, log)
        if not parsed:
            return
        if not parsed.mock:
            log.write("[cyan]Generating learning session...[/cyan]")
        self.run_learn_generate_worker(cwd, mock=parsed.mock, item_id=parsed.item, dry_run=parsed.dry_run, log=log)

    @work(thread=True)
    def run_learn_generate_worker(self, cwd, mock, item_id, dry_run, log):
        from alo.services.learn_service import generate_session
        res = generate_session(cwd, mock=mock, item_id=item_id)
        self.app.call_from_thread(self._on_learn_generated, res, mock, dry_run, log)

    def _on_learn_generated(self, res, mock, dry_run, log):
        if not res.success:
            log.write(f"[red]{res.error}[/red]")
            return
        if res.warning:
            log.write(f"[yellow]{res.warning}[/yellow]")
            
        session_ctx = res.context
        session = session_ctx.session
        
        log.write(Panel(f"Session: {session.topic} ({session_ctx.target_id})", style="blue"))
        log.write(Markdown(session.short_lesson))
        log.write("\n[bold cyan]Example:[/bold cyan]")
        log.write(Markdown(session.example))
        log.write("\n[bold red]Common Mistake:[/bold red]")
        log.write(Markdown(session.common_mistake))
        log.write(Panel(session.practice_question, title="Practice Question", style="green"))
        log.write("\n[yellow]Type your answer and press Enter.[/yellow]")
        
        self.app_state = "learn_answering"
        self.state_data = {"session_ctx": session_ctx, "mock": mock, "dry_run": dry_run}

    @work(thread=True)
    def run_learn_evaluate_worker(self, cwd, session_ctx, answer, mock, dry_run, log):
        from alo.services.learn_service import evaluate_answer
        if not mock:
            self.app.call_from_thread(log.write, "[cyan]Evaluating answer...[/cyan]")
        res = evaluate_answer(cwd, session_ctx, answer, mock=mock, dry_run=dry_run)
        self.app.call_from_thread(self._on_learn_evaluated, res, dry_run, log)

    def _on_learn_evaluated(self, res, dry_run, log):
        if not res.success:
            log.write(f"[red]{res.error}[/red]")
            return
        
        evaluation = res.evaluation
        eval_color = "green" if evaluation.result == "pass" else ("yellow" if evaluation.result == "partial" else "red")
        log.write(Panel(f"Result: {evaluation.result.upper()} (Score: {evaluation.score})", style=eval_color))
        log.write(Markdown(evaluation.feedback))
        log.write(f"\n[bold green]Strengths:[/bold green] {evaluation.strengths}")
        log.write(f"[bold red]Weaknesses:[/bold red] {evaluation.weaknesses}")
        log.write(f"[bold cyan]Next Step:[/bold cyan] {evaluation.recommended_next_step}")
        
        if not dry_run:
            log.write("\n[green]State updated successfully.[/green]")
        else:
            log.write("\n[yellow]State not updated (dry run).[/yellow]")

    def run_assess_flow(self, args, log, cwd):
        parsed = self._parse_args(args, log)
        if not parsed:
            return
        log.write("[cyan]Generating assessment...[/cyan]")
        self.run_assess_generate_worker(cwd, mock=parsed.mock, dry_run=parsed.dry_run, log=log)

    @work(thread=True)
    def run_assess_generate_worker(self, cwd, mock, dry_run, log):
        from alo.services.assess_service import generate_assessment_service
        res = generate_assessment_service(cwd, mock=mock)
        self.app.call_from_thread(self._on_assess_generated, res, mock, dry_run, log)

    def _on_assess_generated(self, res, mock, dry_run, log):
        if not res.success:
            log.write(f"[red]{res.error}[/red]")
            return
        if res.warning:
            log.write(f"[yellow]{res.warning}[/yellow]")
            
        log.write(Panel(f"[bold cyan]ALO Assessment[/bold cyan] - {res.subject}"))
        
        self.app_state = "assess_answering"
        self.state_data = {
            "questions": res.questions,
            "answers": [],
            "current_q": 0,
            "mock": mock,
            "dry_run": dry_run
        }
        self._render_assess_question(log)

    def _render_assess_question(self, log):
        data = self.state_data
        q_idx = data["current_q"]
        q = data["questions"][q_idx]
        log.write(f"\n[bold]Question {q_idx+1}/{len(data['questions'])}[/bold] ({q.domain} - {q.difficulty})")
        log.write(q.question)
        for j, choice in enumerate(q.choices):
            letter = chr(65 + j)
            log.write(f"{letter}) {choice}")
        log.write("[yellow]Your answer (A/B/C/D or 1/2/3/4):[/yellow]")

    @work(thread=True)
    def run_assess_score_worker(self, cwd, questions, answers, mock, dry_run, log):
        from alo.services.assess_service import score_assessment_service
        res = score_assessment_service(cwd, questions, answers, mock=mock, dry_run=dry_run)
        self.app.call_from_thread(self._on_assess_scored, res, dry_run, log)

    def _on_assess_scored(self, res, dry_run, log):
        if not res.success:
            log.write(f"[red]{res.error}[/red]")
            return
            
        result = res.result
        log.write("\n[bold cyan]Assessment Results[/bold cyan]")
        log.write(f"Total Score: {result.score_percent}% ({result.correct_answers}/{result.total_questions})")
        log.write(f"Level: {result.level}")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Domain")
        table.add_column("Score")
        for ds in result.domain_scores:
            table.add_row(ds.domain, f"{ds.score_percent}%")
        log.write(table)
        
        if dry_run:
            log.write("[yellow]Dry run completed. No files were updated.[/yellow]")
        else:
            log.write("[green]Assessment saved successfully.[/green]")

class AloApp(App[None]):
    CSS_PATH = "mimo.css"
    
    def __init__(self, is_workspace: bool, workspace_info: dict = None, **kwargs):
        super().__init__(**kwargs)
        self.is_workspace = is_workspace
        self.workspace_info = workspace_info or {}

    def get_default_screen(self) -> Screen:
        return DashboardScreen(self.is_workspace, self.workspace_info)

def show_dashboard(interactive: bool = True):
    cwd = Path.cwd()
    is_source = workspace.is_alo_source_repo(cwd)
    
    if is_source:
        from alo.ui.console import console
        panel = Panel(
            "[red]Development Repository Detected[/red]\n"
            "This is the ALO source repo, not a learning workspace.\n"
            "Create a separate folder and run `alo init` there.",
            title="Workspace Status",
            border_style="red"
        )
        console.print(panel)
        return

    is_workspace = state_manager.has_user_content(cwd / "learning-profile.md", state_manager.REQUIRED_FILES["learning-profile.md"])
    
    workspace_info = {}
    if is_workspace:
        from datetime import datetime
        lp = state_manager.markdown_store.read_text_safely(cwd / "learning-profile.md") or ""
        rm = state_manager.markdown_store.read_text_safely(cwd / "roadmap.md") or ""
        
        import re
        subject_match = re.search(r"Subject:\s*(.*)", lp)
        subject = subject_match.group(1).strip() if subject_match else "Unknown"
        
        path_match = re.search(r"\*\*Active Learning Path\*\*: (.+)", lp)
        active_path = path_match.group(1).strip() if path_match else "None"
        
        rm_items = len(re.findall(r"### ALO-RM-", rm))
        
        cfg_status = "OK" if alo_config.config_exists() else "Missing"
        
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
            
        git_status = "Tracked" if is_git_repo else "Not tracked"
        
        workspace_info = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cwd": str(cwd),
            "subject": subject,
            "active_path": active_path,
            "rm_items": rm_items,
            "cfg_status": cfg_status,
            "git_status": git_status
        }

    if not interactive:
        if is_workspace:
            from alo.ui.console import console
            console.print(f"Subject: {workspace_info.get('subject')}")
            console.print("Suggested next command: alo paths")
        else:
            from alo.ui.console import console
            console.print("No ALO workspace detected.")
        return

    app = AloApp(is_workspace=is_workspace, workspace_info=workspace_info)
    app.run()
