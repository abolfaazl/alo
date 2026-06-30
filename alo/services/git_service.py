import subprocess
import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional

ALLOWED_SYNC_FILES = [
    "README.md",
    "learning-profile.md",
    "skill-map.md",
    "learning-paths.md",
    "roadmap.md",
    "weaknesses.md",
    "progress-log.md",
    "tutor-rules.md",
    "privacy-rules.md",
    ".gitignore",
    "assets/alo-progress.svg",
    "assets/alo-practice.svg",
    "assets/alo-streak.svg",
    "assets/alo-roadmap.svg"
]

SECRET_PATTERNS = [
    (re.compile(r"sk-[a-zA-Z0-9]{20,}"), "OpenAI API key pattern"),
    (re.compile(r"OPENAI_API_KEY\s*=\s*\S+"), "OpenAI API key environment variable"),
    (re.compile(r"ANTHROPIC_API_KEY\s*=\s*\S+"), "Anthropic API key environment variable"),
    (re.compile(r"api_key\s*:\s*\S+", re.IGNORECASE), "Generic API key YAML/JSON pattern"),
    (re.compile(r"api-key\s*:\s*\S+", re.IGNORECASE), "Generic API key YAML/JSON pattern"),
    (re.compile(r"authorization\s*:\s*bearer\s+\S+", re.IGNORECASE), "Authorization bearer token"),
    (re.compile(r"password\s*:\s*\S+", re.IGNORECASE), "Password pattern"),
    (re.compile(r"token\s*:\s*\S+", re.IGNORECASE), "Token pattern"),
]

@dataclass
class SyncOptions:
    dry_run: bool = False
    push: Optional[bool] = None  # None = use auto_push config
    message: str = "ALO: sync learning state"
    allow_init: bool = False

@dataclass
class SyncResult:
    success: bool
    error: Optional[str] = None
    staged_files: List[str] = None
    ignored_files: List[str] = None
    secrets_found: List[Tuple[str, str]] = None
    commit_hash: Optional[str] = None
    pushed: bool = False
    is_dry_run: bool = False
    repo_initialized: bool = False
    no_changes: bool = False

    def __post_init__(self):
        if self.staged_files is None:
            self.staged_files = []
        if self.ignored_files is None:
            self.ignored_files = []
        if self.secrets_found is None:
            self.secrets_found = []

