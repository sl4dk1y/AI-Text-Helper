import pandas as pd
from sklearn.model_selection import train_test_split

# Загрузка данных
print("Загрузка данных...")
train_df = pd.read_csv("data/finetuning/RuWikiLarge_train.csv")
val_df = pd.read_csv("data/finetuning/RuWikiLarge_val.csv")
test_df = pd.read_csv("data/finetuning/RuWikiLarge_test.csv")

print(f"Обучающая выборка: {len(train_df)} пар")
print(f"Валидационная выборка: {len(val_df)} пары")
print(f"Тестовая выборка: {len(test_df)} пар")

# Посмотрим на структуру
print("\nСтруктура данных:")
print(train_df.columns.tolist())
print("\nПервые 2 примера:")
print(train_df.head(2))

# Колонки
input_col = 'source' if 'source' in train_df.columns else 'original'
output_col = 'target' if 'target' in train_df.columns else 'simple'

# Переименуем для единообразия
train_df = train_df.rename(columns={input_col: 'input', output_col: 'output'})
val_df = val_df.rename(columns={input_col: 'input', output_col: 'output'})
test_df = test_df.rename(columns={input_col: 'input', output_col: 'output'})

# Сохраняем в удобном формате
train_df.to_csv("data/finetuning/train.csv", index=False)
val_df.to_csv("data/finetuning/val.csv", index=False)
test_df.to_csv("data/finetuning/test.csv", index=False)

print("\nГотово! Файлы сохранены:")
print("- data/finetuning/train.csv")
print("- data/finetuning/val.csv")
print("- data/finetuning/test.csv")

print("\nПример пары (вход → выход):")
print(f"Вход:  {train_df['input'].iloc[0][:100]}...")
print(f"Выход: {train_df['output'].iloc[0][:100]}...")