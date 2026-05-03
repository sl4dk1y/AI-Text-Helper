import pandas as pd
import json

print("=" * 60)
print("ПРОВЕРКА ОХВАТА ИЗМЕРЕНИЙ")
print("=" * 60)

df = pd.read_csv("data/synthetic_dataset.csv")

target_distribution = {
    "упрощение текста": 0.91,
    "грамматика": 0.05,
    "без изменений": 0.03,
    "орфография": 0.01,
}

actual_distribution = df['type'].value_counts(normalize=True).to_dict()

print("\n1. ТИП ОПЕРАЦИИ")
print("-" * 40)
for op_type in target_distribution.keys():
    target = target_distribution[op_type] * 100
    actual = actual_distribution.get(op_type, 0) * 100
    diff = abs(target - actual)
    status = "OK" if diff < 5 else "WARN"
    print(f"  {op_type}: целевая {target:.1f}% | реальная {actual:.1f}% | разница {diff:.1f}% [{status}]")

length_distribution = {
    "короткий (10-50)": 0.05,
    "средний (51-200)": 0.78,
    "длинный (201-1000)": 0.17,
}

actual_length = df['length_category'].value_counts(normalize=True).to_dict()

print("\n2. ДЛИНА ТЕКСТА")
print("-" * 40)
for length_cat in length_distribution.keys():
    target = length_distribution[length_cat] * 100
    actual = actual_length.get(length_cat, 0) * 100
    diff = abs(target - actual)
    status = "OK" if diff < 10 else "WARN"
    print(f"  {length_cat}: целевая {target:.1f}% | реальная {actual:.1f}% | разница {diff:.1f}% [{status}]")

print("\n" + "=" * 60)
print("ИТОГОВАЯ СТАТИСТИКА")
print("=" * 60)
print(f"Всего примеров: {len(df)}")
print(f"Типы операций: {dict(actual_distribution)}")
print(f"Категории длины: {dict(actual_length)}")