def run_cmd(args: List[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, check=check)
    except FileNotFoundError:
        # Git is not installed or not in PATH
        raise Exception("Git command not found. Please install Git.")

def is_git_repo(path: Path) -> bool:
    try:
        res = run_cmd(["git", "rev-parse", "--is-inside-work-tree"], cwd=path, check=False)
        return res.returncode == 0
    except Exception:
        return False

def is_alo_source_repo(path: Path) -> bool:
    """Refuse if the directory looks like the ALO source repository."""
    # Check for pyproject.toml, alo directory, tests directory
    if (path / "pyproject.toml").is_file() and (path / "alo").is_dir() and (path / "tests").is_dir():
        # Check if pyproject.toml contains ALO metadata
        try:
            content = (path / "pyproject.toml").read_text(encoding="utf-8", errors="ignore")
            if 'name = "alo"' in content or "alo.cli:app" in content:
                return True
        except Exception:
            pass
    return False

def init_git_repo(path: Path) -> bool:
    res = run_cmd(["git", "init"], cwd=path, check=False)
    return res.returncode == 0

def get_pre_staged_unsafe_files(path: Path) -> List[str]:
    """Check if any file not in ALLOWED_SYNC_FILES is currently staged."""
    res = run_cmd(["git", "diff", "--cached", "--name-only"], cwd=path, check=False)
    if res.returncode != 0:
        return []
    
    staged_files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
    unsafe = [f for f in staged_files if f not in ALLOWED_SYNC_FILES]
    return unsafe

def get_changed_files(path: Path) -> Tuple[List[str], List[str]]:
    """Returns (allowed_changed_files, ignored_changed_files)."""
    res = run_cmd(["git", "status", "--porcelain", "-uall"], cwd=path, check=False)
    if res.returncode != 0:
        return [], []
    
    allowed = []
    ignored = []
    
    for line in res.stdout.splitlines():
        if len(line) < 4:
            continue
        # Format is "XY filename"
        filename = line[3:].strip()
        # Handle renames (e.g., R  file1 -> file2), we just grab the final filename
        if "->" in filename:
            filename = filename.split("->")[-1].strip()
            
        # Strip quotes if any
        if filename.startswith('"') and filename.endswith('"'):
            filename = filename[1:-1]
            
        if filename in ALLOWED_SYNC_FILES:
            allowed.append(filename)
        else:
            ignored.append(filename)
            
    # Deduplicate in case git status returns same file multiple times
    return list(set(allowed)), list(set(ignored))

def scan_for_secrets(path: Path, files: List[str]) -> List[Tuple[str, str]]:
    """Returns a list of (filename, reason)."""
    found = []
    for f in files:
        file_path = path / f
        if not file_path.is_file():
            continue
            
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            for pattern, reason in SECRET_PATTERNS:
                if pattern.search(content):
                    found.append((f, reason))
                    break # One secret reason per file is enough
        except Exception:
            pass
            
    return found

def stage_allowed_files(path: Path, files: List[str]) -> bool:
    if not files:
        return True
    
    # We must explicitly add them by name, NEVER use `.` or `-A`
    args = ["git", "add", "--"] + files
    res = run_cmd(args, cwd=path, check=False)
    return res.returncode == 0

def commit_changes(path: Path, message: str) -> Optional[str]:
    res = run_cmd(["git", "commit", "-m", message], cwd=path, check=False)
    if res.returncode != 0:
        return None
        
    # Get commit hash
    res = run_cmd(["git", "rev-parse", "--short", "HEAD"], cwd=path, check=False)
    if res.returncode == 0:
        return res.stdout.strip()
    return None

def has_remote(path: Path, name: str = "origin") -> bool:
    res = run_cmd(["git", "remote", "get-url", name], cwd=path, check=False)
    return res.returncode == 0

def push_current_branch(path: Path) -> bool:
    # Get current branch
    res = run_cmd(["git", "branch", "--show-current"], cwd=path, check=False)
    if res.returncode != 0:
        return False
    branch = res.stdout.strip()
    if not branch:
        return False
        
    # Push to origin
    res = run_cmd(["git", "push", "origin", branch], cwd=path, check=False)
    return res.returncode == 0


def run_sync_service(cwd: Path, options: SyncOptions) -> SyncResult:
    result = SyncResult(success=False, is_dry_run=options.dry_run)
    
    try:
        # 1. Source repo protection
        if is_alo_source_repo(cwd):
            result.error = "This looks like the ALO source repository.\nGit sync is only for learning workspaces."
            return result
            
        # 2. Check Git repo existence
        if not is_git_repo(cwd):
            if options.dry_run:
                result.repo_initialized = True # Simulate initialization
            elif options.allow_init:
                if not init_git_repo(cwd):
                    result.error = "Failed to initialize Git repository."
                    return result
                result.repo_initialized = True
            else:
                result.error = "Git is not initialized. Please initialize it first."
                return result
                
        # 3. Check for pre-staged unsafe files
        unsafe_staged = get_pre_staged_unsafe_files(cwd)
        if unsafe_staged:
            result.error = f"Unsafe staged files detected: {', '.join(unsafe_staged)}\nSync aborted. Unstage them or commit them manually outside ALO."
            return result
            
        # 4. Get changes
        allowed_changes, ignored_changes = get_changed_files(cwd)
        result.ignored_files = ignored_changes
        result.staged_files = allowed_changes
        
        if not allowed_changes:
            result.no_changes = True
            result.success = True
            return result
            
        # 5. Scan for secrets
        secrets = scan_for_secrets(cwd, allowed_changes)
        result.secrets_found = secrets
        if secrets:
            reason_str = ", ".join([f"{f} ({r})" for f, r in secrets])
            result.error = f"Potential secret detected. Sync aborted.\n{reason_str}"
            return result
            
        if options.dry_run:
            result.success = True
            return result
            
        # 6. Stage files
        if not stage_allowed_files(cwd, allowed_changes):
            result.error = "Failed to stage safe learning files."
            return result
            
        # 7. Commit
        commit_hash = commit_changes(cwd, options.message)
        if not commit_hash:
            result.error = "Failed to create commit."
            return result
            
        result.commit_hash = commit_hash
        
        # 8. Push
        from alo.config import load_config
        config = load_config()
        auto_push = getattr(config, "auto_push", False)
        
        should_push = False
        if options.push is True:
            should_push = True
        elif options.push is None and auto_push:
            should_push = True
            
        if should_push:
            if not has_remote(cwd):
                result.success = False
                result.error = "No Git remote configured.\nAdd a remote first or configure it in settings."
                return result
            else:
                if push_current_branch(cwd):
                    result.pushed = True
                else:
                    result.success = False
                    result.error = "Commit successful, but failed to push to remote."
                    return result
        
        result.success = True
        return result
        
    except Exception as e:
        result.error = f"Unexpected Git service error: {str(e)}"
        return result
