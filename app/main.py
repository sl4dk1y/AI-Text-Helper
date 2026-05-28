import time
import traceback
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.schemas import InfoResponse, RunRequest, RunResponse
from app.service import get_service

# Инициализация FastAPI
app = FastAPI(
    title="AI Text Helper API",
    description="Unified API wrapper for text improvement and summarization.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware для логирования времени
class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs request processing time."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        response = await call_next(request)
        elapsed = time.time() - start
        print(f"[timing] {request.method} {request.url.path} — {elapsed:.3f}s")
        return response


app.add_middleware(TimingMiddleware)

# Получаем инстанс сервиса
service = get_service()


# Эндпоинты
@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/info", response_model=InfoResponse)
def info() -> InfoResponse:
    """Return service metadata for load tester auto-configuration."""
    return service.get_info()


@app.post("/run", response_model=RunResponse)
async def run(request: RunRequest) -> RunResponse:  
    """Unified endpoint for all service tasks."""
    try:
        return await service.run(request)
    except Exception:
        return RunResponse(
            status="error",
            error=traceback.format_exc(),
        )