from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.memory import MemoryCategory, MemorySource, MemoryStatus


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1)
    category: MemoryCategory = MemoryCategory.OTHER
    slot_key: Optional[str] = None
    importance_score: Optional[float] = 0.5
    confidence_score: Optional[float] = 0.5
    source: MemorySource = MemorySource.EXPLICIT
    expiration_date: Optional[datetime] = None


class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    category: Optional[MemoryCategory] = None
    slot_key: Optional[str] = None
    importance_score: Optional[float] = None
    confidence_score: Optional[float] = None
    source: Optional[MemorySource] = None
    status: Optional[MemoryStatus] = None
    expiration_date: Optional[datetime] = None


class MemoryOut(BaseModel):
    id: int
    user_id: int
    content: str
    category: MemoryCategory
    importance_score: float
    confidence_score: float
    source: MemorySource
    status: MemoryStatus
    slot_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_accessed_at: Optional[datetime] = None
    expiration_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConflictDetected(BaseModel):
    message: str
    slot_key: str | None = None
    existing: MemoryOut
    candidate: MemoryCreate
    conflict_id: Optional[int] = None

    class Config:
        from_attributes = True


class MemoryCandidate(BaseModel):
    content: str
    slot_key: Optional[str] = None
    category: Optional[MemoryCategory] = None
    confidence_score: Optional[float] = 0.5
    importance_score: Optional[float] = 0.5


class ExtractRequest(BaseModel):
    text: str


class ExtractResponse(BaseModel):
    candidates: list[MemoryCandidate]

    class Config:
        from_attributes = True


class RetrievalRequest(BaseModel):
    query: str
    category: Optional[MemoryCategory] = None
    limit: Optional[int] = 10


class RetrievalResult(BaseModel):
    id: int
    content: str
    category: Optional[MemoryCategory] = None
    importance_score: float
    created_at: Optional[datetime]
    score: float
    reason: dict


class RetrievalResponse(BaseModel):
    results: list[RetrievalResult]

    class Config:
        from_attributes = True


class MemoryConflictOut(BaseModel):
    id: int
    user_id: int
    old_memory_id: int
    new_memory_id: int
    status: Optional[str]
    resolution: Optional[str]
    created_at: Optional[datetime]


class ConflictResolveRequest(BaseModel):
    action: str  # 'keep_old' | 'keep_new' | 'merge'
    merged_content: Optional[str] = None


class ConflictResolveResponse(BaseModel):
    id: int
    status: str
    resolution: str | None = None


class LifecycleRequest(BaseModel):
    action: str  # 'activate' | 'mark_less_relevant' | 'archive' | 'expire' | 'delete'

