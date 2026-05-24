from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import datetime
import time
from ..models.schemas import (
    ImprovedTextResponseWithMeta, 
    ImproveTextRequest, 
    SummaryResponseWithMeta, 
    SummarizeRequest
)
from ..services.llm_service import LLMService

# Создаём лимитер для эндпоинтов
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

llm_service = LLMService()


@router.post("/improve", response_model=ImprovedTextResponseWithMeta)
async def improve_text(improve_req: ImproveTextRequest, request: Request):
    """
    Улучшает текст согласно инструкции.
    - **text**: исходный текст
    - **instruction**: что сделать
    
    Rate limit: 10 запросов в минуту
    """
    start_time = time.time()
    
    try:
        # Получаем ответ от модели (только reasoning, improved_text, changes_made)
        result = await llm_service.improve_text(improve_req.text, improve_req.instruction)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Добавляем метаинформацию программно
        return ImprovedTextResponseWithMeta(
            # Поля от модели 
            reasoning=result.reasoning,
            original_text=result.original_text,
            improved_text=result.improved_text,
            applied_instruction=result.applied_instruction,
            changes_made=result.changes_made,
            # Метаинформация (добавляется сервером)
            model_name=llm_service.model,
            temperature=llm_service.temperature,
            processing_time_ms=processing_time_ms,
            timestamp=datetime.now(),
            tokens_used=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@router.post("/summarize", response_model=SummaryResponseWithMeta)
async def summarize_text(summarize_req: SummarizeRequest, request: Request):
    """
    Создает краткое содержание текста.
    
    Rate limit: 20 запросов в минуту
    """
    start_time = time.time()
    
    try:
        # Получаем ответ от модели (только reasoning, summary, keywords)
        result = await llm_service.summarize(summarize_req.text)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Добавляем метаинформацию программно
        return SummaryResponseWithMeta(
            # Поля от модели
            reasoning=result.reasoning,
            summary=result.summary,
            keywords=result.keywords,
            original_length=result.original_length,
            summary_length=result.summary_length,
            # Метаинформация (добавляется сервером)
            model_name=llm_service.model,
            temperature=llm_service.temperature,
            processing_time_ms=processing_time_ms,
            timestamp=datetime.now(),
            tokens_used=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

@router.get("/info")
async def get_info():
    return {
        "input_type": "text",
        "input_schema": {
            "type": "object",
            "properties": {
                "instruction": {"type": "string", "description": "Инструкция"}
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "improved_text": {"type": "string"},
                "reasoning": {"type": "string"}
            }
        }
    }

@router.get("/health")
async def health_check(request: Request):
    """Проверка работоспособности"""
    return {"status": "ok", "service": "Text Assistant"}