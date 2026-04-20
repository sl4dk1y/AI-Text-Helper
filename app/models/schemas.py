from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Запросы (с мета-информацией)
class ImproveTextRequest(BaseModel):
    """Запрос на улучшение текста"""
    text: str = Field(..., min_length=1, max_length=5000, description="Текст для исправления")
    instruction: str = Field(..., description="Инструкция для обработки")
    style: Optional[str] = Field(None, description="Стиль текста (official, friendly, academic)")
    
    # Мета-информация запроса
    request_id: Optional[str] = Field(None, description="Уникальный идентификатор запроса")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время отправки запроса")
    user_id: Optional[str] = Field(None, description="Идентификатор пользователя")
    session_id: Optional[str] = Field(None, description="Идентификатор сессии")


class SummarizeRequest(BaseModel):
    """Запрос на суммаризацию"""
    text: str = Field(..., min_length=1, max_length=10000, description="Текст для суммаризации")
    
    # Мета-информация запроса
    request_id: Optional[str] = Field(None, description="Уникальный идентификатор запроса")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время отправки запроса")
    user_id: Optional[str] = Field(None, description="Идентификатор пользователя")
    session_id: Optional[str] = Field(None, description="Идентификатор сессии")



# Ответы (с reasoning trace)
class ImprovedTextResponse(BaseModel):
    """Ответ на улучшение текста с Schema-Guided Reasoning"""
    
    # Chain-of-Thought 
    reasoning: Optional[str] = Field(
        None, 
        description="Рассуждения модели: как были найдены ошибки, почему выбраны именно эти исправления"
    )
    
    # Основные данные
    original_text: str = Field(..., description="Исходный текст")
    improved_text: str = Field(..., description="Исправленный текст")
    applied_instruction: str = Field(..., description="Применённая инструкция")
    changes_made: Optional[str] = Field(None, description="Список исправлений")
    
    # Аудит-поля
    model_name: str = Field(..., description="Название модели")
    temperature: float = Field(..., description="Температура генерации", ge=0.0, le=2.0)
    processing_time_ms: int = Field(..., description="Время обработки в миллисекундах", ge=0)
    timestamp: datetime = Field(default_factory=datetime.now, description="Время запроса")
    tokens_used: Optional[int] = Field(None, description="Количество использованных токенов", ge=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "reasoning": "Я проанализировал текст. Слово 'нагода' отсутствует в словаре, вероятно, имеется в виду 'погода'. Остальные слова написаны правильно.",
                "original_text": "нагода сегодня хорошая",
                "improved_text": "погода сегодня хорошая",
                "applied_instruction": "исправь ошибки",
                "changes_made": "нагода->погода",
                "model_name": "mistral",
                "temperature": 0.3,
                "processing_time_ms": 1245,
                "timestamp": "2026-04-20T21:30:00",
                "tokens_used": 150
            }
        }


class SummaryResponse(BaseModel):
    """Ответ на суммаризацию с Schema-Guided Reasoning"""
    
    # Chain-of-Thought
    reasoning: Optional[str] = Field(
        None,
        description="Рассуждения модели: как была выделена главная мысль, почему выбраны эти ключевые слова"
    )
    
    # Основные данные
    summary: str = Field(..., description="Краткое содержание текста")
    keywords: List[str] = Field(default_factory=list, description="Ключевые слова (3-5 слов)")
    original_length: int = Field(..., description="Длина исходного текста", ge=0)
    summary_length: int = Field(..., description="Длина краткого содержания", ge=0)
    
    # Аудит-поля
    model_name: str = Field(..., description="Название модели")
    temperature: float = Field(..., description="Температура генерации", ge=0.0, le=2.0)
    processing_time_ms: int = Field(..., description="Время обработки в миллисекундах", ge=0)
    timestamp: datetime = Field(default_factory=datetime.now, description="Время запроса")
    tokens_used: Optional[int] = Field(None, description="Количество использованных токенов", ge=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "reasoning": "Основная мысль текста — определение ИИ и его применение. Ключевые слова: искусственный интеллект (главный термин), машинное обучение (ключевая технология), нейросети (пример применения).",
                "summary": "Искусственный интеллект — область компьютерных наук, создающая системы для задач, требующих человеческого интеллекта.",
                "keywords": ["искусственный интеллект", "машинное обучение", "нейросети"],
                "original_length": 500,
                "summary_length": 120,
                "model_name": "mistral",
                "temperature": 0.3,
                "processing_time_ms": 890,
                "timestamp": "2026-04-20T21:30:00",
                "tokens_used": 200
            }
        }