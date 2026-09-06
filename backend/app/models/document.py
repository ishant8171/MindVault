"""
Document and DocumentChunk models.

Stores user-uploaded reference documents (PDF, DOCX) and their extracted text chunks.
Chunking enables targeted keyword/BM25 retrieval without exceeding context limits.
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.database.base import Base


class DocumentStatus(str, enum.Enum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # "pdf", "docx", "txt"
    upload_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(Enum(DocumentStatus), nullable=False, default=DocumentStatus.PROCESSING)

    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True, index=True)

    # Relationships
    user = relationship("User", back_populates="documents")
    subject = relationship("Subject", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    document = relationship("Document", back_populates="chunks")
