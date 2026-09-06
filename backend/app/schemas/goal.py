from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.goal import GoalStatus, GoalPriority


class GoalCreate(BaseModel):
    title: str = Field(min_length=1)
    description: Optional[str] = None
    priority: Optional[GoalPriority] = GoalPriority.MEDIUM
    deadline: Optional[datetime] = None
    progress: Optional[float] = 0.0
    subject_id: Optional[int] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[GoalPriority] = None
    deadline: Optional[datetime] = None
    status: Optional[GoalStatus] = None
    progress: Optional[float] = None
    subject_id: Optional[int] = None


class GoalOut(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str]
    priority: GoalPriority
    deadline: Optional[datetime]
    status: GoalStatus
    progress: float
    subject_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
