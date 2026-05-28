import os
import random
from locust import HttpUser, task, between, events
from typing import Optional

# Тестовые данные
RANDOM_SENTENCES = [
    "привэт мир",
    "нагода сегодня хорошая",
    "ашибка в слове",
    "трапа на дороге",
    "севодня отличный день",
    "Искусственный интеллект — область компьютерных наук.",
    "Нейронные сети — математические модели.",
    "Обработка естественного языка занимается текстом.",
]


def _random_text(length: int = 120) -> str:
    """Return a random sentence."""
    return random.choice(RANDOM_SENTENCES)

# Пользователь для нагрузочного тестирования
class AITextHelperUser(HttpUser):
    """Load test user for AI Text Helper service."""

    wait_time = between(0.5, 2.0)
    host: str = os.environ.get("LOCUST_HOST", "http://localhost:8000")
    _input_type: str = "text"  # Default, will be updated from /info

    def on_start(self) -> None:
        """Read /info to determine input_type for content generation."""
        try:
            resp = self.client.get("/info", timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                self._input_type = data.get("input_type", "text")
        except Exception:
            pass  # Fallback to default

    def _build_run_payload(self) -> dict:
        """Build request payload based on input_type."""
        if self._input_type == "text":
            return {
                "content": _random_text(),
                "extra_body": {
                    "task_type": random.choice(["improve", "summarize"]),
                    "instruction": "исправь ошибки",
                },
            }
        # Для text-only сервиса
        return {
            "content": _random_text(),
            "extra_body": {"task_type": "improve"},
        }

    @task(10)
    def run_service(self) -> None:
        """Main task: send request to /run endpoint."""
        self.client.post(
            "/run",
            json=self._build_run_payload(),
            name="/run",
            headers={"Content-Type": "application/json"},
        )

    @task(1)
    def check_info(self) -> None:
        """Occasional check of /info endpoint."""
        self.client.get("/info", name="/info")


# Глобальные обработчики событий
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log each request for debugging."""
    if exception:
        print(f"[locust] ERROR {name}: {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print(f"[locust] Test started — Host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("[locust] Test finished")