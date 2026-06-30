import html
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, List

from alo.models.stats import LearningStats
from alo.services.stats_service import compute_learning_stats
from alo.services.git_service import is_alo_source_repo
from alo.services.readme_service import extract_subject, sanitize_content

class ChartWriteResult(BaseModel):
    written: bool
    output_dir: str
    files: List[str] = []
    message: str
    warnings: List[str] = []

def escape_svg_text(text: str) -> str:
    """Escapes special characters for safe SVG insertion."""
    if not text:
        return ""
    # Use python's built-in html.escape which handles &, <, >, ", '
    escaped = html.escape(str(text), quote=True)
    # Also sanitize for secrets just in case
    return sanitize_content(escaped)

def generate_progress_svg(stats: LearningStats) -> str:
    subject = escape_svg_text(stats.subject or "Learning")
    
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" style="background:#1e1e1e; font-family:sans-serif; border-radius:8px;">
    <text x="20" y="30" fill="#ffffff" font-size="16" font-weight="bold">Overall Progress: {subject}</text>
    
    <text x="20" y="70" fill="#a0a0a0" font-size="14">Lessons Completed:</text>
    <text x="180" y="70" fill="#4ade80" font-size="14" font-weight="bold">{stats.lessons_completed}</text>
    
    <text x="20" y="100" fill="#a0a0a0" font-size="14">Reviews Completed:</text>
    <text x="180" y="100" fill="#60a5fa" font-size="14" font-weight="bold">{stats.reviews_completed}</text>
    
    <text x="20" y="130" fill="#a0a0a0" font-size="14">Practice Sessions:</text>
    <text x="180" y="130" fill="#f472b6" font-size="14" font-weight="bold">{stats.practice_sessions}</text>
    
    <text x="20" y="160" fill="#a0a0a0" font-size="14">Active Days:</text>
    <text x="180" y="160" fill="#fbbf24" font-size="14" font-weight="bold">{stats.active_learning_days}</text>
    
    <rect x="250" y="60" width="120" height="100" fill="#2d2d2d" rx="4" />
    <text x="310" y="100" fill="#a0a0a0" font-size="12" text-anchor="middle">Consistency</text>
    <text x="310" y="135" fill="#ffffff" font-size="28" font-weight="bold" text-anchor="middle">{int(stats.consistency_score)}</text>
</svg>"""

def generate_practice_svg(stats: LearningStats) -> str:
    max_val = max(1, stats.lessons_completed, stats.practice_sessions, stats.reviews_completed)
    w_lesson = int((stats.lessons_completed / max_val) * 200)
    w_practice = int((stats.practice_sessions / max_val) * 200)
    w_review = int((stats.reviews_completed / max_val) * 200)
    
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="400" height="160" style="background:#1e1e1e; font-family:sans-serif; border-radius:8px;">
    <text x="20" y="30" fill="#ffffff" font-size="16" font-weight="bold">Practice &amp; Review Volume</text>
    
    <text x="20" y="65" fill="#a0a0a0" font-size="12">Lessons</text>
    <rect x="80" y="55" width="{max(1, w_lesson)}" height="12" fill="#4ade80" rx="2" />
    <text x="{90 + w_lesson}" y="65" fill="#ffffff" font-size="12">{stats.lessons_completed}</text>
    
    <text x="20" y="95" fill="#a0a0a0" font-size="12">Practice</text>
    <rect x="80" y="85" width="{max(1, w_practice)}" height="12" fill="#f472b6" rx="2" />
    <text x="{90 + w_practice}" y="95" fill="#ffffff" font-size="12">{stats.practice_sessions}</text>
    
    <text x="20" y="125" fill="#a0a0a0" font-size="12">Reviews</text>
    <rect x="80" y="115" width="{max(1, w_review)}" height="12" fill="#60a5fa" rx="2" />
    <text x="{90 + w_review}" y="125" fill="#ffffff" font-size="12">{stats.reviews_completed}</text>
</svg>"""

def generate_streak_svg(stats: LearningStats) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="400" height="120" style="background:#1e1e1e; font-family:sans-serif; border-radius:8px;">
    <text x="20" y="30" fill="#ffffff" font-size="16" font-weight="bold">Learning Streak</text>
    
    <rect x="20" y="50" width="110" height="50" fill="#2d2d2d" rx="4" />
    <text x="75" y="70" fill="#a0a0a0" font-size="12" text-anchor="middle">Current</text>
    <text x="75" y="92" fill="#fb923c" font-size="20" font-weight="bold" text-anchor="middle">{stats.current_streak_days} <tspan font-size="12" font-weight="normal" fill="#a0a0a0">days</tspan></text>
    
    <rect x="145" y="50" width="110" height="50" fill="#2d2d2d" rx="4" />
    <text x="200" y="70" fill="#a0a0a0" font-size="12" text-anchor="middle">Longest</text>
    <text x="200" y="92" fill="#fbbf24" font-size="20" font-weight="bold" text-anchor="middle">{stats.longest_streak_days} <tspan font-size="12" font-weight="normal" fill="#a0a0a0">days</tspan></text>
    
    <rect x="270" y="50" width="110" height="50" fill="#2d2d2d" rx="4" />
    <text x="325" y="70" fill="#a0a0a0" font-size="12" text-anchor="middle">Active</text>
    <text x="325" y="92" fill="#34d399" font-size="20" font-weight="bold" text-anchor="middle">{stats.active_learning_days} <tspan font-size="12" font-weight="normal" fill="#a0a0a0">days</tspan></text>
