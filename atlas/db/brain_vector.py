"""
Brain Vector Store — pgvector integration for brain memory.

Extends existing vector_store.py with brain-specific tables:
  - vector_brain_memory: Embeddings for BrainMemory
  - vector_brain_notes: Embeddings for BrainNote

Provides semantic search, similarity, and consolidation support.
"""

import asyncpg
import uuid
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import httpx

load_dotenv()

_RAW_URL = os.getenv("DATABASE_URL", "postgresql://heimdall:heimdall_secure_2026@localhost:5432/heimdall")
DATABASE_URL = _RAW_URL.replace("+asyncpg", "")

BRAIN_VECTOR_TABLES = ["vector_brain_memory", "vector_brain_notes"]


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


async def init_brain_vector_tables():
    """Create brain-specific vector tables if they don't exist"""
    conn = await get_conn()
    try:
        for table in BRAIN_VECTOR_TABLES:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    memory_type TEXT,
                    source_type TEXT,
                    embedding vector(768),
                    importance FLOAT DEFAULT 0.5,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    last_accessed TIMESTAMPTZ
                );
            """)
            
            # Create indexes for efficient queries
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table}_importance 
                ON {table} (importance DESC);
            """)
            
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table}_created_at 
                ON {table} (created_at DESC);
            """)
            
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table}_memory_type 
                ON {table} (memory_type);
            """)
    finally:
        await conn.close()


async def store_brain_memory(
    memory_id: str,
    text: str,
    memory_type: str = "semantic",
    source_type: str = "manual",
    importance: float = 0.5
) -> str:
    """Store brain memory with embedding"""
    embedding = await embed_text(text)
    vector_str = "[" + ",".join(map(str, embedding)) + "]"
    now = datetime.utcnow()

    conn = await get_conn()
    try:
        await conn.execute(
            """INSERT INTO vector_brain_memory 
               (id, text, memory_type, source_type, embedding, importance, created_at, last_accessed) 
               VALUES ($1, $2, $3, $4, $5::vector, $6, $7, $8)
               ON CONFLICT (id) DO UPDATE SET
                   text = EXCLUDED.text,
                   memory_type = EXCLUDED.memory_type,
                   source_type = EXCLUDED.source_type,
                   embedding = EXCLUDED.embedding,
                   importance = EXCLUDED.importance,
                   last_accessed = $8""",
            memory_id, text, memory_type, source_type, vector_str, importance, now, now,
        )
        return memory_id
    finally:
        await conn.close()


async def store_brain_note(
    note_id: str,
    text: str,
    source_type: str = "manual",
    importance: float = 0.5
) -> str:
    """Store brain note with embedding"""
    embedding = await embed_text(text)
    vector_str = "[" + ",".join(map(str, embedding)) + "]"
    now = datetime.utcnow()

    conn = await get_conn()
    try:
        await conn.execute(
            """INSERT INTO vector_brain_notes 
               (id, text, memory_type, source_type, embedding, importance, created_at, last_accessed) 
               VALUES ($1, $2, 'note', $3, $4::vector, $5, $6, $7)
               ON CONFLICT (id) DO UPDATE SET
                   text = EXCLUDED.text,
                   source_type = EXCLUDED.source_type,
                   embedding = EXCLUDED.embedding,
                   importance = EXCLUDED.importance,
                   last_accessed = $7""",
            note_id, text, source_type, vector_str, importance, now, now,
        )
        return note_id
    finally:
        await conn.close()


