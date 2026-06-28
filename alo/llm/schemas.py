from pydantic import BaseModel
from typing import Literal, List

class GeneratedAssessmentQuestion(BaseModel):
    id: str
    domain: str
    difficulty: Literal["foundation", "intermediate", "advanced", "professional"]
    question: str
    choices: List[str]
    correct_choice_index: int
    explanation: str
    weakness_topic: str

class AssessmentResponse(BaseModel):
    questions: List[GeneratedAssessmentQuestion]

class LearningPath(BaseModel):
    id: str
    title: str
    summary: str
    who_it_is_for: str
    why_it_matches_user: str
    expected_outcome: str
    core_topics: List[str]
    estimated_duration: str
    difficulty: str
    tradeoffs: str
    first_step: str
    avoid_for_now: str
    confidence: Literal["low", "medium", "high"]

class LearningPathsResponse(BaseModel):
    paths: List[LearningPath]

class RoadmapItem(BaseModel):
    id: str
    title: str
    summary: str
    level: Literal["foundation", "intermediate", "advanced", "professional"]
    status: Literal["todo", "in_progress", "practiced", "passed_once", "mastered", "needs_review", "skipped"] = "todo"
    estimated_time: str
    prerequisites: str
    success_criteria: str
    practice_task: str
    assessment_method: str
    resources_to_find: str
    depends_on: str

class RoadmapResponse(BaseModel):
    items: List[RoadmapItem]

class LearningSession(BaseModel):
    topic: str
    roadmap_item_id: str
    short_lesson: str
    example: str
    common_mistake: str
    practice_question: str
    expected_answer_guidance: str

class WeaknessEntrySchema(BaseModel):
    topic: str
    evidence: str
    recommended_practice: str

class LearningEvaluation(BaseModel):
    result: Literal["pass", "partial", "fail"]
    score: int
    feedback: str
    strengths: str
    weaknesses: str
    recommended_next_step: str
    roadmap_status_update: Literal["practiced", "passed_once", "needs_review"]
    weakness_entries: List[WeaknessEntrySchema]
