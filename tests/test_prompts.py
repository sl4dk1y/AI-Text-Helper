import asyncio
import time
import json
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm_service import LLMService
from app.core.config import settings


async def test_prompt_version(llm_service, version_name: str, prompt: str, test_text: str):
    """Тестирует одну версию промпта на одном тексте"""
    
    start = time.time()
    
    try:
        # Отправляем запрос к модели
        result = await llm_service._make_request(prompt, temperature=0.3)
        elapsed = time.time() - start
        
        # Извлекаем ответ
        if isinstance(result, dict):
            improved = result.get("improved_text", result.get("text", str(result)))
            changes = result.get("changes_made", "")
        else:
            improved = str(result)
            changes = ""
        
        # Проверяем, исправлена ли ошибка
        is_fixed = False
        if "нагода" in test_text and "погода" in improved:
            is_fixed = True
        elif "пашел" in test_text and "пошел" in improved:
            is_fixed = True
        elif "малако" in test_text and "молоко" in improved:
            is_fixed = True
        elif "Искуственный" in test_text and "Искусственный" in improved:
            is_fixed = True
        elif "севодня" in test_text and "сегодня" in improved:
            is_fixed = True
        
        # Проверяем валидность JSON
        is_json = improved.startswith("{") and improved.endswith("}")
        
        return {
            "version": version_name,
            "text": test_text,
            "response": improved[:150],
            "changes": changes[:100],
            "time_ms": int(elapsed * 1000),
            "is_fixed": is_fixed,
            "is_json": is_json,
            "success": True
        }
        
    except Exception as e:
        elapsed = time.time() - start
        return {
            "version": version_name,
            "text": test_text,
            "response": None,
            "changes": "",
            "time_ms": int(elapsed * 1000),
            "is_fixed": False,
            "is_json": False,
            "success": False,
            "error": str(e)[:100]
        }


async def run_experiment():
    """Запускает эксперимент"""
    
    print("=" * 80)
    print("ЭКСПЕРИМЕНТ: ТЕСТИРОВАНИЕ ВЕРСИЙ ПРОМПТОВ")
    print(f"Модель: {settings.llm_model}")
    print("=" * 80)
    
    # Тестовые тексты
    test_texts = [
        "нагода сегодня хорошая",
        "я пашел в магазин",
        "малако вкусное",
        "Искуственный интелект",
        "севодня отличный день"
    ]
    
    # Версии промптов
    prompts = {
        "V0": lambda text: f"Исправь ошибки в тексте: {text}",
        
        "V1": lambda text: f"""Исправь ошибки в тексте: {text}

Верни ответ в формате JSON: {{"improved_text": "исправленный текст"}}""",
        
        "V2": lambda text: f"""Ты — эксперт по русскому языку. Исправляй орфографические и грамматические ошибки.

Текст: {text}

Верни ответ в формате JSON: {{"improved_text": "исправленный текст"}}""",
        
        "V3": lambda text: f"""Ты — эксперт по русскому языку.

Пример:
Вход: "пашел в магазин"
Выход: {{"improved_text": "пошел в магазин", "changes_made": "пашел->пошел"}}

Теперь исправь этот текст:
Текст: {text}

Верни ответ в формате JSON.""",
        
        "V4": lambda text: f"""Ты — эксперт по русскому языку.

Правила:
1. Проанализируй текст
2. Найди орфографические и грамматические ошибки
3. Исправь найденные ошибки
4. Сохрани смысл текста

Текст: {text}

Верни JSON: {{"improved_text": "текст", "changes_made": "исправления"}}""",
        
        "V5": lambda text: f"""Текст: {text}
Инструкция: исправь ошибки

Исправь ошибки. Верни JSON: {{"improved_text": "текст", "changes_made": "исправления"}}"""
    }
    
    # Создаём сервис
    llm_service = LLMService()
    
    # Хранилище результатов
    all_results = []
    
    # Проходим по всем версиям
    for version_name, prompt_func in prompts.items():
        print(f"\n{'='*80}")
        print(f"ТЕСТИРОВАНИЕ {version_name}")
        print('='*80)
        
        version_results = []
        
        for test_text in test_texts:
            print(f"\n  Текст: {test_text}")
            
            prompt = prompt_func(test_text)
            result = await test_prompt_version(llm_service, version_name, prompt, test_text)
            version_results.append(result)
            
            if result["success"]:
                status = "FIXED" if result["is_fixed"] else "NOT_FIXED"
                print(f"    [{status}] Ответ: {result['response'][:80]}")
                print(f"    Time: {result['time_ms']} ms | JSON: {'YES' if result['is_json'] else 'NO'}")
            else:
                print(f"    [ERROR] Ошибка: {result.get('error', 'Unknown')}")
        
        all_results.extend(version_results)
    
    # Выводим сводную таблицу
    print("\n" + "=" * 80)
    print("СВОДНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ")
    print("=" * 80)
    
    # Группируем по версиям
    versions_summary = {}
    for r in all_results:
        ver = r["version"]
        if ver not in versions_summary:
            versions_summary[ver] = {
                "times": [],
                "fixed": 0,
                "json": 0,
                "total": 0
            }
        versions_summary[ver]["times"].append(r["time_ms"])
        if r["is_fixed"]:
            versions_summary[ver]["fixed"] += 1
        if r["is_json"]:
            versions_summary[ver]["json"] += 1
        versions_summary[ver]["total"] += 1
    
    print(f"\n{'Version':<6} {'Fixed (%)':<12} {'JSON (%)':<12} {'Avg Time (ms)':<15}")
    print("-" * 50)
    
    for ver in ["V0", "V1", "V2", "V3", "V4", "V5"]:
        if ver in versions_summary:
            v = versions_summary[ver]
            avg_time = sum(v["times"]) / len(v["times"])
            fixed_pct = (v["fixed"] / v["total"]) * 100
            json_pct = (v["json"] / v["total"]) * 100
            print(f"{ver:<6} {fixed_pct:>5.0f}%       {json_pct:>5.0f}%       {avg_time:>8.0f} ms")
    
    print("=" * 80)
    
    # Анализ
    print("\nАНАЛИЗ РЕЗУЛЬТАТОВ:")
    print("-" * 40)
    
    # Лучшее качество
    best_quality = max(versions_summary.items(), 
                       key=lambda x: x[1]["fixed"] / x[1]["total"])
    print(f"Best quality: {best_quality[0]} ({best_quality[1]['fixed']/best_quality[1]['total']*100:.0f}%)")
    
    # Самый быстрый
    fastest = min(versions_summary.items(), 
                  key=lambda x: sum(x[1]["times"]) / len(x[1]["times"]))
    print(f"Fastest: {fastest[0]} ({sum(fastest[1]['times'])/len(fastest[1]['times']):.0f} ms)")
    
    # Лучший JSON
    best_json = max(versions_summary.items(), 
                    key=lambda x: x[1]["json"] / x[1]["total"])
    print(f"Best JSON: {best_json[0]} ({best_json[1]['json']/best_json[1]['total']*100:.0f}%)")
    
    print("\nRECOMMENDATION:")
    print("-" * 40)
    print("For production: V5 (balance of quality and speed)")
    print("For maximum quality: V4")
    
    # Сохраняем результаты
    filename = f"data/prompt_test_results_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {filename}")


if __name__ == "__main__":
    asyncio.run(run_experiment())
