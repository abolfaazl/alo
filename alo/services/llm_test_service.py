import time
from alo.config import AloConfig, validate_config_readiness
from alo.services.results import ServiceResult

def test_llm_connection(config: AloConfig) -> ServiceResult:
    readiness = validate_config_readiness(config)
    if not readiness.llm_ready:
        missing = ', '.join([i.label for i in readiness.missing_required])
        return ServiceResult(
            success=False,
            error_code='missing_config',
            error=f'Cannot test connection. Missing required config: {missing}'
        )
        
    if config.llm_provider == 'local-mock':
        return ServiceResult(success=True, payload={'message': 'Mock connection test successful (no network).'})
        
    try:
        from alo.llm.client import _get_llm_client
        client = _get_llm_client(config)
        
        messages = [
            {'role': 'user', 'content': 'Reply with the single word: OK'}
        ]
        
        t0 = time.time()
        response = client.chat.completions.create(
            model=config.model,
            messages=messages,
            max_tokens=1,
            temperature=0,
            timeout=10.0
        )
        t1 = time.time()
        
        content = response.choices[0].message.content
        if content and 'OK' in content.upper():
            return ServiceResult(success=True, payload={'message': f'Connection successful! Latency: {t1-t0:.2f}s', 'content': content})
        else:
            return ServiceResult(
                success=False,
                error_code='llm_error',
                error=f'Connection succeeded but received unexpected response: {content}'
            )
            
    except Exception as e:
        import openai
        if isinstance(e, openai.AuthenticationError):
            err_msg = 'Authentication failed: API key was rejected by provider.'
        elif isinstance(e, openai.NotFoundError):
            err_msg = 'Model or endpoint not found. Provider may not recognize the model or base URL.'
        elif isinstance(e, openai.APITimeoutError):
            err_msg = 'Timeout: provider did not respond in time.'
        elif isinstance(e, openai.APIConnectionError):
            err_msg = 'Connection error: network or provider endpoint unreachable.'
        elif getattr(openai, 'RateLimitError', None) and isinstance(e, getattr(openai, 'RateLimitError')):
            err_msg = 'Rate limit or quota error.'
        elif getattr(openai, 'PermissionDeniedError', None) and isinstance(e, getattr(openai, 'PermissionDeniedError')):
            err_msg = 'Permission denied: API key may not have access to this model.'
        elif getattr(openai, 'BadRequestError', None) and isinstance(e, getattr(openai, 'BadRequestError')):
            err_msg = 'Bad request: provider rejected the request or model parameters.'
        elif getattr(openai, 'APIStatusError', None) and isinstance(e, getattr(openai, 'APIStatusError')):
            err_msg = f'Provider returned HTTP {getattr(e, "status_code", "error")} with a status error.'
        else:
            err_msg = 'Unexpected connection test error, safely caught.'
            
        return ServiceResult(
            success=False,
            error_code='llm_error',
            error=err_msg
        )
