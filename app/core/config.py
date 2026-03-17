from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    app_name: str = "AI Text Helper"

    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    llm_model: str = "LLM_MODEL=google/gemini-flash-1.5-8b:free"
    
    temperature: float = 0.7
    max_tokens: int = 500

    model_config = ConfigDict(env_file=".env", extra="ignore")

settings = Settings()