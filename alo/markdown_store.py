from pathlib import Path
from typing import Optional

def read_text_safely(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None

def write_text_safely(path: Path, content: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception:
        return False

def append_text_safely(path: Path, content: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception:
        return False

def create_if_missing(path: Path, template: str) -> bool:
    if path.exists():
        return False
    return write_text_safely(path, template)

def file_exists(path: Path) -> bool:
    return path.exists()
