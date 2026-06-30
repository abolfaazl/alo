from pathlib import Path
from pydantic import BaseModel
import re

from alo.services.stats_service import compute_learning_stats
from alo.services.git_service import is_alo_source_repo
from alo import markdown_store

class ReadmeWriteResult(BaseModel):
    written: bool
    path: str
    content: str | None = None
    message: str
    warnings: list[str] = []

def extract_subject(workspace_path: Path) -> str:
    # Try learning-profile.md
    profile_path = workspace_path / "learning-profile.md"
    if profile_path.exists():
        content = markdown_store.read_text_safely(profile_path)
        if content:
            # Subject: <value>
            match = re.search(r"^Subject:\s*(.+)$", content, re.MULTILINE)
            if match:
                return match.group(1).strip()
    
    # Try README title
    readme_path = workspace_path / "README.md"
    if readme_path.exists():
        content = markdown_store.read_text_safely(readme_path)
        if content:
            match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if match and "ALO Learning Repository" not in match.group(1):
                return match.group(1).strip()
                
    # Fallback to folder name
    return workspace_path.name

def extract_weakness_summary(workspace_path: Path) -> str:
    weaknesses_path = workspace_path / "weaknesses.md"
    if not weaknesses_path.exists():
        return "No weaknesses logged yet."
        
    content = markdown_store.read_text_safely(weaknesses_path)
    if not content:
        return "No weaknesses logged yet."
        
    # High-level summary of open weaknesses without spilling raw details.
    import re
    blocks = re.split(r"(?=### ALO-WK-\w+)", content)
    active_topics = []
    
    for block in blocks:
        if not block.startswith("### ALO-WK-"):
            continue
        status_match = re.search(r"Status:\s*(.*)", block)
        if status_match:
            status = status_match.group(1).strip().lower()
            if status in ["open", "active", "improving"]:
                # Try to grab topic
                topic_match = re.search(r"Topic:\s*(.*)", block)
                if topic_match:
                    active_topics.append(topic_match.group(1).strip())
                else:
                    # Fallback to heading
                    h_match = re.search(r"### ALO-WK-[^:]+:\s*(.*)", block)
                    if h_match:
                        active_topics.append(h_match.group(1).strip())
                        
    if not active_topics:
        return "No open weaknesses at this time."
        
    return "- " + "\n- ".join(active_topics[:5]) + ("\n- ...and more" if len(active_topics) > 5 else "")

def sanitize_content(content: str) -> str:
    """Removes secret-like strings to ensure safe rendering."""
    # List of sensitive patterns to wipe
    patterns = [
        r"sk-[a-zA-Z0-9]+",
        r"OPENAI_API_KEY=\S+",
        r"Bearer\s+\S+",
        r"api_key:\s*\S+"
    ]
    sanitized = content
    for pattern in patterns:
        sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)
    return sanitized

