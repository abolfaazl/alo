
from alo.ui.dashboard import DashboardScreen
from alo.config import AloConfig

def test_settings_connection_tested_flow(monkeypatch):
    app = DashboardScreen(is_workspace=False, workspace_info={})
    app.state_data = {
        'config_obj': AloConfig(llm_provider='openai', model='gpt-3.5-turbo', api_key_storage='env', api_key_env_var='KEY'),
        'connection_tested': 'Not tested'
    }
    
    def mock_update(*args, **kwargs): pass
    def mock_show(*args, **kwargs): pass
    monkeypatch.setattr(app, 'update_input_prompt', mock_update)
    monkeypatch.setattr(app, 'show_choices', mock_show)
    monkeypatch.setenv('KEY', 'secret')
    
    class CollectLog:
        def __init__(self):
            self.lines = []
        def write(self, s):
            self.lines.append(str(s))
            
    log = CollectLog()
    app._render_settings_menu(log)
    output = ''.join(log.lines)
    assert 'Config Complete | Connection: Not tested' in output
    
    app.state_data['connection_tested'] = 'Verified'
    log = CollectLog()
    app._render_settings_menu(log)
    output = ''.join(log.lines)
    assert 'Config Complete | Connection: Verified' in output
    
    app.state_data['connection_tested'] = 'Failed'
    log = CollectLog()
    app._render_settings_menu(log)
    output = ''.join(log.lines)
    assert 'Config Complete | Connection: Failed' in output
