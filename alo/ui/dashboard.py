from pathlib import Path
import shlex
import argparse
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Input, RichLog, Label, TextArea, LoadingIndicator
from textual.screen import Screen
from textual.binding import Binding
from textual import work

from alo import workspace, state_manager, config as alo_config
from alo.ui import views
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from alo.ui.rtl import format_mixed_text_for_display
from alo.ui.choices import ChoicePrompt

class DashboardScreen(Screen):
    """The main dashboard layout."""
    
    BINDINGS = [
        Binding("ctrl+x", "toggle_sidebar", "Toggle Sidebar", show=False),
        Binding("escape", "cancel", "Cancel Operation", show=False),
        Binding("f9", "submit_textarea", "Submit Multiline", show=False),
        Binding("ctrl+j", "submit_textarea", "Submit Multiline", show=False),
        Binding("ctrl+s", "save_settings", "Save Settings", show=False),
        Binding("t", "test_connection", "Test Connection", show=False),
        Binding("q", "quit_settings", "Quit Settings", show=False)
    ]
    
    def __init__(self, is_workspace: bool, workspace_info: dict, **kwargs):
        super().__init__(**kwargs)
        self.is_workspace = is_workspace
        self.workspace_info = workspace_info
        self.app_state = "idle"
        self.state_data = {}

    def compose(self) -> ComposeResult:
        from alo import __version__
        logo_text = (
            "ALO  Agentic Learning OS\n"
            f"Build · {__version__}"
        )
        
        with Vertical(id="app-container"):
            with Container(id="header"):
                yield Static(logo_text, id="logo")
                
            with Horizontal(id="main-layout"):
                with Vertical(id="chat-pane"):
                    yield RichLog(id="chat-log", markup=True, wrap=True)
                    with Container(id="choice-container", classes="hidden"):
                        pass
                    with Vertical(id="chat-input-wrapper"):
                        with Horizontal(id="state-bar", classes="hidden"):
                            yield Static("Mode: idle", id="state-label")
                            yield Static("", id="prompt-label")
                        with Container(id="chat-input-container"):
                            yield Input(placeholder="Type a command or '/' for commands...", id="chat-input")
                            yield TextArea(id="chat-textarea", classes="hidden", show_line_numbers=True)
                            yield LoadingIndicator(id="loading-indicator", classes="hidden")
                
                with Vertical(id="sidebar"):
                    yield from self._build_sidebar_widgets()


    def on_mount(self) -> None:
        self.query_one("#chat-input", Input).focus()
        log = self.query_one("#chat-log", RichLog)
        log.wrap = True
        if self.is_workspace:
            log.write(views.build_home_view(self.workspace_info))
        else:
            log.write(Panel(
                "[yellow]No ALO workspace detected here.[/yellow]\n"
                "Type [bold cyan]init[/bold cyan] to learn how to create one.",
                title="ALO Home", border_style="yellow"
            ))

    def action_cancel(self) -> None:
        if self.app_state == "settings_menu":
            self.action_quit_settings()
            return
            
        if self.app_state != "idle":
            self.reset_input_prompt()
            log = self.query_one("#chat-log", RichLog)
            log.write("[yellow]Operation cancelled.[/yellow]")

    def action_save_settings(self) -> None:
        if self.app_state.startswith("settings_") and "config_obj" in self.state_data:
            from alo.config import save_config, load_config_result, validate_config_readiness
            cfg = self.state_data["config_obj"]
            log = self.query_one("#chat-log", RichLog)
            try:
                save_config(cfg)
                res = load_config_result()
                reloaded = res.config
                if (reloaded.llm_provider != cfg.llm_provider or
                    reloaded.model != cfg.model or
                    reloaded.base_url != cfg.base_url or
                    reloaded.api_key_storage != cfg.api_key_storage or
                    reloaded.default_language != cfg.default_language):
                    raise ValueError("Reload verification failed: fields do not match")
                
                # Check secret store readiness explicitly to ensure valid state
                readiness = validate_config_readiness(reloaded)
                key_status = next((i for i in readiness.items if i.key == "api_key"), None)
                if key_status and "missing" in key_status.safe_value.lower():
                    # We still saved the non-secret settings, but we should warn the user
                    pass
                
                self.state_data["config_result"] = res
                self.state_data["config_obj"] = reloaded
                self.state_data["settings_dirty"] = False
                log.write("\n[green]Saved and reloaded successfully.[/green]")
            except Exception as e:
                log.write(f"\n[red]Save failed:[/red] {e}")

            if self.app_state == "settings_menu":
                self._render_settings_menu(log)
            else:
                self.app_state = "settings_menu"
                self._render_settings_menu(log)

    def action_quit_settings(self) -> None:
        if self.app_state.startswith("settings_"):
            if self.state_data.get("settings_dirty"):
                log = self.query_one("#chat-log", RichLog)
                log.write("\n[yellow]Settings changes discarded.[/yellow]")
            self.reset_input_prompt()

    def action_test_connection(self) -> None:
        if self.app_state == "settings_menu":
            # Simulate selecting "Test API Connection"
            log = self.query_one("#chat-log", RichLog)
            data = self.state_data
            cfg = data["config_obj"]
            
            if data.get("settings_dirty"):
                log.write("[yellow]You have unsaved changes. Save before testing connection?[/yellow]")
                log.write("Select [bold]Save Changes[/bold] first, then test connection.")
                self._render_settings_menu(log)
                return
                
            from alo.config import validate_config_readiness
            cur_readiness = validate_config_readiness(cfg)
            if not cur_readiness.llm_ready:
                log.write("[red]Cannot test: LLM configuration is missing required fields.[/red]")
                self._render_settings_menu(log)
            else:
                self.enter_working_state("Testing API connection... Please wait.")
                self.run_llm_test_worker(cfg, log=log)

    def update_input_prompt(self, prompt_text: str, state_label: str, placeholder: str = "", is_password: bool = False, multi_line: bool = False) -> None:
        sb = self.query_one("#state-bar")
        sb.remove_class("hidden")
        self.query_one("#state-label", Static).update(f"[bold cyan]Mode:[/bold cyan] {state_label}")
        self.query_one("#prompt-label", Static).update(prompt_text)
        
        inp = self.query_one("#chat-input", Input)
        tarea = self.query_one("#chat-textarea", TextArea)
        
        if multi_line:
            inp.add_class("hidden")
            tarea.remove_class("hidden")
            tarea.text = ""
            tarea.focus()
        else:
            tarea.add_class("hidden")
            inp.remove_class("hidden")
            inp.placeholder = placeholder if placeholder else "Type your answer and press Enter. Esc cancels."
            inp.password = is_password
            inp.value = ""
            inp.focus()
        
    def reset_input_prompt(self) -> None:
        self.app_state = "idle"
        self.state_data = {}
        sb = self.query_one("#state-bar")
        sb.add_class("hidden")
        
        self.exit_working_state()
        
        inp = self.query_one("#chat-input", Input)
        inp.placeholder = "Type a command or '/' for commands..."
        inp.password = False
        inp.value = ""
        inp.remove_class("hidden")
        
        tarea = self.query_one("#chat-textarea", TextArea)
        tarea.add_class("hidden")
        tarea.text = ""
        
        inp.focus()
        cc = self.query_one("#choice-container")
        cc.add_class("hidden")
        if cc.children:
            cc.query("*").remove()

    def enter_working_state(self, message: str, pending_action: str | None = None) -> None:
        if pending_action:
            self.state_data["pending_guided_action"] = pending_action
            
        inp = self.query_one("#chat-input", Input)
        tarea = self.query_one("#chat-textarea", TextArea)
        ind = self.query_one("#loading-indicator", LoadingIndicator)
        
        inp.add_class("hidden")
        tarea.add_class("hidden")
        ind.remove_class("hidden")
        
        sb = self.query_one("#state-bar")
        sb.remove_class("hidden")
        self.query_one("#state-label", Static).update("[bold cyan]Working...[/bold cyan]")
        self.query_one("#prompt-label", Static).update(message)
        
    def exit_working_state(self) -> None:
        ind = self.query_one("#loading-indicator", LoadingIndicator)
        ind.add_class("hidden")
        
    def restore_input_after_worker(self) -> None:
        self.exit_working_state()
        if self.app_state == "idle":
            self.reset_input_prompt()
        elif "answering" in self.app_state:
            self.update_input_prompt("Type your answer. (Ctrl+Enter to submit, Esc to cancel)", "Answering", placeholder="Your answer...", multi_line=True)
        else:
            self.reset_input_prompt()

    def handle_worker_error(self, res, action: str, log) -> bool:
        """Returns True if error was handled, False if success"""
        self.restore_input_after_worker()
        
        if not res or not res.success:
            err_msg = res.error if res else "Unknown error occurred."
            err_code = getattr(res, "error_code", None) if res else "unknown_error"
            
            log.write(f"[red]Error during {action}:[/red] {err_msg}")
            
            if err_code in ("missing_config", "missing_api_key", "keyring_unavailable"):
                self.app_state = "guided_recovery"
                self.state_data["pending_guided_action"] = action
                
                title = "Assessment requires LLM configuration." if err_code == "missing_config" else "API key is missing."
                options = [
                    "Configure ALO now",
                    "Skip assessment and generate learning paths from self-report" if action == "assessment" else "Skip this step",
                    "Use mock/demo assessment",
                    "Cancel guided flow"
                ]
                if err_code != "missing_config":
                    options[0] = "Open settings and add API key"
                    options.insert(1, "Switch to environment-variable mode")
                    
                self.update_input_prompt("Choose what to do next:", "Recovery")
                self.show_choices(title, options)
            else:
                self.app_state = "idle"
                self.reset_input_prompt()
            return True
            
        return False

    def action_submit_textarea(self) -> None:
        tarea = self.query_one("#chat-textarea", TextArea)
        if not tarea.has_class("hidden") and tarea.has_focus:
            text = tarea.text
            tarea.text = ""
            log = self.query_one("#chat-log", RichLog)
            log.write(f"\n> {format_mixed_text_for_display(text)}")
            self.handle_state_input(text, log)

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar")
        sidebar.display = not sidebar.display

    def on_input_submitted(self, event: Input.Submitted) -> None:
        cmd_raw = event.value.strip()
        self.query_one("#chat-input", Input).value = ""
        log = self.query_one("#chat-log", RichLog)
        
        if self.app_state != "idle":
            log.write(f"\n> {format_mixed_text_for_display(cmd_raw)}")
            self.handle_state_input(cmd_raw, log)
            return

        if not cmd_raw:
            return
            
        if cmd_raw.endswith("\\"):
            log.write("[red]Invalid command syntax. Do not use a trailing backslash in ALO commands.[/red]")
            return
            
        log.write(f"\n> {format_mixed_text_for_display(cmd_raw)}")
        
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
            self.run_status_cmd(args[1:], log, cwd)
        elif cmd == "readme":
            self.run_readme_cmd(args[1:], log, cwd)
        elif cmd == "charts":
            self.run_charts_cmd(args[1:], log, cwd)
        elif cmd in ["badges", "badge"]:
            self.run_badges_cmd(args[1:], log, cwd)
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
        elif cmd in ["config", "settings"]:
            self.run_settings_flow(log)
        elif cmd == "review":
            self.run_review_flow(args[1:], log, cwd)
        elif cmd == "sync":
            self.run_sync_flow(args[1:], log, cwd)
        elif cmd == "init":
            self.run_init_flow(log, cwd)
        else:
            log.write(f"[red]Unknown command: {cmd}.[/red] Type [bold]/[/bold] to see available commands.")

    def show_command_menu(self, log):
        text = (
            "[bold cyan]/init[/bold cyan]            Initialize a new learning workspace\n"
            "[bold cyan]/config[/bold cyan]          Configure LLM provider and API key\n"
            "[bold cyan]/assess[/bold cyan]          Run a domain-specific assessment to gauge your level\n"
            "[bold cyan]/paths[/bold cyan]           Generate and select a learning path\n"
            "[bold cyan]/roadmap[/bold cyan]         Generate a roadmap for your active path\n"
            "[bold cyan]/learn[/bold cyan]           Start a daily learning session\n"
            "[bold cyan]/review[/bold cyan]          Review concepts and update your weaknesses\n"
            "[bold cyan]/sync[/bold cyan]            Save your learning state to Git\n"
            "[bold cyan]/doctor[/bold cyan]          Check environment health and readiness\n"
            "[bold cyan]/quit[/bold cyan]            Exit ALO\n\n"
            "[bold magenta]Recommended Flow:[/bold magenta]\n"
            "init → config → paths → roadmap → learn → review → sync"
        )
        log.write(Panel(text, title="Available Commands", border_style="blue"))

    def show_choices(self, label: str, options: list):
        container = self.query_one("#choice-container")
        container.remove_children()
        prompt = ChoicePrompt(label, options)
        container.mount(prompt)
        container.remove_class("hidden")
        
        # We also need to map the options index/text to allow text fallback
        self.state_data["choice_options"] = options
        
        # We manually intercept arrow keys on the chat input to route to choice options if we wanted to,
        # but since ChoicePrompt takes focus, arrows will natively work there!
        # If user clicks the input field, they can still type.

    def hide_choices(self):
        container = self.query_one("#choice-container")
        container.add_class("hidden")
        container.remove_children()
        if "choice_options" in self.state_data:
            del self.state_data["choice_options"]
        self.query_one("#chat-input", Input).focus()

    def on_choice_prompt_selected(self, message: ChoicePrompt.Selected):
        # Trigger handle_state_input with the selected value
        cmd_raw = message.value
        log = self.query_one("#chat-log", RichLog)
        log.write(f"\n> {format_mixed_text_for_display(cmd_raw)}")
        self.handle_state_input(cmd_raw, log)

    def on_choice_prompt_cancelled(self, message: ChoicePrompt.Cancelled):
        self.hide_choices()
        self.query_one("#chat-log", RichLog).write("[yellow]Selection cancelled.[/yellow]")
        
        if self.app_state == "settings_menu":
            # Simulate "Back"
            self.handle_state_input("Back", self.query_one("#chat-log", RichLog))
        else:
            self.app_state = "idle"
            self.reset_input_prompt()

    def handle_state_input(self, text: str, log):
        state = self.app_state
        data = self.state_data
        cwd = Path.cwd()
        
        # Choice fallback handler
        if "choice_options" in data:
            choice = text.strip()
            options = data["choice_options"]
            
            # Map numeric selection
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    text = options[idx]
            
            # Since ChoicePrompt emits Selected, we just hide it now.
            self.hide_choices()

        if state == "paths_selecting":
            choice = text.strip()
            # Paths has a special "skip" option that might not be in the numeric list directly if we didn't add it as an option,
            # wait, let's see how paths options are generated.
            # In run_paths_worker, we have an array of options.
            # If the text is the exact option string or numeric, we handled it.
            
            # Let's rebuild paths_selecting using the actual choice string
            # If user typed 'skip', handle it.
            if choice.lower() == "skip":
                choice_idx = None
            else:
                # Find which path it corresponds to
                matched_idx = next((i for i, p in enumerate(data["paths"]) if p.title == choice), None)
                if matched_idx is None:
                    # fallback if they typed '1' instead of title and choice wasn't mapped
                    if choice.isdigit() and 1 <= int(choice) <= len(data["paths"]):
                        choice_idx = int(choice) - 1
                    else:
                        log.write("[red]Invalid choice.[/red]")
                        self.app_state = "idle"
                        return
                else:
                    choice_idx = matched_idx
            
            from alo.services.paths_service import select_path
            msg = select_path(cwd, data["paths"], choice_idx, dry_run=data["dry_run"])
            
            if choice_idx is not None:
                log.write(f"\n[green]{msg}[/green]")
            else:
                log.write(f"\n[yellow]{msg}[/yellow]")
                
            if not data.get("dry_run"):
                from alo.state_manager import trigger_auto_sync
                if trigger_auto_sync(cwd, "paths selection"):
                    log.write("[dim]Safe local sync committed.[/dim]")
                
            if data.get("is_guided_flow"):
                self.app_state = "guided_start_roadmap"
                self.update_input_prompt("Generate roadmap for this path now?", "Guided Flow")
                self.show_choices("Generate roadmap?", ["yes", "no"])
            else:
                self.app_state = "idle"
                self.reset_input_prompt()
                
        elif state == "sync_init_choice":
            if text.strip().lower() == "yes":
                self.enter_working_state("Initializing Git and syncing... Please wait.")
                self.run_sync_worker(data["cwd"], dry_run=False, push=data["push"], message=data["message"], yes=True, log=log)
            else:
                log.write("Git sync aborted.")
                self.app_state = "idle"
                self.reset_input_prompt()
                
        elif state == "guided_recovery":
            choice = text.strip()
            if choice.startswith("Open settings now"):
                pending = self.state_data.get("pending_guided_action")
                self.run_settings_flow(log, pending_action=pending)
            elif choice.startswith("Use mock/demo"):
                pending = self.state_data.get("pending_guided_action")
                if pending == "assessment generation":
                    self.enter_working_state("Generating mock assessment... Please wait.")
                    self.run_assess_generate_worker(cwd, mock=True, dry_run=False, log=log)
                elif pending == "learning session generation":
                    self.enter_working_state("Generating mock learning session... Please wait.")
                    self.run_learn_generate_worker(cwd, mock=True, item_id=None, dry_run=False, log=log)
                elif pending == "paths generation":
                    self.enter_working_state("Generating mock paths... Please wait.")
                    self.run_paths_worker(cwd, mock=True, dry_run=False, log=log)
                elif pending == "roadmap generation":
                    self.enter_working_state("Generating mock roadmap... Please wait.")
                    self.run_roadmap_worker(cwd, mock=True, force=True, dry_run=False, log=log)
                elif pending == "review generation":
                    self.enter_working_state("Generating mock review... Please wait.")
                    self.run_review_generate_worker(cwd, mock=True, dry_run=False, weakness_id=None, item_id=None, log=log)
                else:
                    log.write(f"[yellow]Mock not implemented for {pending} via recovery.[/yellow]")
                    self.app_state = "idle"
                    self.reset_input_prompt()
            else:
                # Cancel or unknown
                self.app_state = "idle"
                self.reset_input_prompt()
            
            
        elif state == "guided_start_assess":
            if text.strip().lower() == "yes":
                self.enter_working_state("Generating assessment... Please wait.")
                self.run_assess_generate_worker(cwd, mock=data.get("mock", False), dry_run=False, log=log)
            else:
                self.app_state = "guided_start_paths"
                self.update_input_prompt("Generate learning paths now?", "Guided Flow")
                self.show_choices("Generate learning paths?", ["yes", "no"])
                
        elif state == "guided_start_paths":
            if text.strip().lower() == "yes":
                self.enter_working_state("Generating paths... Please wait.")
                self.run_paths_worker(cwd, mock=data.get("mock", False), dry_run=False, log=log)
            else:
                log.write("[green]Guided setup complete.[/green]")
                self.app_state = "idle"
                self.reset_input_prompt()
                
        elif state == "guided_start_roadmap":
            if text.strip().lower() == "yes":
                self.enter_working_state("Generating roadmap... Please wait.")
                self.run_roadmap_worker(cwd, mock=data.get("mock", False), force=True, dry_run=False, log=log)
            else:
                log.write("[green]Guided setup complete.[/green]")
                self.app_state = "idle"
                self.reset_input_prompt()
                
        elif state == "guided_start_learn":
            if text.strip().lower() == "yes":
                self.enter_working_state("Generating learning session... Please wait.")
                self.run_learn_generate_worker(cwd, mock=data.get("mock", False), item_id=None, dry_run=False, log=log)
            else:
                log.write("[green]Guided setup complete.[/green]")
                self.app_state = "idle"
                self.reset_input_prompt()

        elif state == "init_overwrite_choice":
            choice = text.strip().lower()
            if choice == "2": # Re-run onboarding
                log.write("Overwriting existing onboarding profile...")
                self.app_state = "init_subject"
                self.update_input_prompt("What is this learning project about? (e.g. English grammar, Java)", "Init - Subject", placeholder="Subject...")
            else: # cancel
                log.write("Onboarding aborted. Existing files preserved.")
                self.app_state = "idle"
                
        elif state == "init_subject":
            self.state_data["init"]["subject"] = text.strip()
            self.app_state = "init_background"
            log.write(f"Subject: {self.state_data['init']['subject']}")
            self.update_input_prompt("What do you already know about this subject? (Ctrl+Enter to submit, Esc to cancel)", "Init - Background", placeholder="Background...", multi_line=True)
            
        elif state == "init_background":
            self.state_data["init"]["background"] = text.strip()
            self.app_state = "init_level"
            log.write(f"Background: {self.state_data['init']['background']}")
            self.update_input_prompt("Current level:", "Init - Level")
            
            from alo.models import ExperienceLevel
            levels = [e.value for e in ExperienceLevel]
            self.show_choices("Current level:", levels)
            
        elif state == "init_level":
            self.state_data["init"]["experience_level"] = text.strip()
            self.app_state = "init_goal"
            log.write(f"Level: {self.state_data['init']['experience_level']}")
            self.update_input_prompt("What do you want to achieve? (Ctrl+Enter to submit, Esc to cancel)", "Init - Goal", placeholder="Goal...", multi_line=True)
            
        elif state == "init_goal":
            self.state_data["init"]["goal"] = text.strip()
            self.app_state = "init_assess_choice"
            log.write(f"Goal: {self.state_data['init']['goal']}")
            self.update_input_prompt("Do you want ALO to assess your current level now?", "Init - Assess Now")
            self.show_choices("Assess now?", ["yes", "no"])
            
        elif state == "init_assess_choice":
            self.state_data["init"]["assess_now"] = (text.strip().lower() == "yes")
            self.app_state = "init_privacy_choice"
            log.write(f"Assess Now: {self.state_data['init']['assess_now']}")
            self.update_input_prompt("May ALO store private project/company/client/repository names if mentioned?", "Init - Privacy")
            self.show_choices("Store private names?", ["yes", "no"])
            
        elif state == "init_privacy_choice":
            self.state_data["init"]["privacy_preference"] = (text.strip().lower() == "yes")
            self.app_state = "init_git_choice"
            log.write(f"Store Private Names: {self.state_data['init']['privacy_preference']}")
            self.update_input_prompt("Do you want to initialize Git here?", "Init - Git")
            self.show_choices("Init Git?", ["yes", "no"])
            
        elif state == "init_git_choice":
            self.state_data["init"]["do_git"] = (text.strip().lower() == "yes")
            self.app_state = "init_remote_choice"
            log.write(f"Init Git: {self.state_data['init']['do_git']}")
            self.update_input_prompt("Do you want to connect a remote Git repository?", "Init - Git Remote")
            self.show_choices("Connect remote?", ["yes", "no"])
            
        elif state == "init_remote_choice":
            if text.strip().lower() == "yes":
                self.app_state = "init_remote_url"
                log.write("Connect Remote: True")
                self.update_input_prompt("Enter remote URL:", "Init - Git Remote URL", placeholder="Remote URL...")
            else:
                self.state_data["init"]["remote_url"] = None
                log.write("Connect Remote: False")
                self.finish_init_flow(log, cwd)
                
        elif state == "init_remote_url":
            self.state_data["init"]["remote_url"] = text.strip()
            log.write(f"Remote URL: {self.state_data['init']['remote_url']}")
            self.finish_init_flow(log, cwd)            
        elif state == "settings_menu":
            cfg = data["config_obj"]
            readiness = data.get("readiness")
            text = text.strip()
            
            if text == "Fix next missing required setting":
                if not readiness or not readiness.next_required_key:
                    log.write("[yellow]No missing required settings![/yellow]")
                    self._render_settings_menu(log)
                    return
                mapping = {
                    "llm_provider": "Edit LLM Provider",
                    "model": "Edit Model",
                    "base_url": "Edit Base URL",
                    "api_key_storage": "Change API Key Storage Mode",
                    "api_key": "Replace API Key"
                }
                text = mapping.get(readiness.next_required_key, "Back")
                
            if text == "Edit LLM Provider":
                self.app_state = "settings_edit_provider"
                self.update_input_prompt("Select LLM Provider:", "Settings - Provider")
                self.show_choices("Provider:", ["openai", "openai-compatible", "local-mock"])
            elif text == "Edit Model":
                self.app_state = "settings_edit_model"
                self.update_input_prompt("Enter new Model:", "Settings - Model")
            elif text == "Edit Base URL":
                self.app_state = "settings_edit_base_url"
                self.update_input_prompt("Enter new Base URL (leave empty for default):", "Settings - Base URL")
            elif text == "Change API Key Storage Mode":
                self.app_state = "settings_edit_key_storage"
                self.update_input_prompt("Enter new API Key Storage Mode:", "Settings - Storage")
                self.show_choices("Mode:", ["keyring", "env"])
            elif text == "Replace API Key":
                if cfg.api_key_storage == "keyring":
                    self.app_state = "settings_edit_api_key_raw"
                    self.update_input_prompt("Paste your API key (will be stored securely):", "Settings - API Key", is_password=True)
                else:
                    self.app_state = "settings_edit_api_key_env_var"
                    self.update_input_prompt("Enter new environment variable name:", "Settings - Env Var")
            elif text == "Edit Default Language":
                self.app_state = "settings_edit_language"
                self.update_input_prompt("Enter new Default Language:", "Settings - Language")
            elif text == "Edit Git Remote":
                log.write("[yellow]Git Remote editing is not fully implemented yet.[/yellow]")
                self._render_settings_menu(log)
            elif text == "Test API Connection":
                if data.get("settings_dirty"):
                    log.write("[yellow]You have unsaved changes. Save before testing connection?[/yellow]")
                    log.write("Select [bold]Save Changes[/bold] first, then test connection.")
                    self._render_settings_menu(log)
                    return
                from alo.config import validate_config_readiness
                cur_readiness = validate_config_readiness(cfg)
                if not cur_readiness.llm_ready:
                    log.write("[red]Cannot test: LLM configuration is missing required fields.[/red]")
                    self._render_settings_menu(log)
                else:
                    self.enter_working_state("Testing API connection... Please wait.")
                    self.run_llm_test_worker(cfg, log=log)
            elif text == "Save Changes":
                if not data.get("settings_dirty"):
                    log.write("[yellow]No changes to save.[/yellow]")
                    self._render_settings_menu(log)
                else:
                    self.action_save_settings()
            elif text == "Back":
                if data.get("settings_dirty"):
                    log.write("[yellow]You have unsaved changes. Press Ctrl+S to save, or Q to discard.[/yellow]")
                    self._render_settings_menu(log)
                else:
                    self.reset_input_prompt()
            else:
                log.write("[red]Unknown option.[/red]")
                self._render_settings_menu(log)
                
        elif state == "settings_edit_provider":
            data["config_obj"].llm_provider = text.strip()
            data["settings_dirty"] = True
            data["connection_tested"] = "Not tested"
            self._render_settings_menu(log)
        elif state == "settings_edit_model":
            data["config_obj"].model = text.strip()
            data["settings_dirty"] = True
            data["connection_tested"] = "Not tested"
            self._render_settings_menu(log)
        elif state == "settings_edit_base_url":
            data["config_obj"].base_url = text.strip() or None
            data["settings_dirty"] = True
            data["connection_tested"] = "Not tested"
            self._render_settings_menu(log)
        elif state == "settings_edit_key_storage":
            data["config_obj"].api_key_storage = text.strip()
            data["settings_dirty"] = True
            data["connection_tested"] = "Not tested"
            self._render_settings_menu(log)
        elif state == "settings_edit_api_key_raw":
            raw_key = text.strip()
            if raw_key:
                import keyring
                key_name = "ALO_" + data["config_obj"].llm_provider.upper().replace("-", "_") + "_API_KEY"
                try:
                    keyring.set_password("alo", key_name, raw_key)
                    data["config_obj"].api_key_name = key_name
                    data["config_obj"].api_key_env_var = None
                    log.write("[green]API Key saved securely to keyring.[/green]")
                except Exception as e:
                    log.write(f"[red]Failed to save to keyring: {e}[/red]")
            data["settings_dirty"] = True
            data["connection_tested"] = "Not tested"
            self._render_settings_menu(log)
        elif state == "settings_edit_api_key_env_var":
            data["config_obj"].api_key_env_var = text.strip() or "OPENAI_API_KEY"
            data["config_obj"].api_key_name = None
            data["settings_dirty"] = True
            data["connection_tested"] = "Not tested"
            self._render_settings_menu(log)
        elif state == "settings_edit_language":
            data["config_obj"].default_language = text.strip() or "en"
            data["settings_dirty"] = True
            self._render_settings_menu(log)
        elif state == "settings_edit_safe_mode":
            data["config_obj"].safe_mode = (text.strip().lower() == "yes")
            data["settings_dirty"] = True
            self._render_settings_menu(log)
        elif state == "settings_edit_auto_push":
            data["config_obj"].auto_push = (text.strip().lower() == "yes")
            data["settings_dirty"] = True
            self._render_settings_menu(log)
            
        elif state == "learn_answering":
            if not text.strip():
                log.write("[red]Your answer cannot be empty.[/red]")
                return
            self.enter_working_state("Evaluating answer... Please wait.")
            
            idx = data.get("current_index", 0)
            items = data.get("items", [])
            
            if items:
                item = items[idx]
                original_question = data["session_ctx"].session.practice_question
                data["session_ctx"].session.practice_question = item.prompt
                data["original_practice_question"] = original_question
                
            self.run_learn_evaluate_worker(cwd, data["session_ctx"], text, mock=data["mock"], dry_run=data["dry_run"], log=log)
            
        elif state == "assess_answering":
            from alo import assessment
            q_idx = data["current_q"]
            q = data["questions"][q_idx]
            
            ans_idx = assessment.normalize_answer(text)
            if ans_idx is None:
                try:
                    ans_idx = q.choices.index(text)
                except ValueError:
                    pass
            
            if ans_idx is None or ans_idx >= len(q.choices):
                log.write("[red]Invalid choice. Please answer A/B/C/D or 1/2/3/4.[/red]")
                return
                
            data["answers"].append(ans_idx)
            data["current_q"] += 1
            
            if data["current_q"] < len(data["questions"]):
                self._render_assess_question(log)
            else:
                self.enter_working_state("Scoring assessment... Please wait.")
                self.run_assess_score_worker(cwd, data["questions"], data["answers"], mock=data["mock"], dry_run=data["dry_run"], log=log)
                
        elif state == "review_answering":
            if not text.strip():
                log.write("[red]Your answer cannot be empty.[/red]")
                return
            self.enter_working_state("Evaluating answer... Please wait.")
            self.run_review_evaluate_worker(cwd, data["session_ctx"], text, mock=data["mock"], dry_run=data["dry_run"], log=log)

    @work(thread=True)
    def run_llm_test_worker(self, cfg, log):
        try:
            from alo.services.llm_test_service import test_llm_connection
            res = test_llm_connection(cfg)
            self.app.call_from_thread(self._on_llm_test_completed, res, log)
        except Exception as e:
            from alo.services.results import ServiceResult
            res = ServiceResult(success=False, error_code='worker_error', error=f'Unexpected error: {e}')
            self.app.call_from_thread(self._on_llm_test_completed, res, log)
            
    def _on_llm_test_completed(self, res, log):
        self.exit_working_state()
        if res.success:
            msg = res.payload.get("message", "Success") if res.payload else "Success"
            log.write(f"\n✅ [green]{msg}[/green]")
            self.state_data["connection_tested"] = "Verified"
        else:
            log.write(f"\n❌ [red]Test failed:[/red] {res.error}")
            self.state_data["connection_tested"] = "Failed"
        self._render_settings_menu(log)

    def _parse_args(self, cmd_name, args, log):
        parser = argparse.ArgumentParser(prog=cmd_name, add_help=False)
        parser.add_argument("--mock", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--yes", action="store_true")
        parser.add_argument("--item", type=str)
        parser.add_argument("--weakness", type=str)
        parser.add_argument("--include-charts", action="store_true")
        parser.add_argument("--include-gamification", action="store_true")
        
        valid_flags = {
            "readme": ["--include-charts", "--include-gamification", "--dry-run", "--force", "--yes"],
            "charts": ["--dry-run", "--force", "--yes"],
            "roadmap": ["--mock", "--dry-run", "--force", "--yes"],
            "paths": ["--mock", "--dry-run", "--force", "--yes"],
            "learn": ["--mock", "--yes", "--item"],
            "review": ["--mock", "--yes", "--weakness", "--item"],
            "sync": ["--dry-run"],
            "badges": [],
            "badge": [],
            "status": [],
            "assess": ["--mock", "--dry-run", "--yes"],
        }
        
        allowed = valid_flags.get(cmd_name, [])
        for arg in args:
            if arg.startswith("--"):
                if arg not in allowed:
                    if arg in ["--including-gamification", "--include-gamification"]:
                        if cmd_name != "readme":
                            log.write(f"[red]Unknown option for {cmd_name}: {arg}[/red]")
                            log.write("Try: readme --include-gamification --force")
                            return None
                    log.write(f"[red]Unknown option for {cmd_name}: {arg}[/red]")
                    return None
                    
        try:
            parsed = parser.parse_args(args)
            if parsed.force and not parsed.yes and cmd_name in ["roadmap", "paths", "readme", "charts"]:
                log.write(f"[red]Refusing to run `{cmd_name} --force` without confirmation.[/red]")
                log.write(f"Use `{cmd_name} --force --yes` if you are sure.")
                return None
            return parsed
        except SystemExit:
            log.write("[red]Invalid arguments.[/red]")
            return None

    def _check_llm_readiness(self, action: str, log, mock: bool = False) -> bool:
        if mock:
            return True
            
        from alo.config import load_config, validate_config_readiness
        cfg = load_config()
        readiness = validate_config_readiness(cfg)
        
        if readiness.llm_ready:
            return True
            
        log.write(f"\n[red]{action.capitalize()} requires LLM configuration.[/red]")
        log.write("\nMissing:")
        for item in readiness.missing_required:
            log.write(f"- {item.label}")
            
        self.app_state = "guided_recovery"
        self.state_data["pending_guided_action"] = action
        self.update_input_prompt("Choose what to do next:", "Recovery")
        
        options = [
            "Open settings now",
            f"Use mock/demo {action.split(' ')[0]}",
            "Cancel"
        ]
        self.show_choices(f"{action.capitalize()} requires config", options)
        return False

    def run_paths_flow(self, args, log, cwd):
        parsed = self._parse_args('paths', args, log)
        if not parsed:
            return
        if not self._check_llm_readiness("paths generation", log, parsed.mock):
            return
            
        self.enter_working_state("Generating paths... Please wait.")
        self.run_paths_worker(cwd, mock=parsed.mock, dry_run=parsed.dry_run, log=log)

    @work(thread=True)
    def run_paths_worker(self, cwd, mock, dry_run, log):
        try:
            from alo.services.paths_service import get_paths
            res = get_paths(cwd, mock=mock)
            self.app.call_from_thread(self._on_paths_generated, res, mock, dry_run, log)

        except Exception as e:
            from alo.services.results import ServiceResult
            res = ServiceResult(success=False, error_code='worker_error', error=f'Unexpected error: {e}')
            self.app.call_from_thread(self._on_paths_generated, res, mock, dry_run, log)
    def _on_paths_generated(self, res, mock, dry_run, log):
        if self.handle_worker_error(res, "paths generation", log):
            return
        if res.warning:
            log.write(f"[yellow]{res.warning}[/yellow]")
            
        options = []
        for idx, p in enumerate(res.paths):
            log.write(f"\n[bold blue]{idx + 1}. {p.title}[/bold blue] (Confidence: {p.confidence})")
            log.write(f"   Summary: {p.summary}")
            log.write(f"   Topics: {', '.join(p.core_topics)}")
            log.write(f"   Duration: {p.estimated_duration} | Difficulty: {p.difficulty}")
            options.append(p.title)
            
        options.append("skip")
        
        self.app_state = "paths_selecting"
        self.state_data = {"paths": res.paths, "dry_run": dry_run}
        self.update_input_prompt("Select a path to continue [or type 'skip']:", "Choosing learning path")
        self.show_choices("Select a path to continue?", options)

    def run_settings_flow(self, log, pending_action: str | None = None):
        import alo.config as alo_config
        res = alo_config.load_config_result()
        self.state_data = {
            "config_obj": res.config,
            "config_result": res,
            "connection_tested": "Not tested"
        }
        if pending_action:
            self.state_data["pending_guided_action"] = pending_action
        self._render_settings_menu(log)
        
    def resume_guided_action(self, pending_action: str, log):
        cwd = Path.cwd()
        if pending_action == "assessment generation":
            self.enter_working_state("Generating assessment... Please wait.")
            self.run_assess_generate_worker(cwd, mock=False, dry_run=False, log=log)
        elif pending_action == "learning session generation":
            self.enter_working_state("Generating learning session... Please wait.")
            # item_id is missing since it was guided
            self.run_learn_generate_worker(cwd, mock=False, item_id=None, dry_run=False, log=log)
        elif pending_action == "paths generation":
            self.enter_working_state("Generating paths... Please wait.")
            self.run_paths_worker(cwd, mock=False, dry_run=False, log=log)
        elif pending_action == "roadmap generation":
            self.enter_working_state("Generating roadmap... Please wait.")
            self.run_roadmap_worker(cwd, mock=False, force=True, dry_run=False, log=log)
        elif pending_action == "review generation":
            self.enter_working_state("Generating review... Please wait.")
            self.run_review_generate_worker(cwd, mock=False, dry_run=False, weakness_id=None, item_id=None, log=log)
        else:
            self.app_state = "idle"
            self.reset_input_prompt()
        
    def _render_settings_menu(self, log):
        from alo.config import validate_config_readiness
        cfg = self.state_data["config_obj"]
        readiness = validate_config_readiness(cfg)
        
        self.state_data["readiness"] = readiness
        
        log.write("\n[bold cyan]ALO Settings[/bold cyan]\n")
        
        cres = self.state_data.get("config_result")
        if cres:
            log.write(f"[dim]Config file: {cres.path}[/dim]")
            log.write(f"[dim]Loaded from: {cres.loaded_from}[/dim]")
            if cres.warnings:
                for w in cres.warnings:
                    log.write(f"[bold yellow]Config warning: {w}[/bold yellow]")
        
        cwd = Path.cwd()
        log.write(f"[dim]Workspace: {cwd}[/dim]\n")
        
        conn_state = self.state_data.get("connection_tested", "Not tested")
        if readiness.llm_ready:
            if conn_state == "Verified":
                ready_status = "✅ [green]Config Complete | Connection: Verified[/green]"
            elif conn_state == "Failed":
                ready_status = "❌ [red]Config Complete | Connection: Failed[/red]"
            else:
                ready_status = "⚠️ [yellow]Config Complete | Connection: Not tested[/yellow]"
        else:
            ready_status = "❌ [red]Config Incomplete | Connection: Not tested[/red]"
            
        log.write(f"LLM Setup: {ready_status}\n")
        
        log.write("[bold]Required for AI learning:[/bold]")
        
        def _get_icon(st):
            if st == "configured":
                return "✅"
            if st == "missing":
                return "❌"
            if st == "warning":
                return "⚠️"
            return "➖"
            
        for item in readiness.items:
            if item.required or item.key == "base_url":
                log.write(f"{_get_icon(item.status)} {item.label:<19} {item.safe_value}")
                
        log.write("\n[bold]Optional:[/bold]")
        log.write(f"✅ Default Language    {cfg.default_language}")
        log.write(f"✅ Safe Mode           {'enabled' if cfg.safe_mode else 'disabled'}")
        log.write(f"➖ Auto Push           {'enabled' if cfg.auto_push else 'disabled'}")
        log.write(f"➖ Git Remote          {'not configured'}") # Keep simple for now
        
        options = []
        if not readiness.llm_ready and readiness.missing_required:
            next_step = readiness.missing_required[0].label
            log.write(f"\n[bold yellow]Next required step: Configure {next_step}[/bold yellow]")
            options.append("Fix next missing required setting")
            
        options.extend([
            "Edit LLM Provider",
            "Edit Model",
            "Edit Base URL",
            "Change API Key Storage Mode",
            "Replace API Key",
            "Edit Default Language",
            "Edit Git Remote",
            "Test API Connection",
            "Save Changes",
            "Back"
        ])
        
        status_text = "[bold yellow]Unsaved changes[/bold yellow]" if self.state_data.get("settings_dirty") else "[bold green]All changes saved[/bold green]"
        log.write(f"\n{status_text}")
        log.write("[bold cyan]Action Bar:[/bold cyan] [Enter] Edit  |  [Ctrl+S] Save  |  [T] Test Connection  |  [Esc] / [Q] Back")
        
        self.app_state = "settings_menu"
        self.update_input_prompt("Select action:", "Settings")
        self.show_choices("Settings:", options)
        
    def run_init_flow(self, log, cwd):
        from alo.services.init_service import detect_init_state
        init_state = detect_init_state(cwd, allow_source_repo=False)
        
        if init_state == "source_repo":
            log.write(Panel(
                "[red]This looks like the ALO source repository.[/red]\n"
                "Create a separate folder for a learning workspace and run `alo init` there.",
                border_style="red"
            ))
            return
            
        from alo.services.init_service import prepare_init_plan
        prepare_init_plan(cwd)
            
        if init_state == "initialized":
            log.write(Panel("ALO workspace already initialized.", border_style="yellow"))
            self.app_state = "init_overwrite_choice"
            self.update_input_prompt("Choose an option:", "Init")
            self.show_choices("Workspace exists:", ["Show status", "Re-run onboarding / update profile", "Cancel"])
            return
            
        log.write("\n[bold cyan]ALO Workspace Setup[/bold cyan]")
        self.app_state = "init_subject"
        self.state_data = {"init": {}}
        self.update_input_prompt("What is this learning project about? (e.g. English grammar, Java)", "Init - Subject", placeholder="Subject...")
        
    def finish_init_flow(self, log, cwd):
        data = self.state_data["init"]
        from alo.services.init_service import create_workspace_state, initialize_git_if_requested
        
        create_workspace_state(cwd, data)
        initialize_git_if_requested(cwd, do_git=data.get("do_git", False), remote_url=data.get("remote_url"))
        
        log.write(Panel("[green]Workspace setup complete.[/green]"))
        
        # update sidebar info
        self.workspace_info["cwd"] = str(cwd)
        self.workspace_info["subject"] = data["subject"]
        self.is_workspace = True
        
        self._refresh_sidebar(self.query_one("#sidebar"), cwd)
        
        self.state_data["is_guided_flow"] = True
        if data.get("assess_now"):
            log.write("\n[bold cyan]Next step:[/bold cyan] Start your assessment.")
            self.app_state = "guided_start_assess"
            self.update_input_prompt("Start assessment now?", "Guided Flow")
            self.show_choices("Start assessment now?", ["yes", "no"])
        else:
            log.write("\n[bold cyan]Next step:[/bold cyan] Generate learning paths.")
            self.app_state = "guided_start_paths"
            self.update_input_prompt("Assessment skipped. Generate learning paths from self-report now?", "Guided Flow")
            self.show_choices("Generate learning paths?", ["yes", "no"])
        
    def _build_sidebar_widgets(self):
        from textual.widgets import Static
        from textual.containers import Vertical
        from alo import __version__
        from alo.services.status_service import compute_workspace_status
        from alo.ui import views
        
        cwd = Path.cwd()
        widgets = []
        
        try:
            status = compute_workspace_status(cwd)
        except Exception as e:
            widgets.append(Label("Workspace Error", classes="sidebar-title", id="uninitialized-warning"))
            widgets.append(Label(f"Error reading status:\n{e}", classes="sidebar-text"))
            return widgets

        if status.is_workspace:
            widgets.append(Label("Workspace", classes="sidebar-title"))
            widgets.append(Label(views.truncate_middle(str(cwd), 30), classes="sidebar-text"))
            widgets.append(Static("", classes="spacer"))
            
            widgets.append(Label("Subject", classes="sidebar-title"))
            widgets.append(Label(status.subject or "None", classes="sidebar-text"))
            widgets.append(Static("", classes="spacer"))
            
            try:
                from alo import state_manager
                lp = state_manager.get_active_learning_path(cwd)
                if isinstance(lp, dict):
                    active_path_title = (
                        lp.get("title")
                        or lp.get("name")
                        or lp.get("label")
                        or lp.get("id")
                        or "None"
                    )
                else:
                    active_path_title = "None"
            except Exception:
                active_path_title = "Error"
                
            widgets.append(Label("Active Path", classes="sidebar-title"))
            widgets.append(Label(active_path_title, classes="sidebar-text"))
            widgets.append(Static("", classes="spacer"))
            
            if status.stats:
                widgets.append(Label("Roadmap Progress", classes="sidebar-title"))
                widgets.append(Label(f"{status.stats.roadmap_completed_items}/{status.stats.roadmap_total_items} ({status.stats.roadmap_completion_percent}%)", classes="sidebar-text"))
                widgets.append(Static("", classes="spacer"))
                
                widgets.append(Label("Learning Stats", classes="sidebar-title"))
                widgets.append(Label(f"Lessons: {status.stats.lessons_completed}", classes="sidebar-text"))
                widgets.append(Label(f"Reviews: {status.stats.reviews_completed}", classes="sidebar-text"))
                widgets.append(Label(f"Practice: {status.stats.practice_sessions}", classes="sidebar-text"))
                widgets.append(Label(f"Active days: {status.stats.active_learning_days}", classes="sidebar-text"))
                widgets.append(Label(f"Current streak: {status.stats.current_streak_days} days", classes="sidebar-text"))
                widgets.append(Static("", classes="spacer"))
            else:
                widgets.append(Label("Learning Stats", classes="sidebar-title"))
                widgets.append(Label("No stats data", classes="sidebar-text"))
                widgets.append(Static("", classes="spacer"))
            
            if status.gamification:
                widgets.append(Label("Momentum", classes="sidebar-title"))
                widgets.append(Label(f"XP: {status.gamification.xp}", classes="sidebar-text"))
                widgets.append(Label(f"Level: {status.gamification.level}", classes="sidebar-text"))
                widgets.append(Label(f"Weekly goal: {status.gamification.weekly_goal_progress}/{status.gamification.weekly_goal_target}", classes="sidebar-text"))
                earned = [b for b in status.gamification.badges if getattr(b, "earned", False)]
                widgets.append(Label(f"Earned badges: {len(earned)}", classes="sidebar-text"))
                widgets.append(Static("", classes="spacer"))
            else:
                widgets.append(Label("Momentum", classes="sidebar-title"))
                widgets.append(Label("No momentum data", classes="sidebar-text"))
                widgets.append(Static("", classes="spacer"))
                
            if status.portfolio:
                widgets.append(Label("Portfolio", classes="sidebar-title"))
                widgets.append(Label(f"README: {'exists' if getattr(status.portfolio, 'readme_exists', False) else 'missing'}", classes="sidebar-text"))
                widgets.append(Label(f"Charts: {getattr(status.portfolio, 'charts_existing', 0)}/{getattr(status.portfolio, 'charts_total', 4)}", classes="sidebar-text"))
                widgets.append(Static("", classes="spacer"))
                
            widgets.append(Label("Next Step", classes="sidebar-title"))
            if status.next_steps:
                widgets.append(Label(status.next_steps[0], classes="sidebar-text"))
                
            if status.warnings:
                widgets.append(Static("", classes="spacer"))
                widgets.append(Label("Warnings", classes="sidebar-title", id="uninitialized-warning"))
                for w in status.warnings:
                    widgets.append(Label(f"- {w}", classes="sidebar-text"))
            
        else:
            widgets.append(Label("Workspace", classes="sidebar-title"))
            widgets.append(Label("Not Initialized", classes="sidebar-text", id="uninitialized-warning"))
            
        footer = Vertical(
            Label("/*", classes="sidebar-text"),
            Label(f"  ALO {__version__}", classes="sidebar-text")
        )
        widgets.append(footer)
        
        return widgets

    def _refresh_sidebar(self, sidebar, cwd):
        sidebar.remove_children()
        widgets = self._build_sidebar_widgets()
        sidebar.mount(*widgets)

    def run_roadmap_flow(self, args, log, cwd):
        parsed = self._parse_args('roadmap', args, log)
        if not parsed:
            return
        if not self._check_llm_readiness("roadmap generation", log, parsed.mock):
            return
            
        if not parsed.mock:
            self.enter_working_state("Generating roadmap... Please wait.")
        self.run_roadmap_worker(cwd, mock=parsed.mock, force=parsed.force, dry_run=parsed.dry_run, log=log)

    @work(thread=True)
    def run_roadmap_worker(self, cwd, mock, force, dry_run, log):
        try:
            from alo.services.roadmap_service import generate_roadmap_service
            res = generate_roadmap_service(cwd, mock=mock, force=force, dry_run=dry_run)
            self.app.call_from_thread(self._on_roadmap_generated, res, dry_run, log)

        except Exception as e:
            from alo.services.results import ServiceResult
            res = ServiceResult(success=False, error_code='worker_error', error=f'Unexpected error: {e}')
            self.app.call_from_thread(self._on_roadmap_generated, res, dry_run, log)
    def _on_roadmap_generated(self, res, dry_run, log):
        if self.handle_worker_error(res, "roadmap generation", log):
            return
        if res.warning:
            log.write(f"[yellow]{res.warning}[/yellow]")
            
        if dry_run:
            log.write(f"\n[yellow]Successfully generated {len(res.items)} roadmap items (dry run).[/yellow]")
        else:
            log.write(f"\n[green]Successfully generated {len(res.items)} roadmap items![/green]")
            from alo.state_manager import trigger_auto_sync
            from pathlib import Path
            if trigger_auto_sync(Path.cwd(), "roadmap generation"):
                log.write("[dim]Safe local sync committed.[/dim]")
            
        table = Table(title=f"Roadmap Summary ({res.active_path_id})")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="magenta")
        table.add_column("Level", style="green")
        table.add_column("Status", style="yellow")
        for item in res.items:
            table.add_row(item.id, item.title, item.level, item.status)
        log.write(table)
        
        is_guided = self.state_data.get("is_guided_flow")
        if is_guided:
            self.app_state = "guided_start_learn"
            self.update_input_prompt("Start first learning session now?", "Guided Flow")
            self.show_choices("Start lesson?", ["yes", "no"])
        else:
            self.app_state = "idle"
            self.reset_input_prompt()

    def run_learn_flow(self, args, log, cwd):
        parsed = self._parse_args('learn', args, log)
        if not parsed:
            return
        if not self._check_llm_readiness("learning session generation", log, parsed.mock):
            return
            
        if not parsed.mock:
            self.enter_working_state("Generating learning session... Please wait.")
        self.run_learn_generate_worker(cwd, mock=parsed.mock, item_id=parsed.item, dry_run=parsed.dry_run, log=log)

    @work(thread=True)
    def run_learn_generate_worker(self, cwd, mock, item_id, dry_run, log):
        try:
            from alo.services.learn_service import generate_session
            res = generate_session(cwd, mock=mock, item_id=item_id)
            self.app.call_from_thread(self._on_learn_generated, res, mock, dry_run, log)

        except Exception as e:
            from alo.services.results import ServiceResult
            res = ServiceResult(success=False, error_code='worker_error', error=f'Unexpected error: {e}')
            self.app.call_from_thread(self._on_learn_generated, res, mock, dry_run, log)
    def _on_learn_generated(self, res, mock, dry_run, log):
        if self.handle_worker_error(res, "learning session generation", log):
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
        
        from alo.services.practice_session_service import parse_practice_items
        items = parse_practice_items(session.practice_question)
        
        self.state_data = {
            "session_ctx": session_ctx,
            "mock": mock,
            "dry_run": dry_run,
            "items": items,
            "current_index": 0,
            "item_results": []
        }
        
        if len(items) > 1:
            log.write(f"\n[bold magenta]Multi-part Practice ({len(items)} items)[/bold magenta]")
            # Assuming prompt starts with preamble, we can extract the part that's not display_prompt
            preamble = items[0].prompt.replace("\n\n" + items[0].display_prompt, "")
            if preamble != items[0].prompt:
                log.write(Panel(preamble, title="Practice Instructions", style="blue"))
            
        self._show_next_practice_item(log)

    def _show_next_practice_item(self, log):
        idx = self.state_data.get("current_index", 0)
        items = self.state_data.get("items", [])
        if idx >= len(items):
            self.app_state = "idle"
            self.reset_input_prompt()
            if len(items) > 1:
                from alo.services.practice_session_service import summarize_practice_results
                summary = summarize_practice_results(self.state_data.get("item_results", []))
                
                summary_text = (
                    f"Items: {summary.total_items}\n"
                    f"Passed: {summary.passed}\n"
                    f"Partial: {summary.partial}\n"
                    f"Failed: {summary.failed}\n"
                    f"Average Score: {summary.average_score}"
                )
                log.write(Panel(summary_text, title="Practice Complete", style="blue"))
                
                if not self.state_data.get("dry_run"):
                    from alo.state_manager import trigger_auto_sync
                    cwd = Path.cwd()
                    if trigger_auto_sync(cwd, "learning session"):
                        log.write("[dim]Safe local sync committed.[/dim]")
            return
            
        item = items[idx]
        if len(items) > 1:
            log.write(f"\n[bold green]Practice Question {idx+1} / {len(items)}[/bold green]")
        log.write(Panel(item.display_prompt, title="Practice Question" if len(items) == 1 else None, style="green"))
        log.write("\n[yellow]Type your answer and press Enter.[/yellow]")
        
        self.app_state = "learn_answering"
        self.update_input_prompt("Type your answer. (Ctrl+Enter to submit, Esc to cancel)", "Answering lesson question", placeholder="Your answer...", multi_line=True)

    @work(thread=True)
    def run_learn_evaluate_worker(self, cwd, session_ctx, answer, mock, dry_run, log):
        try:
            from alo.services.learn_service import evaluate_answer
            if not mock:
                self.app.call_from_thread(log.write, "[cyan]Evaluating answer...[/cyan]")
            res = evaluate_answer(cwd, session_ctx, answer, mock=mock, dry_run=dry_run)
            self.app.call_from_thread(self._on_learn_evaluated, res, dry_run, log)

        except Exception as e:
            from alo.services.results import ServiceResult
            res = ServiceResult(success=False, error_code='worker_error', error=f'Unexpected error: {e}')
            self.app.call_from_thread(self._on_learn_evaluated, res, dry_run, log)
    def _on_learn_evaluated(self, res, dry_run, log):
        if self.handle_worker_error(res, "learn evaluation", log):
            return
            
        if "original_practice_question" in self.state_data:
            self.state_data["session_ctx"].session.practice_question = self.state_data["original_practice_question"]
            
        evaluation = res.evaluation
        from alo.services.practice_session_service import PracticeItemResult
        
        idx = self.state_data.get("current_index", 0)
        self.state_data.setdefault("item_results", []).append(
            PracticeItemResult(index=idx+1, result=evaluation.result, score=evaluation.score)
        )
        
        if evaluation.result == "pass":
            eval_color = "green"
        else:
            eval_color = "yellow" if evaluation.result == "partial" else "red"
            
        log.write(Panel(f"Result: {evaluation.result.upper()} (Score: {evaluation.score})", style=eval_color))
        log.write(Markdown(evaluation.feedback))
        
        items = self.state_data.get("items", [])
        if len(items) <= 1 or self.state_data.get("current_index", 0) == len(items) - 1:
            log.write(f"\n[bold green]Strengths:[/bold green] {evaluation.strengths}")
            log.write(f"[bold red]Weaknesses:[/bold red] {evaluation.weaknesses}")
            log.write(f"[bold cyan]Next Step:[/bold cyan] {evaluation.recommended_next_step}")
            
        if "current_index" in self.state_data:
            self.state_data["current_index"] += 1
            self.exit_working_state()
            self._show_next_practice_item(log)
        else:
            self.app_state = "idle"
            self.reset_input_prompt()

    def run_assess_flow(self, args, log, cwd):
        parsed = self._parse_args('assess', args, log)
        if not parsed:
            return
        if not self._check_llm_readiness("assessment generation", log, parsed.mock):
            return
            
        self.enter_working_state("Generating assessment... Please wait.")
        self.run_assess_generate_worker(cwd, mock=parsed.mock, dry_run=parsed.dry_run, log=log)

    @work(thread=True)
    def run_assess_generate_worker(self, cwd, mock, dry_run, log):
        try:
            from alo.services.assess_service import generate_assessment_service
            res = generate_assessment_service(cwd, mock=mock)
            self.app.call_from_thread(self._on_assess_generated, res, mock, dry_run, log)

        except Exception as e:
            from alo.services.results import ServiceResult
            res = ServiceResult(success=False, error_code='worker_error', error=f'Unexpected error: {e}')
            self.app.call_from_thread(self._on_assess_generated, res, mock, dry_run, log)
    def _on_assess_generated(self, res, mock, dry_run, log):
        if self.handle_worker_error(res, "assessment generation", log):
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
        self.update_input_prompt("Type A/B/C/D or 1/2/3/4", "Answering assessment", placeholder="Your answer...")
        self._render_assess_question(log)

    def _render_assess_question(self, log):
        data = self.state_data
        q_idx = data["current_q"]
        q = data["questions"][q_idx]
        log.write(f"\n[bold cyan]Question {data['current_q'] + 1} of {len(data['questions'])}:[/bold cyan]")
        log.write(Markdown(q.question))
        for i, choice in enumerate(q.choices):
            log.write(f"  {chr(65+i)}. {choice}")
            
        self.show_choices("Select an answer:", q.choices)

    def run_review_flow(self, args, log, cwd):
        parsed = self._parse_args('review', args, log)
        if not parsed:
            return
        if not self._check_llm_readiness("review generation", log, parsed.mock):
            return
            
        if not parsed.mock:
            self.enter_working_state("Generating review session... Please wait.")
        self.run_review_generate_worker(cwd, mock=parsed.mock, dry_run=parsed.dry_run, weakness_id=parsed.weakness, item_id=parsed.item, log=log)

    @work(thread=True)
    def run_review_generate_worker(self, cwd, mock, dry_run, weakness_id, item_id, log):
        try:
            from alo.services.review_service import generate_review_service
            res = generate_review_service(cwd, mock=mock, weakness_id=weakness_id, item_id=item_id)
            self.app.call_from_thread(self._on_review_generated, res, mock, dry_run, log)

        except Exception as e:
            from alo.services.results import ServiceResult
            res = ServiceResult(success=False, error_code='worker_error', error=f'Unexpected error: {e}')
            self.app.call_from_thread(self._on_review_generated, res, mock, dry_run, log)
    def _on_review_generated(self, res, mock, dry_run, log):
        if self.handle_worker_error(res, "review generation", log):
            return
        if res.warning:
            log.write(f"[yellow]{res.warning}[/yellow]")
            
        session_ctx = res.context
        session = session_ctx.session
        
        log.write(Panel(f"Review Session: {session.topic} ({session_ctx.target_id})", style="blue"))
        log.write(Markdown(session.short_review))
        log.write("\n[bold magenta]Why This Matters:[/bold magenta]")
        log.write(Markdown(session.why_this_matters))
        log.write("\n[bold red]Common Mistake:[/bold red]")
        log.write(Markdown(session.common_mistake))
        log.write(Panel(session.review_question, title="Review Question", style="green"))
        
        self.app_state = "review_answering"
        self.state_data = {"session_ctx": session_ctx, "mock": mock, "dry_run": dry_run}
        self.update_input_prompt("Type your answer. (Ctrl+Enter to submit, Esc to cancel)", "Reviewing weakness", placeholder="Your answer...", multi_line=True)

    @work(thread=True)
    def run_review_evaluate_worker(self, cwd, session_ctx, answer, mock, dry_run, log):
        try:
            from alo.services.review_service import evaluate_review_service
            if not mock:
                self.app.call_from_thread(log.write, "[cyan]Evaluating answer...[/cyan]")
            res = evaluate_review_service(cwd, session_ctx, answer, mock=mock, dry_run=dry_run)
            self.app.call_from_thread(self._on_review_evaluated, res, dry_run, log)

        except Exception as e:
            from alo.services.results import ServiceResult
            res = ServiceResult(success=False, error_code='worker_error', error=f'Unexpected error: {e}')
            self.app.call_from_thread(self._on_review_evaluated, res, dry_run, log)
    def _on_review_evaluated(self, res, dry_run, log):
        if self.handle_worker_error(res, "review evaluation", log):
            return
        self.app_state = "idle"
        self.reset_input_prompt()
        
        evaluation = res.evaluation
        eval_color = "green" if evaluation.result == "pass" else ("yellow" if evaluation.result == "partial" else "red")
        log.write(Panel(f"Result: {evaluation.result.upper()} (Score: {evaluation.score})", style=eval_color))
        log.write(Markdown(evaluation.feedback))
        log.write(f"\n[bold green]Strengths:[/bold green] {evaluation.strengths}")
        log.write(f"[bold red]Remaining Gaps:[/bold red] {evaluation.remaining_gaps}")
        log.write(f"[bold cyan]Next Step:[/bold cyan] {evaluation.recommended_next_step}")
        
        if not dry_run:
            log.write("\n[green]State updated successfully.[/green]")
        else:
            log.write("\n[yellow]State not updated (dry run).[/yellow]")

    @work(thread=True)
    def run_assess_score_worker(self, cwd, questions, answers, mock, dry_run, log):
        try:
            from alo.services.assess_service import score_assessment_service
            res = score_assessment_service(cwd, questions, answers, mock=mock, dry_run=dry_run)
            self.app.call_from_thread(self._on_assess_scored, res, dry_run, log)

        except Exception as e:
            from alo.services.results import ServiceResult
            res = ServiceResult(success=False, error_code='worker_error', error=f'Unexpected error: {e}')
            self.app.call_from_thread(self._on_assess_scored, res, dry_run, log)
    def _on_assess_scored(self, res, dry_run, log):
        if self.handle_worker_error(res, "assessment scoring", log):
            return
            
        is_guided = self.state_data.get("is_guided_flow")
        if not is_guided:
            self.app_state = "idle"
            self.reset_input_prompt()
            
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
            from alo.state_manager import trigger_auto_sync
            cwd = Path.cwd()
            if trigger_auto_sync(cwd, "assessment"):
                log.write("[dim]Safe local sync committed.[/dim]")
            
        if is_guided:
            self.app_state = "guided_start_paths"
            self.update_input_prompt("Generate learning paths now?", "Guided Flow")
            self.show_choices("Generate learning paths?", ["yes", "no"])

    def run_sync_flow(self, args: list, log, cwd: Path):
        self.enter_working_state("Syncing Git state... Please wait.")
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--push", action="store_true", default=None)
        parser.add_argument("--no-push", action="store_false", dest="push")
        parser.add_argument("--message", "-m", default="ALO: sync learning state")
        parser.add_argument("--yes", "-y", action="store_true")
        
        try:
            parsed, _ = parser.parse_known_args(args)
        except SystemExit:
            log.write("[red]Invalid arguments for sync.[/red]")
            self.exit_working_state()
            self.app_state = "idle"
            self.reset_input_prompt()
            return
            
        self.run_sync_worker(cwd, parsed.dry_run, parsed.push, parsed.message, parsed.yes, log)

    @work(thread=True)
    def run_sync_worker(self, cwd, dry_run, push, message, yes, log):
        try:
            from alo.services.git_service import SyncOptions, run_sync_service, is_git_repo
            allow_init = yes
            
            if not is_git_repo(cwd) and not dry_run and not yes:
                self.app.call_from_thread(self._ask_sync_init, cwd, push, message, log)
                return
                
            options = SyncOptions(dry_run=dry_run, push=push, message=message, allow_init=allow_init)
            res = run_sync_service(cwd, options)
            self.app.call_from_thread(self._on_sync_completed, res, log)
        except Exception as e:
            from alo.services.results import ServiceResult
            res = ServiceResult(success=False, error_code='worker_error', error=f'Unexpected error: {e}')
            self.app.call_from_thread(self._on_sync_completed, res, log)

    def _ask_sync_init(self, cwd, push, message, log):
        self.exit_working_state()
        self.app_state = "sync_init_choice"
        self.state_data = {"cwd": cwd, "push": push, "message": message}
        self.update_input_prompt("Git is not initialized. Initialize now?", "Sync - Init")
        self.show_choices("Initialize Git?", ["yes", "no"])

    def _on_sync_completed(self, res, log):
        if getattr(res, "error_code", None) == "worker_error":
            # Using handle_worker_error directly for generic ServiceResult
            if self.handle_worker_error(res, "sync", log):
                return
            
        self.exit_working_state()
        self.app_state = "idle"
        self.reset_input_prompt()
        
        if getattr(res, "no_changes", False):
            log.write("[yellow]No safe learning-state changes to sync.[/yellow]")
            return
            
        log.write("\n[bold cyan]Git Sync Summary[/bold cyan]")
        if getattr(res, "repo_initialized", False):
            log.write("  [green]Initialized new Git repository.[/green]")
        if getattr(res, "staged_files", []):
            log.write("  [green]Safe changes:[/green]")
            for f in res.staged_files:
                log.write(f"    - {f}")
        if getattr(res, "ignored_files", []):
            log.write("  [yellow]Ignored files:[/yellow]")
            for f in res.ignored_files:
                log.write(f"    - {f}")
                
        if getattr(res, "is_dry_run", False):
            log.write("\n[yellow]Dry run completed. No files were committed.[/yellow]")
            return
            
        if not getattr(res, "success", False):
            log.write(f"[red]{getattr(res, 'error', 'Sync failed.')}[/red]")
            return
            
        if getattr(res, "commit_hash", None):
            log.write(f"\n[green]Committed safely ({res.commit_hash}).[/green]")
            
        if getattr(res, "pushed", False):
            log.write("[green]Pushed to remote.[/green]")


    def run_status_cmd(self, args, log, cwd):
        from alo.services.status_service import compute_workspace_status
        from rich.text import Text
        
        status_obj = compute_workspace_status(cwd)
        
        if status_obj.is_source_repo:
            log.write("[red]Cannot run status inside ALO source repository.[/red]")
            return
            
        if not status_obj.is_workspace:
            log.write("[red]Not an ALO workspace. Run `alo init` first.[/red]")
            return
            
        # Instead of reinventing the rich panel logic, we just run the CLI logic
        from alo.cli import app
        from typer.testing import CliRunner
        runner = CliRunner()
        res = runner.invoke(app, ["status"])
        log.write(Text.from_ansi(res.stdout))

    def run_readme_cmd(self, args, log, cwd):
        parsed = self._parse_args('readme', args, log)
        if not parsed:
            return
            
        from alo.cli import app
        from typer.testing import CliRunner
        from rich.text import Text
        runner = CliRunner()
        cmd_args = ["readme"]
        if parsed.include_charts:
            cmd_args.append("--include-charts")
        if parsed.include_gamification:
            cmd_args.append("--include-gamification")
        if parsed.force:
            cmd_args.append("--force")
        if parsed.yes:
            cmd_args.append("--yes")
        if parsed.dry_run:
            cmd_args.append("--dry-run")
        
        res = runner.invoke(app, cmd_args)
        log.write(Text.from_ansi(res.stdout))
        self._refresh_sidebar(self.query_one("#sidebar"), cwd)

    def run_charts_cmd(self, args, log, cwd):
        parsed = self._parse_args('charts', args, log)
        if not parsed:
            return
            
        from alo.cli import app
        from typer.testing import CliRunner
        from rich.text import Text
        runner = CliRunner()
        cmd_args = ["charts"]
        if parsed.force:
            cmd_args.append("--force")
        if parsed.yes:
            cmd_args.append("--yes")
        if parsed.dry_run:
            cmd_args.append("--dry-run")
        
        res = runner.invoke(app, cmd_args)
        log.write(Text.from_ansi(res.stdout))
        self._refresh_sidebar(self.query_one("#sidebar"), cwd)

    def run_badges_cmd(self, args, log, cwd):
        from alo.cli import app
        from typer.testing import CliRunner
        from rich.text import Text
        runner = CliRunner()
        res = runner.invoke(app, ["badges"])
        log.write(Text.from_ansi(res.stdout))


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
        
        if alo_config.config_exists():
            cfg = alo_config.load_config()
            cfg_status = f"{cfg.llm_provider} | Mode: {cfg.api_key_storage}"
        else:
            cfg_status = "Missing"
        
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
