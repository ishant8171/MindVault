from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ConceptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    category: Optional[str] = None
    subject_id: Optional[int] = None
    initial_level: Optional[float] = Field(default=0.0, ge=0.0, le=1.0)
    initial_confidence: Optional[float] = Field(default=0.1, ge=0.0, le=1.0)


class ConceptUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    subject_id: Optional[int] = None


class ConceptOut(BaseModel):
    id: int
    user_id: int
    name: str
    category: Optional[str] = None
    current_level: float
    confidence: float
    evidence_count: int
    subject_id: Optional[int] = None
    migrated_from_skill_id: Optional[int] = None
    last_updated: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