def generate_workspace_readme(workspace_path: Path, *, include_charts: bool = False, include_gamification: bool = False) -> str:
    subject = extract_subject(workspace_path)
    stats = compute_learning_stats(workspace_path)
    weakness_summary = extract_weakness_summary(workspace_path)
    
    roadmap_desc = "Just starting out."
    if stats.roadmap_total_items > 0:
        if stats.roadmap_completed_items == stats.roadmap_total_items:
            roadmap_desc = "Roadmap fully completed!"
        else:
            roadmap_desc = f"{stats.roadmap_completed_items} of {stats.roadmap_total_items} items completed ({stats.roadmap_completion_percent}%)."

    charts_section = ""
    if include_charts:
        charts_section = """
## Progress Overview

<img src="assets/alo-progress.svg" alt="Learning progress" />
<img src="assets/alo-practice.svg" alt="Practice volume" />
<img src="assets/alo-streak.svg" alt="Streak and consistency" />
<img src="assets/alo-roadmap.svg" alt="Roadmap completion" />
"""

    gamification_section = ""
    if include_gamification:
        from alo.services.gamification_service import compute_gamification_from_stats
        g_summary = compute_gamification_from_stats(stats)
        
        earned_badges = [b for b in g_summary.badges if b.earned]
        badges_list = ""
        if earned_badges:
            badges_list = "\n### Earned Milestones\n\n"
            for b in earned_badges:
                badges_list += f"- {b.label} — {b.description}\n"
        
        gamification_section = f"""
## Learning Momentum

| Metric | Value |
|---|---:|
| XP | {g_summary.xp} |
| Level | {g_summary.level} |
| Current streak | {g_summary.current_streak_days} days |
| Longest streak | {g_summary.longest_streak_days} days |
| Weekly goal | {g_summary.weekly_goal_progress} / {g_summary.weekly_goal_target} days |
{badges_list}"""

    content = f"""# Learning Workspace: {subject}

A local ALO learning workspace for tracking roadmap, practice, reviews, and progress.
{charts_section}{gamification_section}
## Current Snapshot

| Metric | Value |
|---|---:|
| Lessons completed | {stats.lessons_completed} |
| Reviews completed | {stats.reviews_completed} |
| Practice sessions | {stats.practice_sessions} |
| Active learning days | {stats.active_learning_days} |
| Current streak | {stats.current_streak_days} days |
| Longest streak | {stats.longest_streak_days} days |
| Roadmap completion | {stats.roadmap_completion_percent}% |
| Open weaknesses | {stats.weaknesses_open} |
| Resolved weaknesses | {stats.weaknesses_resolved} |
| Consistency score | {stats.consistency_score} / 100 |

## Learning Flow

profile → paths → roadmap → learn → review → sync

## Roadmap Progress

{roadmap_desc}

## Current Weaknesses

{weakness_summary}

## Workspace Files

| File | Purpose |
|---|---|
| learning-profile.md | High-level goals, subject, and configuration. |
| skill-map.md | Verified knowledge and skill areas. |
| roadmap.md | Active step-by-step learning path. |
| progress-log.md | Chronological journal of all sessions and activities. |
| weaknesses.md | Detected gaps and areas needing review. |

## Generated by ALO

Generated locally from Markdown files.
No cloud dashboard.
No tracking pixel.
No external stats service.
"""
    return sanitize_content(content)

def write_workspace_readme(
    workspace_path: Path,
    *,
    output_path: Path | None = None,
    force: bool = False,
    include_charts: bool = False,
    include_gamification: bool = False,
) -> ReadmeWriteResult:
    if is_alo_source_repo(workspace_path):
        return ReadmeWriteResult(
            written=False,
            path="",
            message="Cannot generate README in the ALO source repository.",
            warnings=[]
        )
        
    profile_path = workspace_path / "learning-profile.md"
    if not profile_path.exists():
        return ReadmeWriteResult(
            written=False,
            path="",
            message="Not an ALO workspace. Missing learning-profile.md. Run `alo init` first.",
            warnings=[]
        )

    target_path = output_path if output_path else workspace_path / "README.md"
    
    # Pre-flight check for charts
    from alo.services.chart_service import write_workspace_charts, generate_workspace_charts
    
    if target_path.exists() and not force:
        return ReadmeWriteResult(
            written=False,
            path=str(target_path),
            message="README.md already exists. Use --force to overwrite or --dry-run to preview.",
            warnings=[]
        )

    if include_charts and not force:
        charts_data = generate_workspace_charts(workspace_path)
        for name in charts_data.keys():
            if (workspace_path / "assets" / name).exists():
                return ReadmeWriteResult(
                    written=False,
                    path=str(target_path),
                    message=f"Chart asset {name} already exists. Use --force to overwrite.",
                    warnings=[]
                )

    content = generate_workspace_readme(workspace_path, include_charts=include_charts, include_gamification=include_gamification)
    
    try:
        markdown_store.write_text_safely(target_path, content)
        
        if include_charts:
            write_workspace_charts(workspace_path, force=force)
            
        return ReadmeWriteResult(
            written=True,
            path=str(target_path),
            content=content,
            message="Successfully generated workspace README.",
            warnings=[]
        )
    except Exception as e:
        return ReadmeWriteResult(
            written=False,
            path=str(target_path),
            message=f"Failed to write README: {e}",
            warnings=[]
        )
