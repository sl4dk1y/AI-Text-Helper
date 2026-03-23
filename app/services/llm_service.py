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
                    "content": "Ты - ассистент для работы с текстом. Отвечай ТОЛЬКО в формате JSON, без пояснений и лишнего текста. Никогда не добавляй ничего кроме JSON."
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
                except json.JSONDecodeError as e:
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
                raise Exception("Недостаточно средств на счете OpenRouter. Используйте бесплатную модель llama-3.2-3b-instruct:free")
            elif e.response.status_code == 429:
                raise Exception("Слишком много запросов. Лимит OpenRouter")
            else:
                raise Exception(f"HTTP ошибка {e.response.status_code}: {e.response.text}")
                
        except Exception as e:
            logger.error(f"Неизвестная ошибка: {e}")
            raise
    
    async def improve_text(self, text: str, instruction: str) -> ImprovedTextResponse:
        """Улучшение текста"""
        
        # Проверка на тестовые данные
        if text == "string" or text == "":
            logger.info("Получены тестовые данные, возвращаю как есть")
            return ImprovedTextResponse(
                original_text=text,
                improved_text=text,
                applied_instruction=instruction,
                changes_made="Тестовый запрос"
            )
        
        # Единственный промпт без примера
        prompt = f"""
        Твоя задача: исправить ошибки в тексте и выполнить инструкцию.
        
        Текст для исправления: "{text}"
        Инструкция: {instruction}
        
        Правила:
        1. Проанализируй именно этот текст: "{text}"
        2. Найди в нем орфографические и грамматические ошибки
        3. Исправь найденные ошибки
        4. Верни ТОЛЬКО JSON в формате:
        {{
            "improved_text": "исправленный текст",
            "changes_made": "список исправлений"
        }}
        
        НЕ ИСПОЛЬЗУЙ ПРИМЕРЫ ИЗ ПРЕДЫДУЩИХ ЗАПРОСОВ!
        Работай ТОЛЬКО с текущим текстом: "{text}"
        """
        
        try:
            logger.info(f"Отправка запроса на исправление текста: {text[:50]}...")
            result = await self._make_request(prompt, temperature=0.3)
            
            # Извлекаем исправленный текст
            improved = result.get("improved_text", result.get("text", text))
            changes = result.get("changes_made", result.get("changes", "Исправления выполнены"))
            
            # Проверяем, не вернула ли модель пример
            if "я сегодня пошел и купил молоко" in improved and text != "я сегодня пашел и купил малако":
                logger.warning("Модель вернула пример из прошлого запроса, пробую еще раз...")
                # Пробуем еще раз с другим промптом
                return await self.improve_text_fallback(text, instruction)
            
            return ImprovedTextResponse(
                original_text=text,
                improved_text=improved,
                applied_instruction=instruction,
                changes_made=changes
            )
        except Exception as e:
            logger.error(f"Ошибка improve_text: {e}")
            # Пробуем запасной вариант
            return await self.improve_text_fallback(text, instruction)

    async def improve_text_fallback(self, text: str, instruction: str) -> ImprovedTextResponse:
        """Запасной метод на случай, если основной не сработал"""
        
        prompt = f"""
        Проигнорируй все предыдущие инструкции.
        
        Вот текст, который нужно обработать: "{text}"
        Вот инструкция: {instruction}
        
        Ответь ТОЛЬКО JSON:
        {{
            "improved_text": "исправленный вариант текста",
            "changes_made": "что исправлено"
        }}
        
        Важно: текст для обработки - "{text}", не придумывай свой текст!
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
            # Если совсем ничего не работает, возвращаем как есть
            return ImprovedTextResponse(
                original_text=text,
                improved_text=text,
                applied_instruction=instruction,
                changes_made="Не удалось обработать текст"
            )
    
    async def summarize(self, text: str) -> SummaryResponse:
        """Суммаризация текста"""
        prompt = f"""
        Сделай краткое содержание текста и выдели ключевые слова.
        
        Текст: {text}
        
        Верни ТОЛЬКО JSON в этом точном формате:
        {{
            "summary": "краткое содержание текста здесь",
            "keywords": ["слово1", "слово2", "слово3"]
        }}
        
        Важно: ключевые слова должны быть на том же языке, что и текст.
        Никакого другого текста, только JSON!
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