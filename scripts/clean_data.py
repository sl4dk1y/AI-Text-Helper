import pandas as pd
import re

print("=" * 60)
print("ОЧИСТКА И ОБРАБОТКА ДАННЫХ (БЕЗ УДАЛЕНИЯ ДУБЛИКАТОВ)")
print("=" * 60)

df = pd.read_csv("data/synthetic_dataset.csv")
print(f"До очистки: {len(df)} примеров")

# 1. Пропускаем удаление дубликатов (для синтетических данных)
print("\nДубликаты не удаляются (синтетические данные могут повторяться)")

# 2. Очистка текста от лишних символов
def clean_text(text):
    text = str(text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s\.,!?\-—]', '', text)
    return text.strip()

df['input'] = df['input'].apply(clean_text)
df['output'] = df['output'].apply(clean_text)

# 3. Удаление пустых строк (если есть)
initial_count = len(df)
df = df[df['input'].str.len() > 0]
df = df[df['output'].str.len() > 0]
empty_removed = initial_count - len(df)
print(f"Удалено пустых строк: {empty_removed}")

# 4. Удаление слишком коротких/длинных
initial_count = len(df)
df = df[df['input'].str.len() >= 3]
df = df[df['input'].str.len() <= 1000]
length_filtered = initial_count - len(df)
print(f"Удалено по длине (за пределами 3-1000 символов): {length_filtered}")

# 5. Сохранение
df.to_csv("data/synthetic_dataset_clean.csv", index=False)

print("\n" + "=" * 60)
print("ИТОГ ОЧИСТКИ")
print("=" * 60)
print(f"Исходное количество: {len(df) + empty_removed + length_filtered}")
print(f"Удалено всего: {empty_removed + length_filtered}")
print(f"Осталось: {len(df)}")
print(f"\nОчищенные данные сохранены в data/synthetic_dataset_clean.csv")

print("\nРаспределение по типам:")
print(df['type'].value_counts())

print("\nРаспределение по длине:")
print(df['length_category'].value_counts())

print("\nПервые 5 примеров:")
print(df[['input', 'output', 'type']].head())