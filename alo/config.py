import json
from pathlib import Path
from pydantic import BaseModel, model_validator
from typing import Optional

class AloConfig(BaseModel):
    llm_provider: str = "openai"
    model: str = "gpt-4o-mini"
    base_url: Optional[str] = None
    api_key_env_var: str = "OPENAI_API_KEY"
    default_language: str = "en"
    safe_mode: bool = True
    auto_push: bool = False
    
    @model_validator(mode='after')
    def validate_base_url(self) -> 'AloConfig':
        if self.llm_provider == "openai-compatible" and not self.base_url:
            raise ValueError("base_url is required when llm_provider is openai-compatible")
        return self

def get_config_dir() -> Path:
    return Path.home() / ".alo"

def get_config_path() -> Path:
    return get_config_dir() / "config.json"

def config_exists() -> bool:
    return get_config_path().exists()

def load_config() -> AloConfig:
    path = get_config_path()
    if not path.exists():
        return AloConfig()
    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        return AloConfig(**data)
    except Exception:
        return AloConfig()

def save_config(config: AloConfig) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.model_dump_json(indent=2), encoding="utf-8")
