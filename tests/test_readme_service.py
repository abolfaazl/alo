from typer.testing import CliRunner
from alo.cli import app
from alo.services.readme_service import generate_workspace_readme, write_workspace_readme

runner = CliRunner()

def test_source_repo_guard(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "alo"\n')
    (tmp_path / "alo").mkdir()
    (tmp_path / "tests").mkdir()
    
    result = write_workspace_readme(tmp_path)
    assert result.written is False
    assert "Cannot generate README in the ALO source repository" in result.message

def test_non_workspace_guard(tmp_path):
    result = write_workspace_readme(tmp_path)
    assert result.written is False
    assert "Not an ALO workspace" in result.message

def test_empty_workspace(tmp_path):
    (tmp_path / "learning-profile.md").write_text("Subject: Core Java")
    
    result = write_workspace_readme(tmp_path)
    assert result.written is True
    
    content = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "Learning Workspace: Core Java" in content
    assert "Lessons completed | 0" in content
    assert "Generated locally from Markdown files" in content

def test_generate_readme_with_stats(tmp_path):
    (tmp_path / "learning-profile.md").write_text("Subject: Advanced Rust")
    (tmp_path / "progress-log.md").write_text("""# Progress Log
## 2026-06-30
### Session: Learn traits
Outcome: pass
What was learned: ...
""")
    (tmp_path / "roadmap.md").write_text("- [x] Learn Traits\n- [ ] Learn lifetimes")
    (tmp_path / "weaknesses.md").write_text("### ALO-WK-1: Borrow Checker\nTopic: borrow check\nStatus: open")
    
    content = generate_workspace_readme(tmp_path)
    assert "Advanced Rust" in content
    assert "Lessons completed | 1" in content
    assert "1 of 2 items completed (50.0%)" in content
    assert "borrow check" in content
    assert "Open weaknesses | 1" in content

def test_readme_exists_aborts_without_force(tmp_path):
    (tmp_path / "learning-profile.md").write_text("Subject: Math")
    (tmp_path / "README.md").write_text("My manual README")
    
    result = write_workspace_readme(tmp_path)
    assert result.written is False
    assert "already exists" in result.message
    
    assert (tmp_path / "README.md").read_text() == "My manual README"

def test_force_overwrites(tmp_path):
    (tmp_path / "learning-profile.md").write_text("Subject: Math")
    (tmp_path / "README.md").write_text("My manual README")
    
    result = write_workspace_readme(tmp_path, force=True)
    assert result.written is True
    
    content = (tmp_path / "README.md").read_text()
    assert "Learning Workspace: Math" in content

def test_secret_leakage_prevented(tmp_path):
    (tmp_path / "learning-profile.md").write_text("Subject: Math\nOPENAI_API_KEY=sk-abc123456\n")
    (tmp_path / "progress-log.md").write_text("### Session: Learn\nBearer token123\n")
    (tmp_path / "weaknesses.md").write_text("### ALO-WK-1\nTopic: api_key: 123456\nStatus: open")
    
    content = generate_workspace_readme(tmp_path)
    assert "sk-" not in content
    assert "OPENAI_API_KEY" not in content
    assert "Bearer" not in content
    assert "api_key" not in content
    assert "[REDACTED]" in content

def test_cli_dry_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "learning-profile.md").write_text("Subject: CLI Test")
    
    res = runner.invoke(app, ["readme", "--dry-run"])
    assert res.exit_code == 0
    assert "Learning Workspace: CLI Test" in res.stdout
    assert not (tmp_path / "README.md").exists()

def test_cli_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "learning-profile.md").write_text("Subject: CLI Run Test")
    
    res = runner.invoke(app, ["readme"])
    assert res.exit_code == 0
    assert "Successfully generated workspace README" in res.stdout
    
    assert (tmp_path / "README.md").exists()

def test_no_gamification_claims(tmp_path):
    (tmp_path / "learning-profile.md").write_text("Subject: No Claims")
    content = generate_workspace_readme(tmp_path)
    content_lower = content.lower()
    
    assert "badge" not in content_lower
    assert "gamification" not in content_lower
    assert "chart" not in content_lower
