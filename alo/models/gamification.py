from pydantic import BaseModel
from typing import List

class Badge(BaseModel):
    id: str
    label: str
    description: str
    earned: bool
    progress: int = 0
    target: int = 1

class GamificationSummary(BaseModel):
    xp: int = 0
    level: int = 1
    current_streak_days: int = 0
    longest_streak_days: int = 0
    weekly_goal_target: int = 5
    weekly_goal_progress: int = 0
    consistency_score: float = 0.0
    badges: List[Badge] = []
    warnings: List[str] = []
