import pytest
import os
from unittest.mock import patch

@pytest.mark.anyio
async def test_dashboard_worker_exception_recovery(tmp_path):
    from alo.ui.dashboard import AloApp
    from textual.widgets import Input, LoadingIndicator
    from alo.cli import app as cli_app
    from typer.testing import CliRunner
    
    runner = CliRunner()
    
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        inputs = "English grammar\nBg\n1\nGoal\nn\nn\nn\n"
        runner.invoke(cli_app, ["init"], input=inputs)
        
        app = AloApp(is_workspace=True, workspace_info={"cwd": str(tmp_path), "subject": "English grammar"})
        
        # Patch the generate_assessment_service to raise an exception
        with patch('alo.services.assess_service.generate_assessment_service') as mock_generate:
            mock_generate.side_effect = Exception("Simulated import or execution failure")
            
            async with app.run_test() as pilot:
                # Wait for app to be ready
                for _ in range(10):
                    if app.query("#logo"):
                        break
                    await pilot.pause(0.1)
                assert app.query_one("#logo")
                
                inp = app.query_one("#chat-input", Input)
                inp.value = "assess --mock"
                await pilot.press("enter")
                
                # Wait a bit for the worker thread to catch exception and call callback
                await pilot.pause(0.5)
                
                # Check that app state returned to idle or appropriate recovery state
                # Since mock=True, it doesn't trigger guided recovery which looks for specific error_code
                assert app.screen.app_state == "idle"
                
                # Input should be visible and usable again
                assert not inp.has_class("hidden")
                
                # Loading indicator should be hidden
                ind = app.query_one("#loading-indicator", LoadingIndicator)
                assert ind.has_class("hidden")
                
                # State label should be hidden actually, since reset_input_prompt hides the state-bar
                sb = app.query_one("#state-bar")
                assert sb.has_class("hidden")
                
    finally:
        os.chdir(cwd)
