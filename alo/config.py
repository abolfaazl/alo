import json
from pathlib import Path
from pydantic import BaseModel, model_validator
from typing import Optional, Literal, List
from dataclasses import dataclass
import os

@dataclass
class ConfigItemStatus:
    key: str
    label: str
    required: bool
    status: Literal["configured", "missing", "warning", "optional"]
    safe_value: str
    message: Optional[str] = None

@dataclass
class ConfigReadiness:
    llm_ready: bool
    next_required_key: Optional[str]
    missing_required: List[ConfigItemStatus]
    warnings: List[ConfigItemStatus]
    items: List[ConfigItemStatus]

class AloConfig(BaseModel):
    llm_provider: str = "openai"
    model: str = "gpt-4o-mini"
    base_url: Optional[str] = None
    api_key_storage: str = "keyring"
    api_key_name: Optional[str] = "ALO_OPENAI_COMPATIBLE_API_KEY"
    api_key_env_var: Optional[str] = None
    default_language: str = "en"
    safe_mode: bool = True
    auto_push: bool = False
    
    @model_validator(mode='before')
    @classmethod
    def migrate_legacy(cls, data: dict) -> dict:
        # If storage is missing but env var is present, this is a legacy config
        if "api_key_storage" not in data and "api_key_env_var" in data and data["api_key_env_var"]:
            data["api_key_storage"] = "env"
        return data

    @model_validator(mode='after')
    def validate_base_url_and_state(self) -> 'AloConfig':
        if self.llm_provider == "openai" and self.base_url and self.base_url.strip():
            self.llm_provider = "openai-compatible"
            
        if self.llm_provider == "openai-compatible" and not self.base_url:
            pass # Removed ValueError to allow saving incomplete configs
            
        # Avoid conflicting state
        if self.api_key_storage == "keyring":
            self.api_key_env_var = None
            if not self.api_key_name:
                self.api_key_name = "ALO_OPENAI_COMPATIBLE_API_KEY"
        elif self.api_key_storage == "env":
            self.api_key_name = None
            if not self.api_key_env_var:
                self.api_key_env_var = "OPENAI_API_KEY"
                
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

def resolve_api_key(cfg: AloConfig) -> str:
    from alo.exceptions import MissingAPIKeyError, KeyringUnavailableError
    if cfg.api_key_storage == "keyring":
        if not cfg.api_key_name:
            raise MissingAPIKeyError("Configured API key name for keyring is missing.")
        try:
            import keyring
            api_key = keyring.get_password("alo", cfg.api_key_name)
        except Exception as e:
            raise KeyringUnavailableError(f"Secure OS keyring is unavailable. ALO cannot safely store the API key directly. Choose environment-variable mode instead. (Error: {e})")
            
        if not api_key:
            raise MissingAPIKeyError("API key is missing from OS keyring.\nRun `alo config` and save the API key again, or switch to environment-variable mode.")
        return api_key
    elif cfg.api_key_storage == "env":
        if not cfg.api_key_env_var:
            raise MissingAPIKeyError("Configured API key environment variable name is missing.")
        import os
        api_key = os.environ.get(cfg.api_key_env_var)
        if not api_key:
            raise MissingAPIKeyError(f"Configured API key environment variable '{cfg.api_key_env_var}' is not set.\nSet the variable or update `alo config`.")
        return api_key
    else:
        raise ValueError(f"Unknown api_key_storage mode: {cfg.api_key_storage}")

def validate_config_readiness(config: AloConfig) -> ConfigReadiness:
    items = []
    
    # 1. Provider
    prov_status = "configured" if config.llm_provider else "missing"
    items.append(ConfigItemStatus(
        key="llm_provider",
        label="LLM Provider",
        required=True,
        status=prov_status,
        safe_value=config.llm_provider if config.llm_provider else "Missing"
    ))
    
    # 2. Model
    model_status = "configured" if config.model else "missing"
    items.append(ConfigItemStatus(
        key="model",
        label="Model",
        required=True,
        status=model_status,
        safe_value=config.model if config.model else "Missing"
    ))
    
    # 3. Base URL
    base_url_req = (config.llm_provider == "openai-compatible")
    if base_url_req:
        bu_status = "configured" if config.base_url else "missing"
        bu_safe = config.base_url if config.base_url else "Missing"
    else:
        bu_status = "optional" if config.base_url else "configured" # It's configured if we don't need it or if it is optional
        # Let's use "optional" if it's there but not required, but actually the prompt says:
        bu_status = "optional"
        if not config.llm_provider:
            bu_safe = "Not required until provider is selected"
        else:
            bu_safe = "not required for this provider" if not config.base_url else config.base_url
            
    items.append(ConfigItemStatus(
        key="base_url",
        label="Base URL",
        required=base_url_req,
        status=bu_status if not base_url_req else ("configured" if config.base_url else "missing"),
        safe_value=bu_safe
    ))
    
    # 4. API Key Storage Mode
    store_status = "configured" if config.api_key_storage else "missing"
    items.append(ConfigItemStatus(
        key="api_key_storage",
        label="API Key Storage",
        required=True,
        status=store_status,
        safe_value=config.api_key_storage if config.api_key_storage else "Missing"
    ))
    
    # 5. API Key
    key_status = "missing"
    key_safe = "Missing"
    if config.api_key_storage == "keyring":
        if config.api_key_name:
            try:
                import keyring
                # Safely check if password exists without exposing it
                if keyring.get_password("alo", config.api_key_name) is not None:
                    key_status = "configured"
                    key_safe = "stored in keyring"
                else:
                    key_safe = "keyring entry missing"
            except Exception:
                key_safe = "keyring unavailable"
        else:
            key_safe = "API key name missing"
    elif config.api_key_storage == "env":
        if config.api_key_env_var:
            if os.environ.get(config.api_key_env_var):
                key_status = "configured"
                key_safe = f"env var {config.api_key_env_var} present"
            else:
                key_safe = f"env var {config.api_key_env_var} missing"
        else:
            key_safe = "env var name missing"
            
    items.append(ConfigItemStatus(
        key="api_key",
        label="API Key",
        required=True,
        status=key_status,
        safe_value=key_safe
    ))
    
    missing_req = [i for i in items if i.required and i.status == "missing"]
    warnings = [i for i in items if i.status == "warning"]
    
    return ConfigReadiness(
        llm_ready=len(missing_req) == 0,
        next_required_key=missing_req[0].key if missing_req else None,
        missing_required=missing_req,
        warnings=warnings,
        items=items
    )
