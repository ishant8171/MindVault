from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.models.memory import Memory, MemoryStatus
from app.models.user import User
from app.schemas.memory import MemoryCreate, MemoryUpdate


def create_memory(db: Session, user: User, memory_in: MemoryCreate, status: MemoryStatus | None = None) -> Memory:
    # Default to ACTIVE for normal creates; allow explicit status for candidates
    initial_status = status if status is not None else MemoryStatus.ACTIVE
    memory = Memory(
        user_id=user.id,
        content=memory_in.content,
        category=memory_in.category,
        slot_key=memory_in.slot_key,
        importance_score=memory_in.importance_score if memory_in.importance_score is not None else 0.5,
        confidence_score=memory_in.confidence_score if memory_in.confidence_score is not None else 0.5,
        source=memory_in.source,
        expiration_date=memory_in.expiration_date,
        status=initial_status,
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def find_slot_conflict(db: Session, user_id: int, slot_key: str, content: str) -> Memory | None:
    if not slot_key:
        return None
    # Find most recent relevant memory in the same slot for this user with different content
    # Consider any non-deleted memory in this slot as relevant for conflict detection
    existing = (
        db.query(Memory)
        .filter(Memory.user_id == user_id, Memory.slot_key == slot_key, Memory.status != MemoryStatus.DELETED)
        .order_by(Memory.created_at.desc())
        .first()
    )
    # return the most recent non-deleted memory in this slot (if any)
    return existing


def create_conflict(db: Session, user_id: int, old_memory_id: int, new_memory_id: int):
    from app.models.memory_history import MemoryConflict

    conflict = MemoryConflict(user_id=user_id, old_memory_id=old_memory_id, new_memory_id=new_memory_id)
    db.add(conflict)
    db.commit()
    db.refresh(conflict)
    return conflict


def get_conflicts_for_user(db: Session, user_id: int):
    from app.models.memory_history import MemoryConflict

    return db.query(MemoryConflict).filter(MemoryConflict.user_id == user_id).order_by(MemoryConflict.created_at.desc()).all()


def get_conflict(db: Session, conflict_id: int, user_id: int):
    from app.models.memory_history import MemoryConflict

    return db.query(MemoryConflict).filter(MemoryConflict.id == conflict_id, MemoryConflict.user_id == user_id).first()


def record_history(db: Session, memory_id: int, old_content: str | None, new_content: str | None, reason: str):
    from app.models.memory_history import MemoryHistory

    hist = MemoryHistory(memory_id=memory_id, old_content=old_content, new_content=new_content, change_reason=reason)
    db.add(hist)
    db.commit()


def resolve_conflict(db: Session, conflict, action: str, merged_content: str | None = None):
    from app.models.memory_history import ConflictResolution, ConflictStatus

    # Load memories
    old_mem = db.query(Memory).filter(Memory.id == conflict.old_memory_id).first()
    new_mem = db.query(Memory).filter(Memory.id == conflict.new_memory_id).first()

    if action == "keep_old":
        # mark new as deleted, keep old as-is
        if new_mem:
            record_history(db, new_mem.id, None, new_mem.content, "conflict_rejected")
            new_mem.status = MemoryStatus.DELETED
            db.add(new_mem)
        conflict.status = ConflictStatus.RESOLVED
        conflict.resolution = ConflictResolution.KEPT_OLD

    elif action == "keep_new":
        # archive old, activate new
        if old_mem:
            record_history(db, old_mem.id, old_mem.content, new_mem.content if new_mem else None, "conflict_resolved_replaced")
            old_mem.status = MemoryStatus.ARCHIVED
            db.add(old_mem)
        if new_mem:
            new_mem.status = MemoryStatus.ACTIVE
            db.add(new_mem)
        conflict.status = ConflictStatus.RESOLVED
        conflict.resolution = ConflictResolution.KEPT_NEW

    elif action == "merge":
        if not merged_content:
            raise ValueError("merged_content required for merge action")
        # apply merged content onto old_mem, delete new_mem
        if old_mem:
            record_history(db, old_mem.id, old_mem.content, merged_content, "conflict_merged")
            old_mem.content = merged_content
            old_mem.status = MemoryStatus.ACTIVE
            db.add(old_mem)
        if new_mem:
            record_history(db, new_mem.id, None, new_mem.content, "conflict_rejected_post_merge")
            new_mem.status = MemoryStatus.DELETED
            db.add(new_mem)
        conflict.status = ConflictStatus.RESOLVED
        conflict.resolution = ConflictResolution.MERGED

    else:
        raise ValueError("unknown action")

    db.add(conflict)
    db.commit()
    db.refresh(conflict)
    return conflict


def transition_lifecycle(db: Session, memory: Memory, new_status: MemoryStatus, reason: str = "lifecycle_transition"):
    old = memory.status
    if old == new_status:
        return memory
    record_history(db, memory.id, memory.content, memory.content, reason)
    memory.status = new_status
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def score_importance(content: str) -> float:
    """Simple heuristic importance scorer.

    Rules (simple MVP heuristic):
    - If content contains urgent/important keywords => 0.9
    - If content length > 200 => 0.7
    - Otherwise => 0.5
    """
    text = content.lower()
    important_keywords = ["important", "urgent", "remember", "must", "critical", "priority"]
    if any(k in text for k in important_keywords):
        return 0.9
    if len(text) > 200:
        return 0.7
    return 0.5


def get_memory(db: Session, memory_id: int, user_id: int) -> Memory | None:
    # Exclude soft-deleted memories by default to preserve privacy and prevent
    # access to content after user-initiated deletion. Use list/query methods
    # for broader retrieval where necessary.
    return (
        db.query(Memory)
        .filter(Memory.id == memory_id, Memory.user_id == user_id, Memory.status != MemoryStatus.DELETED)
        .first()
    )


def list_memories(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Memory]:
    return (
        db.query(Memory)
        .filter(Memory.user_id == user_id, Memory.status != MemoryStatus.DELETED)
        .order_by(Memory.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_memory(db: Session, memory: Memory, memory_in: MemoryUpdate) -> Memory:
    changed = False
    for field, value in memory_in.model_dump(exclude_unset=True).items():
        setattr(memory, field, value)
        changed = True

    if changed:
        memory.updated_at = datetime.utcnow()
        db.add(memory)
        db.commit()
        db.refresh(memory)

    return memory


def delete_memory(db: Session, memory: Memory) -> None:
    # Soft-delete: mark as DELETED so we preserve history.
    memory.status = MemoryStatus.DELETED
    db.add(memory)
    db.commit()
