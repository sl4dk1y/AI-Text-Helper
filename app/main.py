from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .api import endpoints
from .core.config import settings

# Настройка Rate Limiting
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.app_name,
    description="API для работы с текстами",
    version="0.1.0"
)

# Подключаем обработчик ошибки превышения лимита
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Подключаем роутеры
app.include_router(endpoints.router, prefix="/api/v1", tags=["text"])


@app.get("/")
@limiter.limit("100/minute")
async def root(request: Request):  
    return {
        "message": "AI Text Helper",
        "docs": "/docs",
        "rate_limits": {
            "root": "100/minute",
            "improve": "10/minute",
            "summarize": "20/minute",
            "health": "60/minute"
        }
    }


@app.get("/health")
@limiter.limit("60/minute")
async def health_check(request: Request):  
    return {"status": "ok", "service": "Text Assistant"}