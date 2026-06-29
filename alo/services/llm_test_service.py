import time
from alo.config import AloConfig, validate_config_readiness
from alo.services.results import ServiceResult

def test_llm_connection(config: AloConfig) -> ServiceResult:
    readiness = validate_config_readiness(config)
    if not readiness.llm_ready:
        missing = ", ".join([i.label for i in readiness.missing_required])
        return ServiceResult(
            success=False,
            error_code="missing_config",
            error=f"Cannot test connection. Missing required config: {missing}"
        )
        
    if config.llm_provider == "local-mock":
        return ServiceResult(success=True, data={"message": "Mock connection test successful (no network)."})
        
    try:
        from alo.llm.client import _get_llm_client
        client = _get_llm_client(config)
        
        # Make a tiny safe LLM call
        messages = [
            {"role": "user", "content": "Reply with the single word: OK"}
        ]
        
        t0 = time.time()
        # In modern openai, client.chat.completions.create is standard
        response = client.chat.completions.create(
            model=config.model,
            messages=messages,
            max_tokens=5,
            temperature=0
        )
        t1 = time.time()
        
        content = response.choices[0].message.content
        if content and "OK" in content.upper():
            return ServiceResult(success=True, data={"message": f"Connection successful! Latency: {t1-t0:.2f}s"})
        else:
            return ServiceResult(
                success=False,
                error_code="llm_error",
                error=f"Connection succeeded but received unexpected response: {content}"
            )
            
    except Exception as e:
        return ServiceResult(
            success=False,
            error_code="llm_error",
            error=f"Connection test failed safely without exposing credentials. Error: {str(e)}"
        )
