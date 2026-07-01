import json
from pathlib import Path
from alo import config

def test_config_path_is_outside_repo(monkeypatch, tmp_path):
    # Mock platformdirs
    config_mock = tmp_path / "appdata" / "ALO"
    config_mock.mkdir(parents=True)
    
    import platformdirs
    monkeypatch.setattr(platformdirs, "user_config_dir", lambda appname: str(config_mock))

    config_dir = config.get_config_dir()
    assert config_dir == config_mock
    
    cwd = Path.cwd()
    assert cwd not in config_dir.parents

def test_openai_compatible_requires_base_url():
    from alo.config import AloConfig
    
    # We no longer raise ValueError here, to allow incomplete GUI configs to save.
    cfg = AloConfig(llm_provider="openai-compatible", base_url="")
    assert cfg.llm_provider == "openai-compatible"
        
    cfg = AloConfig(llm_provider="openai-compatible", base_url="http://localhost:8080")
    assert cfg.base_url == "http://localhost:8080"
    
def test_save_and_load_config(monkeypatch, tmp_path):
    config_mock = tmp_path / "appdata" / "ALO"
    import platformdirs
    monkeypatch.setattr(platformdirs, "user_config_dir", lambda appname: str(config_mock))
    
    # ensure legacy dir exists empty or mock it so migration doesn't hit real home
    home_dir = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home_dir)

    assert config.config_exists() is False

    from alo.config import AloConfig
    test_config = AloConfig(
        llm_provider="openai",
        model="gpt-4o",
        safe_mode=True
    )
    
    config.save_config(test_config)
    assert config.config_exists() is True

    loaded_config = config.load_config()
    assert loaded_config == test_config
    
    res = config.load_config_result()
    assert res.loaded_from == "persisted"
    assert res.path == config_mock / "config.json"

def test_config_migration(monkeypatch, tmp_path):
    config_mock = tmp_path / "appdata" / "ALO"
    import platformdirs
    monkeypatch.setattr(platformdirs, "user_config_dir", lambda appname: str(config_mock))
    
    home_dir = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home_dir)
    
    legacy_dir = home_dir / ".alo"
    legacy_dir.mkdir(parents=True)
    legacy_file = legacy_dir / "config.json"
    legacy_file.write_text('{"llm_provider": "legacy_prov"}', encoding="utf-8")
    
    assert not config_mock.exists()
    
    res = config.load_config_result()
    assert res.config.llm_provider == "legacy_prov"
    assert res.loaded_from == "migrated"
    assert res.migrated_from == legacy_file
    
    assert config.config_exists() is True
    assert config.get_config_path().read_text(encoding="utf-8") == '{"llm_provider": "legacy_prov"}'

