from pathlib import Path
from typing import List

from alo.models import (
    RoadmapItemUpdate, 
    ProgressLogEntry, 
    WeaknessEntry, 
    StateFileStatus, 
    StateSummary,
    OnboardingProfile,
    AssessmentResult
)
from alo import markdown_store

REQUIRED_FILES = {
    "README.md": "# ALO Learning Repository\n\nThis is a learning repository managed by ALO (Agentic Learning OS).\n",
    "learning-profile.md": """# Learning Profile

## Learning Project

Subject:
Target Goal:
Current Level:
Known Background:
Preferred Language:
Started On:

## Current Level Summary

## Declared Knowledge

## Assessment Summary

Not assessed yet.

## Goals

## Learning Goal Mode

## Preferred Learning Style

## Time Commitment

## Constraints

## Privacy Preference

## Last Updated
""",
    "skill-map.md": """# Skill Map

## Subject Skill Areas

### Area 1: To be determined
Level: self-reported / unknown
Confidence: unverified
Evidence:
Status:

## General Learning Skills

### Study Consistency
Level: unknown
Confidence: unverified
Evidence:
Status:

### Practice and Recall
Level: unknown
Confidence: unverified
Evidence:
Status:

### Feedback Handling
Level: unknown
Confidence: unverified
Evidence:
Status:

## Assessment Evidence

Not assessed yet.
""",
    "learning-paths.md": """# Learning Paths

## Current Recommendations
""",
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

def get_active_weaknesses(repo_path: Path) -> list:
    weaknesses_path = repo_path / "weaknesses.md"
    content = markdown_store.read_text_safely(weaknesses_path)
    if not content:
        return []
    
    import re
    blocks = re.split(r"(?=### ALO-WK-\w+)", content)
    active = []
    for block in blocks:
        if not block.startswith("### ALO-WK-"):
            continue
        status_match = re.search(r"Status:\s*(.*)", block)
        if status_match:
            status = status_match.group(1).strip().lower()
            if status in ["open", "active", "improving"]:
                id_match = re.search(r"### (ALO-WK-[^\:]+)", block)
                if id_match:
                    active.append({"id": id_match.group(1).strip(), "content": block.strip()})
    return active

def get_weakness_by_id(repo_path: Path, weakness_id: str) -> dict | None:
    weaknesses_path = repo_path / "weaknesses.md"
    content = markdown_store.read_text_safely(weaknesses_path)
    if not content:
        return None
    import re
    blocks = re.split(r"(?=### ALO-WK-\w+)", content)
    for block in blocks:
        if block.startswith(f"### {weakness_id}"):
            return {"id": weakness_id, "content": block.strip()}
    return None

def update_weakness_status(repo_path: Path, weakness_id: str, status: str, last_reviewed: str = "", review_result: str = "") -> bool:
    weaknesses_path = repo_path / "weaknesses.md"
    content = markdown_store.read_text_safely(weaknesses_path)
    if not content:
        return False
    
    lines = content.split('\n')
    found_item = False
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"### {weakness_id}"):
            found_item = True
            continue
        
        if found_item and line.startswith('### '):
            break
            
        if found_item and line.startswith('Status:'):
            lines[i] = f"Status: {status}"
            if last_reviewed and review_result:
                lines.insert(i + 1, f"Review Result: {review_result}")
                lines.insert(i + 1, f"Last Reviewed: {last_reviewed}")
            updated = True
            break
            
    if updated:
        markdown_store.write_text_safely(weaknesses_path, '\n'.join(lines))
        return True
    return False

def get_roadmap_review_targets(repo_path: Path) -> list:
    rm_path = repo_path / "roadmap.md"
    content = markdown_store.read_text_safely(rm_path)
    if not content:
        return []
    import re
    blocks = re.split(r"(?=### ALO-RM-\d+)", content)
    
    targets = []
    # priorities: 1. needs_review, 2. practiced
    for status_target in ["needs_review", "practiced"]:
        for block in blocks:
            if not block.startswith("### ALO-RM-"):
                continue
            match = re.search(r"Status: ([a-z_]+)", block)
            if match and match.group(1) == status_target:
                id_match = re.search(r"### (ALO-RM-\d+)", block)
                if id_match:
                    targets.append({"id": id_match.group(1).strip(), "content": block.strip()})
    return targets

