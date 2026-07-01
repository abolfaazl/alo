from alo.services.llm_test_service import test_llm_connection as do_test_llm_connection
from alo.config import AloConfig

class MockChoices:
    def __init__(self):
        self.message = type('MockMessage', (), {'content': 'OK'})()

class MockResponse:
    def __init__(self):
        self.choices = [MockChoices()]

def test_llm_connection_success(monkeypatch):
    cfg = AloConfig(
        llm_provider='openai',
        model='gpt-3.5-turbo',
        api_key_storage='env',
        api_key_env_var='MOCK_KEY'
    )
    monkeypatch.setenv('MOCK_KEY', 'sk-mock')

    def mock_create(*args, **kwargs):
        return MockResponse()

    import openai
    monkeypatch.setattr(openai.resources.chat.completions.Completions, 'create', mock_create)

    res = do_test_llm_connection(cfg)
    assert res.success is True
    assert 'Connection successful' in res.payload['message']

def test_llm_connection_auth_error(monkeypatch):
    cfg = AloConfig(
        llm_provider='openai',
        model='gpt-3.5-turbo',
        api_key_storage='env',
        api_key_env_var='MOCK_KEY'
    )
    monkeypatch.setenv('MOCK_KEY', 'sk-mock')

    def mock_create(*args, **kwargs):
        import openai
        import httpx
        req = httpx.Request("POST", "http://test")
        res = httpx.Response(401, request=req)
        raise openai.AuthenticationError('Auth failed', response=res, body=None)

    import openai
    monkeypatch.setattr(openai.resources.chat.completions.Completions, 'create', mock_create)

    res = do_test_llm_connection(cfg)
    assert res.success is False
    assert 'Authentication failed: API key was rejected' in res.error

def test_llm_connection_not_found_error(monkeypatch):
    cfg = AloConfig(
        llm_provider='openai',
        model='gpt-invalid-model',
        api_key_storage='env',
        api_key_env_var='MOCK_KEY'
    )
    monkeypatch.setenv('MOCK_KEY', 'sk-mock')

    def mock_create(*args, **kwargs):
        import openai
        import httpx
        req = httpx.Request("POST", "http://test")
        res = httpx.Response(404, request=req)
        raise openai.NotFoundError('Model not found', response=res, body=None)

    import openai
    monkeypatch.setattr(openai.resources.chat.completions.Completions, 'create', mock_create)

    res = do_test_llm_connection(cfg)
    assert res.success is False
    assert 'Model or endpoint not found' in res.error

def test_llm_connection_timeout_error(monkeypatch):
    cfg = AloConfig(
        llm_provider='openai',
        model='gpt-3.5-turbo',
        api_key_storage='env',
        api_key_env_var='MOCK_KEY'
    )
    monkeypatch.setenv('MOCK_KEY', 'sk-mock')

    def mock_create(*args, **kwargs):
        import openai
        import httpx
        req = httpx.Request("POST", "http://test")
        raise openai.APITimeoutError(req)

    import openai
    monkeypatch.setattr(openai.resources.chat.completions.Completions, 'create', mock_create)

    res = do_test_llm_connection(cfg)
    assert res.success is False
    assert 'Timeout: provider did not respond' in res.error

def test_llm_connection_generic_error(monkeypatch):
    cfg = AloConfig(
        llm_provider='openai',
        model='gpt-3.5-turbo',
        api_key_storage='env',
        api_key_env_var='MOCK_KEY'
    )
    monkeypatch.setenv('MOCK_KEY', 'sk-mock')

    def mock_create(*args, **kwargs):
        raise ValueError('Some very secret information sk-1234')

    import openai
    monkeypatch.setattr(openai.resources.chat.completions.Completions, 'create', mock_create)

    res = do_test_llm_connection(cfg)
    assert res.success is False
    assert 'Unexpected connection test error, safely caught' in res.error
    assert 'sk-1234' not in res.error
