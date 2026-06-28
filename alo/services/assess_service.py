from dataclasses import dataclass
from pathlib import Path
from typing import List

from alo import state_manager, config as alo_config
from alo.llm.client import generate_assessment, generate_mock_assessment
from alo.models import AssessmentQuestion, AssessmentMode

@dataclass
class AssessGenerateResult:
    success: bool
    questions: list[AssessmentQuestion] = None
    subject: str = None
    error: str = None
    warning: str = None

@dataclass
class AssessScoreResult:
    success: bool
    result: any = None
    error: str = None

def generate_assessment_service(repo_path: Path, mock: bool = False) -> AssessGenerateResult:
    state_manager.ensure_state_files(repo_path)
    
    if not alo_config.config_exists() and not mock:
        return AssessGenerateResult(success=False, error="ALO needs LLM configuration to generate a domain-specific assessment.\nRun: `alo config`")
        
    if not mock:
        cfg = alo_config.load_config()
        import os
        if not os.environ.get(cfg.api_key_env_var):
            return AssessGenerateResult(success=False, error=f"Configured API key environment variable is missing.\nSet {cfg.api_key_env_var} or update `alo config`.")

    lp = state_manager.markdown_store.read_text_safely(repo_path / "learning-profile.md")
    
    subject = "Subject"
    goal = "Goal"
    level = "Level"
    bg = "Background"
    
    import re
    if lp:
        s_m = re.search(r"Subject:\s*(.*)", lp)
        if s_m:
            subject = s_m.group(1).strip()
        g_m = re.search(r"Target Goal:\s*(.*)", lp)
        if g_m:
            goal = g_m.group(1).strip()
        l_m = re.search(r"Current Level:\s*(.*)", lp)
        if l_m:
            level = l_m.group(1).strip()
        b_m = re.search(r"Known Background:\s*(.*)", lp)
        if b_m:
            bg = b_m.group(1).strip()

    warning = None
    if mock:
        warning = "Mock assessment mode is for development/testing only."
        llm_response = generate_mock_assessment(subject)
    else:
        try:
            llm_response = generate_assessment(subject, goal, level, bg)
            if not llm_response:
                return AssessGenerateResult(success=False, error="Failed to generate assessment.")
        except ValueError as e:
            return AssessGenerateResult(success=False, error=str(e))
            
    questions = []
    for q in llm_response.questions:
        questions.append(AssessmentQuestion(
            id=q.id,
            domain=q.domain,
            difficulty=q.difficulty,
            question=q.question,
            choices=q.choices,
            correct_choice_index=q.correct_choice_index,
            explanation=q.explanation,
            weakness_topic=q.weakness_topic
        ))

    return AssessGenerateResult(success=True, questions=questions, subject=subject, warning=warning)

def score_assessment_service(repo_path: Path, questions: List[AssessmentQuestion], answers: List[int], mock: bool = False, dry_run: bool = False) -> AssessScoreResult:
    from alo import assessment
    
    result = assessment.score_assessment(AssessmentMode.llm if not mock else AssessmentMode.local, questions, answers)
    
    if not dry_run:
        state_manager.append_assessment_to_learning_profile(repo_path, result)
        state_manager.update_skill_map_from_assessment(repo_path, result)
        state_manager.upsert_weaknesses_from_assessment(repo_path, result)
        state_manager.append_assessment_progress(repo_path, result)
        
    return AssessScoreResult(success=True, result=result)
