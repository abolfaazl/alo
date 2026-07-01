import os
import re
import urllib.parse
from pathlib import Path
from datetime import datetime
from typing import Optional

from alo.config import load_config, AloConfig

def is_obsidian_enabled(cfg: Optional[AloConfig] = None) -> bool:
    if cfg is None:
        cfg = load_config()
    return cfg.obsidian.enabled and bool(cfg.obsidian.vault_path)

def get_vault_path(cfg: Optional[AloConfig] = None) -> Optional[Path]:
    if cfg is None:
        cfg = load_config()
    if not is_obsidian_enabled(cfg):
        return None
    p = Path(cfg.obsidian.vault_path)
    if not p.exists() or not p.is_dir():
        return None
    return p

def get_alo_folder_path(cfg: Optional[AloConfig] = None) -> Optional[Path]:
    vault = get_vault_path(cfg)
    if not vault:
        return None
    if cfg is None:
        cfg = load_config()
    return vault / cfg.obsidian.folder

def sanitize_filename(name: str) -> str:
    # Remove invalid characters for Windows/Mac/Linux but preserve Unicode (e.g. Persian)
    # Invalid on Windows: < > : " / \ | ? *
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
    # Strip leading/trailing spaces and dots
    return sanitized.strip('. ')

def _merge_content(file_path: Path, new_content: str, begin_marker: str, end_marker: str) -> str:
    if not file_path.exists():
        return f"{begin_marker}\n{new_content}\n{end_marker}\n"
    
    existing = file_path.read_text(encoding="utf-8")
    pattern = re.compile(f"{re.escape(begin_marker)}.*?{re.escape(end_marker)}", re.DOTALL)
    
    replacement = f"{begin_marker}\n{new_content}\n{end_marker}"
    
    if pattern.search(existing):
        return pattern.sub(replacement, existing)
    else:
        # Append to the end if markers aren't found
        if not existing.endswith("\n"):
            existing += "\n"
        return existing + f"\n{replacement}\n"

def update_dashboard(cfg: Optional[AloConfig] = None, latest_lesson: Optional[str] = None, latest_practice: Optional[str] = None, active_path: Optional[str] = None):
    folder = get_alo_folder_path(cfg)
    if not folder:
        return
        
    try:
        folder.mkdir(parents=True, exist_ok=True)
        dash_path = folder / "Dashboard.md"
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        content_lines = []
        if latest_lesson:
            content_lines.append(f"- Latest lesson: {latest_lesson}")
        else:
            content_lines.append("- Latest lesson: N/A")
            
        if latest_practice:
            content_lines.append(f"- Latest practice result: {latest_practice}")
        else:
            content_lines.append("- Latest practice result: N/A")
            
        if active_path:
            content_lines.append(f"- Current path/roadmap if available: {active_path}")
        else:
            content_lines.append("- Current path/roadmap if available: N/A")
            
        content_lines.append(f"- Last updated: {now}")
        
        new_content = "\n".join(content_lines)
        
        if not dash_path.exists():
            dash_path.write_text("# ALO Dashboard\n\n", encoding="utf-8")
            
        merged = _merge_content(
            dash_path,
            new_content,
            "<!-- ALO:BEGIN generated -->",
            "<!-- ALO:END generated -->"
        )
        dash_path.write_text(merged, encoding="utf-8")
    except Exception as e:
        # Fail softly
        print(f"[yellow]Warning: Failed to update Obsidian Dashboard: {e}[/yellow]")

