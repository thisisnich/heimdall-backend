from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from atlas.api.chat import router as chat_router
from atlas.api.memory import router as memory_router
from atlas.api.health import router as health_router
from atlas.api.dashboard import router as dashboard_router
from atlas.api.models import router as models_router
from atlas.api.brief import router as brief_router
from atlas.api.vault import router as vault_router
from atlas.api.ingest import router as ingest_router
from atlas.api.auth import router as auth_router
from atlas.api.habits import router as habits_router
from atlas.api.budget import router as budget_router
from atlas.api.goals import router as goals_router
from atlas.api.knowledge_graph import router as graph_router
from atlas.api.dev import router as dev_router
from atlas.api.calendar import router as calendar_router
from atlas.api.telegram import router as telegram_router
from atlas.db.vector_store import init_vector_tables
from atlas.db.session import get_session
from atlas.db.models import User
from sqlalchemy import select
import uuid

app = FastAPI(
    title="Heimdall API",
    description="Personal AI assistant backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(memory_router)
app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(models_router)
app.include_router(brief_router)
app.include_router(vault_router)
app.include_router(ingest_router)
app.include_router(auth_router)
app.include_router(habits_router)
app.include_router(budget_router)
app.include_router(goals_router)
app.include_router(graph_router)
app.include_router(dev_router)
app.include_router(calendar_router)
app.include_router(telegram_router)


async def ensure_default_user():
    """Create a default user if one doesn't exist."""
    async with get_session() as session:
        result = await session.execute(select(User).where(User.id == "default"))
        if not result.scalar_one_or_none():
            user = User(
                id="default",
                email="user@heimdall.local",
                hashed_password="not-used",
            )
            session.add(user)
            await session.commit()


@app.on_event("startup")
async def startup():
    await init_vector_tables()
    await ensure_default_user()


@app.get("/")
async def root():
    return {"name": "Heimdall", "status": "running", "docs": "/docs"}
