from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.document import DocumentStatus


class DocumentOut(BaseModel):
    id: int
    user_id: int
    filename: str
    file_type: str
    status: DocumentStatus
    subject_id: Optional[int] = None
    upload_date: datetime
    chunk_count: Optional[int] = None

    class Config:
        from_attributes = True


class DocumentStatusOut(BaseModel):
    id: int
    filename: str
    status: DocumentStatus
    chunk_count: int

    class Config:
        from_attributes = True
