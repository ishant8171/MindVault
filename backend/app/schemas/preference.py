from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PreferenceCreate(BaseModel):
    preference_type: str = Field(min_length=1, max_length=100)
    initial_confidence: Optional[float] = Field(default=0.3, ge=0.0, le=1.0)


class PreferenceOut(BaseModel):
    id: int
    user_id: int
    preference_type: str
    confidence: float
    evidence_count: int
    last_updated: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
