import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.database.base import Base


class MemoryHistory(Base):
    """
    Audit trail. Whenever a memory's content/status changes, we record the
    before/after here rather than silently overwriting, so the app can show
    "Previously preferred Python" style context and so we can explain
    conflict-resolution decisions during a viva.
    """
    __tablename__ = "memory_history"

    id = Column(Integer, primary_key=True, index=True)
    memory_id = Column(Integer, ForeignKey("memories.id"), nullable=False, index=True)
    old_content = Column(Text, nullable=True)
    new_content = Column(Text, nullable=True)
    change_reason = Column(String(255), nullable=False)  # e.g. "conflict_resolved", "user_edit"
    changed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    memory = relationship("Memory", back_populates="history")


class ConflictStatus(str, enum.Enum):
    PENDING = "pending"
    RESOLVED = "resolved"


class ConflictResolution(str, enum.Enum):
    KEPT_OLD = "kept_old"
    KEPT_NEW = "kept_new"
    MERGED = "merged"


class MemoryConflict(Base):
    """
    Tracks a detected conflict between an existing memory and a new
    candidate memory in the same slot, until it's resolved (automatically
    or by the user).
    """
    __tablename__ = "memory_conflicts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    old_memory_id = Column(Integer, ForeignKey("memories.id"), nullable=False)
    new_memory_id = Column(Integer, ForeignKey("memories.id"), nullable=False)
    status = Column(Enum(ConflictStatus), nullable=False, default=ConflictStatus.PENDING)
    resolution = Column(Enum(ConflictResolution), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