def append_review_progress(repo_path: Path, eval_result, target_title: str):
    msg = (
        f"Outcome: {eval_result.result}\n"
        f"Score: {eval_result.score}\n"
        f"What was reviewed: {target_title}\n"
        f"Remaining gaps: {eval_result.remaining_gaps}\n"
        f"Next recommendation: {eval_result.recommended_next_step}"
    )
    _append_to_progress_log(repo_path, f"Review — {target_title}", msg)

def has_user_content(file_path: Path, default_template: str) -> bool:
    content = markdown_store.read_text_safely(file_path)
    if not content:
        return False
    return content.strip() != default_template.strip()

def build_learning_profile_markdown(profile: OnboardingProfile) -> str:
    privacy_text = "May store private details." if profile.privacy_preference.value == "store" else "Private identifiers should be generalized."
    return f"""# Learning Profile

## Learning Project

Subject: {profile.subject}
Target Goal: {profile.goal}
Current Level: {profile.experience_level.value}
Known Background: {profile.background}
Preferred Language: English
Started On: {profile.date}

## Current Level Summary
{profile.experience_level.value}

## Declared Knowledge
{profile.background}

## Assessment Summary

Not assessed yet.

## Goals
{profile.goal}

## Learning Goal Mode
Unknown

## Preferred Learning Style
Unknown

## Time Commitment
Unknown

## Constraints
None

## Privacy Preference
{privacy_text}

## Last Updated
{profile.date}
"""

def build_skill_map_markdown(profile: OnboardingProfile) -> str:
    return """# Skill Map

## Subject Skill Areas

### Area 1: To be determined
Level: self-reported / unknown
Confidence: unverified
Evidence: Declared in onboarding
Status:

## General Learning Skills

### Study Consistency
Level: unknown
Confidence: unverified
Evidence:
Status:

### Practice and Recall
Level: unknown
Confidence: unverified
Evidence:
Status:

### Feedback Handling
Level: unknown
Confidence: unverified
Evidence:
Status:

## Assessment Evidence

Not assessed yet.
"""

def save_onboarding_profile(repo_path: Path, profile: OnboardingProfile, overwrite: bool = False):
    lp_path = repo_path / "learning-profile.md"
    sm_path = repo_path / "skill-map.md"
    
    lp_content = build_learning_profile_markdown(profile)
    sm_content = build_skill_map_markdown(profile)
    
    if overwrite or not markdown_store.file_exists(lp_path):
        markdown_store.write_text_safely(lp_path, lp_content)
    if overwrite or not markdown_store.file_exists(sm_path):
        markdown_store.write_text_safely(sm_path, sm_content)
        
    if profile.privacy_preference.value == "generalize":
        pr_path = repo_path / "privacy-rules.md"
        pr_content = markdown_store.read_text_safely(pr_path) or REQUIRED_FILES["privacy-rules.md"]
        if "generalized" not in pr_content:
            pr_content += "\nNote: Private identifiers should be generalized.\n"
            markdown_store.write_text_safely(pr_path, pr_content)

def append_onboarding_progress(repo_path: Path, profile: OnboardingProfile):
    log_path = repo_path / "progress-log.md"
    content = f"""\n## {profile.date}\n
### Session: Initial Onboarding
Outcome: not_evaluated
Score: N/A
What was learned:
- User completed self-report onboarding.

Mistakes:
- Not assessed yet.

Next recommendation:
- Run Phase 4 assessment when available.
"""
    markdown_store.append_text_safely(log_path, content)

def append_assessment_to_learning_profile(repo_path: Path, result: AssessmentResult) -> bool:
    lp_path = repo_path / "learning-profile.md"
    content = markdown_store.read_text_safely(lp_path)
    if not content:
        return False
        
    summary_block = f"""## Assessment Summary

Last Assessment: {result.date}
Mode: {result.mode.value}
Score: {result.score_percent}%
Level: {result.level}
Summary: Self-report plus assessment indicates {result.level}.
Strengths: {", ".join(result.strengths) if result.strengths else "None identified"}
Weaknesses: {", ".join(result.weaknesses) if result.weaknesses else "None identified"}
Recommendations: {", ".join(result.recommendations)}
"""
    
    import re
    pattern = re.compile(r"(## Assessment Summary\n.*?)(?=## Goals|#|$)", re.DOTALL)
    if pattern.search(content):
        new_content = pattern.sub(summary_block + "\n", content)
        markdown_store.write_text_safely(lp_path, new_content)
    return True

