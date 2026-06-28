import json
from pathlib import Path
from typing import Any, Dict

def get_config_dir() -> Path:
    return Path.home() / ".alo"

def get_config_path() -> Path:
    return get_config_dir() / "config.json"

def config_exists() -> bool:
    return get_config_path().exists()

def load_config() -> Dict[str, Any]:
    path = get_config_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_config(config_data: Dict[str, Any]) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)
