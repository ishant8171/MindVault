from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

from app.models.skill import Skill, SkillStatus
from app.models.user import User
from app.schemas.skill import SkillCreate, SkillUpdate


def create_skill(db: Session, user: User, skill_in: SkillCreate) -> Skill:
    skill = Skill(
        user_id=user.id,
        name=skill_in.name,
        category=skill_in.category,
        status=skill_in.status or SkillStatus.NOT_STARTED,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def get_skill(db: Session, skill_id: int, user_id: int) -> Skill | None:
    return db.query(Skill).filter(Skill.id == skill_id, Skill.user_id == user_id).first()


def list_skills(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Skill]:
    return db.query(Skill).filter(Skill.user_id == user_id).order_by(Skill.updated_at.desc()).offset(skip).limit(limit).all()


def update_skill(db: Session, skill: Skill, skill_in: SkillUpdate) -> Skill:
    changed = False
    for field, value in skill_in.model_dump(exclude_unset=True).items():
        setattr(skill, field, value)
        changed = True

    if changed:
        skill.updated_at = datetime.now(timezone.utc)
        db.add(skill)
        db.commit()
        db.refresh(skill)

    return skill


def delete_skill(db: Session, skill: Skill) -> None:
    db.delete(skill)
    db.commit()