def update_skill_map_from_assessment(repo_path: Path, result: AssessmentResult) -> bool:
    sm_path = repo_path / "skill-map.md"
    content = markdown_store.read_text_safely(sm_path)
    if not content:
        return False
        
    lines = content.split('\n')
    
    for ds in result.domain_scores:
        domain_header = f"## {ds.domain}"
        found_domain = False
        start_idx = -1
        
        for i, line in enumerate(lines):
            if line.startswith(domain_header):
                found_domain = True
                start_idx = i
                break
                
        if found_domain:
            evidence_block = [
                "Assessment Evidence:",
                f"- Last assessed: {result.date}",
                f"- Score: {ds.score_percent}% ({ds.correct}/{ds.total})",
                "- Confidence: assessment-based / limited",
                ""
            ]
            
            existing_ev_start = -1
            existing_ev_end = -1
            
            for j in range(start_idx + 1, len(lines)):
                if lines[j].startswith("## "):
                    existing_ev_end = j
                    break
                if lines[j].startswith("Assessment Evidence:"):
                    existing_ev_start = j
                    
            if existing_ev_end == -1:
                existing_ev_end = len(lines)
                
            if existing_ev_start != -1:
                end_block = existing_ev_start + 1
                while end_block < existing_ev_end and (lines[end_block].startswith("- ") or lines[end_block] == ""):
                    end_block += 1
                lines = lines[:existing_ev_start] + evidence_block + lines[end_block:]
            else:
                lines = lines[:existing_ev_end] + evidence_block + lines[existing_ev_end:]
                
    markdown_store.write_text_safely(sm_path, '\n'.join(lines))
    return True

def upsert_weaknesses_from_assessment(repo_path: Path, result: AssessmentResult):
    for i, missed in enumerate(result.missed_questions):
        wid = f"ALO-WK-AS-{i:03d}"
        
        severity = "low"
        if missed.difficulty in ["advanced", "expert"]:
            severity = "medium"
            
        domain_misses = sum(1 for m in result.missed_questions if m.domain == missed.domain)
        if domain_misses > 1:
            severity = "high"
            
        weakness = WeaknessEntry(
            id=wid,
            topic=missed.weakness_topic,
            source="Assessment",
            observed_on=result.date,
            severity=severity,
            evidence=f"Missed {missed.difficulty} question in {missed.domain}: {missed.question}",
            recommended_practice="Review documentation and practice tasks.",
            status="open"
        )
        upsert_weakness(repo_path, weakness)

def save_learning_path_recommendations(repo_path: Path, paths: list):
    content = "# Learning Paths\n\n## Current Recommendations\n\n"
    for p in paths:
        content += f"### {p.id}: {p.title}\n\n"
        content += f"Summary: {p.summary}\n"
        content += f"Who it is for: {p.who_it_is_for}\n"
        content += f"Why it matches: {p.why_it_matches_user}\n"
        content += f"Expected outcome: {p.expected_outcome}\n"
        content += f"Core topics: {', '.join(p.core_topics)}\n"
        content += f"Estimated duration: {p.estimated_duration}\n"
        content += f"Difficulty: {p.difficulty}\n"
        content += f"Tradeoffs: {p.tradeoffs}\n"
        content += f"First step: {p.first_step}\n"
        content += f"Avoid for now: {p.avoid_for_now}\n"
        content += f"Confidence: {p.confidence}\n"
        content += "Status: proposed\n\n"
        
    markdown_store.write_text_safely(repo_path / "learning-paths.md", content.strip() + "\n")

