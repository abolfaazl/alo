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
