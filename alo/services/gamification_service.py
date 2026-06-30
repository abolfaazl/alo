from pathlib import Path
from alo.models.stats import LearningStats
from alo.models.gamification import GamificationSummary, Badge
from alo.services.stats_service import compute_learning_stats

def compute_gamification_from_stats(stats: LearningStats) -> GamificationSummary:
    # Calculate XP
    xp = (
        stats.lessons_completed * 20
        + stats.reviews_completed * 10
        + stats.practice_sessions * 15
        + stats.active_learning_days * 5
        + stats.weaknesses_resolved * 25
    )
    xp = max(0, xp)  # XP must never be negative
    
    # Calculate Level
    level = max(1, xp // 100 + 1)
    
    # Weekly Goal
    weekly_goal_progress = min(stats.active_learning_days, 5)
    
    # Calculate Badges
    badges = []
    
    def add_badge(id: str, label: str, desc: str, current: int, target: int):
        earned = current >= target
        # For badges, progress cannot exceed target, but it's safe to just cap it if we want.
        # But leaving raw progress is also fine. Let's cap at target for neatness if earned.
        progress = min(current, target) if earned else current
        badges.append(Badge(
            id=id,
            label=label,
            description=desc,
            earned=earned,
            progress=progress,
            target=target
        ))
        
    add_badge(
        "first-lesson", "First Lesson", "Completed your first lesson.", 
        stats.lessons_completed, 1
    )
    add_badge(
        "first-review", "First Review", "Completed your first review.", 
        stats.reviews_completed, 1
    )
    add_badge(
        "first-practice", "First Practice", "Completed your first practice.", 
        stats.practice_sessions, 1
    )
    add_badge(
        "seven-day-streak", "7-Day Streak", "Maintained a 7-day learning streak.", 
        stats.current_streak_days, 7
    )
    add_badge(
        "ten-lessons", "10 Lessons Completed", "Completed 10 lessons.", 
        stats.lessons_completed, 10
    )
    add_badge(
        "twenty-five-lessons", "25 Lessons Completed", "Completed 25 lessons.", 
        stats.lessons_completed, 25
    )
    add_badge(
        "weakness-hunter", "Weakness Hunter", "Resolved 3 weaknesses.", 
        stats.weaknesses_resolved, 3
    )
    add_badge(
        "roadmap-starter", "Roadmap Starter", "Completed your first roadmap item.", 
        stats.roadmap_completed_items, 1
    )
    
    # Roadmap Halfway & Finisher require a bit of custom logic since they use percentages
    rm_halfway_earned = stats.roadmap_completion_percent >= 50
    badges.append(Badge(
        id="roadmap-halfway",
        label="Roadmap Halfway",
        description="Reached 50% roadmap completion.",
        earned=rm_halfway_earned,
        progress=stats.roadmap_completion_percent if not rm_halfway_earned else 50,
        target=50
    ))
    
    rm_finisher_earned = stats.roadmap_total_items > 0 and stats.roadmap_completion_percent >= 100
    badges.append(Badge(
        id="roadmap-finisher",
        label="Roadmap Finisher",
        description="Completed the entire roadmap.",
        earned=rm_finisher_earned,
        progress=stats.roadmap_completion_percent if not rm_finisher_earned else 100,
        target=100
    ))
    
    add_badge(
        "deep-practice-week", "Deep Practice Week", "Completed 7 practice sessions.", 
        stats.practice_sessions, 7
    )
    
    # Consistent Learner
    consistent_earned = stats.consistency_score >= 70
    badges.append(Badge(
        id="consistent-learner",
        label="Consistent Learner",
        description="Achieved a consistency score of 70 or higher.",
        earned=consistent_earned,
        progress=int(stats.consistency_score) if not consistent_earned else 70,
        target=70
    ))

    return GamificationSummary(
        xp=xp,
        level=level,
        current_streak_days=stats.current_streak_days,
        longest_streak_days=stats.longest_streak_days,
        weekly_goal_target=5,
        weekly_goal_progress=weekly_goal_progress,
        consistency_score=stats.consistency_score,
        badges=badges
    )

def compute_gamification_summary(workspace_path: Path) -> GamificationSummary:
    stats = compute_learning_stats(workspace_path)
    return compute_gamification_from_stats(stats)
