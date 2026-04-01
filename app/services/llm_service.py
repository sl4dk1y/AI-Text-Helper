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
                    "content": "Ты - эксперт по русскому языку. Исправляй орфографические и грамматические ошибки в тексте. Сохраняй смысл."
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
        """Улучшение текста с применением лучших практик промпт-инжиниринга"""

        start_time = time.time()

        if text == "string" or text == "":
            logger.info("Получены тестовые данные, возвращаю как есть")
            return ImprovedTextResponse(
                original_text=text,
                improved_text=text,
                applied_instruction=instruction,
                changes_made="Тестовый запрос",
                model_name=self.model,
                temperature=self.temperature,
                processing_time_ms=0,
                timestamp=datetime.now(),
                tokens_used=None
            )

        prompt = f"""
        # ЗАДАЧА
        Ты — профессиональный редактор русского языка. Твоя задача — исправлять орфографические и грамматические ошибки в тексте, следуя правилам русского языка.

        # КОНТЕКСТ
        Пользователь отправляет текст, который может содержать ошибки. Нужно:
        - Сохранить смысл текста
        - Не добавлять лишнюю информацию
        - Исправить только ошибки

        # ИСХОДНЫЕ ДАННЫЕ
        --- НАЧАЛО ТЕКСТА ---
        {text}
        --- КОНЕЦ ТЕКСТА ---

        # ИНСТРУКЦИЯ
        {instruction}

        # АЛГОРИТМ ДЕЙСТВИЙ
        1. Прочитай текст и определи, есть ли в нём ошибки
        2. Найди орфографические ошибки (неправильное написание слов)
        3. Найди грамматические ошибки (неправильное окончание, падеж, род)
        4. Исправь найденные ошибки
        5. Составь список исправлений в формате "ошибка->исправление"

        # ФОРМАТ ОТВЕТА
        Ответ должен быть строго в формате JSON. Никакого дополнительного текста вне JSON.

        {{
            "improved_text": "исправленный текст целиком",
            "changes_made": "список исправлений через запятую"
        }}

        # ПРИМЕР (для понимания формата)
        Вход: "я пашел в магазин"
        Выход: {{"improved_text": "я пошел в магазин", "changes_made": "пашел->пошел"}}

        # ВАЖНО
        - Ответь только JSON
        - Не добавляй пояснений
        - Не меняй смысл текста
        - Исправляй только реальные ошибки
        """

        try:
            logger.info(f"Отправка запроса на исправление текста: {text[:50]}...")
            result = await self._make_request(prompt, temperature=0.3)

            processing_time_ms = int((time.time() - start_time) * 1000)

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
        """Запасной метод для улучшения текста"""

        if start_time is None:
            start_time = time.time()

        prompt = f"""
        # ЗАДАЧА
        Ты — редактор русского языка. Исправь ошибки в тексте.

        # ИСХОДНЫЕ ДАННЫЕ
        --- НАЧАЛО ТЕКСТА ---
        {text}
        --- КОНЕЦ ТЕКСТА ---

        # ИНСТРУКЦИЯ
        {instruction}

        # ФОРМАТ ОТВЕТА
        {{
            "improved_text": "исправленный текст",
            "changes_made": "что исправлено"
        }}
        """

        try:
            result = await self._make_request(prompt, temperature=0.5)

            processing_time_ms = int((time.time() - start_time) * 1000)

            return ImprovedTextResponse(
                original_text=text,
                improved_text=result.get("improved_text", result.get("text", text)),
                applied_instruction=instruction,
                changes_made=result.get("changes_made", "Исправления выполнены"),
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
                model_name=self.model,
                temperature=self.temperature,
                processing_time_ms=processing_time_ms,
                timestamp=datetime.now(),
                tokens_used=None
            )

    async def summarize(self, text: str) -> SummaryResponse:
        """Суммаризация текста с применением лучших практик промпт-инжиниринга"""

        start_time = time.time()

        prompt = f"""
        # ЗАДАЧА
        Ты — профессиональный редактор и аналитик. Твоя задача — создавать краткое содержание текста и выделять ключевые слова.

        # КОНТЕКСТ
        Пользователь отправляет длинный текст. Нужно:
        - Сократить текст, сохранив основную мысль
        - Выделить 3-5 ключевых слов
        - Сохранить язык оригинала

        # ИСХОДНЫЕ ДАННЫЕ
        --- НАЧАЛО ТЕКСТА ---
        {text}
        --- КОНЕЦ ТЕКСТА ---

        # АЛГОРИТМ ДЕЙСТВИЙ
        1. Прочитай текст и определи главную тему
        2. Выдели основные мысли (обычно 1-3 предложения)
        3. Сформулируй краткое содержание своими словами
        4. Выдели 3-5 ключевых слов, отражающих суть текста
        5. Убедись, что ключевые слова на том же языке, что и текст

        # ФОРМАТ ОТВЕТА
        Ответ должен быть строго в формате JSON. Никакого дополнительного текста вне JSON.

        {{
            "summary": "краткое содержание текста (2-4 предложения)",
            "keywords": ["ключевое_слово1", "ключевое_слово2", "ключевое_слово3"]
        }}

        # ВАЖНО
        - Ответь только JSON
        - Не добавляй пояснений
        - Сохрани смысл исходного текста
        - Ключевые слова должны быть на том же языке, что и текст
        """

        try:
            result = await self._make_request(prompt, temperature=0.3)

            processing_time_ms = int((time.time() - start_time) * 1000)

            return SummaryResponse(
                summary=result.get("summary", result.get("text", "")),
                keywords=result.get("keywords", []),
                original_length=len(text),
                summary_length=len(result.get("summary", result.get("text", ""))),
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
                model_name=self.model,
                temperature=0.3,
                processing_time_ms=processing_time_ms,
                timestamp=datetime.now(),
                tokens_used=None
            )