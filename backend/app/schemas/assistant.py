from typing import Optional
from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    conversation_id: Optional[int] = None


class AskResponse(BaseModel):
    response: str
    conversation_id: int
    user_message_id: int
    assistant_message_id: int
