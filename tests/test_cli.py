from typer.testing import CliRunner
from alo.cli import app

runner = CliRunner()

def test_app_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ALO - Agentic Learning OS" in result.stdout

def test_app_doctor():
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "ALO Doctor" in result.stdout
    assert "Python Version" in result.stdout

def test_placeholder_commands():
    for cmd in ["assess", "paths", "roadmap", "learn", "review", "sync"]:
        result = runner.invoke(app, [cmd])
        assert result.exit_code == 0
        assert "implemented" in result.stdout.lower()

def test_init_no_onboarding(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "--no-onboarding"])
    assert result.exit_code == 0
    assert "Onboarding skipped" in result.stdout
    assert (tmp_path / "learning-profile.md").exists()

def test_interactive_onboarding(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    
    inputs = "Python, Pytest\n2\n1\nTDD\n3\n30m\n3\nn\n"
    
    result = runner.invoke(app, ["init"], input=inputs)
    assert result.exit_code == 0
    assert "Onboarding complete" in result.stdout
    
    lp = (tmp_path / "learning-profile.md").read_text(encoding="utf-8")
    assert "Junior" in lp
    assert "Python, Pytest" in lp
    assert "TDD" in lp
    assert "Deep explanations" in lp
    assert "generalized" in lp
    
    sm = (tmp_path / "skill-map.md").read_text(encoding="utf-8")
    assert "Python" in sm
    
    log = (tmp_path / "progress-log.md").read_text(encoding="utf-8")
    assert "Initial Onboarding" in log
    
    result2 = runner.invoke(app, ["init"], input="n\n")
    assert result2.exit_code == 0
    assert "Existing learning profile detected" in result2.stdout
    assert "Onboarding aborted" in result2.stdout
    
    result3 = runner.invoke(app, ["init", "--force"], input=inputs)
    assert result3.exit_code == 0
    assert "Onboarding complete" in result3.stdout
