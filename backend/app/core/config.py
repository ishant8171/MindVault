"""
Central configuration for MindVault.

All secrets and environment-specific values are loaded from environment
variables (via a .env file in development). Nothing here is hard-coded.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "MindVault"
    ENV: str = "development"

    # --- Database ---
    # Default: local SQLite file. Swap to a Postgres URL later
    # (e.g. postgresql://user:pass@host:5432/dbname) with no code changes,
    # since we access the DB only through SQLAlchemy.
    DATABASE_URL: str = "sqlite:///./mindvault.db"

    # --- Auth / JWT ---
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # --- AI Provider ---
    # ai_service.py reads these. Provider is swappable because nothing
    # outside ai_service.py knows which provider is in use.
    AI_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-lite-latest"

    # --- Storage ---
    UPLOAD_DIR: str = "uploads"

    # --- CORS ---
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
