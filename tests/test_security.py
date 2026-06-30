import pytest
from unittest.mock import patch, MagicMock
from alo.llm.client import _safe_raise
import openai
from alo.services.paths_service import get_paths
from alo.ui.dashboard import DashboardScreen

def test_safe_raise_authentication_error():
    # Mock an authentication error with a fake secret
    fake_secret = "sk-test-secret-value"
    err = openai.AuthenticationError(
        message=f"Incorrect API key provided: {fake_secret}. You can find your API key at https://platform.openai.com/account/api-keys.",
        response=MagicMock(),
        body={"error": {"message": f"Incorrect API key provided: {fake_secret}."}}
    )
    
    with pytest.raises(ValueError) as exc:
        _safe_raise("Test action.", err)
        
    err_str = str(exc.value)
    assert "sk-" not in err_str
    assert fake_secret not in err_str
    assert "LLM authentication failed. Check your API key in settings." in err_str

def test_safe_raise_generic_error_with_secret():
    # If some unknown error contains a secret, ensure it's not stringified
    fake_secret = "Bearer secret123"
    err = Exception(f"Unknown error with {fake_secret}")
    
    with pytest.raises(ValueError) as exc:
        _safe_raise("Test action.", err)
        
    err_str = str(exc.value)
    assert fake_secret not in err_str
    assert "LLM processing error. (Type: Exception)" in err_str

@patch('alo.llm.client._get_llm_client')
@patch('alo.services.paths_service.alo_config.validate_config_readiness')
def test_cli_service_path_error_scrubbing(mock_validate, mock_get_client, tmp_path):
    # Setup mock workspace
    (tmp_path / "learning-profile.md").write_text("Subject: Security")
    (tmp_path / "skill-map.md").write_text("")
    (tmp_path / "weaknesses.md").write_text("")
    
    mock_readiness = MagicMock()
    mock_readiness.llm_ready = True
    mock_validate.return_value = mock_readiness
    
    # Mock client to throw AuthenticationError on parsing
    fake_secret = "sk-test-secret-value-in-client"
    mock_err = openai.AuthenticationError(
        message=f"Incorrect API key provided: {fake_secret}.",
        response=MagicMock(),
        body={"error": {"message": f"Incorrect API key provided: {fake_secret}."}}
    )
    
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse.side_effect = mock_err
    mock_client.chat.completions.create.side_effect = mock_err
    mock_get_client.return_value = mock_client
    
    res = get_paths(tmp_path, mock=False)
    
    assert res.success is False
    assert res.error_code == "llm_error"
    assert "sk-" not in res.error
    assert fake_secret not in res.error
    assert "LLM authentication failed. Check your API key in settings." in res.error

def test_dashboard_worker_recovery_path():
    # Check that the dashboard's handle_worker_error properly triggers recovery
    # and doesn't log the raw API key if somehow passed
    from alo.services.paths_service import PathsServiceResult
    screen = DashboardScreen(is_workspace=True, workspace_info={})
    
    mock_log = MagicMock()
    
    with patch.object(screen, 'restore_input_after_worker') as _mock_restore, \
         patch.object(screen, 'update_input_prompt') as _mock_prompt, \
         patch.object(screen, 'show_choices') as _mock_choices:
        
        # Simulate a result that somehow has a message
        res = PathsServiceResult(success=False, error_code="missing_config", error="Failed to generate valid JSON paths. LLM authentication failed. Check your API key in settings.")
        
        # It shouldn't crash and should write to log without keys
        handled = screen.handle_worker_error(res, "paths generation", mock_log)
        
        assert handled is True
        assert screen.app_state == "guided_recovery"
        
        log_calls = mock_log.write.call_args_list
        assert len(log_calls) > 0
        logged_text = str(log_calls[0])
        assert "sk-" not in logged_text
        assert "LLM authentication failed" in logged_text
    
    log_calls = mock_log.write.call_args_list
    assert len(log_calls) > 0
    logged_text = str(log_calls[0])
    assert "sk-" not in logged_text
    assert "LLM authentication failed" in logged_text
