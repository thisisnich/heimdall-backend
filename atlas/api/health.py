from fastapi import APIRouter
import httpx
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/health", tags=["health"])

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
_DB_URL = os.getenv("DATABASE_URL", "postgresql://heimdall:heimdall_secure_2026@localhost:5432/heimdall")
DATABASE_URL = _DB_URL.replace("+asyncpg", "")


async def _check_postgres() -> dict:
    try:
        conn = await asyncpg.connect(DATABASE_URL, timeout=5)
        version = await conn.fetchval("SELECT version()")
        await conn.close()
        return {"status": "ok", "detail": version.split(",")[0]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


async def _check_ollama() -> dict:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            models = [m["name"] for m in r.json()["models"]]
            return {"status": "ok", "models": models}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("")
async def health_check():
    postgres = await _check_postgres()
    ollama = await _check_ollama()
    all_ok = postgres["status"] == "ok" and ollama["status"] == "ok"
    return {
        "status": "ok" if all_ok else "degraded",
        "services": {
            "postgres": postgres,
            "ollama": ollama,
        },
    }
