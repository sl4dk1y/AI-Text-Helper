from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ImproveTextRequest(BaseModel):
    """Запрос на улучшение текста"""
    text: str = Field(..., min_length=1, max_length=5000, description="Текст для исправления")
    instruction: str = Field(..., description="Инструкция для обработки")
    style: Optional[str] = Field(None, description="Стиль текста (official, friendly, academic)")


class SummarizeRequest(BaseModel):
    """Запрос на суммаризацию"""
    text: str = Field(..., min_length=1, max_length=10000, description="Текст для суммаризации")


class ImprovedTextResponse(BaseModel):
    """Ответ на улучшение текста с аудит-полями (Schema-Guided Reasoning)"""
    
    # Основные данные
    original_text: str = Field(..., description="Исходный текст")
    improved_text: str = Field(..., description="Исправленный текст")
    applied_instruction: str = Field(..., description="Применённая инструкция")
    changes_made: Optional[str] = Field(None, description="Список исправлений")
    
    # Аудит-поля (Schema-Guided Reasoning)
    model_name: str = Field(..., description="Название модели")
    temperature: float = Field(..., description="Температура генерации", ge=0.0, le=2.0)
    processing_time_ms: int = Field(..., description="Время обработки в миллисекундах", ge=0)
    timestamp: datetime = Field(default_factory=datetime.now, description="Время запроса")
    tokens_used: Optional[int] = Field(None, description="Количество использованных токенов", ge=0)
    
    # Валидация
    class Config:
        json_schema_extra = {
            "example": {
                "original_text": "нагода сегодня хорошая",
                "improved_text": "погода сегодня хорошая",
                "applied_instruction": "исправь ошибки",
                "changes_made": "нагода->погода",
                "model_name": "mistral",
                "temperature": 0.3,
                "processing_time_ms": 1245,
                "timestamp": "2026-03-31T21:30:00",
                "tokens_used": 150
            }
        }


class SummaryResponse(BaseModel):
    """Ответ на суммаризацию с аудит-полями (Schema-Guided Reasoning)"""
    
    # Основные данные
    summary: str = Field(..., description="Краткое содержание текста")
    keywords: list[str] = Field(default_factory=list, description="Ключевые слова (3-5 слов)")
    original_length: int = Field(..., description="Длина исходного текста", ge=0)
    summary_length: int = Field(..., description="Длина краткого содержания", ge=0)
    
    # Аудит-поля (Schema-Guided Reasoning)
    model_name: str = Field(..., description="Название модели")
    temperature: float = Field(..., description="Температура генерации", ge=0.0, le=2.0)
    processing_time_ms: int = Field(..., description="Время обработки в миллисекундах", ge=0)
    timestamp: datetime = Field(default_factory=datetime.now, description="Время запроса")
    tokens_used: Optional[int] = Field(None, description="Количество использованных токенов", ge=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "summary": "Искусственный интеллект — область компьютерных наук...",
                "keywords": ["искусственный интеллект", "машинное обучение", "нейросети"],
                "original_length": 500,
                "summary_length": 120,
                "model_name": "mistral",
                "temperature": 0.3,
                "processing_time_ms": 890,
                "timestamp": "2026-03-31T21:30:00",
                "tokens_used": 200
            }
        }