def test_invalid_config_backup(monkeypatch, tmp_path):
    config_mock = tmp_path / "appdata" / "ALO"
    import platformdirs
    monkeypatch.setattr(platformdirs, "user_config_dir", lambda appname: str(config_mock))
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    
    config_mock.mkdir(parents=True)
    bad_file = config_mock / "config.json"
    bad_file.write_text('{"llm_provider": broken_json_here}', encoding="utf-8")
    
    res = config.load_config_result()
    assert res.loaded_from == "invalid-fallback"
    assert len(res.warnings) == 1
    assert "invalid JSON" in res.warnings[0]
    
    # Original is preserved
    assert bad_file.read_text(encoding="utf-8") == '{"llm_provider": broken_json_here}'
    
    # Backup is created
    backups = list(config_mock.glob("config_broken_*.json"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == '{"llm_provider": broken_json_here}'

def test_partial_config_preservation(monkeypatch, tmp_path):
    config_mock = tmp_path / "appdata" / "ALO"
    import platformdirs
    monkeypatch.setattr(platformdirs, "user_config_dir", lambda appname: str(config_mock))
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    
    config_mock.mkdir(parents=True)
    file = config_mock / "config.json"
    file.write_text('{"llm_provider": "openai-compatible", "model": "gpt-custom"}', encoding="utf-8")
    
    res = config.load_config_result()
    assert res.loaded_from == "persisted"
    assert res.config.llm_provider == "openai-compatible"
    assert res.config.model == "gpt-custom"
    assert res.config.base_url is None

def test_no_secret_written_to_repo():
    example_config_path = Path("alo_config.example.json")
    if example_config_path.exists():
        with open(example_config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "sk-" not in str(data)
            assert "key" not in str(data).lower() or data.get("llm_provider") is None

def test_backward_compatible_config():
    from alo.config import AloConfig
    # Simulating older config structure parsed from JSON
    legacy_data = {
        "llm_provider": "openai",
        "model": "gpt-3.5-turbo",
        "api_key_env_var": "MY_LEGACY_KEY"
    }
    cfg = AloConfig(**legacy_data)
    assert cfg.api_key_storage == "env"
    assert cfg.api_key_env_var == "MY_LEGACY_KEY"
    assert cfg.api_key_name is None

def test_resolve_api_key_env(monkeypatch):
    from alo.config import AloConfig, resolve_api_key
    cfg = AloConfig(api_key_storage="env", api_key_env_var="MOCKED_ENV_KEY")
    monkeypatch.setenv("MOCKED_ENV_KEY", "sk-test-env-val")
    key = resolve_api_key(cfg)
    assert key == "sk-test-env-val"

def test_resolve_api_key_keyring(monkeypatch):
    from alo.config import AloConfig, resolve_api_key
    cfg = AloConfig(api_key_storage="keyring", api_key_name="TEST_KEY_NAME")
    
    class MockKeyring:
        def get_password(self, service, username):
            if username == "TEST_KEY_NAME":
                return "sk-test-keyring-val"
            return None
            
    import keyring
    monkeypatch.setattr(keyring, "get_password", MockKeyring().get_password)
    
    key = resolve_api_key(cfg)
    assert key == "sk-test-keyring-val"

def test_config_readiness_missing_provider():
    from alo.config import AloConfig, validate_config_readiness
    cfg = AloConfig(llm_provider="")
    res = validate_config_readiness(cfg)
    assert res.llm_ready is False
    assert any(i.key == "llm_provider" and i.status == "missing" for i in res.missing_required)

def test_config_readiness_missing_model():
    from alo.config import AloConfig, validate_config_readiness
    cfg = AloConfig(model="")
    res = validate_config_readiness(cfg)
    assert res.llm_ready is False
    assert any(i.key == "model" and i.status == "missing" for i in res.missing_required)

def test_config_readiness_keyring_missing(monkeypatch):
    from alo.config import AloConfig, validate_config_readiness
    cfg = AloConfig(api_key_storage="keyring", api_key_name="TEST_KEY")
    
    class MockKeyring:
        def get_password(self, service, username):
            return None
    import keyring
    monkeypatch.setattr(keyring, "get_password", MockKeyring().get_password)
    
    res = validate_config_readiness(cfg)
    assert res.llm_ready is False
    api_status = next(i for i in res.missing_required if i.key == "api_key")
    assert api_status.status == "missing"
    assert "keyring entry missing" in api_status.safe_value

def test_config_readiness_env_present_is_masked(monkeypatch):
    from alo.config import AloConfig, validate_config_readiness
    cfg = AloConfig(api_key_storage="env", api_key_env_var="MY_KEY")
    monkeypatch.setenv("MY_KEY", "secret-value")
    
    res = validate_config_readiness(cfg)
    assert res.llm_ready is True
    api_status = next(i for i in res.items if i.key == "api_key")
    assert api_status.status == "configured"
    assert "secret-value" not in api_status.safe_value
    assert "MY_KEY present" in api_status.safe_value

def test_config_readiness_base_url_requirements():
    from alo.config import AloConfig, validate_config_readiness
    
    # openai ignores base url requirement
    cfg1 = AloConfig.model_construct(llm_provider="openai", base_url="")
    res1 = validate_config_readiness(cfg1)
    # assuming we test with valid keyring/env to isolate base_url
    assert not any(i.key == "base_url" and i.required for i in res1.items)
    
    # openai-compatible requires it
    cfg2 = AloConfig.model_construct(llm_provider="openai-compatible", base_url=None)
    res2 = validate_config_readiness(cfg2)
    assert any(i.key == "base_url" and i.required for i in res2.items)
