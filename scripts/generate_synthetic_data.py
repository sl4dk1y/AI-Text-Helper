import pandas as pd
import random

print("=" * 60)
print("ГЕНЕРАЦИЯ РАЗНООБРАЗНОГО СИНТЕТИЧЕСКОГО НАБОРА ДАННЫХ")
print("=" * 60)

# 1. БАЗА РАЗНЫХ ПРЕДЛОЖЕНИЙ
short_sentences = [
    ("погода хорошая", "погода хорошая"),
    ("молоко вкусное", "молоко вкусное"),
    ("я иду домой", "я иду домой"),
    ("кот спит", "кот спит"),
    ("солнце светит", "солнце светит"),
    ("машина едет", "машина едет"),
    ("кошка мяукает", "кошка мяукает"),
    ("собака лает", "собака лает"),
    ("птица летит", "птица летит"),
    ("вода холодная", "вода холодная"),
]

medium_sentences = [
    ("сегодня на улице хорошая погода, солнце светит ярко", "сегодня хорошая погода, солнце светит"),
    ("я пошел в магазин чтобы купить молоко и хлеб", "я пошел в магазин за молоком и хлебом"),
    ("у меня дома живет пушистый кот, который любит спать на диване", "у меня есть кот, который любит спать"),
    ("вчера я смотрел интересный фильм про космос", "я смотрел фильм про космос"),
    ("мой друг пригласил меня на свой день рождения в субботу", "друг пригласил меня на день рождения"),
]

long_sentences = [
    ("Вчера я ходил в большой торговый центр, который находится недалеко от моего дома, и купил там новую книгу, о которой давно мечтал", "Я купил новую книгу в торговом центре"),
    ("На уроке биологии учитель рассказывал про строение клетки, её органоиды и функции, и это было очень интересно", "На биологии рассказывали про строение клетки"),
    ("Из-за сильного дождя мы не смогли пойти на прогулку в парк, поэтому остались дома и смотрели телевизор весь вечер", "Из-за дождя мы остались дома и смотрели телевизор"),
]


# 2. ПРАВИЛА ГЕНЕРАЦИИ ОШИБОК
typo_pairs = [
    ("погода", "нагода"),
    ("молоко", "малако"),
    ("пошел", "пашел"),
    ("сегодня", "севодня"),
    ("хорошая", "хороша"),
    ("искусственный", "искуственный"),
    ("интеллект", "интелект"),
    ("кошка", "кошке"),
    ("быстро", "быстра"),
    ("кот", "код"),
]

grammar_pairs = [
    ("хорошая погода", "хороша погода"),
    ("красивая девушка", "красивая девушка"),
    ("большой дом", "большой дом"),
    ("белый кот", "белый кот"),
    ("вкусное молоко", "вкусное молоко"),
]

def add_typo(text):
    for correct, wrong in typo_pairs:
        if correct in text:
            return text.replace(correct, wrong, 1)
    return text

def add_grammar_error(text):
    for correct, wrong in grammar_pairs:
        if correct in text:
            return text.replace(correct, wrong, 1)
    return text


# 3. ГЕНЕРАЦИЯ С ЦЕЛЕВЫМИ ПРОПОРЦИЯМИ
# Целевое распределение (100 примеров)
target_counts = {
    "упрощение текста": 91,
    "грамматика": 5,
    "без изменений": 3,
    "орфография": 1,
}

generated = []

# 1. Упрощение текста (91 пример)
for i in range(91):
    if i % 2 == 0 and medium_sentences:
        original, simplified = random.choice(medium_sentences)
    elif long_sentences:
        original, simplified = random.choice(long_sentences)
    else:
        original, simplified = random.choice(short_sentences)
    generated.append({
        "input": original,
        "output": simplified,
        "type": "упрощение текста",
        "length_category": "средний (51-200)" if len(original) > 50 else "короткий (10-50)"
    })

# 2. Грамматика (5 примеров)
for _ in range(5):
    orig, _ = random.choice(medium_sentences if medium_sentences else short_sentences)
    wrong = add_grammar_error(orig)
    generated.append({
        "input": wrong,
        "output": orig,
        "type": "грамматика",
        "length_category": "средний (51-200)" if len(orig) > 50 else "короткий (10-50)"
    })

# 3. Без изменений (3 примера)
for _ in range(3):
    orig, _ = random.choice(short_sentences)
    generated.append({
        "input": orig,
        "output": orig,
        "type": "без изменений",
        "length_category": "короткий (10-50)"
    })

# 4. Орфография (1 пример)
orig, _ = random.choice(short_sentences)
# Создаём реальную орфографическую ошибку
typo_map = {
    "погода": "нагода",
    "молоко": "малако",
    "пошел": "пашел",
    "сегодня": "севодня",
    "хорошая": "хороша",
    "машина": "машина",
    "едет": "едит",
}
wrong = orig
for correct, typo in typo_map.items():
    if correct in orig:
        wrong = orig.replace(correct, typo)
        break
if wrong == orig:
    wrong = "малако вкусное"  # fallback
generated.append({
    "input": wrong,
    "output": orig,
    "type": "орфография",
    "length_category": "короткий (10-50)"
})

# Перемешиваем
random.shuffle(generated)

# Добавляем id
for i, item in enumerate(generated):
    item["id"] = i + 1

df = pd.DataFrame(generated)
df.to_csv("data/synthetic_dataset.csv", index=False)

print(f"\nСгенерировано {len(df)} примеров")
print("\nРаспределение по типам:")
print(df['type'].value_counts())
print("\nРаспределение по длине:")
print(df['length_category'].value_counts())
print("\nПервые 10 примеров:")
print(df[['input', 'output', 'type']].head(10))