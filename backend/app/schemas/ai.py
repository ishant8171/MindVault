from pydantic import BaseModel, Field
from typing import Optional, List


class AIRequest(BaseModel):
    prompt: str
    system_message: Optional[str] = None


class AIResponse(BaseModel):
    text: str
    raw: dict


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1)


class ChatResponse(BaseModel):
    text: str
    memories_used: List[int]
