from typer.testing import CliRunner
from alo.cli import app
from alo.services.chart_service import write_workspace_charts, generate_workspace_charts
from alo.services.git_service import get_changed_files

runner = CliRunner()

def test_source_repo_guard(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "alo"\n')
    (tmp_path / "alo").mkdir()
    (tmp_path / "tests").mkdir()
    
    result = write_workspace_charts(tmp_path)
    assert result.written is False
    assert "Cannot generate charts in the ALO source repository" in result.message

def test_non_workspace_guard(tmp_path):
    result = write_workspace_charts(tmp_path)
    assert result.written is False
    assert "Not an ALO workspace" in result.message

def test_write_creates_assets_dir(tmp_path):
    (tmp_path / "learning-profile.md").write_text("Subject: Charts")
    
    result = write_workspace_charts(tmp_path)
    assert result.written is True
    assert (tmp_path / "assets").exists()
    
    assert (tmp_path / "assets" / "alo-progress.svg").exists()
    assert (tmp_path / "assets" / "alo-practice.svg").exists()
    assert (tmp_path / "assets" / "alo-streak.svg").exists()
    assert (tmp_path / "assets" / "alo-roadmap.svg").exists()
    
def test_generate_svg_content(tmp_path):
    (tmp_path / "learning-profile.md").write_text("Subject: Math")
    (tmp_path / "roadmap.md").write_text("- [x] Learn math\n- [ ] Learn physics")
    
    charts = generate_workspace_charts(tmp_path)
    
    assert len(charts) == 4
    for content in charts.values():
        assert content.startswith("<svg")
        assert "</svg>" in content
        
    roadmap_svg = charts["alo-roadmap.svg"]
    assert "1 of 2 items completed" in roadmap_svg
    assert "50.0%" in roadmap_svg

def test_roadmap_zero_case(tmp_path):
    (tmp_path / "learning-profile.md").write_text("Subject: Math")
    charts = generate_workspace_charts(tmp_path)
    roadmap_svg = charts["alo-roadmap.svg"]
    assert "No roadmap items yet" in roadmap_svg

def test_existing_files_abort_without_force(tmp_path):
    (tmp_path / "learning-profile.md").write_text("Subject: Math")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "alo-progress.svg").write_text("OLD CONTENT")
    
    result = write_workspace_charts(tmp_path)
    assert result.written is False
    assert "already exists" in result.message
    
    assert (tmp_path / "assets" / "alo-progress.svg").read_text() == "OLD CONTENT"

def test_force_overwrites(tmp_path):
    (tmp_path / "learning-profile.md").write_text("Subject: Math")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "alo-progress.svg").write_text("OLD CONTENT")
    
    result = write_workspace_charts(tmp_path, force=True)
    assert result.written is True
    
    content = (tmp_path / "assets" / "alo-progress.svg").read_text()
    assert "OLD CONTENT" not in content
    assert "<svg" in content

def test_path_traversal_guard(tmp_path):
    (tmp_path / "learning-profile.md").write_text("Subject: Math")
    # try to write outside
    out_dir = tmp_path.parent / "sneaky"
    
    result = write_workspace_charts(tmp_path, output_dir=out_dir)
    assert result.written is False
    assert "Cannot write charts outside the workspace" in result.message

def test_malicious_subject_escaped(tmp_path):
    bad_subject = 'Subject: bad <script>alert(1)</script> & "stuff"'
    (tmp_path / "learning-profile.md").write_text(bad_subject)
    
    charts = generate_workspace_charts(tmp_path)
    progress_svg = charts["alo-progress.svg"]
    
    assert "<script>" not in progress_svg
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in progress_svg
    assert "&amp; &quot;stuff&quot;" in progress_svg

def test_secret_leakage_prevented(tmp_path):
    (tmp_path / "learning-profile.md").write_text("Subject: Math\nOPENAI_API_KEY=sk-abc123456")
    
    charts = generate_workspace_charts(tmp_path)
    for content in charts.values():
        assert "sk-" not in content
        assert "OPENAI_API_KEY" not in content

def test_cli_dry_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "learning-profile.md").write_text("Subject: CLI Test")
    
    res = runner.invoke(app, ["charts", "--dry-run"])
    assert res.exit_code == 0
    assert "Dry run" in res.stdout
    assert "alo-progress.svg" in res.stdout
    assert not (tmp_path / "assets").exists()

def test_cli_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "learning-profile.md").write_text("Subject: CLI Run Test")
    
    res = runner.invoke(app, ["charts"])
    assert res.exit_code == 0
    assert "Successfully generated SVG charts" in res.stdout
    
    assert (tmp_path / "assets" / "alo-streak.svg").exists()

def test_unsafe_assets_blocked_by_sync(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    
    # Needs to be a git repo
    import subprocess
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "alo-progress.svg").write_text("safe")
    (tmp_path / "assets" / "unsafe-chart.svg").write_text("unsafe")
    (tmp_path / "assets" / "malware.exe").write_text("unsafe")
    
    allowed, ignored = get_changed_files(tmp_path)
    
    # In Windows format they might use forward or backslashes from git porcelain depending on config
    # We should normalize
    allowed_norm = [p.replace('\\', '/') for p in allowed]
    ignored_norm = [p.replace('\\', '/') for p in ignored]
    
    assert "assets/alo-progress.svg" in allowed_norm
    assert "assets/unsafe-chart.svg" in ignored_norm
    assert "assets/malware.exe" in ignored_norm