def select_learning_path(repo_path: Path, selected_id: str | None):
    lp_path = repo_path / "learning-paths.md"
    content = markdown_store.read_text_safely(lp_path)
    if not content:
        return None
        
    # Mark the selected one as selected, others stay proposed
    lines = content.split('\n')
    new_lines = []
    current_id = None
    
    for line in lines:
        if line.startswith("### "):
            current_id = line.split(":")[0].replace("### ", "").strip()
        if line.startswith("Status:"):
            if current_id == selected_id:
                new_lines.append("Status: selected")
            else:
                # keep as proposed or whatever it was
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    markdown_store.write_text_safely(lp_path, "\n".join(new_lines))

def update_active_learning_path(repo_path: Path, selected_path):
    lp_path = repo_path / "learning-profile.md"
    content = markdown_store.read_text_safely(lp_path)
    if not content:
        return
    
    # Simple regex to replace Learning Goal Mode or append Active Path
    import re
    if "## Active Learning Path" not in content:
        content = re.sub(
            r"## Learning Goal Mode",
            f"## Active Learning Path\n**Active Learning Path**: {selected_path.id}\nTitle: {selected_path.title}\n\n## Learning Goal Mode",
            content
        )
    else:
        content = re.sub(
            r"## Active Learning Path\n.*?\n.*?\n",
            f"## Active Learning Path\n**Active Learning Path**: {selected_path.id}\nTitle: {selected_path.title}\n",
            content,
            flags=re.DOTALL
        )
        
    markdown_store.write_text_safely(lp_path, content)

def _append_to_progress_log(repo_path: Path, title: str, msg: str):
    from alo import markdown_store
    log_path = repo_path / "progress-log.md"
    content = markdown_store.read_text_safely(log_path)
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    new_entry = f"## [{date_str}] Session: {title}\n\n{msg}\n\n"
    
    if content:
        content = content.replace("# Progress Log\n", f"# Progress Log\n\n{new_entry}")
    else:
        content = f"# Progress Log\n\n{new_entry}"
        
    markdown_store.write_text_safely(log_path, content)

def append_paths_progress(repo_path: Path, selected_id: str | None = None):
    if not selected_id:
        msg = "- Path recommendations generated but none selected."
    else:
        msg = f"- Selected learning path: {selected_id}."
    _append_to_progress_log(repo_path, "Path Recommendations", msg)

def get_active_learning_path(repo_path: Path) -> dict | None:
    lp_path = repo_path / "learning-profile.md"
    content = markdown_store.read_text_safely(lp_path)
    if not content:
        return None
    import re
    match = re.search(r"\*\*Active Learning Path\*\*: (.+)", content)
    if not match:
        return None
    path_info = match.group(1).strip()
    return {"id": path_info} # Simplified returning the string identifier

def preserve_existing_roadmap_statuses(existing_text: str, new_roadmap) -> None:
    import re
    # Extract statuses from existing text
    # e.g., "### ALO-RM-001: Title\nStatus: practiced"
    status_map = {}
    pattern = r"### (ALO-RM-\d+)[^\n]*\nStatus: ([a-z_]+)"
    for match in re.finditer(pattern, existing_text):
        item_id = match.group(1)
        status = match.group(2)
        status_map[item_id] = status
        
    for item in new_roadmap.items:
        if item.id in status_map:
            item.status = status_map[item.id]

def save_roadmap(repo_path: Path, roadmap, active_path_info: str) -> None:
    rm_path = repo_path / "roadmap.md"
    
    # Check if we need to preserve statuses
    existing_content = markdown_store.read_text_safely(rm_path) or ""
    preserve_existing_roadmap_statuses(existing_content, roadmap)
    
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d")
    
    lines = [
        "# Roadmap",
        "",
        "## Active Path",
        "",
        f"Path ID: {active_path_info}",
        f"Generated On: {now}",
        "",
        "## Roadmap Items",
        ""
    ]
    
    for item in roadmap.items:
        lines.append(f"### {item.id}: {item.title}")
        lines.append(f"Status: {item.status}")
        lines.append(f"Level: {item.level}")
        lines.append(f"Estimated Time: {item.estimated_time}")
        lines.append(f"Depends On: {item.depends_on}")
        lines.append(f"Prerequisites: {item.prerequisites}")
        lines.append(f"Success Criteria: {item.success_criteria}")
        lines.append(f"Practice Task: {item.practice_task}")
        lines.append(f"Assessment Method: {item.assessment_method}")
        lines.append(f"Resources To Find: {item.resources_to_find}")
        lines.append(f"Summary: {item.summary}")
        lines.append("")
        
    markdown_store.write_text_safely(rm_path, "\n".join(lines))

