from alo.models.stats import LearningStats
from alo.services.gamification_service import compute_gamification_from_stats
from typer.testing import CliRunner
from alo.cli import app

def test_xp_calculation_zero():
    stats = LearningStats(workspace_path=".")
    summary = compute_gamification_from_stats(stats)
    assert summary.xp == 0
    assert summary.level == 1
    assert summary.weekly_goal_progress == 0

def test_xp_calculation_normal():
    stats = LearningStats(
        workspace_path=".",
        lessons_completed=2,      # 2 * 20 = 40
        reviews_completed=1,      # 1 * 10 = 10
        practice_sessions=3,      # 3 * 15 = 45
        active_learning_days=2,   # 2 * 5 = 10
        weaknesses_resolved=1     # 1 * 25 = 25
    )
    summary = compute_gamification_from_stats(stats)
    assert summary.xp == 130
    assert summary.level == 2
    assert summary.weekly_goal_progress == 2

def test_badges_earned():
    stats = LearningStats(
        workspace_path=".",
        lessons_completed=26,
        reviews_completed=2,
        practice_sessions=8,
        active_learning_days=10,
        weaknesses_resolved=4,
        current_streak_days=8,
        roadmap_total_items=10,
        roadmap_completed_items=5,
        roadmap_completion_percent=50,
        consistency_score=75
    )
    summary = compute_gamification_from_stats(stats)
    
    # Let's check a few badges
    earned_ids = [b.id for b in summary.badges if b.earned]
    assert "first-lesson" in earned_ids
    assert "ten-lessons" in earned_ids
    assert "twenty-five-lessons" in earned_ids
    assert "seven-day-streak" in earned_ids
    assert "deep-practice-week" in earned_ids
    assert "roadmap-halfway" in earned_ids
    assert "weakness-hunter" in earned_ids
    assert "consistent-learner" in earned_ids
    
    # Not earned yet
    assert "roadmap-finisher" not in earned_ids

def test_badge_progress():
    stats = LearningStats(
        workspace_path=".",
        lessons_completed=1,
        roadmap_total_items=10,
        roadmap_completed_items=1,
        roadmap_completion_percent=10
    )
    summary = compute_gamification_from_stats(stats)
    
    badges = {b.id: b for b in summary.badges}
    
    # Earned badge
    assert badges["first-lesson"].earned is True
    assert badges["first-lesson"].progress == 1
    assert badges["first-lesson"].target == 1
    
    # Locked badge
    assert badges["ten-lessons"].earned is False
    assert badges["ten-lessons"].progress == 1
    assert badges["ten-lessons"].target == 10
    
    # Percentage badge
    assert badges["roadmap-halfway"].earned is False
    assert badges["roadmap-halfway"].progress == 10


runner = CliRunner()

def test_badges_command(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "learning-profile.md").write_text("Subject: Badges Test")
    
    # Needs valid stats so we add progress log
    (tmp_path / "progress-log.md").write_text("## Session 1\nLesson complete.\n")
    
    res = runner.invoke(app, ["badges"])
    assert res.exit_code == 0
    assert "Learning Gamification" in res.stdout
    assert "XP:" in res.stdout
    assert "Level:" in res.stdout
    
def test_badges_command_outside_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    res = runner.invoke(app, ["badges"])
    assert res.exit_code == 1
    assert "Not an ALO workspace" in res.stdout

