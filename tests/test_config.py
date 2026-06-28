import json
from pathlib import Path
from alo import config

def test_config_path_is_outside_repo(monkeypatch, tmp_path):
    # Mock home directory
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("USERPROFILE", str(home_dir)) # Windows
    monkeypatch.setenv("HOME", str(home_dir)) # Unix
    
    monkeypatch.setattr(Path, "home", lambda: home_dir)

    config_dir = config.get_config_dir()
    assert config_dir == home_dir / ".alo"
    
    cwd = Path.cwd()
    assert cwd not in config_dir.parents

def test_openai_compatible_requires_base_url():
    from alo.config import AloConfig
    import pytest
    
    with pytest.raises(ValueError):
        AloConfig(llm_provider="openai-compatible", base_url=None)
        
    cfg = AloConfig(llm_provider="openai-compatible", base_url="http://localhost:8080")
    assert cfg.base_url == "http://localhost:8080"
    
def test_save_and_load_config(monkeypatch, tmp_path):
    home_dir = tmp_path / "home"
    home_dir.mkdir()
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

def test_no_secret_written_to_repo():
    example_config_path = Path("alo_config.example.json")
    if example_config_path.exists():
        with open(example_config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "sk-" not in str(data)
            assert "key" not in str(data).lower() or data.get("llm_provider") is None
