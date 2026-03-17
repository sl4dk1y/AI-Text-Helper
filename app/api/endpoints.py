from fastapi import APIRouter, HTTPException
from ..models.schemas import ImprovedTextResponse, ImproveTextRequest, SummaryResponse, SummarizeRequest
from ..services.llm_service import LLMService

router = APIRouter()

llm_service = LLMService()

@router.post("/improve", response_model=ImprovedTextResponse)
async def improve_text(request: ImproveTextRequest):
    """
    Улучшает текст согласно инструкции.
    - **text**: исходный текст
    - **instruction**: что сделать
    """
    try:
        result = await llm_service.improve_text(request.text, request.instruction)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")
    
@router.post("/summarize", response_model=SummaryResponse)
async def summarize_text(request: SummarizeRequest):
    """
    Создает краткое содержание текста.
    """
    try:
        result = await llm_service.summarize(request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

@router.get("/health")
async def health_check():
    """Проверка работоспособности"""
    return {"status":"ok","service":"Text Assistant"}    