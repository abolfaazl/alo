from dataclasses import dataclass
from pathlib import Path

from alo import markdown_store, config as alo_config
from alo.llm.client import generate_roadmap, generate_mock_roadmap
from alo.state_manager import get_active_learning_path, save_roadmap, append_roadmap_progress

@dataclass
class RoadmapServiceResult:
    success: bool
    items: list = None
    active_path_id: str = None
    error: str = None
    warning: str = None

def generate_roadmap_service(repo_path: Path, mock: bool = False, force: bool = False, dry_run: bool = False) -> RoadmapServiceResult:
    if not (repo_path / "learning-profile.md").exists():
        return RoadmapServiceResult(success=False, error="Workspace not initialized. Run `alo init`.")
        
    active_path = get_active_learning_path(repo_path)
    if not active_path:
        return RoadmapServiceResult(success=False, error="No active learning path selected.\nRun `alo paths` first and select a path.")
        
    rm_path = repo_path / "roadmap.md"
    existing_roadmap = markdown_store.read_text_safely(rm_path)
    has_items = existing_roadmap and "### ALO-RM-001" in existing_roadmap
    
    if has_items and not force:
        return RoadmapServiceResult(success=False, error="A roadmap already exists.\nRun `alo roadmap --force` to regenerate it (existing statuses will be preserved).")
        
    if not mock and not alo_config.config_exists():
        return RoadmapServiceResult(success=False, error="ALO needs LLM configuration to generate a personalized roadmap.\nRun: alo config")

    lp = markdown_store.read_text_safely(repo_path / "learning-profile.md") or ""
    sm = markdown_store.read_text_safely(repo_path / "skill-map.md") or ""
    wk = markdown_store.read_text_safely(repo_path / "weaknesses.md") or ""
    lpaths = markdown_store.read_text_safely(repo_path / "learning-paths.md") or ""
    
    import re
    subject_match = re.search(r"Subject: (.+)", lp)
    subject = subject_match.group(1).strip() if subject_match else "Subject"
    
    context = f"Profile:\n{lp}\n\nSkill Map:\n{sm}\n\nWeaknesses:\n{wk}\n\nPaths:\n{lpaths}"

    warning = None
    if mock:
        warning = "Mock roadmap mode is for development/testing only."
        llm_response = generate_mock_roadmap(subject)
    else:
        try:
            llm_response = generate_roadmap(context)
            if not llm_response:
                return RoadmapServiceResult(success=False, error="Failed to generate roadmap.")
        except ValueError as e:
            err_msg = str(e)
            if "not set" in err_msg.lower() or "missing" in err_msg.lower():
                err_msg = "Configured API key environment variable is missing.\nSet the configured environment variable or update alo config."
            return RoadmapServiceResult(success=False, error=err_msg)
            
    if not llm_response or not hasattr(llm_response, "items"):
        return RoadmapServiceResult(success=False, error="LLM failed to return a valid roadmap.")
        
    num_items = len(llm_response.items)
    if not (8 <= num_items <= 15):
        return RoadmapServiceResult(success=False, error=f"LLM returned {num_items} items, but expected between 8 and 15.")

    if not dry_run:
        save_roadmap(repo_path, llm_response, active_path["id"])
        append_roadmap_progress(repo_path)
        
    return RoadmapServiceResult(
        success=True,
        items=llm_response.items,
        active_path_id=active_path["id"],
        warning=warning
    )
