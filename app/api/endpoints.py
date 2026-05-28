from fastapi import APIRouter, HTTPException, Request
#from slowapi import Limiter, _rate_limit_exceeded_handler
#from slowapi.util import get_remote_address
#from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Union, List, Dict, Any, Optional
import time
import logging

from ..models.schemas import (
    ImprovedTextResponseWithMeta, 
    ImproveTextRequest, 
    SummaryResponseWithMeta, 
    SummarizeRequest
)
from ..services.llm_service import LLMService

logger = logging.getLogger(__name__)

# Создаём роутер
router = APIRouter()

# Инициализируем сервис (синглтон)
# Делаем это глобально, чтобы не инициализировать при каждом запросе
try:
    llm_service = LLMService()
except Exception as e:
    logger.error(f"Failed to init LLMService: {e}")
    llm_service = None



# Модели для унифицированного API (locust-api-template)
class RunRequest(BaseModel):
    """Запрос для унифицированного эндпоинта /run"""
    content: Union[str, List[Dict[str, Any]]]
    extra_body: Dict[str, Any] = Field(default_factory=dict)

class RunResponse(BaseModel):
    """Ответ для унифицированного эндпоинта /run"""
    status: str  # "success" или "error"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Унифицированные эндпоинты (для нагрузки)
@router.post("/run", response_model=RunResponse)
async def run_unified(req: RunRequest):
    """
    Унифицированный эндпоинт для нагрузочного тестирования.
    Принимает content (текст или список) и extra_body с параметрами.
    """
    start_time = time.time()
    if not llm_service:
        return RunResponse(status="error", error="Сервис LLM не инициализирован")

    try:
        # 1. Извлекаем текст из content
        text = ""
        if isinstance(req.content, str):
            text = req.content.strip()
        elif isinstance(req.content, list):
            # Поддержка мультимодальности (ищем текст в списке)
            for item in req.content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text += item.get("text", "") + " "
            text = text.strip()
        
        if not text:
            return RunResponse(status="error", error="Поле content пустое или не содержит текста")

        # 2. Читаем параметры из extra_body
        # По умолчанию задача - улучшение текста
        task_type = req.extra_body.get("task_type", "improve")
        instruction = req.extra_body.get("instruction", "исправь ошибки")
        
        # 3. Выполняем задачу
        result_obj = None
        if task_type == "improve":
            result_obj = await llm_service.improve_text(text, instruction)
        elif task_type == "summarize":
            result_obj = await llm_service.summarize(text)
        else:
            return RunResponse(status="error", error=f"Неизвестный task_type: {task_type}")
            
        # Преобразуем Pydantic объект в dict
        res_dict = result_obj.model_dump() if hasattr(result_obj, 'model_dump') else dict(result_obj)
        
        # Добавляем метрики времени обработки
        res_dict["processing_time_ms"] = int((time.time() - start_time) * 1000)
            
        return RunResponse(status="success", result=res_dict, error=None)
        
    except Exception as e:
        logger.error(f"Error in /run: {e}")
        # Возвращаем ошибку в теле ответа, чтобы Locust мог её залогировать
        return RunResponse(status="error", result=None, error=str(e))


@router.get("/info")
async def get_info():
    """
    Метаданные сервиса. 
    Автотест обращается сюда, чтобы понять структуру входных/выходных данных.
    """
    return {
        "input_type": "text",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_type": {
                    "type": "string", 
                    "enum": ["improve", "summarize"], 
                    "default": "improve",
                    "description": "Тип задачи"
                },
                "instruction": {
                    "type": "string", 
                    "default": "исправь ошибки",
                    "description": "Инструкция для модели"
                }
            }
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "improved_text": {"type": "string"},
                "summary": {"type": "string"},
                "reasoning": {"type": "string"},
                "changes_made": {"type": "string"},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "processing_time_ms": {"type": "integer"}
            }
        }
    }


@router.get("/health")
async def health_check():
    """Проверка работоспособности сервиса."""
    return {"status": "ok", "service": "AI Text Helper", "version": "1.0.0"}


# Старые эндпоинты (для обратной совместимости)
@router.post("/improve", response_model=ImprovedTextResponseWithMeta)
async def improve_text(improve_req: ImproveTextRequest):
    """Улучшает текст согласно инструкции."""
    start_time = time.time()
    if not llm_service:
        raise HTTPException(status_code=503, detail="Service Unavailable")
        
    try:
        result = await llm_service.improve_text(improve_req.text, improve_req.instruction)
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return ImprovedTextResponseWithMeta(
            reasoning=result.reasoning,
            original_text=result.original_text,
            improved_text=result.improved_text,
            applied_instruction=result.applied_instruction,
            changes_made=result.changes_made,
            model_name=llm_service.model,
            temperature=llm_service.temperature,
            processing_time_ms=processing_time_ms,
            timestamp=datetime.now(),
            tokens_used=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@router.post("/summarize", response_model=SummaryResponseWithMeta)
async def summarize_text(summarize_req: SummarizeRequest):
    """Создает краткое содержание текста."""
    start_time = time.time()
    if not llm_service:
        raise HTTPException(status_code=503, detail="Service Unavailable")

    try:
        result = await llm_service.summarize(summarize_req.text)
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return SummaryResponseWithMeta(
            reasoning=result.reasoning,
            summary=result.summary,
            keywords=result.keywords,
            original_length=result.original_length,
            summary_length=result.summary_length,
            model_name=llm_service.model,
            temperature=llm_service.temperature,
            processing_time_ms=processing_time_ms,
            timestamp=datetime.now(),
            tokens_used=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")