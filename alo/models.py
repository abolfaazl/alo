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
    absolute_beginner = "Absolute beginner"
    beginner = "Beginner"
    intermediate = "Intermediate"
    advanced = "Advanced"
    professional = "Professional"

class PrivacyPreference(str, Enum):
    generalize = "generalize"
    store = "store"

class OnboardingProfile(BaseModel):
    subject: str
    background: str
    experience_level: ExperienceLevel
    goal: str
    assess_now: bool
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

class AssessmentDifficulty(str, Enum):
    foundation = "foundation"
    intermediate = "intermediate"
    advanced = "advanced"
    professional = "professional"
    expert = "expert"

class AssessmentDomain(str, Enum):
    python = "Python"
    git = "Git and GitHub"
    testing = "Testing"
    architecture = "Architecture"
    ai = "AI-Native Development"
    product = "Product Engineering"
    writing = "Technical Writing"

class AssessmentMode(str, Enum):
    local = "local"
    llm = "llm"

class AssessmentQuestion(BaseModel):
    id: str
    domain: str
    difficulty: str
    question: str
    choices: List[str]
    correct_choice_index: int
    explanation: str
    weakness_topic: str

class AssessmentAnswer(BaseModel):
    question_id: str
    selected_index: Optional[int]
    is_correct: bool

class AssessmentDomainScore(BaseModel):
    domain: str
    score_percent: int
    correct: int
    total: int

class AssessmentDifficultyScore(BaseModel):
    difficulty: str
    score_percent: int
    correct: int
    total: int

class AssessmentResult(BaseModel):
    mode: AssessmentMode
    total_questions: int
    correct_answers: int
    score_percent: int
    level: str
    domain_scores: List[AssessmentDomainScore]
    difficulty_scores: List[AssessmentDifficultyScore]
    missed_questions: List[AssessmentQuestion]
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    date: str
