from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    goal_id: Optional[int] = None
    related_concept_ids: Optional[List[int]] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    goal_id: Optional[int] = None
    related_concept_ids: Optional[List[int]] = None


class TaskOut(BaseModel):
    id: int
    user_id: int
    goal_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: TaskStatus
    related_concept_ids: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
