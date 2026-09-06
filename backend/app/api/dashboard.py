from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.services.dashboard_service import get_dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/")
def get_user_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Retrieve the personal reflection dashboard for the authenticated user.
    Answers 'What is happening with me?' using the user's evolving knowledge model.
    """
    return get_dashboard(db=db, user_id=current_user.id)
