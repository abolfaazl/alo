from pydantic import BaseModel
from typing import Literal, Optional, List
from enum import Enum

RoadmapStatus = Literal[
    "todo", "in_progress", "practiced", "passed_once", 
    "mastered", "needs_review", "skipped"
]

EvaluationOutcome = Literal[
    "pass", "partial", "fail", "not_evaluated"
]

class ExperienceLevel(str, Enum):
    beginner = "Beginner"
    junior = "Junior"
    intermediate = "Intermediate"
    advanced = "Advanced"
    professional = "Professional / Senior"

class LearningGoalMode(str, Enum):
    know = "I know what I want to learn"
    recommend = "Recommend paths later"

class LearningStyle(str, Enum):
    short_theory = "Short theory then practice"
    mostly_practical = "Mostly practical exercises"
    deep_explanations = "Deep explanations"
    interview_style = "Interview-style questions"
    mixed = "Mixed"

class PrivacyPreference(str, Enum):
    generalize = "generalize"
    store = "store"

class OnboardingProfile(BaseModel):
    declared_skills: str
    experience_level: ExperienceLevel
    goal_mode: LearningGoalMode
    specific_goal: Optional[str] = None
    learning_style: LearningStyle
    time_per_session: str
    sessions_per_week: str
    privacy_preference: PrivacyPreference
    date: str

class RoadmapItemUpdate(BaseModel):
    id: str
    status: RoadmapStatus

class ProgressLogEntry(BaseModel):
    date: str
    topic: str
    outcome: EvaluationOutcome
    score: Optional[int] = None
    learned: str
    mistakes: str
    next_recommendation: str

class WeaknessEntry(BaseModel):
    id: str
    topic: str
    source: str
    observed_on: str
    severity: str
    evidence: str
    recommended_practice: str
    status: str

class StateFileStatus(BaseModel):
    name: str
    exists: bool

class StateSummary(BaseModel):
    repo_path: str
    files: List[StateFileStatus]

