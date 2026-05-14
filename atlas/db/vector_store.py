import httpx
import asyncpg
import uuid
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

_RAW_URL = os.getenv("DATABASE_URL", "postgresql://heimdall:heimdall_secure_2026@localhost:5432/heimdall")
DATABASE_URL = _RAW_URL.replace("+asyncpg", "")

VECTOR_TABLES = ["vector_memory", "vector_notes", "vector_chat_summaries", "vector_code_chunks"]


async def get_conn():
    return await asyncpg.connect(DATABASE_URL)


async def embed_text(text: str) -> list[float]:
    """Generate embedding using local Ollama nomic-embed-text"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:11434/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": text},
            timeout=30,
        )
        return response.json()["embedding"]


async def init_vector_tables():
    """Create pgvector tables if they don't exist, and migrate created_at if missing"""
    conn = await get_conn()
    try:
        for table in VECTOR_TABLES:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_path TEXT DEFAULT '',
                    embedding vector(768),
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            # Migrate existing tables that lack created_at
            await conn.execute(f"""
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
            """)
    finally:
        await conn.close()


async def store(table: str, text: str, source_type: str, source_path: str = "") -> str:
    """Store text with its embedding in a vector table"""
    entry_id = str(uuid.uuid4())
    embedding = await embed_text(text)
    vector_str = "[" + ",".join(map(str, embedding)) + "]"
    now = datetime.utcnow()

    conn = await get_conn()
    try:
        await conn.execute(
            f"INSERT INTO {table} (id, text, source_type, source_path, embedding, created_at) VALUES ($1, $2, $3, $4, $5::vector, $6)",
            entry_id, text, source_type, source_path, vector_str, now,
        )
        return entry_id
    finally:
        await conn.close()


async def search(table: str, query: str, limit: int = 5) -> list[dict]:
    """Search a vector table for semantically similar entries"""
    embedding = await embed_text(query)
    vector_str = "[" + ",".join(map(str, embedding)) + "]"

    conn = await get_conn()
    try:
        rows = await conn.fetch(
            f"""
            SELECT id, text, source_type, source_path, created_at,
                   embedding <=> $1::vector AS distance
            FROM {table}
            ORDER BY embedding <=> $1::vector
            LIMIT $2
            """,
            vector_str, limit,
        )
        return [
            {"id": r["id"], "text": r["text"], "source_type": r["source_type"],
             "source_path": r["source_path"], "distance": r["distance"],
             "created_at": r["created_at"].isoformat() if r["created_at"] else None}
            for r in rows
        ]
    finally:
        await conn.close()


async def search_recent(table: str, query: str, hours: int = 48, limit: int = 10) -> list[dict]:
    """Search a vector table filtered to entries created within the last N hours, ordered by recency then similarity."""
    embedding = await embed_text(query)
    vector_str = "[" + ",".join(map(str, embedding)) + "]"
    since = datetime.utcnow() - timedelta(hours=hours)

    conn = await get_conn()
    try:
        rows = await conn.fetch(
            f"""
            SELECT id, text, source_type, source_path, created_at,
                   embedding <=> $1::vector AS distance
            FROM {table}
            WHERE created_at >= $2
            ORDER BY created_at DESC, embedding <=> $1::vector
            LIMIT $3
            """,
            vector_str, since, limit,
        )
        return [
            {"id": r["id"], "text": r["text"], "source_type": r["source_type"],
             "source_path": r["source_path"], "distance": r["distance"],
             "created_at": r["created_at"].isoformat() if r["created_at"] else None}
            for r in rows
        ]
    finally:
        await conn.close()


async def search_all(query: str, limit: int = 5) -> list[dict]:
    """Search across all vector tables"""
    results = []
    for table in VECTOR_TABLES:
        try:
            results += await search(table, query, limit=3)
        except Exception:
            pass
    results.sort(key=lambda r: r["distance"])
    return results[:limit]


async def browse(table: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """Return entries from a table ordered by created_at desc, no embedding needed."""
    conn = await get_conn()
    try:
        rows = await conn.fetch(
            f"SELECT id, text, source_type, source_path, created_at FROM {table} ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit, offset,
        )
        return [
            {"id": r["id"], "text": r["text"],
             "source_type": r["source_type"], "source_path": r["source_path"],
             "created_at": r["created_at"].isoformat() if r["created_at"] else None}
            for r in rows
        ]
    finally:
        await conn.close()


async def counts() -> dict[str, int]:
    """Return entry count for each vector table."""
    conn = await get_conn()
    try:
        result = {}
        for table in VECTOR_TABLES:
            row = await conn.fetchrow(f"SELECT COUNT(*) AS n FROM {table}")
            result[table] = row["n"]
        return result
    finally:
        await conn.close()
