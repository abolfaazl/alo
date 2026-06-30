from pathlib import Path
from pydantic import BaseModel
from typing import List, Dict, Optional

from alo.models.stats import LearningStats
from alo.models.gamification import GamificationSummary
from alo.services.stats_service import compute_learning_stats
from alo.services.gamification_service import compute_gamification_from_stats
from alo.services.git_service import is_git_repo, has_remote, get_pre_staged_unsafe_files, is_alo_source_repo
from alo.services.readme_service import extract_subject

class PortfolioStatus(BaseModel):
    readme_exists: bool = False
    charts_total: int = 4
    charts_existing: int = 0
    chart_files: Dict[str, bool] = {}

class GitStatusSummary(BaseModel):
    is_git_repo: bool = False
    remote_configured: bool = False
    unsafe_staged_count: int = 0
    warnings: List[str] = []

class WorkspaceStatus(BaseModel):
    workspace_path: str
    subject: Optional[str] = None
    is_workspace: bool = False
    is_source_repo: bool = False
    stats: Optional[LearningStats] = None
    gamification: Optional[GamificationSummary] = None
    portfolio: PortfolioStatus = PortfolioStatus()
    git: GitStatusSummary = GitStatusSummary()
    next_steps: List[str] = []
    warnings: List[str] = []

def compute_workspace_status(workspace_path: Path) -> WorkspaceStatus:
    status = WorkspaceStatus(workspace_path=str(workspace_path))
    
    if is_alo_source_repo(workspace_path):
        status.is_source_repo = True
        status.warnings.append("This is the ALO development repository.")
        status.next_steps.append("Create a separate learning workspace using `alo init` in a new directory.")
        return status
        
    profile_path = workspace_path / "learning-profile.md"
    if not profile_path.exists():
        status.warnings.append("Not an ALO workspace. Missing learning-profile.md.")
        status.next_steps.append("Run `alo init` to create a new workspace.")
        return status
        
    status.is_workspace = True
    status.subject = extract_subject(workspace_path)
    
    # Core stats & Gamification
    stats = compute_learning_stats(workspace_path)
    status.stats = stats
    status.gamification = compute_gamification_from_stats(stats)
    
    # Portfolio
    port = PortfolioStatus()
    port.readme_exists = (workspace_path / "README.md").exists()
    
    chart_names = [
        "alo-progress.svg",
        "alo-practice.svg",
        "alo-streak.svg",
        "alo-roadmap.svg"
    ]
    
    for c in chart_names:
        exists = (workspace_path / "assets" / c).exists()
        port.chart_files[c] = exists
        if exists:
            port.charts_existing += 1
            
    status.portfolio = port
    
    # Git
    git_stat = GitStatusSummary()
    git_stat.is_git_repo = is_git_repo(workspace_path)
    if git_stat.is_git_repo:
        git_stat.remote_configured = has_remote(workspace_path)
        unsafe = get_pre_staged_unsafe_files(workspace_path)
        git_stat.unsafe_staged_count = len(unsafe)
    
    status.git = git_stat
    
    # Next steps logic
    if not port.readme_exists:
        status.next_steps.append("Run `alo readme --include-charts --include-gamification` to build your portfolio.")
    elif port.charts_existing < port.charts_total:
        status.next_steps.append("Run `alo charts` or `alo readme --include-charts --force` to generate missing charts.")
    elif stats.active_learning_days == 0:
        status.next_steps.append("Run `alo learn` or `alo review` to start learning.")
    else:
        status.next_steps.append("Run `alo sync --dry-run` to preview saving your progress.")
        
    return status
