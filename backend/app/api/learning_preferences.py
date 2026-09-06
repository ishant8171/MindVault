from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.models.learning_preference import LearningPreference
from app.models.evidence import EvidenceType, SubjectType
from app.schemas.preference import PreferenceCreate, PreferenceOut
from app.services.evidence_service import record_evidence

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("/", response_model=List[PreferenceOut])
def list_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all learning preferences for the authenticated user."""
    return (
        db.query(LearningPreference)
        .filter(LearningPreference.user_id == current_user.id)
        .order_by(LearningPreference.confidence.desc())
        .all()
    )


@router.get("/{pref_id}", response_model=PreferenceOut)
def get_preference(
    pref_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single learning preference."""
    pref = (
        db.query(LearningPreference)
        .filter(LearningPreference.id == pref_id, LearningPreference.user_id == current_user.id)
        .first()
    )
    if not pref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preference not found")
    return pref


@router.post("/", response_model=PreferenceOut, status_code=status.HTTP_201_CREATED)
def create_or_reinforce_preference(
    pref_in: PreferenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Explicitly create or reinforce a learning preference.
    Calls EvidenceService with evidence_type='explicit_statement'.
    """
    pref_type = pref_in.preference_type.strip().lower()

    # Find existing or create initial row
    pref = (
        db.query(LearningPreference)
        .filter(LearningPreference.user_id == current_user.id, LearningPreference.preference_type == pref_type)
        .first()
    )
    if not pref:
        pref = LearningPreference(
            user_id=current_user.id,
            preference_type=pref_type,
            confidence=0.1,
            evidence_count=0,
            created_at=datetime.now(timezone.utc),
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)

    # Emit explicit statement evidence to update confidence
    weight = pref_in.initial_confidence if pref_in.initial_confidence is not None else 0.6
    record_evidence(
        db=db,
        user_id=current_user.id,
        evidence_type=EvidenceType.EXPLICIT_STATEMENT,
        subject_type=SubjectType.LEARNING_PREFERENCE,
        subject_id=pref.id,
        weight=weight,
        summary=f"User stated learning preference: {pref_type}",
        source_ref="user_statement",
    )

    db.refresh(pref)
    return pref
