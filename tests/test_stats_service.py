from datetime import date, timedelta
from alo.services.stats_service import compute_learning_stats

def test_missing_files(tmp_path):
    stats = compute_learning_stats(tmp_path)
    assert stats.lessons_completed == 0
    assert stats.current_streak_days == 0
    assert len(stats.warnings) == 3
    assert "progress-log.md not found" in stats.warnings
    assert "roadmap.md not found" in stats.warnings
    assert "weaknesses.md not found" in stats.warnings

def test_empty_workspace(tmp_path):
    (tmp_path / "progress-log.md").write_text("# Progress Log\n")
    (tmp_path / "roadmap.md").write_text("# Roadmap\n")
    (tmp_path / "weaknesses.md").write_text("# Weaknesses\n")
    
    stats = compute_learning_stats(tmp_path)
    assert stats.lessons_completed == 0
    assert stats.roadmap_total_items == 0
    assert stats.weaknesses_open == 0
    assert len(stats.warnings) == 0

def test_progress_log_parsing_and_streaks(tmp_path):
    today = date.today()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)
    five_days_ago = today - timedelta(days=5)
    
    content = f"""# Progress Log

## {today.isoformat()}
### Session: Learn Python
Outcome: pass
What was learned: Built a script.

## {yesterday.isoformat()}
### Session: Review loops
Outcome: pass
What was learned: Reviewed loops.

## {two_days_ago.isoformat()}
### Session: Practice dicts
Outcome: pass
What was learned: Practiced dicts.

## {five_days_ago.isoformat()}
### Session: Learn sets
Outcome: pass
What was learned: Learned about sets.
"""
    (tmp_path / "progress-log.md").write_text(content)
    (tmp_path / "roadmap.md").write_text("")
    (tmp_path / "weaknesses.md").write_text("")
    
    stats = compute_learning_stats(tmp_path, today=today)
    assert stats.lessons_completed == 2
    assert stats.reviews_completed == 1
    assert stats.practice_sessions == 1
    assert stats.active_learning_days == 4
    
    # 3 consecutive days ending today -> streak 3
    assert stats.current_streak_days == 3
    assert stats.longest_streak_days == 3

def test_streak_ending_yesterday(tmp_path):
    today = date(2026, 6, 30)
    yesterday = date(2026, 6, 29)
    two_days_ago = date(2026, 6, 28)
    
    content = f"""# Progress Log
## {yesterday.isoformat()}
### Session: Learn something

## {two_days_ago.isoformat()}
### Session: Practice something
"""
    (tmp_path / "progress-log.md").write_text(content)
    stats = compute_learning_stats(tmp_path, today=today)
    assert stats.current_streak_days == 2
    assert stats.active_learning_days == 2

def test_streak_broken(tmp_path):
    today = date(2026, 6, 30)
    three_days_ago = date(2026, 6, 27)
    
    content = f"""# Progress Log
## {three_days_ago.isoformat()}
### Session: Learn something
"""
    (tmp_path / "progress-log.md").write_text(content)
    stats = compute_learning_stats(tmp_path, today=today)
    assert stats.current_streak_days == 0
    assert stats.longest_streak_days == 1

def test_roadmap_parsing(tmp_path):
    content = """# Roadmap
- [x] Learn Python
- [x] Learn Git
- [ ] Learn Docker
- [ ] Learn K8s
"""
    (tmp_path / "roadmap.md").write_text(content)
    stats = compute_learning_stats(tmp_path)
    assert stats.roadmap_total_items == 4
    assert stats.roadmap_completed_items == 2
    assert stats.roadmap_completion_percent == 50.0

def test_roadmap_malformed_no_checkboxes(tmp_path):
    content = """# Roadmap
### ALO-RM-001
Status: todo
"""
    (tmp_path / "roadmap.md").write_text(content)
    stats = compute_learning_stats(tmp_path)
    assert stats.roadmap_total_items == 0
    assert stats.roadmap_completed_items == 0
    assert any("Roadmap format unknown" in w for w in stats.warnings)

def test_weaknesses_parsing(tmp_path):
    content = """# Weaknesses
### ALO-WK-001
Status: open

### ALO-WK-002
Status: resolved

### ALO-WK-003
Status: active
"""
    (tmp_path / "weaknesses.md").write_text(content)
    stats = compute_learning_stats(tmp_path)
    assert stats.weaknesses_open == 2
    assert stats.weaknesses_resolved == 1

def test_weaknesses_malformed(tmp_path):
    content = """# Weaknesses
### ALO-WK-001
No status here
"""
    (tmp_path / "weaknesses.md").write_text(content)
    stats = compute_learning_stats(tmp_path)
    assert stats.weaknesses_open == 0
    assert any("Weaknesses format unknown" in w for w in stats.warnings)

def test_consistency_score_bounds(tmp_path):
    # Setup for max consistency score
    content = ""
    today = date.today()
    for i in range(20):
        d = today - timedelta(days=i)
        content += f"\n## {d.isoformat()}\n### Session: Review stuff\n"
        
    (tmp_path / "progress-log.md").write_text(content)
    stats = compute_learning_stats(tmp_path, today=today)
    assert stats.consistency_score == 100.0  # Cap at 100

def test_security_secrets_are_not_leaked(tmp_path):
    # Inject fake secrets into markdown files
    content = """# Progress Log
## 2026-06-30
### Session: Learn
OPENAI_API_KEY=sk-test-fake-key
Bearer some-fake-token
api_key: another-fake-key
"""
    (tmp_path / "progress-log.md").write_text(content)
    (tmp_path / "roadmap.md").write_text("- [x] sk-fake-key\n")
    (tmp_path / "weaknesses.md").write_text("Status: open\nOPENAI_API_KEY=sk-test-fake-key")
    
    stats = compute_learning_stats(tmp_path)
    
    stats_dict = stats.model_dump()
    stats_str = str(stats_dict)
    
    # Assert that none of these secrets ended up in the computed stats
    assert "sk-test-fake-key" not in stats_str
    assert "OPENAI_API_KEY" not in stats_str
    assert "Bearer" not in stats_str
    assert "some-fake-token" not in stats_str
    assert "api_key" not in stats_str
    
    assert stats.lessons_completed == 1
    assert stats.roadmap_completed_items == 1
    assert stats.weaknesses_open == 1
