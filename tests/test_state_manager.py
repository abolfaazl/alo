from pathlib import Path
from alo import state_manager
from alo.models import ProgressLogEntry, RoadmapItemUpdate, WeaknessEntry

def test_ensure_state_files(tmp_path: Path):
    summary = state_manager.ensure_state_files(tmp_path)
    assert len(summary.files) == 8
    for f in summary.files:
        assert f.exists is True
        
    readme_path = tmp_path / "README.md"
    original_content = "# My Custom README\n"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(original_content)
        
    state_manager.ensure_state_files(tmp_path)
    with open(readme_path, "r", encoding="utf-8") as f:
        assert f.read() == original_content

def test_progress_log_append(tmp_path: Path):
    state_manager.ensure_state_files(tmp_path)
    entry = ProgressLogEntry(
        date="2026-06-28",
        topic="Testing",
        outcome="pass",
        score=100,
        learned="A lot",
        mistakes="None",
        next_recommendation="More testing"
    )
    state_manager.append_progress_log(tmp_path, entry)
    
    log_path = tmp_path / "progress-log.md"
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "## 2026-06-28" in content
    assert "Outcome: pass" in content

def test_roadmap_item_status(tmp_path: Path):
    state_manager.ensure_state_files(tmp_path)
    roadmap_path = tmp_path / "roadmap.md"
    with open(roadmap_path, "a", encoding="utf-8") as f:
        f.write("\n### ALO-RM-001: Topic Title\nStatus: todo\nLevel: intermediate\n")
        
    update = RoadmapItemUpdate(id="ALO-RM-001", status="in_progress")
    success = state_manager.update_roadmap_item_status(tmp_path, update)
    assert success is True
    
    with open(roadmap_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Status: in_progress" in content

def test_roadmap_update_fails_safely(tmp_path: Path):
    state_manager.ensure_state_files(tmp_path)
    update = RoadmapItemUpdate(id="NON-EXISTENT", status="in_progress")
    success = state_manager.update_roadmap_item_status(tmp_path, update)
    assert success is False

def test_weakness_append_and_update(tmp_path: Path):
    state_manager.ensure_state_files(tmp_path)
    weakness = WeaknessEntry(
        id="ALO-WK-001",
        topic="Python Classes",
        source="Assessment",
        observed_on="2026-06-28",
        severity="high",
        evidence="Failed test",
        recommended_practice="Read docs",
        status="open"
    )
    
    success = state_manager.upsert_weakness(tmp_path, weakness)
    assert success is True
    
    weaknesses_path = tmp_path / "weaknesses.md"
    with open(weaknesses_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "### ALO-WK-001: Python Classes" in content
    assert "Severity: high" in content
    
    weakness.severity = "low"
    success = state_manager.upsert_weakness(tmp_path, weakness)
    assert success is True
    
    with open(weaknesses_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Severity: low" in content
    assert "Severity: high" not in content
