from alo.services.status_service import compute_workspace_status
from typer.testing import CliRunner
from alo.cli import app
import json

runner = CliRunner()

def test_status_outside_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    res = runner.invoke(app, ["status"])
    assert res.exit_code == 1
    assert "Not an ALO workspace" in res.stdout

def test_status_inside_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "learning-profile.md").write_text("Subject: Status Test")
    
    res = runner.invoke(app, ["status"])
    assert res.exit_code == 0
    assert "Workspace" in res.stdout
    assert "Status Test" in res.stdout
    assert "Learning Stats" in res.stdout
    assert "Learning Momentum" in res.stdout
    assert "Portfolio" in res.stdout
    assert "Git Sync" in res.stdout
    assert "Next Step" in res.stdout

def test_status_json_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "learning-profile.md").write_text("Subject: JSON Test")
    
    res = runner.invoke(app, ["status", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["is_workspace"] is True
    assert data["subject"] == "JSON Test"
    assert data["portfolio"]["readme_exists"] is False
    assert data["portfolio"]["charts_existing"] == 0

def test_status_with_portfolio(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "learning-profile.md").write_text("Subject: Port Test")
    (tmp_path / "README.md").write_text("# Test")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "alo-progress.svg").write_text("<svg>")
    (tmp_path / "assets" / "alo-streak.svg").write_text("<svg>")
    (tmp_path / "assets" / "alo-practice.svg").write_text("<svg>")
    (tmp_path / "assets" / "alo-roadmap.svg").write_text("<svg>")
    
    res = runner.invoke(app, ["status"])
    assert res.exit_code == 0
    assert "README.md: exists" in res.stdout
    assert "Charts: 4 / 4 generated" in res.stdout
    assert "Safe generated files: ready" in res.stdout

def test_status_logic_missing_charts(tmp_path):
    (tmp_path / "learning-profile.md").write_text("Subject: Missing Charts")
    (tmp_path / "README.md").write_text("# Test")
    
    status = compute_workspace_status(tmp_path)
    assert "Run `alo charts`" in status.next_steps[0]

def test_status_logic_ready_to_sync(tmp_path):
    (tmp_path / "learning-profile.md").write_text("Subject: Sync")
    (tmp_path / "README.md").write_text("# Test")
    (tmp_path / "progress-log.md").write_text("## 2026-06-30\n\n### Session: Lesson\nTest")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "alo-progress.svg").write_text("<svg>")
    (tmp_path / "assets" / "alo-streak.svg").write_text("<svg>")
    (tmp_path / "assets" / "alo-practice.svg").write_text("<svg>")
    (tmp_path / "assets" / "alo-roadmap.svg").write_text("<svg>")
    
    status = compute_workspace_status(tmp_path)
    assert "Run `alo sync --dry-run`" in status.next_steps[0]
