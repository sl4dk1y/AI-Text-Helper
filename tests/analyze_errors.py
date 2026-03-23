import csv
from collections import defaultdict

def analyze_results(csv_file):
    """Анализирует результаты тестирования и выявляет паттерны ошибок"""
    
    results = []
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    
    # Статистика
    total = len(results)
    success = sum(1 for r in results if r["Статус"] == "success")
    errors = total - success
    
    # Категории ошибок
    error_types = defaultdict(int)
    unchanged_count = 0
    
    for r in results:
        if r["Статус"] != "success":
            error_types["Ошибка API"] += 1
        else:
            # Проверяем, изменился ли текст
            if r["Запрос"] == r["Результат"]:
                unchanged_count += 1
                error_types["Текст не изменился"] += 1
    
    print("=" * 60)
    print("АНАЛИЗ РЕЗУЛЬТАТОВ")
    print("=" * 60)
    print(f"Всего тестов: {total}")
    print(f"Успешно: {success} ({success/total*100:.1f}%)")
    print(f"Ошибок: {errors} ({errors/total*100:.1f}%)")
    print(f"\nКатегории проблем:")
    for error_type, count in error_types.items():
        print(f"   - {error_type}: {count} ({count/total*100:.1f}%)")
    
    # Список примеров, требующих внимания
    print("\nПРИМЕРЫ ДЛЯ АНАЛИЗА:")
    print("-" * 60)
    
    problems = []
    for r in results:
        if r["Запрос"] == r["Результат"]:
            problems.append(("Текст не изменился", r["Запрос"], r["Результат"]))
        elif r["Статус"] != "success":
            problems.append(("Ошибка API", r["Запрос"], r["Ошибка"]))
    
    for i, (problem_type, query, result) in enumerate(problems[:5]):
        print(f"\n{i+1}. [{problem_type}]")
        print(f"   Запрос: {query}")
        print(f"   Результат: {result[:100]}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        analyze_results(sys.argv[1])
    else:
        print("Укажите файл с результатами: python analyze_errors.py data/test_results_20250323_xxxxxx.csv")