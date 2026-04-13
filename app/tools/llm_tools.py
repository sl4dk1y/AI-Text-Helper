import time
from datetime import datetime
from ..models.tools import (
    ImproveTextRequest, ImproveTextResponse,
    SummarizeRequest, SummarizeResponse,
    ValidationRequest,
    SuspiciousCheckRequest,
    LogRequest
)
from ..services.llm_service import LLMService

# Глобальный экземпляр LLM сервиса
_llm_service = None


def get_llm_service() -> LLMService:
    """Получение экземпляра LLM сервиса (синглтон)"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


async def improve_text(request: ImproveTextRequest) -> ImproveTextResponse:
    """
    Инструмент улучшения текста с помощью LLM.
    """
    start_time = time.time()
    
    llm_service = get_llm_service()
    
    # Предварительная валидация
    from .security_tools import validate_input
    validation = validate_input(ValidationRequest(text=request.text, max_length=5000))
    if not validation.is_valid:
        return ImproveTextResponse(
            original_text=request.text,
            improved_text=request.text,
            applied_instruction=request.instruction,
            changes_made=f"Ошибка валидации: {validation.error_message}",
            model_name=llm_service.model,
            temperature=llm_service.temperature,
            processing_time_ms=int((time.time() - start_time) * 1000),
            timestamp=datetime.now()
        )
    
    # Проверка на подозрительные паттерны
    from .security_tools import check_suspicious
    suspicious = check_suspicious(SuspiciousCheckRequest(text=request.text))
    if suspicious.is_suspicious and suspicious.requires_human_review:
        return ImproveTextResponse(
            original_text=request.text,
            improved_text=request.text,
            applied_instruction=request.instruction,
            changes_made=f"Запрос требует проверки человеком. Найдены паттерны: {suspicious.matched_patterns}",
            model_name=llm_service.model,
            temperature=llm_service.temperature,
            processing_time_ms=int((time.time() - start_time) * 1000),
            timestamp=datetime.now()
        )
    
    # Вызов LLM
    result = await llm_service.improve_text(request.text, request.instruction)
    
    # Логирование
    from .logging_tools import log_action
    await log_action(LogRequest(
        action="improve_text",
        status="success",
        details={"text_length": len(request.text)}
    ))
    
    return result


async def summarize(request: SummarizeRequest) -> SummarizeResponse:
    """
    Инструмент суммаризации текста с помощью LLM.
    """
    start_time = time.time()
    
    llm_service = get_llm_service()
    
    # Валидация
    from .security_tools import validate_input
    validation = validate_input(ValidationRequest(text=request.text, max_length=10000))
    if not validation.is_valid:
        return SummarizeResponse(
            summary=f"Ошибка валидации: {validation.error_message}",
            keywords=[],
            original_length=len(request.text),
            summary_length=0,
            model_name=llm_service.model,
            temperature=llm_service.temperature,
            processing_time_ms=int((time.time() - start_time) * 1000),
            timestamp=datetime.now()
        )
    
    result = await llm_service.summarize(request.text)
    
    return result