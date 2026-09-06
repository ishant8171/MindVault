"""
SQLAlchemy engine + declarative base.

Every model in app/models inherits from `Base` so that
Base.metadata.create_all() (called at startup) creates all tables.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# `check_same_thread` is only needed for SQLite; harmless to set generally
# since Postgres ignores unknown connect_args when omitted below.
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

Base = declarative_base()
