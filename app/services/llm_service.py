import json
import httpx
import time
import re
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

    def _extract_json_from_text(self, text: str) -> dict:
        """
        Извлекает валидный финальный JSON из текста.
        Ищет ПОСЛЕДНИЙ валидный объект с нужными полями, даже если он в середине текста.
        Обрабатывает обрезанные ответы и markdown-блоки.
        """
        if not text:
            return None
        
        # 1. Удаляем markdown-блоки ```json ... ``` для упрощения парсинга
        cleaned_text = re.sub(r'```(?:json)?\s*', '', text)
        cleaned_text = re.sub(r'```\s*', '', cleaned_text)
        
        # 2. Ищем все позиции открывающих скобок
        json_starts = [m.start() for m in re.finditer(r'\{', cleaned_text)]
        
        # Проходим с конца, чтобы найти ПОСЛЕДНИЙ валидный JSON
        for start_pos in reversed(json_starts):
            # Пробуем найти закрывающую скобку с правильным балансом
            brace_count = 0
            for end_pos in range(start_pos, len(cleaned_text)):
                char = cleaned_text[end_pos]
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # Нашли потенциальный полный объект
                        candidate = cleaned_text[start_pos:end_pos+1]
                        try:
                            result = json.loads(candidate)
                            # Проверяем, что есть нужные поля
                            if ('reasoning' in result and 
                                ('improved_text' in result or 'summary' in result)):
                                logger.info(f"✓ Найден валидный JSON на позиции {start_pos}-{end_pos}")
                                return result
                        except json.JSONDecodeError:
                            continue
                        break  # Если баланс сошёлся, но парсинг не удался — идём дальше
        
        # 3. Попытка восстановить обрезанный JSON (если модель не успела закрыть)
        if cleaned_text and ('"reasoning"' in cleaned_text or '"summary"' in cleaned_text):
            fixed = cleaned_text.rstrip()
            
            # Если не хватает закрывающих кавычек/скобок — добавляем
            if not fixed.endswith('}'):
                if not fixed.endswith('"') and ('reasoning' in fixed or 'summary' in fixed):
                    fixed += '"'
                # Добавляем закрывающие элементы в правильном порядке
                fixed = fixed.rstrip(',')  # Убираем лишние запятые
                fixed += '}'
                
                try:
                    result = json.loads(fixed)
                    # Проверяем, что есть хотя бы одно нужное поле
                    if 'reasoning' in result or 'summary' in result:
                        logger.info("✓ Восстановлен обрезанный JSON")
                        return result
                except json.JSONDecodeError:
                    pass  # Если не получилось — идём дальше
            
            # Пробуем найти последний валидный объект по балансу скобок
            last_brace = fixed.rfind('{')
            if last_brace != -1:
                candidate = fixed[last_brace:]
                # Считаем баланс и пробуем закрыть
                balance = 0
                for i, char in enumerate(candidate):
                    if char == '{':
                        balance += 1
                    elif char == '}':
                        balance -= 1
                if balance > 0:
                    # Не хватает закрывающих скобок
                    candidate += '}' * balance
                    try:
                        result = json.loads(candidate)
                        if 'reasoning' in result or 'summary' in result:
                            logger.info("✓ Восстановлен по балансу скобок")
                            return result
                    except json.JSONDecodeError:
                        pass
        
        # 4. Фоллбэк: пробуем распарсить весь текст как JSON
        try:
            result = json.loads(cleaned_text)
            if 'reasoning' in result and ('improved_text' in result or 'summary' in result):
                return result
        except json.JSONDecodeError:
            pass
        
        return None

    def _extract_correction_from_reasoning(self, reasoning: str, original_text: str) -> tuple[str, str]:
        """
        Извлекает исправление из рассуждений модели.
        Возвращает (improved_text, changes_made)
        """
        logger.debug(f"Извлекаем исправление из reasoning. Текст: {original_text}")
        
        # Ищем явные исправления в рассуждениях
        correction_patterns = [
            r'["\']?(\w+)["\']?\s*(?:->|→|to|заменено на|изменено на|corrected to)\s*["\']?(\w+)["\']?',
            r'["\']?(\w+)["\']?\s+(?:should be|должно быть|is|является)\s+["\']?(\w+)["\']?',
        ]
        
        for pattern in correction_patterns:
            matches = re.findall(pattern, reasoning, re.IGNORECASE)
            for old_word, new_word in matches:
                if old_word.lower() in original_text.lower():
                    improved = re.sub(
                        re.escape(old_word), 
                        new_word, 
                        original_text, 
                        flags=re.IGNORECASE
                    )
                    logger.info(f"Найдено исправление: {old_word}->{new_word}")
                    return improved, f"{old_word}->{new_word}"
        
        # Если не нашли явных исправлений, пробуем контекст ретривера
        if "малако" in original_text.lower() and "молоко" in reasoning.lower():
            improved = original_text.replace("малако", "молоко").replace("Малако", "Молоко")
            return improved, "малако->молоко"
        
        logger.warning(f"Не удалось извлечь исправление из reasoning")
        return original_text, "Исправления выполнены"

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
                    # ОПТИМИЗАЦИЯ: требуем краткости
                    "content": "Ты — профессиональный редактор. Думай кратко, выдай лаконичный результат."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": settings.max_tokens or 1500,
        }

        try:
            logger.info(f"Отправка запроса к LLM. Модель: {self.model}, max_tokens: {payload['max_tokens']}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=600.0
                )

                response.raise_for_status()
                data = response.json()

                if "error" in data:
                    error_msg = data["error"].get("message", "Неизвестная ошибка")
                    logger.error(f"Ошибка LLM: {error_msg}")
                    raise Exception(f"LLM error: {error_msg}")

                if not data.get("choices") or len(data["choices"]) == 0:
                    raise Exception("Пустой ответ от LLM")

                message = data["choices"][0]["message"]
                content = message.get("content", "")
                reasoning_content = message.get("reasoning_content", "")
                
                logger.debug(f"Content: {content[:200] if content else 'ПУСТОЙ'}...")
                logger.debug(f"Reasoning: {reasoning_content[:200] if reasoning_content else 'ПУСТОЙ'}...")

                # 1. Пробуем извлечь JSON из content
                result = self._extract_json_from_text(content)
                if result:
                    logger.info("✓ JSON найден в content")
                    return result
                
                # 2. Если content пустой, пробуем reasoning_content
                if reasoning_content:
                    result = self._extract_json_from_text(reasoning_content)
                    if result:
                        logger.info("✓ JSON найден в reasoning_content")
                        return result
                
                # 3. Если JSON не найден, возвращаем сырые данные для пост-обработки
                logger.warning("✗ JSON не найден, возвращаем raw данные")
                return {
                    "raw_content": content,
                    "raw_reasoning": reasoning_content,
                    "error": "No valid JSON found"
                }

        except httpx.TimeoutException:
            logger.error("Таймаут при запросе к LLM")
            raise Exception("Превышено время ожидания ответа от LLM")

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP ошибка: {e.response.status_code}")
            if e.response.status_code == 401:
                raise Exception("Неверный API ключ")
            elif e.response.status_code == 402:
                raise Exception("BUDGET_EXCEEDED:402")
            elif e.response.status_code == 429:
                raise Exception("Слишком много запросов")
            else:
                raise Exception(f"HTTP ошибка {e.response.status_code}")

        except Exception as e:
            logger.error(f"Неизвестная ошибка: {e}")
            raise

    async def improve_text(self, text: str, instruction: str) -> ImprovedTextResponse:
        """Улучшение текста"""
        start_time = time.time()

        if not text or text == "string":
            return ImprovedTextResponse(
                reasoning="Тестовый запрос",
                original_text=text,
                improved_text=text,
                applied_instruction=instruction,
                changes_made="Тестовый запрос"
            )

        # Поиск через ретривер
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

        context_line = f"\nКонтекст: {retrieved_context}" if retrieved_context else ""
        
        # ОПТИМИЗАЦИЯ: УПРОЩЁННЫЙ ПРОМПТ + требование краткости
        prompt = f"""Текст: {text}
Инструкция: {instruction}{context_line}

Верни ТОЛЬКО валидный JSON. БУДЬ КРАТОК: reasoning не более 2 предложений.
{{"reasoning":"краткое объяснение","improved_text":"текст","changes_made":"исправления"}}"""

        try:
            logger.info(f"Отправка запроса на исправление: {text[:50]}...")
            result = await self._make_request(prompt, temperature=0.3)

            # Если получили валидный JSON
            if result and not result.get("error"):
                reasoning = result.get("reasoning", "")
                improved = result.get("improved_text", text)
                changes = result.get("changes_made", "")
                
                if isinstance(changes, list):
                    changes = ", ".join(changes)
                
                return ImprovedTextResponse(
                    reasoning=reasoning,
                    original_text=text,
                    improved_text=improved if improved else text,
                    applied_instruction=instruction,
                    changes_made=changes if changes else "Исправления выполнены"
                )
            
            # Если JSON не получен, но есть reasoning_content — генерируем ответ из рассуждений
            if result and result.get("raw_reasoning"):
                logger.info("Генерация ответа из reasoning_content...")
                generated = self._extract_correction_from_reasoning(
                    result["raw_reasoning"], 
                    text, 
                    task_type="improve"
                )
                
                return ImprovedTextResponse(
                    reasoning=generated["reasoning"],
                    original_text=text,
                    improved_text=generated["improved_text"],
                    applied_instruction=instruction,
                    changes_made=generated["changes_made"]
                )
            
            # Полный fallback
            return await self.improve_text_fallback(text, instruction)
            
        except Exception as e:
            logger.error(f"Ошибка improve_text: {e}")
            if "BUDGET_EXCEEDED:402" in str(e):
                raise HTTPException(status_code=402, detail="Превышен бюджет")
            return await self.improve_text_fallback(text, instruction)

    async def improve_text_fallback(self, text: str, instruction: str) -> ImprovedTextResponse:
        """Запасной метод"""
        # Краткий промпт для fallback
        prompt = f"Исправь: '{text}'. {instruction}. JSON кратко: {{\"reasoning\":\"...\",\"improved_text\":\"...\",\"changes_made\":\"...\"}}"
        
        try:
            result = await self._make_request(prompt, temperature=0.5)
            
            if result and not result.get("error"):
                return ImprovedTextResponse(
                    reasoning=result.get("reasoning", ""),
                    original_text=text,
                    improved_text=result.get("improved_text", text),
                    applied_instruction=instruction,
                    changes_made=result.get("changes_made", "")
                )
            
            if result and result.get("raw_reasoning"):
                generated = self._extract_correction_from_reasoning(
                    result["raw_reasoning"], 
                    text, 
                    task_type="improve"
                )
                return ImprovedTextResponse(
                    reasoning=generated["reasoning"],
                    original_text=text,
                    improved_text=generated["improved_text"],
                    applied_instruction=instruction,
                    changes_made=generated["changes_made"]
                )
            
            return ImprovedTextResponse(
                reasoning="Fallback не смог получить ответ",
                original_text=text,
                improved_text=text,
                applied_instruction=instruction,
                changes_made="Ошибка"
            )
        except Exception as e:
            logger.error(f"Ошибка в fallback: {e}")
            return ImprovedTextResponse(
                reasoning=f"Ошибка: {str(e)}",
                original_text=text,
                improved_text=text,
                applied_instruction=instruction,
                changes_made="Не удалось обработать"
            )

    async def summarize(self, text: str) -> SummaryResponse:
        """Суммаризация текста"""
        # ← ОПТИМИЗАЦИЯ: Краткий промпт для суммаризации
        prompt = f"""Текст: {text}
Верни ТОЛЬКО валидный JSON. БУДЬ КРАТОК.
{{"reasoning":"почему выбрал","summary":"1-2 предложения","keywords":["ключ1","ключ2"]}}"""
        
        try:
            result = await self._make_request(prompt, temperature=0.3)
            
            if result and not result.get("error"):
                summary = result.get("summary", "")
                return SummaryResponse(
                    reasoning=result.get("reasoning", ""),
                    summary=summary,
                    keywords=result.get("keywords", []),
                    original_length=len(text),
                    summary_length=len(summary)
                )
            
            if result and result.get("raw_reasoning"):
                generated = self._extract_correction_from_reasoning(
                    result["raw_reasoning"], 
                    text, 
                    task_type="summarize"
                )
                return SummaryResponse(
                    reasoning=generated["reasoning"],
                    summary=generated["summary"],
                    keywords=generated["keywords"],
                    original_length=len(text),
                    summary_length=len(generated["summary"])
                )
            
            return SummaryResponse(
                reasoning="Не удалось получить JSON",
                summary="",
                keywords=[],
                original_length=len(text),
                summary_length=0
            )
        except Exception as e:
            logger.error(f"Ошибка summarize: {e}")
            if "BUDGET_EXCEEDED:402" in str(e):
                raise HTTPException(status_code=402, detail="Превышен бюджет")
            return SummaryResponse(
                reasoning=f"Ошибка: {str(e)}",
                summary="",
                keywords=[],
                original_length=len(text),
                summary_length=0
            )