</svg>"""

def generate_roadmap_svg(stats: LearningStats) -> str:
    if stats.roadmap_total_items == 0:
        return """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="100" style="background:#1e1e1e; font-family:sans-serif; border-radius:8px;">
    <text x="20" y="30" fill="#ffffff" font-size="16" font-weight="bold">Roadmap Completion</text>
    <text x="20" y="65" fill="#a0a0a0" font-size="14">No roadmap items yet</text>
</svg>"""

    bar_width = 360
    fill_width = int((stats.roadmap_completed_items / stats.roadmap_total_items) * bar_width)
    
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="400" height="100" style="background:#1e1e1e; font-family:sans-serif; border-radius:8px;">
    <text x="20" y="30" fill="#ffffff" font-size="16" font-weight="bold">Roadmap Completion</text>
    <text x="380" y="30" fill="#a0a0a0" font-size="14" text-anchor="end">{stats.roadmap_completion_percent}%</text>
    
    <rect x="20" y="50" width="{bar_width}" height="16" fill="#2d2d2d" rx="8" />
    <rect x="20" y="50" width="{fill_width}" height="16" fill="#818cf8" rx="8" />
    
    <text x="200" y="85" fill="#a0a0a0" font-size="12" text-anchor="middle">{stats.roadmap_completed_items} of {stats.roadmap_total_items} items completed</text>
</svg>"""

def generate_workspace_charts(workspace_path: Path) -> Dict[str, str]:
    stats = compute_learning_stats(workspace_path)
    subject = extract_subject(workspace_path)
    stats.subject = subject
    
    return {
        "alo-progress.svg": generate_progress_svg(stats),
        "alo-practice.svg": generate_practice_svg(stats),
        "alo-streak.svg": generate_streak_svg(stats),
        "alo-roadmap.svg": generate_roadmap_svg(stats),
    }

def write_workspace_charts(
    workspace_path: Path,
    *,
    output_dir: Path | None = None,
    force: bool = False,
) -> ChartWriteResult:
    if is_alo_source_repo(workspace_path):
        return ChartWriteResult(
            written=False,
            output_dir="",
            message="Cannot generate charts in the ALO source repository.",
            warnings=[]
        )
        
    profile_path = workspace_path / "learning-profile.md"
    if not profile_path.exists():
        return ChartWriteResult(
            written=False,
            output_dir="",
            message="Not an ALO workspace. Missing learning-profile.md. Run `alo init` first.",
            warnings=[]
        )

    target_dir = output_dir if output_dir else workspace_path / "assets"
    
    try:
        target_dir = target_dir.resolve()
        workspace_path = workspace_path.resolve()
        
        # Path traversal guard
        if not str(target_dir).startswith(str(workspace_path)):
            return ChartWriteResult(
                written=False,
                output_dir=str(target_dir),
                message="Cannot write charts outside the workspace.",
                warnings=[]
            )
    except Exception as e:
         return ChartWriteResult(
            written=False,
            output_dir=str(target_dir),
            message=f"Path resolution error: {e}",
            warnings=[]
        )

    charts = generate_workspace_charts(workspace_path)
    
    if not force:
        for filename in charts.keys():
            if (target_dir / filename).exists():
                return ChartWriteResult(
                    written=False,
                    output_dir=str(target_dir),
                    message=f"{filename} already exists. Use --force to overwrite.",
                    warnings=[]
                )

    target_dir.mkdir(parents=True, exist_ok=True)
    
    written_files = []
    try:
        for filename, content in charts.items():
            file_path = target_dir / filename
            file_path.write_text(content, encoding="utf-8")
            written_files.append(str(file_path))
            
        return ChartWriteResult(
            written=True,
            output_dir=str(target_dir),
            files=written_files,
            message="Successfully generated SVG charts.",
            warnings=[]
        )
    except Exception as e:
        return ChartWriteResult(
            written=False,
            output_dir=str(target_dir),
            message=f"Failed to write SVG charts: {e}",
            warnings=[]
        )
