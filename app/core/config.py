from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    app_name: str = "AI Text Helper"

    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = "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"
    llm_model: str = "LLM_MODEL=google/gemini-flash-1.5-8b:free"
    
    temperature: float = 0.7
    max_tokens: int = 500

    model_config = ConfigDict(env_file=".env", extra="ignore")

settings = Settings()