import json
import httpx
import time
from datetime import datetime
from ..core.config import settings
from ..models.schemas import ImprovedTextResponse, SummaryResponse
import logging

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
            logger.error("API ключ OpenRouter не найден! Проверьте .env файл")
            raise ValueError("API ключ OpenRouter не найден")

        logger.info(f"Инициализация LLMService с моделью: {self.model}")

    async def _make_request(self, prompt: str, temperature: float = None):
        """Отправка запроса к OpenRouter"""
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
            logger.info(f"Отправка запроса к OpenRouter. Модель: {self.model}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )

                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    error_msg = data["error"].get("message", "Неизвестная ошибка")
                    logger.error(f"Ошибка OpenRouter: {error_msg}")
                    raise Exception(f"OpenRouter error: {error_msg}")

                if not data.get("choices") or len(data["choices"]) == 0:
                    raise Exception("Пустой ответ от OpenRouter")

                content = data["choices"][0]["message"]["content"]

                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    logger.error(f"Не удалось распарсить JSON ответ: {content}")
                    return {"text": content}

        except httpx.TimeoutException:
            logger.error("Таймаут при запросе к OpenRouter")
            raise Exception("Превышено время ожидания ответа от OpenRouter")

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка: {e.response.status_code}")
            if e.response.status_code == 401:
                raise Exception("Неверный API ключ OpenRouter. Проверьте .env файл")
            elif e.response.status_code == 402:
                raise Exception("Недостаточно средств на счете OpenRouter. Используйте бесплатную модель")
            elif e.response.status_code == 429:
                raise Exception("Слишком много запросов. Лимит OpenRouter")
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
                original_text=text,
                improved_text=text,
                applied_instruction=instruction,
                changes_made="Тестовый запрос",
                reasoning="Тестовый запрос, обработка не требуется.",
                model_name=self.model,
                temperature=self.temperature,
                processing_time_ms=0,
                timestamp=datetime.now(),
                tokens_used=None
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

        # 2. Формирование промпта с учётом контекста ретривера и требованием reasoning
        base_prompt = """
# ЗАДАЧА
Ты — профессиональный редактор русского языка. Исправь ошибки в тексте.

# ПРАВИЛА
1. Проанализируй текст и найди орфографические и грамматические ошибки
2. Запиши свои рассуждения в поле reasoning (что ты нашёл, почему решил исправить именно так)
3. Исправь найденные ошибки
4. Составь список исправлений

# ФОРМАТ ОТВЕТА
Верни JSON с четырьмя полями:
- reasoning: твои рассуждения о том, какие ошибки ты нашёл и почему их исправил именно так
- improved_text: исправленный текст целиком
- changes_made: список исправлений через запятую
"""

        if retrieved_context:
            prompt = f"""
{base_prompt}

# БАЗА ЗНАНИЙ (найденные соответствия)
{retrieved_context}

# ИСХОДНЫЕ ДАННЫЕ
--- НАЧАЛО ТЕКСТА ---
{text}
--- КОНЕЦ ТЕКСТА ---

# ИНСТРУКЦИЯ
{instruction}

# ПРИМЕР ФОРМАТА
{{
    "reasoning": "Я проанализировал текст. Слово 'нагода' не существует в русском языке. Ближайшее по смыслу и звучанию — 'погода'. Остальные слова написаны правильно.",
    "improved_text": "погода сегодня хорошая",
    "changes_made": "нагода->погода"
}}
"""
        else:
            prompt = f"""
{base_prompt}

# ИСХОДНЫЕ ДАННЫЕ
--- НАЧАЛО ТЕКСТА ---
{text}
--- КОНЕЦ ТЕКСТА ---

# ИНСТРУКЦИЯ
{instruction}

# ПРИМЕР ФОРМАТА
{{
    "reasoning": "Я проанализировал текст. Слово 'нагода' не существует в русском языке. Ближайшее по смыслу и звучанию — 'погода'. Остальные слова написаны правильно.",
    "improved_text": "погода сегодня хорошая",
    "changes_made": "нагода->погода"
}}
"""

        try:
            logger.info(f"Отправка запроса на исправление текста: {text[:50]}...")
            result = await self._make_request(prompt, temperature=0.3)

            processing_time_ms = int((time.time() - start_time) * 1000)

            # Извлекаем данные из ответа
            reasoning = result.get("reasoning", "Рассуждения не предоставлены")
            improved = result.get("improved_text", result.get("text", text))
            changes_raw = result.get("changes_made", result.get("changes", "Исправления выполнены"))
            
            if isinstance(changes_raw, list):
                changes = ", ".join(changes_raw)
            else:
                changes = str(changes_raw)

            return ImprovedTextResponse(
                original_text=text,
                improved_text=improved,
                applied_instruction=instruction,
                changes_made=changes,
                reasoning=reasoning,
                model_name=self.model,
                temperature=self.temperature,
                processing_time_ms=processing_time_ms,
                timestamp=datetime.now(),
                tokens_used=None
            )
        except Exception as e:
            logger.error(f"Ошибка improve_text: {e}")
            return await self.improve_text_fallback(text, instruction, start_time)

    async def improve_text_fallback(self, text: str, instruction: str, start_time: float = None) -> ImprovedTextResponse:
        """Запасной метод для улучшения текста с reasoning"""

        if start_time is None:
            start_time = time.time()

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

        base_prompt = """
# ЗАДАЧА
Ты — редактор русского языка. Исправь ошибки в тексте.

# ФОРМАТ ОТВЕТА
Верни JSON с четырьмя полями:
- reasoning: твои рассуждения
- improved_text: исправленный текст
- changes_made: что исправлено
"""

        if retrieved_context:
            prompt = f"""
{base_prompt}

# БАЗА ЗНАНИЙ (найденные соответствия)
{retrieved_context}

# ТЕКСТ
{text}

# ИНСТРУКЦИЯ
{instruction}
"""
        else:
            prompt = f"""
{base_prompt}

# ТЕКСТ
{text}

# ИНСТРУКЦИЯ
{instruction}
"""

        try:
            result = await self._make_request(prompt, temperature=0.5)

            processing_time_ms = int((time.time() - start_time) * 1000)

            reasoning = result.get("reasoning", "Рассуждения не предоставлены")

            return ImprovedTextResponse(
                original_text=text,
                improved_text=result.get("improved_text", result.get("text", text)),
                applied_instruction=instruction,
                changes_made=result.get("changes_made", "Исправления выполнены"),
                reasoning=reasoning,
                model_name=self.model,
                temperature=0.5,
                processing_time_ms=processing_time_ms,
                timestamp=datetime.now(),
                tokens_used=None
            )
        except Exception as e:
            logger.error(f"Ошибка в fallback методе: {e}")
            processing_time_ms = int((time.time() - start_time) * 1000)

            return ImprovedTextResponse(
                original_text=text,
                improved_text=text,
                applied_instruction=instruction,
                changes_made="Не удалось обработать текст",
                reasoning=f"Произошла ошибка при обработке: {str(e)}",
                model_name=self.model,
                temperature=self.temperature,
                processing_time_ms=processing_time_ms,
                timestamp=datetime.now(),
                tokens_used=None
            )

    async def summarize(self, text: str) -> SummaryResponse:
        """Суммаризация текста с Schema-Guided Reasoning"""

        start_time = time.time()

        prompt = f"""
# ЗАДАЧА
Ты — профессиональный редактор и аналитик. Создай краткое содержание текста.

# ПРАВИЛА
1. Прочитай текст и определи главную тему
2. Запиши свои рассуждения в поле reasoning (что ты выделил как главное, почему)
3. Сформулируй краткое содержание
4. Выдели 3-5 ключевых слов

# ФОРМАТ ОТВЕТА
Верни JSON с тремя полями:
- reasoning: твои рассуждения о том, что является главной мыслью текста
- summary: краткое содержание (2-4 предложения)
- keywords: список ключевых слов

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

            processing_time_ms = int((time.time() - start_time) * 1000)

            reasoning = result.get("reasoning", "Рассуждения не предоставлены")

            return SummaryResponse(
                summary=result.get("summary", result.get("text", "")),
                keywords=result.get("keywords", []),
                original_length=len(text),
                summary_length=len(result.get("summary", result.get("text", ""))),
                reasoning=reasoning,
                model_name=self.model,
                temperature=0.3,
                processing_time_ms=processing_time_ms,
                timestamp=datetime.now(),
                tokens_used=None
            )
        except Exception as e:
            logger.error(f"Ошибка summarize: {e}")
            processing_time_ms = int((time.time() - start_time) * 1000)

            return SummaryResponse(
                summary="",
                keywords=[],
                original_length=len(text),
                summary_length=0,
                reasoning=f"Произошла ошибка при суммаризации: {str(e)}",
                model_name=self.model,
                temperature=0.3,
                processing_time_ms=processing_time_ms,
                timestamp=datetime.now(),
                tokens_used=None
            )