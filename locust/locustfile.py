from locust import HttpUser, task, between
import random

class AiTextHelperUser(HttpUser):
    wait_time = between(5, 15)
    
    @task(10)
    def improve_short_text(self):
        """Тест: улучшение короткого текста (частый сценарий)"""
        test_cases = [
            ("привэт", "исправь орфографию"),
            ("ашибка", "исправь"),
            ("трапа", "исправь опечатки"),
            ("нагода хорошая", "исправь ошибки"),
        ]
        text, instruction = random.choice(test_cases)
        self.client.post(
            "/api/v1/improve",
            json={"text": text, "instruction": instruction},
            headers={"Content-Type": "application/json"},
            name="improve"
        )
    
    @task(5)
    def summarize_text(self):
        """Тест: суммаризация текста"""
        test_texts = [
            "Искусственный интеллект — область компьютерных наук, создающая системы для выполнения задач, требующих человеческого интеллекта. Машинное обучение — подраздел ИИ, использующий статистические методы для обучения на данных.",
            "Нейронные сети — математические модели, вдохновленные биологическими нейронными сетями. Они состоят из взаимосвязанных узлов (нейронов), организованных в слои.",
            "Обработка естественного языка (NLP) — область искусственного интеллекта, которая занимается взаимодействием компьютеров и человеческого языка.",
        ]
        text = random.choice(test_texts)
        self.client.post(
            "/api/v1/summarize",
            json={"text": text},
            headers={"Content-Type": "application/json"},
            name="summarize"
        )
    
    @task(1)
    def health_check(self):
        """Тест: проверка доступности"""
        self.client.get("/health", name="health")