import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.database.base import Base


class MemoryCategory(str, enum.Enum):
    PERSONAL = "personal"
    PREFERENCE = "preference"
    GOAL = "goal"
    SKILL = "skill"
    EDUCATION = "education"
    PROJECT = "project"
    HABIT = "habit"
    INTEREST = "interest"
    IMPORTANT_EVENT = "important_event"
    TEMPORARY = "temporary"
    OTHER = "other"


class MemorySource(str, enum.Enum):
    EXPLICIT = "explicit"   # directly stated by the user
    INFERRED = "inferred"   # derived by the AI from patterns


class MemoryStatus(str, enum.Enum):
    NEW = "new"
    ACTIVE = "active"
    LESS_RELEVANT = "less_relevant"
    ARCHIVED = "archived"
    EXPIRED = "expired"
    DELETED = "deleted"


class Memory(Base):
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    content = Column(Text, nullable=False)
    category = Column(Enum(MemoryCategory), nullable=False, default=MemoryCategory.OTHER)

    importance_score = Column(Float, nullable=False, default=0.5)  # 0.0 - 1.0
    confidence_score = Column(Float, nullable=False, default=0.5)  # 0.0 - 1.0
    source = Column(Enum(MemorySource), nullable=False, default=MemorySource.EXPLICIT)

    status = Column(Enum(MemoryStatus), nullable=False, default=MemoryStatus.ACTIVE, index=True)

    # Groups memories that answer the same underlying question
    # (e.g. "preferred_language"), enabling cheap, scoped conflict detection
    # instead of comparing every new memory against the whole table.
    slot_key = Column(String(100), nullable=True, index=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))
    last_accessed_at = Column(DateTime, nullable=True)
    expiration_date = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="memories")
    history = relationship("MemoryHistory", back_populates="memory", cascade="all, delete-orphan")
