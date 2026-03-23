import asyncio
import httpx
import csv
import time
from datetime import datetime

async def test_single_request(client, query: str, instruction: str, index: int):
    """Отправляет один запрос к API и возвращает результат"""
    
    url = "http://127.0.0.1:8000/api/v1/improve"
    
    payload = {
        "text": query,
        "instruction": instruction,
        "style": None
    }
    
    start_time = time.time()
    

    try:
        response = await client.post(url, json=payload, timeout=30.0)
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            return {
                "index": index,
                "query": query,
                "instruction": instruction,
                "result": data.get("improved_text", ""),
                "changes_made": data.get("changes_made", ""),
                "status": "success",
                "time_seconds": round(elapsed_time, 2),
                "error": None
            }
        else:
            return {
                "index": index,
                "query": query,
                "instruction": instruction,
                "result": "",
                "changes_made": "",
                "status": "error",
                "time_seconds": round(elapsed_time, 2),
                "error": f"HTTP {response.status_code}: {response.text[:100]}"
            }
            
    except Exception as e:
        elapsed_time = time.time() - start_time
        return {
            "index": index,
            "query": query,
            "instruction": instruction,
            "result": "",
            "changes_made": "",
            "status": "error",
            "time_seconds": round(elapsed_time, 2),
            "error": str(e)[:100]
        }

async def run_tests():
    """Запускает все тесты и сохраняет результаты"""
    
    print("=" * 60)
    print("Запуск тестирования API AI Text Helper")
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Читаем тестовые данные
    test_cases = []
    with open("data/test_data.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            test_cases.append((row["query"], row["instruction"]))
    
    print(f"\nЗагружено {len(test_cases)} тестовых примеров\n")
    
    # Отправляем запросы
    results = []
    
    async with httpx.AsyncClient() as client:
        for i, (query, instruction) in enumerate(test_cases):
            print(f"  [{i+1}/{len(test_cases)}] Тестируем: \"{query[:40]}...\"", end=" ")
            
            result = await test_single_request(client, query, instruction, i+1)
            results.append(result)
            
            if result["status"] == "success":
                print(f"Успех ({result['time_seconds']} сек)")
            else:
                print(f"Ошибка: {result['error']}")
    
    # Сохраняем результаты в CSV
    output_file = f"data/test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["№", "Запрос", "Инструкция", "Результат", "Изменения", "Статус", "Время (сек)", "Ошибка"])
        
        for r in results:
            writer.writerow([
                r["index"],
                r["query"],
                r["instruction"],
                r["result"],
                r["changes_made"],
                r["status"],
                r["time_seconds"],
                r["error"] or ""
            ])
    
    # Статистика
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = len(results) - success_count
    avg_time = sum(r["time_seconds"] for r in results) / len(results)
    
    print("\n" + "=" * 60)
    print("СТАТИСТИКА ТЕСТИРОВАНИЯ")
    print("=" * 60)
    print(f"Всего тестов: {len(results)}")
    print(f"Успешно: {success_count} ({success_count/len(results)*100:.1f}%)")
    print(f"Ошибок: {error_count} ({error_count/len(results)*100:.1f}%)")
    print(f"Среднее время ответа: {avg_time:.2f} сек")
    print("=" * 60)
    print(f"\nРезультаты сохранены в файл: {output_file}")
    
    return results

if __name__ == "__main__":
    asyncio.run(run_tests())