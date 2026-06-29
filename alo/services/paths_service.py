from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from alo.exceptions import MissingAPIKeyError, KeyringUnavailableError
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
    error_code: str = None
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
        cfg = alo_config.load_config()
        readiness = alo_config.validate_config_readiness(cfg)
        if not readiness.llm_ready:
            missing = ", ".join([i.label for i in readiness.missing_required])
            return PathsServiceResult(success=False, error_code="missing_config", error=f"ALO needs LLM configuration. Missing: {missing}")

    if mock:
        llm_response = generate_mock_paths(subject)
        warning = "Mock path recommendation mode is for development/testing only."
    else:
        try:
            llm_response = generate_paths(context)
            if not llm_response:
                return PathsServiceResult(success=False, error="Failed to generate paths.")
        except MissingAPIKeyError as e:
            return PathsServiceResult(success=False, error_code="missing_api_key", error=str(e))
        except KeyringUnavailableError as e:
            return PathsServiceResult(success=False, error_code="keyring_unavailable", error=str(e))
        except Exception as e:
            return PathsServiceResult(success=False, error_code="llm_error", error=f"LLM or processing error: {e}")
            
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
