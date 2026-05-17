import json
import httpx
import time
from datetime import datetime
from ..core.config import settings
from ..models.schemas import ImprovedTextResponse, SummaryResponse
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.base_url = settings.llm_base_url.rstrip('/')
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.temperature = settings.temperature

        # Инициализация ретривера
        self.retriever = None
        try:
            from .retriever import LexicalRetriever
            self.retriever = LexicalRetriever("data/knowledge_base.csv")
            logger.info("Ретривер успешно инициализирован")
        except Exception as e:
            logger.warning(f"Не удалось инициализировать ретривер: {e}")

        if not self.api_key:
            logger.error("API ключ не найден! Проверьте .env файл")
            raise ValueError("API ключ не найден")

        logger.info(f"Инициализация LLMService с моделью: {self.model}")

    async def _make_request(self, prompt: str, temperature: float = None):
        """Отправка запроса к LLM через LiteLLM"""
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "AI Text Helper"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Ты - эксперт по русскому языку. Исправляй орфографические и грамматические ошибки в тексте. Сохраняй смысл. Перед ответом подумай и запиши свои рассуждения в поле reasoning."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": settings.max_tokens,
            "response_format": {"type": "json_object"}
        }

        try:
            logger.info(f"Отправка запроса к LLM. Модель: {self.model}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=180.0
                )

                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    error_msg = data["error"].get("message", "Неизвестная ошибка")
                    logger.error(f"Ошибка LLM: {error_msg}")
                    raise Exception(f"LLM error: {error_msg}")

                if not data.get("choices") or len(data["choices"]) == 0:
                    raise Exception("Пустой ответ от LLM")

                # Читаем из reasoning_content, если content пустой (для Ollama)
                message = data["choices"][0]["message"]
                content = message.get("content") or message.get("reasoning_content") or ""

                # Безопасный парсинг JSON с фоллбэком
                try:
                    return json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    # Если модель вернула не-JSON — возвращаем как текст
                    logger.warning(f"Ответ не в формате JSON, используем как текст: {content[:100]}...")
                    return {"improved_text": content, "reasoning": "Текстовый ответ (не JSON)"}

        except httpx.TimeoutException:
            logger.error("Таймаут при запросе к LLM")
            raise Exception("Превышено время ожидания ответа от LLM")

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка: {e.response.status_code}")
            if e.response.status_code == 401:
                raise Exception("Неверный API ключ. Проверьте .env файл")
            elif e.response.status_code == 402:
                # Пробрасываем ошибку бюджета, чтобы не вызывать fallback
                raise Exception("BUDGET_EXCEEDED:402")
            elif e.response.status_code == 429:
                raise Exception("Слишком много запросов. Превышен лимит")
            else:
                raise Exception(f"HTTP ошибка {e.response.status_code}: {e.response.text}")

        except Exception as e:
            logger.error(f"Неизвестная ошибка: {e}")
            raise

    async def improve_text(self, text: str, instruction: str) -> ImprovedTextResponse:
        """Улучшение текста с использованием ретривера и Schema-Guided Reasoning"""

        start_time = time.time()

        if text == "string" or text == "":
            logger.info("Получены тестовые данные, возвращаю как есть")
            return ImprovedTextResponse(
                reasoning="Тестовый запрос, обработка не требуется.",
                original_text=text,
                improved_text=text,
                applied_instruction=instruction,
                changes_made="Тестовый запрос"
            )

        # 1. Поиск через ретривер
        retrieved_context = None
        if self.retriever:
            corrections = []
            words = text.lower().split()
            for word in words:
                correction = self.retriever.get_correction(word)
                if correction:
                    corrections.append(f"{word}->{correction}")
            
            if corrections:
                retrieved_context = f"Известные исправления: {', '.join(corrections)}"
                logger.info(f"Ретривер нашёл: {retrieved_context}")

        # 2. Формирование промпта с учётом контекста ретривера
        if retrieved_context:
            prompt = f"""
# ЗАДАЧА
Ты — профессиональный редактор русского языка. Исправь ошибки в тексте.

# БАЗА ЗНАНИЙ (найденные соответствия)
{retrieved_context}

# ИСХОДНЫЕ ДАННЫЕ
--- НАЧАЛО ТЕКСТА ---
{text}
--- КОНЕЦ ТЕКСТА ---

# ИНСТРУКЦИЯ
{instruction}

# ФОРМАТ ОТВЕТА
Верни JSON с полями в следующем порядке:
1. reasoning - твои рассуждения о том, какие ошибки ты нашёл и почему их исправил именно так
2. improved_text - исправленный текст целиком
3. changes_made - список исправлений через запятую

Пример:
{{
    "reasoning": "Я проанализировал текст. Слово 'нагода' не существует в русском языке. Ближайшее по смыслу и звучанию — 'погода'. Остальные слова написаны правильно.",
    "improved_text": "погода сегодня хорошая",
    "changes_made": "нагода->погода"
}}
"""
        else:
            prompt = f"""
# ЗАДАЧА
Ты — профессиональный редактор русского языка. Исправь ошибки в тексте.

# ИСХОДНЫЕ ДАННЫЕ
--- НАЧАЛО ТЕКСТА ---
{text}
--- КОНЕЦ ТЕКСТА ---

# ИНСТРУКЦИЯ
{instruction}

# ФОРМАТ ОТВЕТА
Верни JSON с полями в следующем порядке:
1. reasoning - твои рассуждения о том, какие ошибки ты нашёл и почему их исправил именно так
2. improved_text - исправленный текст целиком
3. changes_made - список исправлений через запятую

Пример:
{{
    "reasoning": "Я проанализировал текст. Слово 'нагода' не существует в русском языке. Ближайшее по смыслу и звучанию — 'погода'. Остальные слова написаны правильно.",
    "improved_text": "погода сегодня хорошая",
    "changes_made": "нагода->погода"
}}
"""

        try:
            logger.info(f"Отправка запроса на исправление текста: {text[:50]}...")
            result = await self._make_request(prompt, temperature=0.3)

            # Извлекаем данные из ответа
            reasoning = result.get("reasoning", "Рассуждения не предоставлены")
            improved = result.get("improved_text", result.get("text", text))
            changes_raw = result.get("changes_made", result.get("changes", "Исправления выполнены"))
            
            if isinstance(changes_raw, list):
                changes = ", ".join(changes_raw)
            else:
                changes = str(changes_raw)

            return ImprovedTextResponse(
                reasoning=reasoning,
                original_text=text,
                improved_text=improved if improved else text,  # Фоллбэк на исходный текст
                applied_instruction=instruction,
                changes_made=changes
            )
        except Exception as e:
            logger.error(f"Ошибка improve_text: {e}")
            # Обработка превышения бюджета
            if "BUDGET_EXCEEDED:402" in str(e):
                raise HTTPException(status_code=402, detail="Превышен дневной бюджет на API")
            return await self.improve_text_fallback(text, instruction)

    async def improve_text_fallback(self, text: str, instruction: str) -> ImprovedTextResponse:
        """Запасной метод для улучшения текста с reasoning"""

        # Проверка через ретривер в fallback
        retrieved_context = None
        if self.retriever:
            corrections = []
            words = text.lower().split()
            for word in words:
                correction = self.retriever.get_correction(word)
                if correction:
                    corrections.append(f"{word}->{correction}")
            
            if corrections:
                retrieved_context = f"Известные исправления: {', '.join(corrections)}"

        if retrieved_context:
            prompt = f"""
# ЗАДАЧА
Ты — редактор русского языка. Исправь ошибки в тексте.

# БАЗА ЗНАНИЙ (найденные соответствия)
{retrieved_context}

# ТЕКСТ
{text}

# ИНСТРУКЦИЯ
{instruction}

# ФОРМАТ ОТВЕТА
{{
    "reasoning": "твои рассуждения",
    "improved_text": "исправленный текст",
    "changes_made": "что исправлено"
}}
"""
        else:
            prompt = f"""
# ЗАДАЧА
Ты — редактор русского языка. Исправь ошибки в тексте.

# ТЕКСТ
{text}

# ИНСТРУКЦИЯ
{instruction}

# ФОРМАТ ОТВЕТА
{{
    "reasoning": "твои рассуждения",
    "improved_text": "исправленный текст",
    "changes_made": "что исправлено"
}}
"""

        try:
            result = await self._make_request(prompt, temperature=0.5)

            reasoning = result.get("reasoning", "Рассуждения не предоставлены")
            improved = result.get("improved_text", result.get("text", text))
            
            # Фоллбэк: если нет improved_text, берём reasoning_content или сырой текст
            if not improved and result.get("reasoning_content"):
                improved = result["reasoning_content"]

            return ImprovedTextResponse(
                reasoning=reasoning,
                original_text=text,
                improved_text=improved if improved else text,
                applied_instruction=instruction,
                changes_made=result.get("changes_made", "Исправления выполнены")
            )
        except Exception as e:
            logger.error(f"Ошибка в fallback методе: {e}")
            # Обработка превышения бюджета и в fallback
            if "BUDGET_EXCEEDED:402" in str(e):
                raise HTTPException(status_code=402, detail="Превышен дневной бюджет на API")
            
            return ImprovedTextResponse(
                reasoning=f"Произошла ошибка при обработке: {str(e)}",
                original_text=text,
                improved_text=text,
                applied_instruction=instruction,
                changes_made="Не удалось обработать текст"
            )

    async def summarize(self, text: str) -> SummaryResponse:
        """Суммаризация текста с Schema-Guided Reasoning"""

        prompt = f"""
# ЗАДАЧА
Ты — профессиональный редактор и аналитик. Создай краткое содержание текста.

# ПРАВИЛА
1. Прочитай текст и определи главную тему
2. Запиши свои рассуждения в поле reasoning (что ты выделил как главное, почему)
3. Сформулируй краткое содержание
4. Выдели 3-5 ключевых слов

# ФОРМАТ ОТВЕТА
Верни JSON с полями в следующем порядке:
1. reasoning - твои рассуждения о том, что является главной мыслью текста
2. summary - краткое содержание (2-4 предложения)
3. keywords - список ключевых слов

# ТЕКСТ
{text}

# ПРИМЕР ФОРМАТА
{{
    "reasoning": "Основная мысль текста — определение ИИ и его применение. Ключевые слова: искусственный интеллект (главный термин), машинное обучение (ключевая технология), нейросети (пример применения).",
    "summary": "Искусственный интеллект — область компьютерных наук, создающая системы для задач, требующих человеческого интеллекта.",
    "keywords": ["искусственный интеллект", "машинное обучение", "нейросети"]
}}
"""

        try:
            result = await self._make_request(prompt, temperature=0.3)

            reasoning = result.get("reasoning", "Рассуждения не предоставлены")
            summary = result.get("summary", result.get("text", ""))
            
            # Фоллбэк для summary
            if not summary and result.get("reasoning_content"):
                summary = result["reasoning_content"]

            return SummaryResponse(
                reasoning=reasoning,
                summary=summary if summary else "",
                keywords=result.get("keywords", []),
                original_length=len(text),
                summary_length=len(summary)
            )
        except Exception as e:
            logger.error(f"Ошибка summarize: {e}")
            # Обработка превышения бюджета и здесь
            if "BUDGET_EXCEEDED:402" in str(e):
                raise HTTPException(status_code=402, detail="Превышен дневной бюджет на API")
            
            return SummaryResponse(
                reasoning=f"Произошла ошибка при суммаризации: {str(e)}",
                summary="",
                keywords=[],
                original_length=len(text),
                summary_length=0
            )