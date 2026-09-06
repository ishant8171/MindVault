from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.memory import Memory, MemoryStatus, MemoryCategory


def _tokenize(query: str) -> list[str]:
    return [t.strip().lower() for t in query.split() if t.strip()]


def retrieve_memories(db: Session, user_id: int, query: Optional[str] = None, category: Optional[MemoryCategory] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve relevant memories for a user based on keyword match + category + recency + importance.

    Returns a list of dicts with memory metadata and a `score` and `reason` object explaining ranking.
    """
    base_q = db.query(Memory).filter(Memory.user_id == user_id, Memory.status == MemoryStatus.ACTIVE)

    tokens = []
    if query:
        tokens = _tokenize(query)

    filters = []
    if tokens:
        for t in tokens:
            filters.append(Memory.content.ilike(f"%{t}%"))

    if category:
        # allow category match even without token matches
        if isinstance(category, str):
            try:
                category = MemoryCategory(category)
            except Exception:
                category = None
    
    if filters:
        base_q = base_q.filter(or_(*filters) | (Memory.category == category) if category else or_(*filters))
    else:
        if category:
            base_q = base_q.filter(Memory.category == category)

    results = base_q.all()

    scored: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    for m in results:
        content = (m.content or "").lower()
        keyword_score = 0.0
        for t in tokens:
            keyword_score += content.count(t)

        category_bonus = 1.0 if (category and m.category == category) else 0.0

        # importance_score stored 0..1; scale it
        importance_component = (m.importance_score or 0.5) * 2.0

        # simple recency boost: created in last 30 days => +1.0, 31-90 days => +0.5
        recency_bonus = 0.0
        if m.created_at:
            created = m.created_at
            # ensure timezone-aware for safe subtraction
            if created.tzinfo is None:
                from datetime import timezone as _tz

                created = created.replace(tzinfo=_tz.utc)
            delta = now - created
            days = delta.days
            if days <= 30:
                recency_bonus = 1.0
            elif days <= 90:
                recency_bonus = 0.5

        total_score = keyword_score + category_bonus + importance_component + recency_bonus

        reason = {
            "keyword_score": keyword_score,
            "category_bonus": category_bonus,
            "importance_component": importance_component,
            "recency_bonus": recency_bonus,
        }

        scored.append({
            "memory": m,
            "score": total_score,
            "reason": reason,
        })

    # sort descending by score
    scored.sort(key=lambda r: r["score"], reverse=True)

    # Limit results
    out: List[Dict[str, Any]] = []
    for r in scored[:limit]:
        m = r["memory"]
        out.append({
            "id": m.id,
            "content": m.content,
            "category": m.category.value if m.category else None,
            "importance_score": m.importance_score,
            "created_at": m.created_at,
            "score": r["score"],
            "reason": r["reason"],
        })

    return out
