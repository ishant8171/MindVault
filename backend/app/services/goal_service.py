from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

from app.models.goal import Goal
from app.models.user import User
from app.schemas.goal import GoalCreate, GoalUpdate
from app.models.goal import GoalStatus


def create_goal(db: Session, user: User, goal_in: GoalCreate) -> Goal:
    goal = Goal(
        user_id=user.id,
        title=goal_in.title,
        description=goal_in.description,
        priority=goal_in.priority,
        deadline=goal_in.deadline,
        progress=goal_in.progress if goal_in.progress is not None else 0.0,
        subject_id=goal_in.subject_id,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)

    # Wire into Knowledge Graph
    from app.services.knowledge_graph_service import hook_on_goal_created
    try:
        hook_on_goal_created(db, goal)
    except Exception:
        pass

    return goal


def get_goal(db: Session, goal_id: int, user_id: int) -> Goal | None:
    return db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user_id).first()


def list_goals(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Goal]:
    return db.query(Goal).filter(Goal.user_id == user_id).order_by(Goal.created_at.desc()).offset(skip).limit(limit).all()


def update_goal(db: Session, goal: Goal, goal_in: GoalUpdate) -> Goal:
    changed = False
    for field, value in goal_in.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)
        changed = True

    if changed:
        goal.updated_at = datetime.now(timezone.utc)
        db.add(goal)
        db.commit()
        db.refresh(goal)

    return goal


def delete_goal(db: Session, goal: Goal) -> None:
    # mark as abandoned rather than deleting to preserve records
    goal.status = GoalStatus.ABANDONED
    db.add(goal)
    db.commit()
