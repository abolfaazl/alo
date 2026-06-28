import subprocess
from pathlib import Path

def is_alo_source_repo(path: Path) -> bool:
    return (path / "pyproject.toml").exists() and \
           (path / "alo").exists() and \
           (path / "PROJECT_INSTRUCTURE.MD").exists()

def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()

def ensure_git_repo(path: Path) -> None:
    if not is_git_repo(path):
        subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)

def set_git_remote(path: Path, remote_url: str) -> None:
    subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=path, check=True, capture_output=True)

def get_workspace_state(path: Path):
    from alo.state_manager import get_state_summary
    return get_state_summary(path)
