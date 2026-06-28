from pathlib import Path
from typing import List

from alo.models import (
    RoadmapItemUpdate, 
    ProgressLogEntry, 
    WeaknessEntry, 
    StateFileStatus, 
    StateSummary
)
from alo import markdown_store

REQUIRED_FILES = {
    "README.md": "# ALO Learning Repository\n\nThis is a learning repository managed by ALO (Agentic Learning OS).\n",
    "learning-profile.md": "# Learning Profile\n\n## Current Level Summary\n\n## Declared Skills\n\n## Assessment Summary\n\n## Goals\n\n## Preferred Learning Style\n\n## Constraints\n\n## Last Updated\n",
    "skill-map.md": "# Skill Map\n\n## Python\n\n## Git and GitHub\n\n## Testing\n\n## Architecture\n\n## AI-Native Development\n\n## Product Engineering\n\n## Technical Writing\n",
    "roadmap.md": "# Roadmap\n\n## Active Path\n\n## Roadmap Items\n",
    "weaknesses.md": "# Weaknesses\n\n## Active Weaknesses\n",
    "progress-log.md": "# Progress Log\n",
    "tutor-rules.md": "# Tutor Rules\n\nALO must:\n* avoid treating professional users as beginners\n* teach in small chunks\n* evaluate strictly but fairly\n* track weaknesses\n* avoid false mastery\n",
    "privacy-rules.md": "# Privacy Rules\n\nALO must not store private company, client, project, repository, or product details unless explicitly approved by the user.\n"
}

def get_required_state_files() -> List[str]:
    return list(REQUIRED_FILES.keys())

def ensure_state_files(repo_path: Path) -> StateSummary:
    files_status = []
    for filename, template in REQUIRED_FILES.items():
        file_path = repo_path / filename
        markdown_store.create_if_missing(file_path, template)
        files_status.append(StateFileStatus(name=filename, exists=markdown_store.file_exists(file_path)))
    
    return StateSummary(repo_path=str(repo_path), files=files_status)

def get_state_summary(repo_path: Path) -> StateSummary:
    files_status = []
    for filename in REQUIRED_FILES.keys():
        file_path = repo_path / filename
        files_status.append(StateFileStatus(name=filename, exists=markdown_store.file_exists(file_path)))
    return StateSummary(repo_path=str(repo_path), files=files_status)

def append_progress_log(repo_path: Path, entry: ProgressLogEntry) -> bool:
    log_path = repo_path / "progress-log.md"
    score_str = str(entry.score) if entry.score is not None else ""
    content = (
        f"\n## {entry.date}\n\n"
        f"### Session: {entry.topic}\n"
        f"Outcome: {entry.outcome}\n"
        f"Score: {score_str}\n"
        f"What was learned: {entry.learned}\n"
        f"Mistakes: {entry.mistakes}\n"
        f"Next recommendation: {entry.next_recommendation}\n"
    )
    return markdown_store.append_text_safely(log_path, content)

def update_roadmap_item_status(repo_path: Path, update: RoadmapItemUpdate) -> bool:
    roadmap_path = repo_path / "roadmap.md"
    content = markdown_store.read_text_safely(roadmap_path)
    if content is None:
        return False
    
    lines = content.split('\n')
    found_item = False
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('### ') and update.id in line:
            found_item = True
            continue
        
        if found_item and line.startswith('### '):
            break
            
        if found_item and line.startswith('Status:'):
            lines[i] = f"Status: {update.status}"
            updated = True
            break
            
    if updated:
        markdown_store.write_text_safely(roadmap_path, '\n'.join(lines))
        return True
    return False

def upsert_weakness(repo_path: Path, weakness: WeaknessEntry) -> bool:
    weaknesses_path = repo_path / "weaknesses.md"
    content = markdown_store.read_text_safely(weaknesses_path)
    if content is None:
        return False
        
    weakness_block = (
        f"### {weakness.id}: {weakness.topic}\n"
        f"Topic: {weakness.topic}\n"
        f"Source: {weakness.source}\n"
        f"Observed On: {weakness.observed_on}\n"
        f"Severity: {weakness.severity}\n"
        f"Evidence: {weakness.evidence}\n"
        f"Recommended Practice: {weakness.recommended_practice}\n"
        f"Status: {weakness.status}\n"
    )

    lines = content.split('\n')
    found_item = False
    start_idx = -1
    end_idx = -1
    
    for i, line in enumerate(lines):
        if line.startswith(f"### {weakness.id}"):
            found_item = True
            start_idx = i
            continue
            
        if found_item and line.startswith('### '):
            end_idx = i
            break
            
    if found_item:
        if end_idx == -1:
            end_idx = len(lines)
        lines = lines[:start_idx] + weakness_block.strip().split('\n') + lines[end_idx:]
        markdown_store.write_text_safely(weaknesses_path, '\n'.join(lines))
    else:
        markdown_store.append_text_safely(weaknesses_path, "\n" + weakness_block)
        
    return True