async def search_brain_memory(
    query: str,
    memory_type: str = None,
    min_importance: float = 0.0,
    limit: int = 10
) -> list[dict]:
    """Search brain memory semantically with optional filters"""
    embedding = await embed_text(query)
    vector_str = "[" + ",".join(map(str, embedding)) + "]"

    conn = await get_conn()
    try:
        # Build query with optional filters
        where_clause = ""
        params = [vector_str, limit]
        param_idx = 3
        
        if memory_type:
            where_clause += f" AND memory_type = ${param_idx}"
            params.append(memory_type)
            param_idx += 1
            
        if min_importance > 0:
            where_clause += f" AND importance >= ${param_idx}"
            params.append(min_importance)
            param_idx += 1
        
        query_sql = f"""
            SELECT id, text, memory_type, source_type, importance, created_at, last_accessed,
                   embedding <=> $1::vector AS distance
            FROM vector_brain_memory
            WHERE 1=1 {where_clause}
            ORDER BY importance DESC, embedding <=> $1::vector
            LIMIT $2
        """
        
        rows = await conn.fetch(query_sql, *params)
        return [
            {
                "id": r["id"],
                "text": r["text"],
                "memory_type": r["memory_type"],
                "source_type": r["source_type"],
                "importance": r["importance"],
                "distance": r["distance"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "last_accessed": r["last_accessed"].isoformat() if r["last_accessed"] else None
            }
            for r in rows
        ]
    finally:
        await conn.close()


async def search_brain_notes(
    query: str,
    min_importance: float = 0.0,
    limit: int = 10
) -> list[dict]:
    """Search brain notes semantically"""
    embedding = await embed_text(query)
    vector_str = "[" + ",".join(map(str, embedding)) + "]"

    conn = await get_conn()
    try:
        params = [vector_str, min_importance, limit]
        
        query_sql = """
            SELECT id, text, source_type, importance, created_at, last_accessed,
                   embedding <=> $1::vector AS distance
            FROM vector_brain_notes
            WHERE importance >= $2
            ORDER BY importance DESC, embedding <=> $1::vector
            LIMIT $3
        """
        
        rows = await conn.fetch(query_sql, *params)
        return [
            {
                "id": r["id"],
                "text": r["text"],
                "source_type": r["source_type"],
                "importance": r["importance"],
                "distance": r["distance"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "last_accessed": r["last_accessed"].isoformat() if r["last_accessed"] else None
            }
            for r in rows
        ]
    finally:
        await conn.close()


async def search_brain_all(query: str, limit: int = 10) -> dict:
    """Search across both brain memory and notes"""
    memory_results = await search_brain_memory(query, limit=limit//2)
    note_results = await search_brain_notes(query, limit=limit//2)
    
    return {
        "memories": memory_results,
        "notes": note_results,
        "total": len(memory_results) + len(note_results)
    }


async def update_access(memory_id: str, table: str = "vector_brain_memory"):
    """Update last_accessed timestamp and increment access count"""
    conn = await get_conn()
    try:
        await conn.execute(
            f"UPDATE {table} SET last_accessed = NOW() WHERE id = $1",
            memory_id
        )
    finally:
        await conn.close()


async def update_importance(memory_id: str, importance: float, table: str = "vector_brain_memory"):
    """Update importance score"""
    conn = await get_conn()
    try:
        await conn.execute(
            f"UPDATE {table} SET importance = $1 WHERE id = $2",
            importance, memory_id
        )
    finally:
        await conn.close()


async def get_decay_candidates(
    table: str = "vector_brain_memory",
    days_threshold: int = 30,
    max_importance: float = 0.3
) -> list[dict]:
    """Get memories that haven't been accessed recently and have low importance"""
    conn = await get_conn()
    try:
        threshold_date = datetime.utcnow() - timedelta(days=days_threshold)
        
        rows = await conn.fetch(
            f"""
            SELECT id, text, importance, last_accessed, created_at
            FROM {table}
            WHERE last_accessed < $1 
              AND importance < $2
            ORDER BY importance ASC, last_accessed ASC
            LIMIT 50
            """,
            threshold_date, max_importance
        )
        
        return [
            {
                "id": r["id"],
                "text": r["text"],
                "importance": r["importance"],
                "last_accessed": r["last_accessed"].isoformat() if r["last_accessed"] else None,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None
            }
            for r in rows
        ]
    finally:
        await conn.close()


async def delete_vector(memory_id: str, table: str = "vector_brain_memory"):
    """Delete a vector entry"""
    conn = await get_conn()
    try:
        await conn.execute(f"DELETE FROM {table} WHERE id = $1", memory_id)
    finally:
        await conn.close()


async def get_brain_stats() -> dict:
    """Get statistics about brain vector tables"""
    conn = await get_conn()
    try:
        stats = {}
        for table in BRAIN_VECTOR_TABLES:
            # Total count
            count_row = await conn.fetchrow(f"SELECT COUNT(*) as n FROM {table}")
            stats[table] = {"total": count_row["n"]}
            
            # By memory type
            type_rows = await conn.fetch(
                f"SELECT memory_type, COUNT(*) as n FROM {table} GROUP BY memory_type"
            )
            stats[table]["by_type"] = {r["memory_type"]: r["n"] for r in type_rows}
            
            # Average importance
            imp_row = await conn.fetchrow(f"SELECT AVG(importance) as avg_imp FROM {table}")
            stats[table]["avg_importance"] = float(imp_row["avg_imp"]) if imp_row["avg_imp"] else 0.0
            
            # Recently accessed
            recent_row = await conn.fetchrow(
                f"SELECT COUNT(*) as n FROM {table} WHERE last_accessed > NOW() - INTERVAL '7 days'"
            )
            stats[table]["recent_access"] = recent_row["n"]
        
        return stats
    finally:
        await conn.close()
