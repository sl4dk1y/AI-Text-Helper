from fastapi import FastAPI
from .api import endpoints
from .core.config import settings

app = FastAPI(
    title=settings.app_name,
    description="API для работы с текстами",
    version="0.1.0"
)

app.include_router(endpoints.router, prefix="/api/v1", tags=["text"])

@app.get("/")
async def root():
    return {
        "message": "AI Text Helper",
        "docs": "/docs" 
    }