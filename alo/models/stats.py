from pydantic import BaseModel
from typing import Optional, List

class LearningStats(BaseModel):
    workspace_path: str
    subject: Optional[str] = None

    lessons_completed: int = 0
    reviews_completed: int = 0
    practice_sessions: int = 0

    active_learning_days: int = 0
    current_streak_days: int = 0
    longest_streak_days: int = 0

    lessons_per_day: float = 0.0
    lessons_per_week: float = 0.0
    review_frequency: float = 0.0

    roadmap_total_items: int = 0
    roadmap_completed_items: int = 0
    roadmap_completion_percent: float = 0.0

    weaknesses_open: int = 0
    weaknesses_resolved: int = 0

    consistency_score: float = 0.0

    warnings: List[str] = []
