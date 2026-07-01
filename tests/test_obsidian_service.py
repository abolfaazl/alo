from alo.config import AloConfig, ObsidianConfig
from alo.services.obsidian_service import (
    is_obsidian_enabled,
    get_vault_path,
    get_alo_folder_path,
    sanitize_filename,
    export_lesson,
    export_practice_result,
    update_dashboard
)

def test_default_config_is_disabled():
    cfg = AloConfig()
    assert not cfg.obsidian.enabled
    assert not is_obsidian_enabled(cfg)

def test_sanitize_filename():
    assert sanitize_filename('Valid Name') == 'Valid Name'
    assert sanitize_filename('Invalid: < > : " / \\ | ? * Name') == 'Invalid          Name'
    assert sanitize_filename('Persian فارسی') == 'Persian فارسی'

def test_invalid_vault_path_safe(tmp_path):
    cfg = AloConfig(obsidian=ObsidianConfig(enabled=True, vault_path=str(tmp_path / "does_not_exist")))
    assert get_vault_path(cfg) is None
    
    # Should not throw exception
    export_lesson("ID", "Title", "Path", "Content", cfg)
    export_practice_result("ID", "Title", "Path", "pass", 100, [], [], cfg)
    update_dashboard(cfg)

def test_setup_and_export_success(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    
    cfg = AloConfig(obsidian=ObsidianConfig(enabled=True, vault_path=str(vault)))
    assert get_vault_path(cfg) == vault
    
    folder = get_alo_folder_path(cfg)
    assert folder == vault / "ALO"
    
    # Update dashboard
    update_dashboard(cfg, latest_lesson="L1", latest_practice="P1")
    dash = folder / "Dashboard.md"
    assert dash.exists()
    content = dash.read_text(encoding="utf-8")
    assert "Latest lesson: L1" in content
    
    # Export lesson
    lesson_path = export_lesson("ALO-RM-001", "Intro to Persian", "Lang Path", "Salam means hello.", cfg)
    assert lesson_path.exists()
    content = lesson_path.read_text(encoding="utf-8")
    assert "alo_type: lesson" in content
    assert "Salam means hello." in content
    assert "<!-- ALO:BEGIN lesson -->" in content
    
    # Add user notes outside marker
    lesson_path.write_text(content + "\nMy personal note.", encoding="utf-8")
    
    # Re-export lesson (merge)
    export_lesson("ALO-RM-001", "Intro to Persian", "Lang Path", "Salam means hello again.", cfg)
    content2 = lesson_path.read_text(encoding="utf-8")
    assert "Salam means hello again." in content2
    assert "My personal note." in content2 # User notes preserved
    
    # Export practice result
    export_practice_result("ALO-RM-001", "Intro to Persian", "Lang Path", "pass", 100, ["Great"], ["None"], cfg)
    content3 = lesson_path.read_text(encoding="utf-8")
    assert "<!-- ALO:BEGIN practice-result -->" in content3
    assert "Score: 100" in content3
    
    # Practice log
    log_path = folder / "Practice Log.md"
    assert log_path.exists()
    log_content = log_path.read_text(encoding="utf-8")
    assert "Score: 100" in log_content
