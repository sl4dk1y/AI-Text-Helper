# 🤖 AI Text Helper

Сервис для улучшения и суммаризации текста на русском языке с использованием LLM (Qwen 3.5 9B через Ollama).

---

## 📋 Описание проекта

### Цель
Создание унифицированного API-сервиса для:
- ✏️ **Исправления ошибок** в тексте (орфография, пунктуация, стиль)
- 📝 **Суммаризации** текста с выделением ключевых слов
- 🔍 **Поиска известных исправлений** через лексический ретривер (BM25)


### Технологический стек

| Компонент | Технология | Назначение |
|-----------|-----------|------------|
| **Backend** | FastAPI + Python 3.11 | REST API сервер |
| **LLM Proxy** | LiteLLM | Унификация доступа к моделям |
| **Модель** | Qwen 3.5 9B (Ollama) | Генерация ответов |
| **База знаний** | BM25 Retriever | Поиск известных исправлений |
| **Мониторинг** | Langfuse | Трассировка и метрики |
| **Нагрузка** | Locust | Нагрузочное тестирование |
| **Контейнеризация** | Docker Compose | Оркестрация сервисов |

---

## 🚀 Быстрый старт

### Предварительные требования
- [Docker](https://docs.docker.com/get-docker/) и [Docker Compose](https://docs.docker.com/compose/install/)
- [Ollama](https://ollama.ai) с моделью `qwen3.5:9b`
- Минимум 8 ГБ ОЗУ (рекомендуется 16 ГБ для локальной модели)
>>>>>>> fccfda2 (Обновленная документация)

### Шаг 1: Клонирование и настройка

```bash
# Клонировать репозиторий
git clone <repo-url>
cd ai-text-helper

# Создать файл окружения (скопировать шаблон)
cp .env.example .env

# Отредактировать .env — заполнить API ключи при необходимости
nano .env
```

### Шаг 2: Запуск сервисов
```bash
# Запустить все сервисы в фоновом режиме
docker-compose up -d

# Проверить статус контейнеров
docker-compose ps

# Просмотреть логи (опционально)
docker-compose logs -f fastapi
```

### Шаг 3: Проверка работоспособности
```bash
# Health check
curl http://localhost:8000/health

# Ожидаемый ответ:
# {"status":"ok"}
```
## 📡 API Reference
### Унифицированный эндпоинт /run
```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "content": "купил малако",
    "extra_body": {
      "task_type": "improve",
      "instruction": "исправь ошибки"
    }
  }' | jq

Ответ:

{
  "status": "success",
  "result": {
    "reasoning": "Исправлена опечатка в слове «малако» на «молоко».",
    "improved_text": "купил молоко",
    "changes_made": "малако -> молоко",
    "original_text": "купил малако"
  }
}
```
### Эндпоинт /info — метаданные сервиса
```bash
curl http://localhost:8000/info | jq

Ответ:
{
  "input_type": "text",
  "input_schema": {
    "task_type": {"type": "string", "enum": ["improve", "summarize"]},
    "instruction": {"type": "string", "default": "исправь ошибки"}
  },
  "output_schema": {
    "improved_text": {"type": "string"},
    "summary": {"type": "string"},
    "reasoning": {"type": "string"},
    "changes_made": {"type": "string"},
    "keywords": {"type": "array"},
    "processing_time_ms": {"type": "integer"}
  }
}
```
### Эндпоинт /health — проверка работоспособности
```bash
curl http://localhost:8000/health
# {"status":"ok"}
```
## 🧪 Примеры использования
### ✏️ Исправление ошибок
>>>>>>> fccfda2 (Обновленная документация)

```bash
# Простая орфография
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"content":"сегоднешний день был очен хороший","extra_body":{"task_type":"improve"}}' | jq

# Множественные ошибки
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"content":"мы пашли в парк и видели многа цветов","extra_body":{"task_type":"improve"}}' | jq

# Сленг → литературный
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"content":"щас пойду куплю хлебушка","extra_body":{"task_type":"improve","instruction":"сделай текст литературным"}}' | jq
```
## 📝 Суммаризация
```bash
# Короткий текст
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"content":"ИИ — это область компьютерных наук. Машинное обучение — подраздел ИИ.","extra_body":{"task_type":"summarize"}}' | jq

# Длинный текст
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"content":"Искусственный интеллект — это область компьютерных наук, которая занимается созданием систем, способных выполнять задачи, требующие человеческого интеллекта. Машинное обучение — это подраздел ИИ, который использует статистические методы для обучения моделей на данных.","extra_body":{"task_type":"summarize"}}' | jq

```

## 🔍 Edge cases
>>>>>>> fccfda2 (Обновленная документация)
```bash
# Текст без ошибок
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"content":"Привет, мир!","extra_body":{"task_type":"improve"}}' | jq

# Очень короткий текст
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"content":"прив","extra_body":{"task_type":"improve"}}' | jq

```
## 📊 Мониторинг и отладка

| Сервис | URL | Описание |
|-----------|-----------|------------|
| **API Docs** | http://localhost:8000/docs | Swagger UI для тестирования эндпоинтов |
| **Langfuse UI** | http://localhost:3000 | Трассировка запросов, метрики, отладка промптов |
| **Locust UI** | http://localhost:8089 | Нагрузочное тестирование в реальном времени |

## 🔍 Просмотр логов
```bash
# Логи FastAPI
docker-compose logs -f fastapi

# Логи LiteLLM
docker-compose logs -f litellm

# Логи модели (Ollama)
docker-compose logs -f ollama

# Логи всех сервисов
docker-compose logs -f
```

## 📈 Метрики в Langfuse
>>>>>>> fccfda2 (Обновленная документация)
- Откройте http://localhost:3000
- Войдите (по умолчанию без пароля для dev-режима)
- Перейдите в Traces для просмотра:
    - Входных промптов
    - Рассуждений модели (reasoning_content)
    - Финальных ответов (content)
    - Использованных токенов и стоимости


## 🧪 Нагрузочное тестирование (Locust)
### Запуск тестов
>>>>>>> fccfda2 (Обновленная документация)
```bash
# Запустить контейнер Locust
docker-compose --profile test up -d locust

# Открыть веб-интерфейс
# Перейти на http://localhost:8089

# Настроить параметры:
# - Users: 10 (одновременных пользователей)
# - Spawn rate: 2 (пользователей в секунду)
# - Host: http://fastapi:8000

Альтернатива: запуск через CLI

# Быстрый тест на 100 запросов
locust -f locust/locustfile.py \
  --headless \
  -u 10 \
  -r 2 \
  --run-time 60s \
  --host http://localhost:8000

```

## 🔧 Устранение неполадок
### ❌ Ошибка: "Connection refused" к Ollama
>>>>>>> fccfda2 (Обновленная документация)
```bash
# Проверить, запущена ли модель
ollama list

# Если нет — запустить
ollama run qwen3.5:9b

# Проверить доступность внутри Docker
docker-compose exec fastapi curl http://host.docker.internal:11434/api/tags

```

### ❌ Ошибка: "JSON не найден" в ответе
>>>>>>> fccfda2 (Обновленная документация)
Причина: Модель обрезала ответ из-за max_tokens.
Решение:
- Увеличить max_tokens в litellm_config.yaml до 2000
- Пересобрать: docker-compose build --no-cache fastapi litellm
- Перезапустить: docker-compose up -d

### ❌ Ошибка: Таймаут запроса
>>>>>>> fccfda2 (Обновленная документация)
Причина: Локальная модель работает медленно.
Решение:
- Увеличить timeout в llm_service.py (по умолчанию 300 сек)
- Использовать более мощное железо или GPU
- Уменьшить max_tokens для ускорения

### ❌ Ошибка: "API ключ не найден"
>>>>>>> fccfda2 (Обновленная документация)
```bash
# Проверить .env файл
cat .env | grep LLM_API_KEY

# Перезапустить сервис для применения изменений
docker-compose restart fastapi

```
## Оптимизация
>>>>>>> fccfda2 (Обновленная документация)
```bash
Для ускорения ответов (ценой качества):
max_tokens: 1000      # Меньше токенов = быстрее
temperature: 0.1      # Более детерминированные ответы

Для улучшения качества (ценой скорости):
max_tokens: 2000      # Больше места для рассуждений
temperature: 0.7      # Более "творческие" ответы
```

