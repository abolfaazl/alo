from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from alo.exceptions import MissingAPIKeyError, KeyringUnavailableError
from alo import state_manager, config as alo_config
from alo.llm.schemas import ReviewSession, ReviewEvaluation

@dataclass
class ReviewSessionContext:
    target_id: str
    target_type: str
    target_content: str
    session: ReviewSession

@dataclass
class ReviewGenerateResult:
    success: bool
    error_code: str = None
    error: Optional[str] = None
    warning: Optional[str] = None
    context: Optional[ReviewSessionContext] = None

@dataclass
class ReviewEvaluateResult:
    success: bool
    error_code: str = None
    error: Optional[str] = None
    evaluation: Optional[ReviewEvaluation] = None

def get_review_target(cwd: Path, weakness_id: Optional[str] = None, item_id: Optional[str] = None):
    if weakness_id and item_id:
        return None, "Cannot pass both --weakness and --item."
        
    if weakness_id:
        w = state_manager.get_weakness_by_id(cwd, weakness_id)
        if w:
            return {"id": w["id"], "type": "weakness", "content": w["content"]}, None
        return None, f"Weakness {weakness_id} not found."
        
    if item_id:
        i = state_manager.get_roadmap_item_by_id(cwd, item_id)
        if i:
            return {"id": item_id, "type": "roadmap_item", "content": i}, None
        return None, f"Roadmap item {item_id} not found."
        
    # Auto-select
    active_weaknesses = state_manager.get_active_weaknesses(cwd)
    if active_weaknesses:
        return {"id": active_weaknesses[0]["id"], "type": "weakness", "content": active_weaknesses[0]["content"]}, None
        
    targets = state_manager.get_roadmap_review_targets(cwd)
    if targets:
        return {"id": targets[0]["id"], "type": "roadmap_item", "content": targets[0]["content"]}, None
        
    return None, "No review target found.\nRun `alo learn` to create progress and weaknesses first."

def generate_review_service(cwd: Path, mock: bool = False, weakness_id: Optional[str] = None, item_id: Optional[str] = None) -> ReviewGenerateResult:
    target, err = get_review_target(cwd, weakness_id, item_id)
    if err:
        return ReviewGenerateResult(success=False, error=err)
        
    lp = state_manager.markdown_store.read_text_safely(cwd / "learning-profile.md")
    sm = state_manager.markdown_store.read_text_safely(cwd / "skill-map.md")
    context = f"{lp}\n\n{sm}"

    if not mock:
        from alo.llm.client import generate_review_session
        cfg = alo_config.load_config()
        readiness = alo_config.validate_config_readiness(cfg)
        if not readiness.llm_ready:
            missing = ", ".join([i.label for i in readiness.missing_required])
            return ReviewGenerateResult(success=False, error_code="missing_config", error=f"ALO needs LLM configuration. Missing: {missing}")
            
        try:
            session = generate_review_session(context, target["id"], target["type"], target["content"])
            if not session:
                return ReviewGenerateResult(success=False, error="Failed to generate review session.")
        except MissingAPIKeyError as e:
            return ReviewGenerateResult(success=False, error_code="missing_api_key", error=str(e))
        except KeyringUnavailableError as e:
            return ReviewGenerateResult(success=False, error_code="keyring_unavailable", error=str(e))
        except Exception as e:
            return ReviewGenerateResult(success=False, error_code="llm_error", error=f"LLM or processing error: {e}")
    else:
        from alo.llm.client import generate_mock_review_session
        session = generate_mock_review_session(target["id"], target["type"], "Mock topic")
        
    ctx = ReviewSessionContext(
        target_id=target["id"],
        target_type=target["type"],
        target_content=target["content"],
        session=session
    )
    
    warning = None
    if mock:
        warning = "Mock review mode is for development/testing only."
        
    return ReviewGenerateResult(success=True, warning=warning, context=ctx)

def evaluate_review_service(cwd: Path, session_ctx: ReviewSessionContext, answer: str, mock: bool = False, dry_run: bool = False) -> ReviewEvaluateResult:
    if not mock:
        from alo.llm.client import evaluate_review_session
        lp = state_manager.markdown_store.read_text_safely(cwd / "learning-profile.md")
        sm = state_manager.markdown_store.read_text_safely(cwd / "skill-map.md")
        context = f"{lp}\n\n{sm}"
        
        try:
            evaluation = evaluate_review_session(
                context, 
                session_ctx.target_id, 
                session_ctx.target_type, 
                session_ctx.target_content, 
                session_ctx.session.short_review, 
                session_ctx.session.review_question, 
                answer
            )
            if not evaluation:
                return ReviewEvaluateResult(success=False, error="Failed to evaluate review.")
        except MissingAPIKeyError as e:
            return ReviewEvaluateResult(success=False, error_code="missing_api_key", error=str(e))
        except KeyringUnavailableError as e:
            return ReviewEvaluateResult(success=False, error_code="keyring_unavailable", error=str(e))
        except Exception as e:
            return ReviewEvaluateResult(success=False, error_code="llm_error", error=f"LLM or processing error: {e}")
    else:
        from alo.llm.client import evaluate_mock_review_session
        evaluation = evaluate_mock_review_session(answer, session_ctx.target_type)
        
    if not dry_run:
        state_manager.append_review_progress(cwd, evaluation, session_ctx.session.topic)
        
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d")
        
        if session_ctx.target_type == "weakness":
            state_manager.update_weakness_status(cwd, session_ctx.target_id, evaluation.weakness_status_update, now, evaluation.result)
        elif session_ctx.target_type == "roadmap_item":
            from alo.models import RoadmapItemUpdate
            state_manager.update_roadmap_item_status(cwd, RoadmapItemUpdate(id=session_ctx.target_id, status=evaluation.roadmap_status_update))
            
    return ReviewEvaluateResult(success=True, evaluation=evaluation)
