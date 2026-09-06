from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.schemas.skill import SkillCreate, SkillOut, SkillUpdate
from app.services import skill_service
from app.models.user import User


router = APIRouter(prefix="/skills", tags=["skills"])


@router.post("/", response_model=SkillOut, status_code=status.HTTP_201_CREATED)
def create_skill(skill_in: SkillCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    skill = skill_service.create_skill(db, current_user, skill_in)
    return skill


@router.get("/", response_model=list[SkillOut])
def list_skills(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return skill_service.list_skills(db, current_user.id)


@router.get("/{skill_id}", response_model=SkillOut)
def read_skill(skill_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    skill = skill_service.get_skill(db, skill_id, current_user.id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return skill


@router.patch("/{skill_id}", response_model=SkillOut)
def update_skill(skill_id: int, skill_in: SkillUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    skill = skill_service.get_skill(db, skill_id, current_user.id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    skill = skill_service.update_skill(db, skill, skill_in)
    return skill


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(skill_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    skill = skill_service.get_skill(db, skill_id, current_user.id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    skill_service.delete_skill(db, skill)
    return None
