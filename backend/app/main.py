"""
MindVault backend entrypoint.
Registers database tables, middlewares, and all feature routers.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.memory import router as memory_router
from app.api.ai import router as ai_router
from app.api.goals import router as goals_router
from app.api.skills import router as skills_router
from app.api.knowledge import router as knowledge_router
from app.api.knowledge_concepts import router as concepts_router
from app.api.learning_preferences import router as preferences_router
from app.api.tasks import router as tasks_router
from app.api.documents import router as documents_router
from app.api.knowledge_graph import router as knowledge_graph_router
from app.api.assistant import router as assistant_router

from app.core.config import settings
from app.database.base import Base, engine
import app.models  # noqa: F401  (registers all models on Base.metadata)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure any tables that don't exist yet are created. Safe to run repeatedly.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# Auth & Core Routers
app.include_router(auth_router)
app.include_router(memory_router)
app.include_router(ai_router)
app.include_router(goals_router)
app.include_router(skills_router)
app.include_router(knowledge_router)

# Virtual Brain Phase 5 Routers
app.include_router(concepts_router)
app.include_router(preferences_router)
app.include_router(tasks_router)
app.include_router(documents_router)
app.include_router(knowledge_graph_router)
app.include_router(assistant_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENV}
