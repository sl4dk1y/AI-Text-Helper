from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

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
    
    # Reasoning 
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

class ImprovedTextResponseWithMeta(ImprovedTextResponse):
    """Ответ на улучшение текста с метаинформацией (добавляется сервером)"""
    
    model_name: str = Field(..., description="Название модели")
    temperature: float = Field(..., description="Температура генерации")
    processing_time_ms: int = Field(..., description="Время обработки в миллисекундах")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время запроса")
    tokens_used: Optional[int] = Field(None, description="Количество использованных токенов")


class SummaryResponseWithMeta(SummaryResponse):
    """Ответ на суммаризацию с метаинформацией (добавляется сервером)"""
    
    model_name: str = Field(..., description="Название модели")
    temperature: float = Field(..., description="Температура генерации")
    processing_time_ms: int = Field(..., description="Время обработки в миллисекундах")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время запроса")
    tokens_used: Optional[int] = Field(None, description="Количество использованных токенов")