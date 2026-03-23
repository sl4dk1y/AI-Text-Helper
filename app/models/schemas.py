from pydantic import BaseModel, Field
from typing import Optional

class ImproveTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    instruction: str = Field(...)
    style: Optional[str] = Field(None)

class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)

class ImprovedTextResponse(BaseModel):
    original_text: str
    improved_text: str = Field(..., description="Исправленный текст")
    applied_instruction: str
    changes_made: Optional[str] = Field(None)

class SummaryResponse(BaseModel):
    summary: str= Field(..., description="Краткое содержание")
    keywords: list[str] = Field(default_factory=list)
    original_length: int
    summary_length: int