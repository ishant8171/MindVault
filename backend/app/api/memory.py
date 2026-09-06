from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.schemas.memory import MemoryCreate, MemoryOut, MemoryUpdate, ConflictDetected
from app.schemas.memory import ExtractRequest, ExtractResponse
from app.services.extraction_service import extract_candidates
from app.services.memory_service import score_importance
from app.services.retrieval_service import retrieve_memories
from app.schemas.memory import RetrievalRequest, RetrievalResponse
from app.services import memory_service
from app.models.user import User
from app.schemas.memory import MemoryConflictOut, ConflictResolveRequest, ConflictResolveResponse, LifecycleRequest
from app.models.memory import MemoryCategory, MemoryStatus


router = APIRouter(prefix="/memories", tags=["memories"])


@router.post("/", response_model=MemoryOut, status_code=status.HTTP_201_CREATED)
def create_memory(
    memory_in: MemoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check for slot-scoped conflicts first
    if memory_in.slot_key:
        existing = memory_service.find_slot_conflict(db, current_user.id, memory_in.slot_key, memory_in.content)
        if existing:
            # exact same content -> return existing (no-op)
            if existing.content.strip() == memory_in.content.strip():
                from fastapi.responses import JSONResponse

                return JSONResponse(status_code=status.HTTP_200_OK, content=MemoryOut.from_orm(existing).model_dump(mode="json"))

            # potential conflict: persist candidate as NEW and record conflict
            new_mem = memory_service.create_memory(db, current_user, memory_in, status=MemoryStatus.NEW)
            conflict = memory_service.create_conflict(db, current_user.id, existing.id, new_mem.id)
            conflict_body = ConflictDetected(
                message="Slot-conflict detected",
                slot_key=memory_in.slot_key,
                existing=existing,
                candidate=memory_in,
                conflict_id=conflict.id,
            )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=conflict_body.model_dump(mode="json"))
    memory = memory_service.create_memory(db, current_user, memory_in)
    return memory


@router.get("/", response_model=list[MemoryOut])
def list_memories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    memories = memory_service.list_memories(db, current_user.id, skip=skip, limit=limit)
    return memories


@router.get("/conflicts", response_model=list[MemoryConflictOut])
def list_conflicts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conflicts = memory_service.get_conflicts_for_user(db, current_user.id)
    out = []
    for c in conflicts:
        out.append({
            "id": c.id,
            "user_id": c.user_id,
            "old_memory_id": c.old_memory_id,
            "new_memory_id": c.new_memory_id,
            "status": c.status.value if c.status else None,
            "resolution": c.resolution.value if c.resolution else None,
            "created_at": c.created_at,
        })
    return out


@router.post("/conflicts/{conflict_id}/resolve", response_model=ConflictResolveResponse)
def resolve_conflict(conflict_id: int, req: ConflictResolveRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conflict = memory_service.get_conflict(db, conflict_id, current_user.id)
    if not conflict:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found")
    if conflict.status and conflict.status.value != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Conflict already resolved")
    try:
        resolved = memory_service.resolve_conflict(db, conflict, req.action, req.merged_content)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return ConflictResolveResponse(id=resolved.id, status=resolved.status.value, resolution=resolved.resolution.value if resolved.resolution else None)


@router.post("/{memory_id}/lifecycle", response_model=MemoryOut)
def lifecycle_transition(memory_id: int, req: LifecycleRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    memory = memory_service.get_memory(db, memory_id, current_user.id)
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    action = req.action
    mapping = {
        "activate": MemoryStatus.ACTIVE,
        "mark_less_relevant": MemoryStatus.LESS_RELEVANT,
        "archive": MemoryStatus.ARCHIVED,
        "expire": MemoryStatus.EXPIRED,
        "delete": MemoryStatus.DELETED,
    }
    if action not in mapping:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown lifecycle action")

    new_status = mapping[action]
    memory = memory_service.transition_lifecycle(db, memory, new_status, reason=f"lifecycle:{action}")
    return memory


@router.get("/{memory_id}", response_model=MemoryOut)
def read_memory(memory_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    memory = memory_service.get_memory(db, memory_id, current_user.id)
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return memory


@router.patch("/{memory_id}", response_model=MemoryOut)
def update_memory(memory_id: int, memory_in: MemoryUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    memory = memory_service.get_memory(db, memory_id, current_user.id)
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    memory = memory_service.update_memory(db, memory, memory_in)
    return memory


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(memory_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    memory = memory_service.get_memory(db, memory_id, current_user.id)
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    memory_service.delete_memory(db, memory)
    return None


@router.post("/extract", response_model=ExtractResponse)
def extract_memories(req: ExtractRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Use the configured AI provider to extract memory candidates from free text.

    Candidates are returned but not persisted. Each candidate receives an
    importance score by a simple heuristic.
    """
    candidates = extract_candidates(req.text)
    # Score importance for each candidate
    for c in candidates:
        c.importance_score = score_importance(c.content)
    return ExtractResponse(candidates=candidates)


@router.post("/retrieve", response_model=RetrievalResponse)
def retrieve(req: RetrievalRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = (req.query or "").strip()
    if len(q) < 3:
        # Avoid noisy/short queries
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query too short; provide at least 3 characters")

    category = req.category
    if isinstance(category, str):
        try:
            category = MemoryCategory(category)
        except Exception:
            category = None

    results = retrieve_memories(db, current_user.id, query=q, category=category, limit=req.limit or 10)

    return RetrievalResponse(results=results)

