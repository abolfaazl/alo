from pathlib import Path
from datetime import date, timedelta
import re

from alo.models.stats import LearningStats
from alo import markdown_store

def parse_progress_log(content: str) -> dict:
    """
    Parses progress-log.md content.
    Returns a dict with:
    - active_dates: set of date objects
    - lessons_completed: int
    - reviews_completed: int
    - practice_sessions: int
    """
    active_dates = set()
    lessons = 0
    reviews = 0
    practices = 0

    # Split by entry. Entries usually start with ## date or ## [date]
    # We will just look line by line.
    current_date = None
    
    # Regex to extract YYYY-MM-DD from any line
    date_regex = re.compile(r"((?:19|20)\d\d)-(0[1-9]|1[012])-(0[1-9]|[12][0-9]|3[01])")
    
    for line in content.splitlines():
        line_lower = line.lower()
        
        # Detect dates in headings
        if line.startswith("## "):
            match = date_regex.search(line)
            if match:
                try:
                    current_date = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                except ValueError:
                    pass
        
        if current_date:
            # We are in an entry. Check for keywords.
            # Only count if the keyword is in a heading or session line to be conservative, 
            # or just anywhere in the entry? Prompt says "lines/headings containing..."
            
            # To avoid double counting, we'll keep track of what we counted for this entry?
            # Actually, let's just count occurrences. 
            # But the prompt says "try to detect lesson entries, review entries, practice entries".
            # We'll count one per matched heading/session line.
            
            if line_lower.startswith("### session:"):
                if "lesson" in line_lower or "learn" in line_lower:
                    lessons += 1
                    active_dates.add(current_date)
                elif "review" in line_lower:
                    reviews += 1
                    active_dates.add(current_date)
                elif "practice" in line_lower or "assessment" in line_lower:
                    practices += 1
                    active_dates.add(current_date)

    return {
        "active_dates": active_dates,
        "lessons_completed": lessons,
        "reviews_completed": reviews,
        "practice_sessions": practices
    }

def calculate_streaks(active_dates: set, today: date) -> tuple[int, int]:
    """
    Returns (current_streak, longest_streak)
    """
    if not active_dates:
        return 0, 0

    sorted_dates = sorted(list(active_dates))
    longest = 1
    
    # Calculate longest
    temp_streak = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
            temp_streak += 1
        else:
            if temp_streak > longest:
                longest = temp_streak
            temp_streak = 1
    if temp_streak > longest:
        longest = temp_streak

    # Calculate current streak ending today or yesterday
    current_streak = 0
    check_date = today
    if check_date not in active_dates:
        check_date = today - timedelta(days=1)
        
    if check_date in active_dates:
        current_streak = 1
        while (check_date - timedelta(days=1)) in active_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

    return current_streak, longest

def parse_roadmap_progress(content: str) -> tuple[int, int]:
    """
    Returns (total_items, completed_items)
    """
    total = 0
    completed = 0
    has_checkboxes = False
    
    for line in content.splitlines():
        if "- [x]" in line.lower():
            completed += 1
            total += 1
            has_checkboxes = True
        elif "- [ ]" in line:
            total += 1
            has_checkboxes = True
            
    if not has_checkboxes:
        # Prompt explicitly says: If no checkboxes exist, completion should be 0, not guessed.
        return 0, 0
        
    return total, completed

def parse_weaknesses(content: str) -> tuple[int, int]:
    """
    Returns (open_weaknesses, resolved_weaknesses)
    """
    open_w = 0
    resolved_w = 0
    has_status = False

    for line in content.splitlines():
        if line.startswith("Status:"):
            has_status = True
            status_val = line.split(":", 1)[1].strip().lower()
            if status_val in ["open", "active", "improving"]:
                open_w += 1
            elif status_val in ["resolved", "closed", "passed", "mastered"]:
                resolved_w += 1
                
    if not has_status:
        return 0, 0
        
    return open_w, resolved_w

def calculate_consistency_score(current_streak: int, active_days: int, reviews: int) -> float:
    score = current_streak * 10 + active_days * 2 + reviews * 1
    return float(min(100, round(score)))

def compute_learning_stats(workspace_path: Path, today: date | None = None) -> LearningStats:
    if today is None:
        today = date.today()
        
    warnings = []
    
    # 1. Progress Log
    prog_log_path = workspace_path / "progress-log.md"
    active_dates = set()
    lessons = 0
    reviews = 0
    practices = 0
    
    if prog_log_path.exists():
        content = markdown_store.read_text_safely(prog_log_path)
        if content:
            parsed_prog = parse_progress_log(content)
            active_dates = parsed_prog["active_dates"]
            lessons = parsed_prog["lessons_completed"]
            reviews = parsed_prog["reviews_completed"]
            practices = parsed_prog["practice_sessions"]
    else:
        warnings.append("progress-log.md not found")

    # 2. Roadmap
    roadmap_path = workspace_path / "roadmap.md"
    total_roadmap = 0
    completed_roadmap = 0
    if roadmap_path.exists():
        content = markdown_store.read_text_safely(roadmap_path)
        if content:
            total_roadmap, completed_roadmap = parse_roadmap_progress(content)
            if total_roadmap == 0 and completed_roadmap == 0 and "### " in content:
                warnings.append("Roadmap format unknown (no checkboxes found)")
    else:
        warnings.append("roadmap.md not found")
        
    # 3. Weaknesses
    weaknesses_path = workspace_path / "weaknesses.md"
    open_weaknesses = 0
    resolved_weaknesses = 0
    if weaknesses_path.exists():
        content = markdown_store.read_text_safely(weaknesses_path)
        if content:
            open_weaknesses, resolved_weaknesses = parse_weaknesses(content)
            if open_weaknesses == 0 and resolved_weaknesses == 0 and "### " in content:
                warnings.append("Weaknesses format unknown (no status markers found)")
    else:
        warnings.append("weaknesses.md not found")

    # Computations
    current_streak, longest_streak = calculate_streaks(active_dates, today)
    active_learning_days = len(active_dates)
    
    roadmap_percent = 0.0
    if total_roadmap > 0:
        roadmap_percent = round((completed_roadmap / total_roadmap) * 100, 2)
        
    # Lessons per day/week
    lessons_per_day = 0.0
    lessons_per_week = 0.0
    if active_learning_days > 0:
        lessons_per_day = round(lessons / active_learning_days, 2)
        # Approximate weeks
        weeks = max(1.0, active_learning_days / 7.0)
        lessons_per_week = round(lessons / weeks, 2)
        
    review_frequency = 0.0
    if active_learning_days > 0:
        review_frequency = round(reviews / active_learning_days, 2)
        
    consistency = calculate_consistency_score(current_streak, active_learning_days, reviews)

    return LearningStats(
        workspace_path=str(workspace_path),
        lessons_completed=lessons,
        reviews_completed=reviews,
        practice_sessions=practices,
        active_learning_days=active_learning_days,
        current_streak_days=current_streak,
        longest_streak_days=longest_streak,
        lessons_per_day=lessons_per_day,
        lessons_per_week=lessons_per_week,
        review_frequency=review_frequency,
        roadmap_total_items=total_roadmap,
        roadmap_completed_items=completed_roadmap,
        roadmap_completion_percent=roadmap_percent,
        weaknesses_open=open_weaknesses,
        weaknesses_resolved=resolved_weaknesses,
        consistency_score=consistency,
        warnings=warnings
    )
