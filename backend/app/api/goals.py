from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.schemas.goal import GoalCreate, GoalOut, GoalUpdate
from app.services import goal_service
from app.models.user import User


router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("/", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(goal_in: GoalCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if goal_in.progress is not None and not (0.0 <= goal_in.progress <= 1.0):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Progress must be between 0.0 and 1.0")
    goal = goal_service.create_goal(db, current_user, goal_in)
    return goal


@router.get("/", response_model=list[GoalOut])
def list_goals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return goal_service.list_goals(db, current_user.id)


@router.get("/{goal_id}", response_model=GoalOut)
def read_goal(goal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    goal = goal_service.get_goal(db, goal_id, current_user.id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(goal_id: int, goal_in: GoalUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    goal = goal_service.get_goal(db, goal_id, current_user.id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    # validate progress
    if goal_in.progress is not None and not (0.0 <= goal_in.progress <= 1.0):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Progress must be between 0.0 and 1.0")
    goal = goal_service.update_goal(db, goal, goal_in)
    return goal


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    goal = goal_service.get_goal(db, goal_id, current_user.id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    goal_service.delete_goal(db, goal)
    return None
