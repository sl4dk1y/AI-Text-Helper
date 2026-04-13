from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from ..models.schemas import ImprovedTextResponse, ImproveTextRequest, SummaryResponse, SummarizeRequest
from ..services.llm_service import LLMService

# Создаём лимитер для эндпоинтов
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

llm_service = LLMService()


@router.post("/improve", response_model=ImprovedTextResponse)
@limiter.limit("10/minute")
async def improve_text(improve_req: ImproveTextRequest, request: Request):
    """
    Улучшает текст согласно инструкции.
    Rate limit: 10 запросов в минуту
    """
    try:
        result = await llm_service.improve_text(improve_req.text, improve_req.instruction)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@router.post("/summarize", response_model=SummaryResponse)
@limiter.limit("20/minute")
async def summarize_text(summarize_req: SummarizeRequest, request: Request):
    """
    Создает краткое содержание текста.
    Rate limit: 20 запросов в минуту
    """
    try:
        result = await llm_service.summarize(summarize_req.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@router.get("/health")
@limiter.limit("60/minute")
async def health_check(request: Request):
    """Проверка работоспособности"""
    return {"status": "ok", "service": "Text Assistant"}