from pydantic import BaseModel
from typing import Literal, Optional, List

RoadmapStatus = Literal[
    "todo", "in_progress", "practiced", "passed_once", 
    "mastered", "needs_review", "skipped"
]

EvaluationOutcome = Literal[
    "pass", "partial", "fail", "not_evaluated"
]

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
