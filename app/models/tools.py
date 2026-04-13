from pydantic import BaseModel, Field
from typing import Optional, List, Tuple, Any
from datetime import datetime
from enum import Enum



# 1. Инструменты чтения (Retriever)


class SearchRequest(BaseModel):
    """Запрос к ретриверу для поиска в базе знаний"""
    query: str = Field(..., description="Поисковый запрос (слово или текст)")
    top_k: int = Field(3, description="Количество результатов", ge=1, le=10)
    min_score: float = Field(0.5, description="Минимальный порог релевантности", ge=0.0, le=1.0)


class SearchResult(BaseModel):
    """Результат поиска в базе знаний"""
    error: str = Field(..., description="Слово с ошибкой")
    correction: str = Field(..., description="Правильное написание")
    score: float = Field(..., description="Оценка релевантности")
    context: Optional[str] = Field(None, description="Контекст ошибки")


class SearchResponse(BaseModel):
    """Ответ ретривера"""
    results: List[SearchResult] = Field(default_factory=list, description="Найденные результаты")
    total_found: int = Field(0, description="Всего найдено")
    processing_time_ms: int = Field(0, description="Время обработки в миллисекундах")


class GetCorrectionRequest(BaseModel):
    """Запрос на получение исправления для слова"""
    text: str = Field(..., description="Слово или текст для поиска", min_length=1, max_length=100)


class GetCorrectionResponse(BaseModel):
    """Ответ с исправлением"""
    original: str = Field(..., description="Исходное слово")
    correction: Optional[str] = Field(None, description="Исправление (если найдено)")
    found: bool = Field(False, description="Найдено ли исправление")
    score: Optional[float] = Field(None, description="Оценка релевантности")



# 2. Инструменты расширения возможностей (LLM)


class ImproveTextRequest(BaseModel):
    """Запрос на улучшение текста"""
    text: str = Field(..., description="Текст для исправления", min_length=1, max_length=5000)
    instruction: str = Field(..., description="Инструкция для обработки")


class ImproveTextResponse(BaseModel):
    """Ответ с исправленным текстом"""
    original_text: str = Field(..., description="Исходный текст")
    improved_text: str = Field(..., description="Исправленный текст")
    applied_instruction: str = Field(..., description="Применённая инструкция")
    changes_made: Optional[str] = Field(None, description="Список исправлений")
    model_name: str = Field(..., description="Название модели")
    temperature: float = Field(..., description="Температура генерации")
    processing_time_ms: int = Field(..., description="Время обработки в миллисекундах")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время запроса")


class SummarizeRequest(BaseModel):
    """Запрос на суммаризацию текста"""
    text: str = Field(..., description="Текст для суммаризации", min_length=1, max_length=10000)


class SummarizeResponse(BaseModel):
    """Ответ с кратким содержанием"""
    summary: str = Field(..., description="Краткое содержание текста")
    keywords: List[str] = Field(default_factory=list, description="Ключевые слова")
    original_length: int = Field(..., description="Длина исходного текста")
    summary_length: int = Field(..., description="Длина краткого содержания")
    model_name: str = Field(..., description="Название модели")
    temperature: float = Field(..., description="Температура генерации")
    processing_time_ms: int = Field(..., description="Время обработки в миллисекундах")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время запроса")



# 3. Инструменты записи (Логирование)


class LogLevel(str, Enum):
    """Уровни логирования"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"


class LogRequest(BaseModel):
    """Запрос на логирование действия"""
    action: str = Field(..., description="Название действия")
    status: str = Field(..., description="Статус выполнения (success/error)")
    details: Optional[dict] = Field(None, description="Детали выполнения")
    level: LogLevel = Field(LogLevel.INFO, description="Уровень логирования")


class LogResponse(BaseModel):
    """Ответ на логирование"""
    logged: bool = Field(..., description="Успешно ли записано")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время записи")



# 4. Политики и безопасность


class ValidationRequest(BaseModel):
    """Запрос на валидацию входных данных"""
    text: str = Field(..., description="Текст для проверки")
    max_length: int = Field(5000, description="Максимальная длина текста")


class ValidationResponse(BaseModel):
    """Ответ валидации"""
    is_valid: bool = Field(..., description="Прошёл ли текст валидацию")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    sanitized_text: Optional[str] = Field(None, description="Очищенный текст")


class SuspiciousCheckRequest(BaseModel):
    """Запрос на проверку подозрительных паттернов"""
    text: str = Field(..., description="Текст для проверки")


class SuspiciousCheckResponse(BaseModel):
    """Ответ проверки на подозрительные паттерны"""
    is_suspicious: bool = Field(False, description="Является ли запрос подозрительным")
    matched_patterns: List[str] = Field(default_factory=list, description="Найденные паттерны")
    requires_human_review: bool = Field(False, description="Требуется ли проверка человеком")