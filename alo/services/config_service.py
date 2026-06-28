from dataclasses import dataclass
from typing import Optional

from alo import config as alo_config

@dataclass
class ConfigState:
    llm_provider: str = "openai"
    model: str = "gpt-4o-mini"
    base_url: Optional[str] = None
    api_key_env_var: str = "OPENAI_API_KEY"
    default_language: str = "en"
    safe_mode: bool = True
    auto_push: bool = False

def get_current_config() -> ConfigState:
    if alo_config.config_exists():
        cfg = alo_config.load_config()
        return ConfigState(
            llm_provider=cfg.llm_provider,
            model=cfg.model,
            base_url=cfg.base_url,
            api_key_env_var=cfg.api_key_env_var,
            default_language=cfg.default_language,
            safe_mode=cfg.safe_mode,
            auto_push=cfg.auto_push
        )
    return ConfigState()

def save_new_config(state: ConfigState) -> None:
    cfg = alo_config.AloConfig(
        llm_provider=state.llm_provider,
        model=state.model,
        base_url=state.base_url,
        api_key_env_var=state.api_key_env_var,
        default_language=state.default_language,
        safe_mode=state.safe_mode,
        auto_push=state.auto_push
    )
    alo_config.save_config(cfg)
