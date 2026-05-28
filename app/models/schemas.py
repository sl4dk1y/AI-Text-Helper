from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Union, List, Dict, Any, Literal
from datetime import datetime
from abc import ABC, abstractmethod


# Типы контента для input_type (Literal для совместимости с Pydantic v2)
InputType = Literal["text", "image", "text_and_image"]

# БИЗНЕС-МОДЕЛИ 
# ЗАПРОСЫ
class ImproveTextRequest(BaseModel):
    """Запрос на улучшение текста"""
    text: str = Field(..., min_length=1, max_length=5000, description="Текст для исправления")
    instruction: str = Field(..., description="Инструкция для обработки")
    style: Optional[str] = Field(None, description="Стиль текста (official, friendly, academic)")


class SummarizeRequest(BaseModel):
    """Запрос на суммаризацию"""
    text: str = Field(..., min_length=1, max_length=10000, description="Текст для суммаризации")


# ОТВЕТЫ (только то, что генерирует модель)
class ImprovedTextResponse(BaseModel):
    """Ответ на улучшение текста (генерируется моделью)"""
    reasoning: Optional[str] = Field(
        None, 
        description="Рассуждения модели о том, как были найдены ошибки и почему выбраны именно эти исправления"
    )
    original_text: str = Field(..., description="Исходный текст")
    improved_text: str = Field(..., description="Исправленный текст")
    applied_instruction: str = Field(..., description="Применённая инструкция")
    changes_made: Optional[str] = Field(None, description="Список исправлений")


class SummaryResponse(BaseModel):
    """Ответ на суммаризацию (генерируется моделью)"""
    reasoning: Optional[str] = Field(
        None, 
        description="Рассуждения модели о том, как была выделена главная мысль и почему выбраны эти ключевые слова"
    )
    summary: str = Field(..., description="Краткое содержание текста")
    keywords: list[str] = Field(default_factory=list, description="Ключевые слова (3-5 слов)")
    original_length: int = Field(..., description="Длина исходного текста")
    summary_length: int = Field(..., description="Длина краткого содержания")


# ОТВЕТЫ С МЕТАИНФОРМАЦИЕЙ
# model_config чтобы избежать предупреждения о protected_namespaces
class ImprovedTextResponseWithMeta(ImprovedTextResponse):
    """Ответ на улучшение текста с метаинформацией (добавляется сервером)"""
    model_config = ConfigDict(protected_namespaces=())
    
    model_name: str = Field(..., description="Название модели")
    temperature: float = Field(..., description="Температура генерации")
    processing_time_ms: int = Field(..., description="Время обработки в миллисекундах")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время запроса")
    tokens_used: Optional[int] = Field(None, description="Количество использованных токенов")


class SummaryResponseWithMeta(SummaryResponse):
    """Ответ на суммаризацию с метаинформацией (добавляется сервером)"""
    model_config = ConfigDict(protected_namespaces=())
    
    model_name: str = Field(..., description="Название модели")
    temperature: float = Field(..., description="Температура генерации")
    processing_time_ms: int = Field(..., description="Время обработки в миллисекундах")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время запроса")
    tokens_used: Optional[int] = Field(None, description="Количество использованных токенов")

# УНИФИЦИРОВАННЫЕ СХЕМЫ 
# Запрос и ответ для /run (унифицированный API)
class RunRequest(BaseModel):
    """Unified request from load tester to /run endpoint."""
    content: Union[str, List[dict]] = Field(
        ...,
        description="Main input: string for text-only services.",
    )
    extra_body: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional parameters (task_type, instruction, temperature, etc.)",
    )


class RunResponse(BaseModel):
    """Unified response from /run endpoint."""
    status: Literal["success", "error"]
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class InfoResponse(BaseModel):
    """Service metadata returned by /info endpoint."""
    input_type: InputType  
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


# Конструктор схем
_UNSET = object()


class Schema:
    """Builder for JSON Schema dicts used in input_schema / output_schema."""

    @staticmethod
    def of(**kwargs: dict[str, Any]) -> dict[str, Any]:
        return {"type": "object", "properties": {k: v for k, v in kwargs.items()}}

    @staticmethod
    def string(
        description: str = "",
        default: Any = _UNSET,
        enum: Optional[List[str]] = None,
    ) -> dict[str, Any]:
        d: dict[str, Any] = {"type": "string"}
        if description:
            d["description"] = description
        if default is not _UNSET:
            d["default"] = default
        if enum is not None:
            d["enum"] = enum
        return d

    @staticmethod
    def number(
        description: str = "",
        default: Any = _UNSET,
        minimum: Optional[float] = None,
        maximum: Optional[float] = None,
    ) -> dict[str, Any]:
        d: dict[str, Any] = {"type": "number"}
        if description:
            d["description"] = description
        if default is not _UNSET:
            d["default"] = default
        if minimum is not None:
            d["minimum"] = minimum
        if maximum is not None:
            d["maximum"] = maximum
        return d

    @staticmethod
    def integer(
        description: str = "",
        default: Any = _UNSET,
        minimum: Optional[int] = None,
        maximum: Optional[int] = None,
    ) -> dict[str, Any]:
        d: dict[str, Any] = {"type": "integer"}
        if description:
            d["description"] = description
        if default is not _UNSET:
            d["default"] = default
        if minimum is not None:
            d["minimum"] = minimum
        if maximum is not None:
            d["maximum"] = maximum
        return d

    @staticmethod
    def boolean(
        description: str = "",
        default: Any = _UNSET,
    ) -> dict[str, Any]:
        d: dict[str, Any] = {"type": "boolean"}
        if description:
            d["description"] = description
        if default is not _UNSET:
            d["default"] = default
        return d

    @staticmethod
    def array(
        items: dict[str, Any],
        description: str = "",
    ) -> dict[str, Any]:
        d: dict[str, Any] = {"type": "array", "items": items}
        if description:
            d["description"] = description
        return d

    @staticmethod
    def object(
        description: str = "",
        **fields: dict[str, Any],
    ) -> dict[str, Any]:
        d: dict[str, Any] = {
            "type": "object",
            "properties": {k: v for k, v in fields.items()},
        }
        if description:
            d["description"] = description
        return d


# БАЗОВЫЙ КЛАСС СЕРВИСА
class ServiceBase(ABC):
    """
    Базовый класс сервиса для шаблона нагрузочного тестирования.
    Каждый студент должен унаследовать этот класс и реализовать:
    - get_info() — возвращает тип входных данных сервиса
    - run() — основная логика обработки запроса
    """

    @abstractmethod
    def get_info(self) -> InfoResponse:
        """Вернуть метаданные сервиса."""
        pass

    @abstractmethod
    def run(self, request: RunRequest) -> RunResponse:
        """Обработать запрос и вернуть результат."""
        pass

    # Helper-методы для извлечения данных из запроса
    def get_text(self, request: RunRequest) -> Optional[str]:
        """
        Извлечь текст из content.
        - Если content — строка, возвращает её как есть.
        - Если content — список, ищет первую часть с type="text".
        - Если текст не найден, возвращает None.
        """
        content = request.content
        if isinstance(content, str):
            return content.strip() if content.strip() else None
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "")
                    if text.strip():
                        return text.strip()
        return None