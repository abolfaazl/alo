import subprocess
import sys
import shutil
import os
from pathlib import Path

def test_alo_importable_outside_cwd(tmp_path):
    """
    Smoke test to ensure the 'alo' package can be imported 
    and run when the current working directory is not the source repo.
    """
    repo_root = str(Path(__file__).parent.parent.absolute())
    env = dict(os.environ)
    env["PYTHONPATH"] = repo_root

    # 1. Test importing alo programmatically
    result = subprocess.run(
        [sys.executable, "-c", "import alo; from alo.cli import app; print('ok')"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Failed to import alo outside source cwd:\n{result.stderr}"
    assert "ok" in result.stdout

    # 2. Test running the CLI via python -m
    result_cli = subprocess.run(
        [sys.executable, "-m", "alo.cli", "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result_cli.returncode == 0, f"Failed to run python -m alo.cli --help:\n{result_cli.stderr}"
    assert "Usage:" in result_cli.stdout

    # 3. Test running the console script (if installed in the current environment)
    # The 'alo' command might be alo.exe on windows. We can use shutil.which to find it.
    alo_bin = shutil.which("alo")
    if alo_bin:
        result_bin = subprocess.run(
            [alo_bin, "--help"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result_bin.returncode == 0, f"Failed to run alo --help:\n{result_bin.stderr}"
        assert "Usage:" in result_bin.stdout

def test_version_match():
    import alo
    from pathlib import Path
    import tomllib
    
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    pkg_version = data["project"]["version"]
    
    assert alo.__version__ == pkg_version, f"Version mismatch: __init__.py ({alo.__version__}) vs pyproject.toml ({pkg_version})"

def test_package_data_included():
    from importlib.resources import files
    css = files("alo.ui").joinpath("mimo.css")
    assert css.is_file(), "mimo.css was not bundled or resolved correctly at runtime."

def test_no_raw_api_keys_in_docs():
    from pathlib import Path
    import re
    
    repo_root = Path(__file__).parent.parent
    md_files = list(repo_root.glob("*.md")) + list(repo_root.glob("docs/*.md"))
    
    # Regexes that typically indicate accidentally hardcoded dummy keys
    bad_patterns = [
        re.compile(r"sk-[a-zA-Z0-9]{20,}"),
        re.compile(r"OPENAI_API_KEY\s*=\s*sk-", re.IGNORECASE),
        re.compile(r"Bearer\s+sk-", re.IGNORECASE),
        re.compile(r"api_key:\s*sk-", re.IGNORECASE)
    ]
    
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        for pattern in bad_patterns:
            matches = pattern.findall(content)
            assert not matches, f"Found raw API key format in {md_file}: {matches}"