def append_roadmap_progress(repo_path: Path):
    _append_to_progress_log(repo_path, "Roadmap Generation", "- Generated new step-by-step roadmap.")

def append_assessment_progress(repo_path: Path, result: AssessmentResult):
    log_path = repo_path / "progress-log.md"
    missed_domains = set(m.domain for m in result.missed_questions)
    missed_str = "\n".join([f"- {d}" for d in missed_domains]) if missed_domains else "- None"
    
    content = f"""\n## {result.date}\n
### Session: Assessment
Outcome: not_evaluated
Score: {result.score_percent}%
What was learned:
- Completed 20-question calibration assessment.

Mistakes:
{missed_str}

Next recommendation:
- Use results for Phase 5 learning path recommendations.
"""
    markdown_store.append_text_safely(log_path, content)

def get_next_learnable_roadmap_item(repo_path: Path) -> str | None:
    from alo import markdown_store
    import re
    rm_path = repo_path / "roadmap.md"
    content = markdown_store.read_text_safely(rm_path)
    if not content:
        return None
    
    blocks = re.split(r"(?=### ALO-RM-\d+)", content)
    
    for status_target in ["in_progress", "needs_review", "todo"]:
        for block in blocks:
            if not block.startswith("### ALO-RM-"):
                continue
            match = re.search(r"Status: ([a-z_]+)", block)
            if match and match.group(1) == status_target:
                return block.strip()
    return None

def get_roadmap_item_by_id(repo_path: Path, item_id: str) -> str | None:
    from alo import markdown_store
    import re
    rm_path = repo_path / "roadmap.md"
    content = markdown_store.read_text_safely(rm_path)
    if not content:
        return None
    blocks = re.split(r"(?=### ALO-RM-\d+)", content)
    for block in blocks:
        if block.startswith(f"### {item_id}"):
            return block.strip()
    return None

def append_learning_session_progress(repo_path: Path, eval_result, item_id: str, title: str):
    msg = (
        f"Outcome: {eval_result.result}\n"
        f"Score: {eval_result.score}\n"
        f"What was learned: {title}\n"
        f"Mistakes: {eval_result.weaknesses}\n"
        f"Next recommendation: {eval_result.recommended_next_step}"
    )
    _append_to_progress_log(repo_path, f"{item_id} — {title}", msg)

def upsert_learning_session_weaknesses(repo_path: Path, eval_result, item_id: str):
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d")
    for idx, w in enumerate(eval_result.weakness_entries):
        w_id = f"ALO-WK-{item_id}-{idx+1:02d}"
        entry = WeaknessEntry(
            id=w_id,
            topic=w.topic,
            source="Learning Session",
            observed_on=now,
            severity="medium",
            evidence=w.evidence,
            recommended_practice=w.recommended_practice,
            status="active"
        )
        upsert_weakness(repo_path, entry)

def trigger_auto_sync(repo_path: Path, action_name: str) -> bool:
    from alo.services.git_service import commit_changes, push_current_branch
    from alo.config import load_config
    
    # 1. Ensure portfolio files are updated ONLY IF they exist
    from alo.services.readme_service import write_workspace_readme
    from alo.services.chart_service import write_workspace_charts
    
    if (repo_path / "README.md").exists():
        write_workspace_readme(repo_path, include_charts=(repo_path / "charts").exists())
    if (repo_path / "charts").exists():
        write_workspace_charts(repo_path)
    
    cfg = load_config()
    commit_msg = f"alo({action_name.lower().replace(' ', '_')}): sync progress after {action_name}"
    
    success = False
    try:
        success = commit_changes(repo_path, commit_msg)
    except Exception:
        pass
        
    if success and getattr(cfg, 'auto_push', False):
        try:
            push_current_branch(repo_path)
        except Exception:
            pass
            
    return success
