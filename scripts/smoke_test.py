import sys
import subprocess
import tempfile
from pathlib import Path
import os

def run_command(cmd, cwd=None, env=None):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        sys.exit(1)
    return result.stdout

def main():
    repo_root = Path(__file__).parent.parent.absolute()
    python = sys.executable

    print("=== Phase 10 Smoke Test ===")
    
    # 1. compileall
    run_command([python, "-m", "compileall", "alo"], cwd=repo_root)
    
    # 2. pytest
    run_command([python, "-m", "pytest"], cwd=repo_root)
    
    # 3. ruff
    run_command([python, "-m", "ruff", "check", "."], cwd=repo_root)
    
    # Create temp workspace
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temp workspace: {temp_dir}")
        env = os.environ.copy()
        # Ensure we don't pick up global config during tests
        env["ALO_HOME"] = temp_dir
        # Ensure we can import alo even if not globally installed
        env["PYTHONPATH"] = str(repo_root)
        
        # 4. help
        run_command([python, "-m", "alo.cli", "--help"], cwd=temp_dir, env=env)
        
        # 5. version
        out = run_command([python, "-m", "alo.cli", "version"], cwd=temp_dir, env=env)
        assert "Version: 1.0.1" in out, "Version output mismatch"
        
        out = run_command([python, "-m", "alo.cli", "--version"], cwd=temp_dir, env=env)
        assert "Version: 1.0.1" in out, "--version output mismatch"
        
        # 6. doctor
        out = run_command([python, "-m", "alo.cli", "doctor"], cwd=temp_dir, env=env)
        assert "Checking environment health" in out, "Doctor output missing health check"
        
        # 7. home --no-interactive
        run_command([python, "-m", "alo.cli", "home", "--no-interactive"], cwd=temp_dir, env=env)
        
        print("=== All smoke tests passed! ===")

if __name__ == "__main__":
    main()
