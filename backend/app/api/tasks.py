import json
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.models.task import Task, TaskStatus
from app.models.goal import Goal
from app.models.knowledge_concept import KnowledgeConcept
from app.models.evidence import EvidenceType, SubjectType
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate
from app.services.evidence_service import record_evidence

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=List[TaskOut])
def list_tasks(
    goal_id: Optional[int] = Query(None),
    status: Optional[TaskStatus] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List tasks for the authenticated user, optionally filtered by goal_id or status."""
    query = db.query(Task).filter(Task.user_id == current_user.id)
    if goal_id is not None:
        query = query.filter(Task.goal_id == goal_id)
    if status is not None:
        query = query.filter(Task.status == status)

    return query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a single task owned by the authenticated user."""
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a task for the authenticated user."""
    if task_in.goal_id:
        goal = (
            db.query(Goal)
            .filter(Goal.id == task_in.goal_id, Goal.user_id == current_user.id)
            .first()
        )
        if not goal:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Goal not found or not owned")

    concept_ids_str = json.dumps(task_in.related_concept_ids or [])

    task = Task(
        user_id=current_user.id,
        goal_id=task_in.goal_id,
        title=task_in.title.strip(),
        description=task_in.description,
        status=TaskStatus.NOT_STARTED,
        related_concept_ids=concept_ids_str,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a task.
    CRITICAL: When task status transitions to COMPLETED, this endpoint automatically
    calls EvidenceService.record_evidence for all associated related_concept_ids.
    """
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    old_status = task.status

    if task_in.title is not None:
        task.title = task_in.title.strip()
    if task_in.description is not None:
        task.description = task_in.description
    if task_in.goal_id is not None:
        goal = (
            db.query(Goal)
            .filter(Goal.id == task_in.goal_id, Goal.user_id == current_user.id)
            .first()
        )
        if not goal:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Goal not found or not owned")
        task.goal_id = task_in.goal_id
    if task_in.related_concept_ids is not None:
        task.related_concept_ids = json.dumps(task_in.related_concept_ids)

    if task_in.status is not None:
        task.status = task_in.status

    task.updated_at = datetime.now(timezone.utc)

    # Check for transition to COMPLETED
    if old_status != TaskStatus.COMPLETED and task.status == TaskStatus.COMPLETED:
        task.completed_at = datetime.now(timezone.utc)

        # Parse related concepts and record evidence
        try:
            concept_ids = json.loads(task.related_concept_ids or "[]")
        except Exception:
            concept_ids = []

        for cid in concept_ids:
            concept = (
                db.query(KnowledgeConcept)
                .filter(KnowledgeConcept.id == cid, KnowledgeConcept.user_id == current_user.id)
                .first()
            )
            if concept:
                record_evidence(
                    db=db,
                    user_id=current_user.id,
                    evidence_type=EvidenceType.TASK_COMPLETED,
                    subject_type=SubjectType.KNOWLEDGE_CONCEPT,
                    subject_id=concept.id,
                    weight=0.5,
                    summary=f"Completed task: {task.title}",
                    source_ref=f"task:{task.id}",
                )

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a task owned by the authenticated user."""
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    db.delete(task)
    db.commit()
    return None
