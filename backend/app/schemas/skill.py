from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.skill import SkillStatus


class SkillCreate(BaseModel):
    name: str = Field(min_length=1)
    category: Optional[str] = None
    status: Optional[SkillStatus] = SkillStatus.NOT_STARTED


class SkillUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    category: Optional[str] = None
    status: Optional[SkillStatus] = None


class SkillOut(BaseModel):
    id: int
    user_id: int
    name: str
    category: Optional[str]
    status: SkillStatus
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
