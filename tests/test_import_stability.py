import subprocess
from pathlib import Path

def test_compileall():
    """Verify that all Python files compile without SyntaxError or IndentationError."""
    result = subprocess.run(
        ["python", "-m", "compileall", "alo"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent)
    )
    assert result.returncode == 0, f"Compileall failed: {result.stderr}\n{result.stdout}"

def test_service_imports():
    """Verify that all service modules can be imported without crashing."""
