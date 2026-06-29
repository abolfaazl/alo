import pytest
import subprocess
from alo.services.git_service import (
    SyncOptions, run_sync_service, is_git_repo, is_alo_source_repo
)

@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), check=True)
    return tmp_path

def test_git_repo_detection(repo):
    assert is_git_repo(repo) is True
    
def test_not_git_repo(tmp_path):
    assert is_git_repo(tmp_path) is False

def test_is_alo_source_repo(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "alo"')
    (tmp_path / "alo").mkdir()
    (tmp_path / "tests").mkdir()
    assert is_alo_source_repo(tmp_path) is True
    
    # Missing tests directory
    (tmp_path / "tests").rmdir()
    assert is_alo_source_repo(tmp_path) is False

def test_sync_commits_only_allowed_files(repo):
    # Create an allowed file and an unallowed file
    (repo / "learning-profile.md").write_text("Profile data")
    (repo / "secret-file.txt").write_text("Secret data")
    
    options = SyncOptions(message="Test commit", allow_init=False, dry_run=False, push=False)
    result = run_sync_service(repo, options)
    
    assert result.success is True
    assert "learning-profile.md" in result.staged_files
    assert "secret-file.txt" in result.ignored_files
    assert result.commit_hash is not None
    
    # Verify via git that only the allowed file is tracked
    res = subprocess.run(["git", "ls-tree", "-r", "HEAD", "--name-only"], cwd=str(repo), capture_output=True, text=True)
    tracked_files = res.stdout.strip().splitlines()
    assert "learning-profile.md" in tracked_files
    assert "secret-file.txt" not in tracked_files

def test_dry_run_does_not_commit(repo):
    (repo / "roadmap.md").write_text("Roadmap")
    
    options = SyncOptions(dry_run=True)
    result = run_sync_service(repo, options)
    
    assert result.success is True
    assert result.is_dry_run is True
    assert "roadmap.md" in result.staged_files
    assert result.commit_hash is None
    
    # Check no commit made
    res = subprocess.run(["git", "log"], cwd=str(repo), capture_output=True)
    assert res.returncode != 0  # No commits yet

def test_pre_staged_unsafe_file_aborts_sync(repo):
    (repo / "unsafe.txt").write_text("Unsafe")
    subprocess.run(["git", "add", "unsafe.txt"], cwd=str(repo), check=True)
    
    (repo / "roadmap.md").write_text("Roadmap")
    
    options = SyncOptions()
    result = run_sync_service(repo, options)
    
    assert result.success is False
    assert "Unsafe staged files detected" in result.error
    assert "unsafe.txt" in result.error
    assert result.commit_hash is None

def test_pre_staged_allowed_file_secret_scanned(repo):
    # Stage a file with a secret
    (repo / "learning-profile.md").write_text("My OPENAI_API_KEY=sk-12345678901234567890")
    subprocess.run(["git", "add", "learning-profile.md"], cwd=str(repo), check=True)
    
    options = SyncOptions()
    result = run_sync_service(repo, options)
    
    assert result.success is False
    assert "Potential secret detected" in result.error
    assert "sk-12345678901234567890" not in result.error  # Value not printed
    assert "learning-profile.md" in result.error
    assert result.commit_hash is None

def test_sync_detects_secrets(repo):
    (repo / "learning-profile.md").write_text("My OPENAI_API_KEY=sk-12345678901234567890123456")
    
    options = SyncOptions()
    result = run_sync_service(repo, options)
    
    assert result.success is False
    assert "Potential secret detected" in result.error
    assert "sk-12345678901234567890" not in result.error
    assert "learning-profile.md" in result.error

def test_sync_avoids_empty_commits(repo):
    options = SyncOptions()
    result = run_sync_service(repo, options)
    
    assert result.success is True
    assert result.no_changes is True
    assert result.commit_hash is None

def test_push_behavior_no_remote(repo):
    (repo / "roadmap.md").write_text("Roadmap")
    
    options = SyncOptions(push=True)
    result = run_sync_service(repo, options)
    
    # Should commit but fail to push due to no remote
    assert result.success is False
    assert "No Git remote configured" in result.error
    assert result.commit_hash is not None  # It did commit!

def test_git_not_initialized(tmp_path):
    (tmp_path / "roadmap.md").write_text("Roadmap")
    options = SyncOptions(allow_init=False)
    result = run_sync_service(tmp_path, options)
    assert result.success is False
    assert "Git is not initialized" in result.error

def test_git_init_allowed(tmp_path):
    # Need global or local git config to commit. We'll just let it fail on commit but repo_initialized should be True.
    # Actually wait, commit requires user.email if not set globally.
    # Just checking if repo is initialized is enough.
    (tmp_path / "roadmap.md").write_text("Roadmap")
    options = SyncOptions(allow_init=True)
    result = run_sync_service(tmp_path, options)
    # The commit might fail because no user/email config in the new temp repo, 
    # but the repo should be initialized.
    assert result.repo_initialized is True
    assert (tmp_path / ".git").exists()

def test_git_init_dry_run(tmp_path):
    (tmp_path / "roadmap.md").write_text("Roadmap")
    options = SyncOptions(dry_run=True)
    result = run_sync_service(tmp_path, options)
    assert result.success is True
    assert result.is_dry_run is True
    assert result.repo_initialized is True # Simulated
    assert not (tmp_path / ".git").exists() # Actually not created
