"""
MindVault Phase 1 Database Migration Script.

Responsibilities:
1. Base.metadata.create_all: creates all net-new tables (evidence, knowledge_concepts,
   learning_preferences, knowledge_state_snapshots, tasks, documents,
   document_chunks, subjects).
2. Schema patching: Adds nullable `subject_id` column to `goals` table if not already present.
3. Data Migration: Copies existing records from `skills` table to `knowledge_concepts`:
   - "completed"   -> current_level = 1.0, confidence = 0.8
   - "learning"    -> current_level = 0.3, confidence = 0.5
   - "not_started" -> current_level = 0.0, confidence = 0.3
   (Lossy heuristic: mapping a 3-state enum to continuous confidence scores).
4. Idempotent: checks for already migrated skill IDs via `migrated_from_skill_id`.
"""

import sys
import os
from pathlib import Path

# Add backend directory to sys.path so app imports work
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import inspect, text
from app.database.base import Base, engine
from app.database.session import SessionLocal
import app.models  # Registers all models with Base.metadata
from app.models.skill import Skill, SkillStatus
from app.models.knowledge_concept import KnowledgeConcept


def migrate():
    print("[1/3] Creating new tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    print("      Table creation complete.")

    db = SessionLocal()
    try:
        print("[2/3] Checking column additions on existing tables...")
        inspector = inspect(engine)
        goals_cols = [c["name"] for c in inspector.get_columns("goals")]
        if "subject_id" not in goals_cols:
            print("      Adding 'subject_id' column to 'goals' table...")
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE goals ADD COLUMN subject_id INTEGER REFERENCES subjects(id)"))
                conn.commit()
            print("      'subject_id' column added.")
        else:
            print("      'subject_id' already exists in 'goals'.")

        print("[3/3] Migrating existing Skill rows to KnowledgeConcept...")
        existing_skills = db.query(Skill).all()
        already_migrated_ids = set(
            row[0]
            for row in db.query(KnowledgeConcept.migrated_from_skill_id)
            .filter(KnowledgeConcept.migrated_from_skill_id.isnot(None))
            .all()
        )

        migrated_count = 0
        skipped_count = 0

        # Mapping heuristic from SkillStatus enum to numeric level & confidence:
        # - COMPLETED: Full conceptual exposure (1.0 level), high confidence (0.8)
        # - LEARNING: In progress (0.3 level), moderate initial confidence (0.5)
        # - NOT_STARTED: No active progress (0.0 level), low baseline confidence (0.3)
        STATUS_MAPPING = {
            SkillStatus.COMPLETED: (1.0, 0.8),
            SkillStatus.LEARNING: (0.3, 0.5),
            SkillStatus.NOT_STARTED: (0.0, 0.3),
        }

        for skill in existing_skills:
            if skill.id in already_migrated_ids:
                skipped_count += 1
                continue

            current_level, confidence = STATUS_MAPPING.get(
                skill.status, (0.0, 0.3)
            )

            concept = KnowledgeConcept(
                user_id=skill.user_id,
                name=skill.name,
                category=skill.category,
                current_level=current_level,
                confidence=confidence,
                evidence_count=1 if skill.status != SkillStatus.NOT_STARTED else 0,
                last_updated=skill.updated_at,
                migrated_from_skill_id=skill.id,
            )
            db.add(concept)
            migrated_count += 1

        db.commit()
        print(f"      Migration completed: {migrated_count} skills migrated, {skipped_count} already migrated.")

    finally:
        db.close()

    print("\nPhase 1 migration successful!")


if __name__ == "__main__":
    migrate()
