from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from alo.exceptions import MissingAPIKeyError, KeyringUnavailableError
from alo import markdown_store, config as alo_config
from alo.llm.client import (
    generate_learning_session, generate_mock_learning_session,
    evaluate_learning_session, evaluate_mock_learning_session
)
from alo.state_manager import (
    get_roadmap_item_by_id, get_next_learnable_roadmap_item,
    update_roadmap_item_status, append_learning_session_progress,
    upsert_learning_session_weaknesses
)
from alo.models import RoadmapItemUpdate

@dataclass
class LearnSessionContext:
    target_id: str
    target_item: str
    session: any # The LLM session object
    context_str: str

@dataclass
class LearnGenerateResult:
    success: bool
    error_code: str = None
    context: Optional[LearnSessionContext] = None
    error: str = None
    warning: str = None

@dataclass
class LearnEvaluateResult:
    success: bool
    error_code: str = None
    evaluation: any = None
    error: str = None

def generate_session(repo_path: Path, mock: bool = False, item_id: str = None) -> LearnGenerateResult:
    if not (repo_path / "learning-profile.md").exists():
        return LearnGenerateResult(success=False, error="Workspace not initialized. Run `alo init`.")
        
    rm_path = repo_path / "roadmap.md"
    existing_roadmap = markdown_store.read_text_safely(rm_path)
    if not existing_roadmap or "### ALO-RM-" not in existing_roadmap:
        return LearnGenerateResult(success=False, error="No learnable roadmap item found.\nRun `alo roadmap` or review completed items.")
        
    if not mock:
        cfg = alo_config.load_config()
        readiness = alo_config.validate_config_readiness(cfg)
        if not readiness.llm_ready:
            missing = ", ".join([i.label for i in readiness.missing_required])
            return LearnGenerateResult(success=False, error_code="missing_config", error=f"ALO needs LLM configuration. Missing: {missing}")

    if item_id:
        target_item = get_roadmap_item_by_id(repo_path, item_id)
        if not target_item:
            return LearnGenerateResult(success=False, error=f"Roadmap item {item_id} not found.")
    else:
        target_item = get_next_learnable_roadmap_item(repo_path)
        if not target_item:
            return LearnGenerateResult(success=False, error="No learnable roadmap item found.\nRun `alo roadmap` or review completed items.")
            
    import re
    item_id_match = re.search(r"### (ALO-RM-\d+)", target_item)
    if not item_id_match:
        return LearnGenerateResult(success=False, error="Could not parse roadmap item ID.")
    target_id = item_id_match.group(1)
    
    lp = markdown_store.read_text_safely(repo_path / "learning-profile.md") or ""
    sm = markdown_store.read_text_safely(repo_path / "skill-map.md") or ""
    wk = markdown_store.read_text_safely(repo_path / "weaknesses.md") or ""
    context_str = f"Profile:\n{lp}\n\nSkill Map:\n{sm}\n\nWeaknesses:\n{wk}"

    warning = None
    if mock:
        warning = "Mock learning session mode is for development/testing only."
        session = generate_mock_learning_session(target_id)
    else:
        try:
            session = generate_learning_session(context_str, target_item)
            if not session:
                return LearnGenerateResult(success=False, error="Failed to generate learning session.")
        except MissingAPIKeyError as e:
            return LearnGenerateResult(success=False, error_code="missing_api_key", error=str(e))
        except KeyringUnavailableError as e:
            return LearnGenerateResult(success=False, error_code="keyring_unavailable", error=str(e))
        except Exception as e:
            return LearnGenerateResult(success=False, error_code="llm_error", error=f"LLM or processing error: {e}")

    return LearnGenerateResult(
        success=True,
        context=LearnSessionContext(target_id=target_id, target_item=target_item, session=session, context_str=context_str),
        warning=warning
    )

def evaluate_answer(repo_path: Path, context: LearnSessionContext, answer: str, mock: bool = False, dry_run: bool = False) -> LearnEvaluateResult:
    if mock:
        evaluation = evaluate_mock_learning_session(answer)
    else:
        try:
            evaluation = evaluate_learning_session(
                context.context_str, 
                context.target_item, 
                context.session.short_lesson, 
                context.session.practice_question, 
                answer
            )
            if not evaluation:
                return LearnEvaluateResult(success=False, error="Failed to evaluate answer.")
        except MissingAPIKeyError as e:
            return LearnGenerateResult(success=False, error_code="missing_api_key", error=str(e))
        except KeyringUnavailableError as e:
            return LearnGenerateResult(success=False, error_code="keyring_unavailable", error=str(e))
        except Exception as e:
            return LearnGenerateResult(success=False, error_code="llm_error", error=f"LLM or processing error: {e}")

    if not dry_run:
        update_roadmap_item_status(repo_path, RoadmapItemUpdate(id=context.target_id, status=evaluation.roadmap_status_update))
        if evaluation.weakness_entries:
            upsert_learning_session_weaknesses(repo_path, evaluation, context.target_id)
        append_learning_session_progress(repo_path, evaluation, context.target_id, context.session.topic)

    return LearnEvaluateResult(success=True, evaluation=evaluation)
