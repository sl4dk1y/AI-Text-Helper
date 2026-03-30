import json
import httpx
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
        """Улучшение текста"""
        
        if text == "string" or text == "":
            logger.info("Получены тестовые данные, возвращаю как есть")
            return ImprovedTextResponse(
                original_text=text,
                improved_text=text,
                applied_instruction=instruction,
                changes_made="Тестовый запрос"
            )
        
        prompt = f"""
        Текст для исправления: "{text}"
        Инструкция: {instruction}
        
        Ответ должен содержать:
        - improved_text: исправленный текст
        - changes_made: список исправлений (например, "нагода->погода")
        """
        
        try:
            logger.info(f"Отправка запроса на исправление текста: {text[:50]}...")
            result = await self._make_request(prompt, temperature=0.3)
            
            improved = result.get("improved_text", result.get("text", text))
            changes = result.get("changes_made", result.get("changes", "Исправления выполнены"))
            
            return ImprovedTextResponse(
                original_text=text,
                improved_text=improved,
                applied_instruction=instruction,
                changes_made=changes
            )
        except Exception as e:
            logger.error(f"Ошибка improve_text: {e}")
            return await self.improve_text_fallback(text, instruction)

    async def improve_text_fallback(self, text: str, instruction: str) -> ImprovedTextResponse:
        """Запасной метод"""
        
        prompt = f"""
        Текст: "{text}"
        Инструкция: {instruction}
        
        Ответ должен содержать:
        - improved_text: исправленный текст
        - changes_made: что исправлено
        """
        
        try:
            result = await self._make_request(prompt, temperature=0.5)
            return ImprovedTextResponse(
                original_text=text,
                improved_text=result.get("improved_text", result.get("text", text)),
                applied_instruction=instruction,
                changes_made=result.get("changes_made", "Исправления выполнены")
            )
        except Exception as e:
            logger.error(f"Ошибка в fallback методе: {e}")
            return ImprovedTextResponse(
                original_text=text,
                improved_text=text,
                applied_instruction=instruction,
                changes_made="Не удалось обработать текст"
            )
    
    async def summarize(self, text: str) -> SummaryResponse:
        """Суммаризация текста"""
        prompt = f"""
        Текст: "{text}"
        
        Ответ должен содержать:
        - summary: краткое содержание текста
        - keywords: список ключевых слов (3-5 слов)
        """
        
        try:
            result = await self._make_request(prompt, temperature=0.3)
            
            return SummaryResponse(
                summary=result.get("summary", result.get("text", "")),
                keywords=result.get("keywords", []),
                original_length=len(text),
                summary_length=len(result.get("summary", result.get("text", "")))
            )
        except Exception as e:
            logger.error(f"Ошибка summarize: {e}")
            raise