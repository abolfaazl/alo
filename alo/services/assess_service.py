from dataclasses import dataclass
from pathlib import Path
from typing import List

from alo.exceptions import MissingAPIKeyError, KeyringUnavailableError
from alo import state_manager, config as alo_config
from alo.llm.client import generate_assessment, generate_mock_assessment
from alo.models import AssessmentQuestion, AssessmentMode

@dataclass
class AssessGenerateResult:
    success: bool
    error_code: str = None
    questions: list[AssessmentQuestion] = None
    subject: str = None
    error: str = None
    warning: str = None

@dataclass
class AssessScoreResult:
    success: bool
    error_code: str = None
    result: any = None
    error: str = None

def generate_assessment_service(repo_path: Path, mock: bool = False) -> AssessGenerateResult:
    state_manager.ensure_state_files(repo_path)
    
    if not mock:
        cfg = alo_config.load_config()
        readiness = alo_config.validate_config_readiness(cfg)
        if not readiness.llm_ready:
            missing = ", ".join([i.label for i in readiness.missing_required])
            return AssessGenerateResult(success=False, error_code="missing_config", error=f"ALO needs LLM configuration. Missing: {missing}")
        

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
        except MissingAPIKeyError as e:
            return AssessGenerateResult(success=False, error_code="missing_api_key", error=str(e))
        except KeyringUnavailableError as e:
            return AssessGenerateResult(success=False, error_code="keyring_unavailable", error=str(e))
        except Exception as e:
            return AssessGenerateResult(success=False, error_code="llm_error", error=f"LLM or processing error: {e}")
            
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
