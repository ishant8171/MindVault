"""
Session management. Every request gets its own SQLAlchemy session via
the `get_db` dependency, which is closed automatically after the request.
"""

from sqlalchemy.orm import sessionmaker, Session

from app.database.base import engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