def export_lesson(item_id: str, title: str, path_name: str, lesson_content: str, cfg: Optional[AloConfig] = None) -> Optional[Path]:
    folder = get_alo_folder_path(cfg)
    if not folder:
        return None
        
    try:
        safe_title = sanitize_filename(title)
        safe_path = sanitize_filename(path_name)
        
        course_dir = folder / "Courses" / safe_path
        course_dir.mkdir(parents=True, exist_ok=True)
        
        # Use item_id for uniqueness if we can't extract a number, but let's just make it look like "Lesson 001 - Title.md"
        # Since we don't strictly have a number, we use the item_id as the prefix
        file_name = f"{item_id} - {safe_title}.md"
        file_path = course_dir / file_name
        
        frontmatter = f"""---
alo_type: lesson
lesson_id: {item_id}
path: "{safe_path}"
practice_status: pending
generated_by: alo
---
"""

        header = f"# {item_id} — {title}\n\n"
        
        # Write lesson block
        lesson_block = f"<!-- ALO:BEGIN lesson -->\n{lesson_content}\n<!-- ALO:END lesson -->"
        
        practice_block = """
## Practice

Practice is handled inside ALO.

Run:

```bash
alo learn
```
"""
        
        if not file_path.exists():
            file_path.write_text(frontmatter + header + lesson_block + practice_block, encoding="utf-8")
        else:
            merged = _merge_content(file_path, lesson_content, "<!-- ALO:BEGIN lesson -->", "<!-- ALO:END lesson -->")
            file_path.write_text(merged, encoding="utf-8")
            
        update_dashboard(cfg=cfg, latest_lesson=file_name, active_path=safe_path)
            
        return file_path
    except Exception as e:
        print(f"[yellow]Warning: Failed to export lesson to Obsidian: {e}[/yellow]")
        return None

def export_practice_result(item_id: str, title: str, path_name: str, status: str, score: int, strengths: list[str], weaknesses: list[str], cfg: Optional[AloConfig] = None):
    if cfg is None:
        cfg = load_config()
    if not cfg.obsidian.export_practice_results:
        return
        
    folder = get_alo_folder_path(cfg)
    if not folder:
        return
        
    try:
        # Append to Practice Log
        log_path = folder / "Practice Log.md"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        str_s = ", ".join(strengths) if strengths else "None"
        str_w = ", ".join(weaknesses) if weaknesses else "None"
        
        log_entry = f"## {now} — {item_id}: {title}\n- Status: {status}\n- Score: {score}\n- Strengths: {str_s}\n- Weaknesses: {str_w}\n\n"
        
        if not log_path.exists():
            log_path.write_text("# Practice Log\n\n" + log_entry, encoding="utf-8")
        else:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
                
        # Append to lesson file
        safe_title = sanitize_filename(title)
        safe_path = sanitize_filename(path_name)
        course_dir = folder / "Courses" / safe_path
        file_name = f"{item_id} - {safe_title}.md"
        file_path = course_dir / file_name
        
        if file_path.exists():
            result_content = f"## Practice Result\n\n- Status: {status}\n- Score: {score}\n- Strengths: {str_s}\n- Weaknesses: {str_w}\n"
            merged = _merge_content(file_path, result_content, "<!-- ALO:BEGIN practice-result -->", "<!-- ALO:END practice-result -->")
            file_path.write_text(merged, encoding="utf-8")
            
        update_dashboard(cfg=cfg, latest_practice=f"{item_id} ({score}%)")
        
    except Exception as e:
        print(f"[yellow]Warning: Failed to export practice result to Obsidian: {e}[/yellow]")

def auto_open_file(file_path: Path, cfg: Optional[AloConfig] = None):
    if cfg is None:
        cfg = load_config()
        
    if not cfg.obsidian.auto_open_lesson:
        return
        
    vault = get_vault_path(cfg)
    if not vault:
        return
        
    try:
        # Attempt to use obsidian:// URI
        # Need vault name (the folder name) and relative file path
        vault_name = vault.name
        rel_path = file_path.relative_to(vault).as_posix()
        
        # URL encode components
        encoded_vault = urllib.parse.quote(vault_name)
        encoded_file = urllib.parse.quote(rel_path)
        
        uri = f"obsidian://open?vault={encoded_vault}&file={encoded_file}"
        
        # Startfile works on Windows for URIs. On mac/linux, use open/xdg-open
        if os.name == 'nt':
            os.startfile(uri)
        else:
            import subprocess
            cmd = 'open' if os.sys.platform == 'darwin' else 'xdg-open'
            subprocess.Popen([cmd, uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
    except Exception as e:
        print(f"[yellow]Warning: Could not auto-open Obsidian: {e}[/yellow]")
