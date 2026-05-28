from __future__ import annotations
from typing import Any, Dict, List, Union, Optional
import logging

from app.models.schemas import (
    InfoResponse,
    RunRequest,
    RunResponse,
    Schema,
    ServiceBase,
)

# Импорт бизнес-логики
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class AITextHelperService(ServiceBase):
    """
    Сервис для улучшения и суммаризации текста.
    Наследует ServiceBase для совместимости с нагрузочным тестом.
    """

    def __init__(self):
        super().__init__()
        self.llm_service = LLMService()

    def get_info(self) -> InfoResponse:
        """Возвращает метаданные сервиса для авто-генерации тестов."""
        return InfoResponse(
            input_type="text",  
            input_schema=Schema.of(
                task_type=Schema.string(
                    "Тип задачи: 'improve' или 'summarize'",
                    default="improve",
                    enum=["improve", "summarize"],
                ),
                instruction=Schema.string(
                    "Инструкция для улучшения текста",
                    default="исправь ошибки",
                ),
                temperature=Schema.number(
                    "Температура генерации",
                    default=0.3,
                    minimum=0.0,
                    maximum=1.0,
                ),
            ),
            output_schema=Schema.of(
                reasoning=Schema.string("Рассуждения модели"),
                improved_text=Schema.string("Исправленный текст (для improve)"),
                summary=Schema.string("Краткое содержание (для summarize)"),
                changes_made=Schema.string("Список исправлений"),
                keywords=Schema.array(
                    Schema.string(),
                    "Ключевые слова (для summarize)",
                ),
                processing_time_ms=Schema.integer("Время обработки в мс"),
            ),
        )

    async def run(self, request: RunRequest) -> RunResponse:
        """
        Основная логика обработки запроса.
        Использует хелпер get_text() из базового класса.
        """
        try:
            # Извлекаем текст с помощью хелпера из ServiceBase
            text = self.get_text(request)
            if not text:
                return RunResponse(status="error", error="Пустой текст или контент не распознан")

            # Читаем параметры из extra_body
            task_type = request.extra_body.get("task_type", "improve")
            instruction = request.extra_body.get("instruction", "исправь ошибки")

            logger.info(f"Processing task={task_type}, text={text[:50]}...")

            # Выполняем задачу
            if task_type == "improve":
                result = await self.llm_service.improve_text(text, instruction)
                return RunResponse(
                    status="success",
                    result={
                        "reasoning": result.reasoning,
                        "improved_text": result.improved_text,
                        "changes_made": result.changes_made,
                        "original_text": result.original_text,
                    },
                )
            elif task_type == "summarize":
                result = await self.llm_service.summarize(text)
                return RunResponse(
                    status="success",
                    result={
                        "reasoning": result.reasoning,
                        "summary": result.summary,
                        "keywords": result.keywords,
                        "original_length": result.original_length,
                        "summary_length": result.summary_length,
                    },
                )
            else:
                return RunResponse(
                    status="error",
                    error=f"Неизвестная задача: {task_type}. Доступны: improve, summarize",
                )

        except Exception as e:
            logger.error(f"Error in run: {e}", exc_info=True)
            return RunResponse(status="error", error=str(e))

# СИНГЛТОН
_service_instance: Optional[AITextHelperService] = None


def get_service() -> AITextHelperService:
    """
    Возвращает singleton-экземпляр сервиса.
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = AITextHelperService()
    return _service_instance