from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from alo import markdown_store, config as alo_config
from alo.llm.client import generate_paths, generate_mock_paths
from alo.state_manager import (
    save_learning_path_recommendations,
    select_learning_path,
    append_paths_progress,
    update_active_learning_path
)

@dataclass
class PathsServiceResult:
    success: bool
    paths: list = None
    error: str = None
    warning: str = None

def get_paths(repo_path: Path, mock: bool = False) -> PathsServiceResult:
    """Generates learning paths based on the current profile."""
    if not (repo_path / "learning-profile.md").exists():
        return PathsServiceResult(success=False, error="Workspace not initialized. Run `alo init`.")
        
    lp = markdown_store.read_text_safely(repo_path / "learning-profile.md") or ""
    sm = markdown_store.read_text_safely(repo_path / "skill-map.md") or ""
    wk = markdown_store.read_text_safely(repo_path / "weaknesses.md") or ""
    
    import re
    subject_match = re.search(r"Subject: (.+)", lp)
    subject = subject_match.group(1).strip() if subject_match else "Subject"
    
    context = f"Profile:\n{lp}\n\nSkill Map:\n{sm}\n\nWeaknesses:\n{wk}"

    if not mock:
        if not alo_config.config_exists():
            return PathsServiceResult(success=False, error="ALO needs LLM configuration to generate personalized learning paths.\nRun: alo config")

    if mock:
        llm_response = generate_mock_paths(subject)
        warning = "Mock path recommendation mode is for development/testing only."
    else:
        try:
            llm_response = generate_paths(context)
            if not llm_response:
                return PathsServiceResult(success=False, error="Failed to generate paths.")
        except ValueError as e:
            err_msg = str(e)
            if "not set" in err_msg.lower() or "missing" in err_msg.lower():
                err_msg = "Configured API key environment variable is missing.\nSet the configured environment variable or update alo config."
            return PathsServiceResult(success=False, error=err_msg)
            
    if not llm_response or not hasattr(llm_response, "paths") or len(llm_response.paths) != 3:
        return PathsServiceResult(success=False, error="LLM failed to return exactly 3 learning paths.")

    return PathsServiceResult(success=True, paths=llm_response.paths, warning=warning if mock else None)

def select_path(repo_path: Path, paths: list, choice_index: Optional[int], dry_run: bool = False) -> str:
    """Selects a path and updates state files.
    choice_index is 0-based. If None, it means skipped.
    Returns a success message to display.
    """
    if choice_index is not None and 0 <= choice_index < len(paths):
        selected_path = paths[choice_index]
        if not dry_run:
            save_learning_path_recommendations(repo_path, paths)
            select_learning_path(repo_path, selected_path.id)
            update_active_learning_path(repo_path, selected_path)
            append_paths_progress(repo_path, selected_path.id)
        return f"Path '{selected_path.title}' selected!"
    else:
        if not dry_run:
            save_learning_path_recommendations(repo_path, paths)
            select_learning_path(repo_path, None)
            append_paths_progress(repo_path, None)
        return "Skipped path selection."
