from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from datetime import datetime

from alo import state_manager, workspace
from alo.models import OnboardingProfile, ExperienceLevel, PrivacyPreference

@dataclass
class InitServiceResult:
    success: bool
    error_code: str = None
    error: Optional[str] = None
    next_step: Optional[str] = None

def detect_init_state(cwd: Path, allow_source_repo: bool = False) -> str:
    """
    Returns the current initialization state:
    - 'source_repo': Inside ALO source and not allowed.
    - 'initialized': Required state files exist (learning-profile or skill-map).
    - 'uninitialized': Ready to init.
    """
    if workspace.is_alo_source_repo(cwd) and not allow_source_repo:
        return "source_repo"
        
    lp_path = cwd / "learning-profile.md"
    sm_path = cwd / "skill-map.md"
    lp_exists = state_manager.has_user_content(lp_path, state_manager.REQUIRED_FILES["learning-profile.md"])
    sm_exists = state_manager.has_user_content(sm_path, state_manager.REQUIRED_FILES["skill-map.md"])
    
    if lp_exists or sm_exists:
        return "initialized"
        
    return "uninitialized"

def prepare_init_plan(cwd: Path) -> None:
    """Prepares the workspace for initialization."""
    state_manager.ensure_state_files(cwd)

def create_workspace_state(cwd: Path, profile_data: dict) -> None:
    """Creates/Updates the workspace state with the given profile data."""
    level = ExperienceLevel(profile_data["experience_level"])
    privacy = PrivacyPreference.store if profile_data["privacy_preference"] else PrivacyPreference.generalize
    
    profile = OnboardingProfile(
        subject=profile_data["subject"],
        background=profile_data["background"],
        experience_level=level,
        goal=profile_data["goal"],
        assess_now=profile_data["assess_now"],
        privacy_preference=privacy,
        date=datetime.now().strftime("%Y-%m-%d")
    )
    
    state_manager.save_onboarding_profile(cwd, profile, overwrite=True)
    state_manager.append_onboarding_progress(cwd, profile)

def initialize_git_if_requested(cwd: Path, do_git: bool, remote_url: Optional[str] = None) -> None:
    """Initializes Git and sets remote URL if requested."""
    if do_git:
        workspace.ensure_git_repo(cwd)
    if remote_url:
        workspace.set_git_remote(cwd, remote_url)
