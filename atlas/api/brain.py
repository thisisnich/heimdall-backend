"""
Heimdall Brain API — Endpoints for brain memory operations.

Provides REST API for:
  - Memory storage and retrieval
  - Note indexing and search
  - Brain statistics and health
  - Memory consolidation
  - Context management
"""

from typing import Optional, List
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atlas.db.session import get_session
from atlas.db.brain_models import (
    BrainMemory, BrainNote, BrainEntity, BrainContext,
    MemoryType, MemoryRegion
)
from atlas.services.brain_service import brain_service
from atlas.core.brain_indexer import brain_indexer
from atlas.core.brain_vault_writer import (
    sync_full_brain, sync_all_memories, sync_all_notes, sync_all_entities,
    BRAIN_VAULT_ROOT
)
from atlas.core.brain_git import (
    init_git_repo, commit_changes, push_to_remote,
    sync_and_push, get_git_status
)

router = APIRouter(prefix="/brain", tags=["brain"])


# Request/Response Models
class MemoryRequest(BaseModel):
    content: str
    memory_type: str = MemoryType.SEMANTIC.value
    memory_region: str = MemoryRegion.CORTEX.value
    source_type: str = "manual"
    source_id: Optional[str] = None
    importance: float = 0.5
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    metadata: Optional[dict] = None


class NoteRequest(BaseModel):
    title: str
    content: str
    note_type: str = "general"
    note_format: str = "markdown"
    folder: str = "general"
    collection: str = "default"
    source_type: str = "manual"
    importance: float = 0.5
    tags: Optional[List[str]] = None


class SearchRequest(BaseModel):
    query: str
    memory_type: Optional[str] = None
    min_importance: float = 0.0
    limit: int = 10


class ContextRequest(BaseModel):
    context_type: str = "general"
    context_name: str = ""
    active_memory_ids: Optional[List[str]] = None
    active_note_ids: Optional[List[str]] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    expires_in_hours: int = 24


class ConsolidationRequest(BaseModel):
    min_access_count: int = 3
    min_importance: float = 0.6
    days_threshold: int = 7


class IndexRequest(BaseModel):
    text: str
    source_type: str = "manual"
    source_id: Optional[str] = None


class ChatIndexRequest(BaseModel):
    user_message: str
    assistant_reply: str
    session_id: Optional[str] = None


# Memory Endpoints
@router.post("/memories")
async def store_memory(request: MemoryRequest, background_tasks: BackgroundTasks):
    """Store a new memory in the brain."""
    async with get_session() as session:
        try:
            memory = await brain_service.store_memory(
                session=session,
                content=request.content,
                memory_type=request.memory_type,
                memory_region=request.memory_region,
                source_type=request.source_type,
                source_id=request.source_id,
                importance=request.importance,
                tags=request.tags,
                categories=request.categories,
                metadata=request.metadata
            )
            
            return {
                "status": "success",
                "memory_id": memory.id,
                "memory_type": memory.memory_type,
                "memory_region": memory.memory_region,
                "importance": memory.importance,
                "created_at": memory.created_at.isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/memories/{memory_id}")
async def get_memory(memory_id: str):
    """Retrieve a specific memory by ID."""
    async with get_session() as session:
        memory = await brain_service.retrieve_memory(session, memory_id)
        
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return {
            "id": memory.id,
            "content": memory.content,
            "summary": memory.summary,
            "memory_type": memory.memory_type,
            "memory_region": memory.memory_region,
            "source_type": memory.source_type,
            "source_id": memory.source_id,
            "importance": memory.importance,
            "access_count": memory.access_count,
            "last_accessed": memory.last_accessed.isoformat() if memory.last_accessed else None,
            "tags": memory.tags,
            "categories": memory.categories,
            "created_at": memory.created_at.isoformat(),
            "updated_at": memory.updated_at.isoformat()
        }


@router.post("/memories/search")
async def search_memories(request: SearchRequest):
    """Search memories semantically."""
    try:
        results = await brain_service.search_memories(
            query=request.query,
            memory_type=request.memory_type,
            min_importance=request.min_importance,
            limit=request.limit
        )
        
        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/memories/{memory_id}/importance")
async def update_memory_importance(memory_id: str, importance: float):
    """Update importance score for a memory."""
    async with get_session() as session:
        try:
            await brain_service.update_importance(session, memory_id, importance)
            return {"status": "success", "memory_id": memory_id, "new_importance": importance}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# Note Endpoints
@router.post("/notes")
async def store_note(request: NoteRequest):
    """Store a new note in the brain."""
    async with get_session() as session:
        try:
            note = await brain_service.store_note(
                session=session,
                title=request.title,
                content=request.content,
                note_type=request.note_type,
                note_format=request.note_format,
                folder=request.folder,
                collection=request.collection,
                source_type=request.source_type,
                importance=request.importance,
                tags=request.tags
            )
            
            return {
                "status": "success",
                "note_id": note.id,
                "title": note.title,
                "note_type": note.note_type,
                "folder": note.folder,
                "word_count": note.word_count,
                "created_at": note.created_at.isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/notes/{note_id}")
async def get_note(note_id: str):
    """Retrieve a specific note by ID."""
    async with get_session() as session:
        result = await session.execute(
            select(BrainNote).where(BrainNote.id == note_id)
        )
        note = result.scalar_one_or_none()
        
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        
        return {
            "id": note.id,
            "title": note.title,
            "content": note.content,
            "summary": note.summary,
            "note_type": note.note_type,
            "note_format": note.note_format,
            "folder": note.folder,
            "collection": note.collection,
            "source_type": note.source_type,
            "importance": note.importance,
            "word_count": note.word_count,
            "read_count": note.read_count,
            "tags": note.tags,
            "linked_memory_ids": note.linked_memory_ids,
            "created_at": note.created_at.isoformat(),
            "updated_at": note.updated_at.isoformat()
        }


@router.post("/notes/search")
async def search_notes(request: SearchRequest):
    """Search notes semantically."""
    try:
        results = await brain_service.search_notes(
            query=request.query,
            min_importance=request.min_importance,
            limit=request.limit
        )
        
        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notes/{note_id}/reindex")
async def reindex_note(note_id: str):
    """Re-index a note (update embeddings and re-extract memories)."""
    async with get_session() as session:
        try:
            note = await brain_indexer.reindex_note(session, note_id)
            
            if not note:
                raise HTTPException(status_code=404, detail="Note not found")
            
            return {
                "status": "success",
                "note_id": note.id,
                "title": note.title,
                "updated_at": note.updated_at.isoformat()
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# Combined Search
@router.post("/search")
async def search_all(request: SearchRequest):
    """Search across both memories and notes."""
    try:
        results = await brain_service.search_all(
            query=request.query,
            limit=request.limit
        )
        
        return {
            "query": request.query,
            "memories": results["memories"],
            "notes": results["notes"],
            "total": results["total"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Indexing Endpoints
@router.post("/index")
async def index_text(request: IndexRequest):
    """Extract and store memories from text."""
    async with get_session() as session:
        try:
            memories = await brain_indexer.extract_memories(
                text=request.text,
                source_type=request.source_type,
                source_id=request.source_id
            )
            
            stored = await brain_indexer.store_extracted_memories(
                session=session,
                memories=memories,
                auto_connect=True
            )
            
            return {
                "status": "success",
                "extracted": len(memories),
                "stored": len(stored),
                "memory_ids": [m.id for m in stored]
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/index/chat")
async def index_chat_turn(request: ChatIndexRequest):
    """Index a chat turn, extracting memories."""
    async with get_session() as session:
        try:
            result = await brain_indexer.index_chat_turn(
                session=session,
                user_message=request.user_message,
                assistant_reply=request.assistant_reply,
                session_id=request.session_id
            )
            
            return {
                "status": "success",
                **result
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/index/note")
async def index_note(request: NoteRequest):
    """Index a note with automatic entity extraction."""
    async with get_session() as session:
        try:
            note = await brain_indexer.index_note(
                session=session,
                title=request.title,
                content=request.content,
                source_type=request.source_type,
                folder=request.folder
            )
            
            return {
                "status": "success",
                "note_id": note.id,
                "title": note.title,
                "created_at": note.created_at.isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# Consolidation Endpoints
@router.post("/consolidate/{memory_id}")
async def consolidate_memory(memory_id: str, reason: str = "Manual consolidation"):
    """Manually consolidate a memory to long-term storage."""
    async with get_session() as session:
        try:
            success = await brain_service.consolidate_memory(
                session=session,
                memory_id=memory_id,
                reason=reason
            )
            
            if not success:
                raise HTTPException(status_code=404, detail="Memory not found or not eligible")
            
            return {"status": "success", "memory_id": memory_id, "reason": reason}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/consolidate/auto")
async def auto_consolidate(request: ConsolidationRequest, background_tasks: BackgroundTasks):
    """Trigger automatic memory consolidation in background."""
    async def run_consolidation():
        async with get_session() as session:
            await brain_service.auto_consolidate(
                session=session,
                min_access_count=request.min_access_count,
                min_importance=request.min_importance,
                days_threshold=request.days_threshold
            )
    
    background_tasks.add_task(run_consolidation)
    
    return {
        "status": "started",
        "message": "Auto-consolidation running in background",
        "criteria": {
            "min_access_count": request.min_access_count,
            "min_importance": request.min_importance,
            "days_threshold": request.days_threshold
        }
    }


# Context Endpoints
@router.post("/context")
async def set_context(request: ContextRequest):
    """Set current working context."""
    async with get_session() as session:
        try:
            context = await brain_service.set_context(
                session=session,
                context_type=request.context_type,
                context_name=request.context_name,
                active_memory_ids=request.active_memory_ids,
                active_note_ids=request.active_note_ids,
                session_id=request.session_id,
                user_id=request.user_id,
                expires_in_hours=request.expires_in_hours
            )
            
            return {
                "status": "success",
                "context_id": context.id,
                "context_type": context.context_type,
                "context_name": context.context_name,
                "expires_at": context.expires_at.isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/context")
async def get_active_context(context_type: Optional[str] = None, session_id: Optional[str] = None):
    """Get active context."""
    async with get_session() as session:
        try:
            context = await brain_service.get_active_context(
                session=session,
                context_type=context_type,
                session_id=session_id
            )
            
            if not context:
                return {"status": "no_active_context"}
            
            return {
                "id": context.id,
                "context_type": context.context_type,
                "context_name": context.context_name,
                "active_memory_ids": context.active_memory_ids,
                "active_note_ids": context.active_note_ids,
                "session_id": context.session_id,
                "expires_at": context.expires_at.isoformat(),
                "created_at": context.created_at.isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# Statistics and Health
@router.get("/stats")
async def get_brain_stats():
    """Get brain statistics and health metrics."""
    try:
        stats = await brain_service.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decay")
async def decay_memories(
    background_tasks: BackgroundTasks,
    days_threshold: int = 30,
    max_importance: float = 0.3,
    decay_factor: float = 0.1
):
    """Apply memory decay to old, low-importance memories."""
    async def run_decay():
        async with get_session() as session:
            await brain_service.decay_memories(
                session=session,
                days_threshold=days_threshold,
                max_importance=max_importance,
                decay_factor=decay_factor
            )
    
    background_tasks.add_task(run_decay)
    
    return {
        "status": "started",
        "message": "Memory decay running in background",
        "criteria": {
            "days_threshold": days_threshold,
            "max_importance": max_importance,
            "decay_factor": decay_factor
        }
    }


# Vault Sync Endpoints
@router.post("/vault/sync")
async def sync_brain_to_vault(
    background_tasks: BackgroundTasks,
    push_to_git: bool = False,
    git_message: str = None
):
    """Sync the entire brain to the Obsidian vault."""
    async def run_sync():
        async with get_session() as session:
            result = await sync_full_brain(session)
            
            # Git operations if requested
            if push_to_git:
                git_result = sync_and_push(git_message)
                result["git"] = git_result
            
            return result
    
    # Run in background
    if push_to_git:
        background_tasks.add_task(run_sync)
        return {
            "status": "started",
            "message": "Brain vault sync running in background with git push",
            "vault_path": str(BRAIN_VAULT_ROOT)
        }
    else:
        result = await run_sync()
        return result


@router.post("/vault/sync/memories")
async def sync_memories_to_vault(
    background_tasks: BackgroundTasks,
    limit: int = 1000,
    memory_type: Optional[str] = None,
    memory_region: Optional[str] = None
):
    """Sync memories to the vault."""
    async def run_sync():
        async with get_session() as session:
            return await sync_all_memories(session, limit, memory_type, memory_region)
    
    background_tasks.add_task(run_sync)
    
    return {
        "status": "started",
        "message": "Memory sync running in background",
        "vault_path": str(BRAIN_VAULT_ROOT)
    }


@router.post("/vault/sync/notes")
async def sync_notes_to_vault(
    background_tasks: BackgroundTasks,
    limit: int = 1000,
    folder: Optional[str] = None
):
    """Sync notes to the vault."""
    async def run_sync():
        async with get_session() as session:
            return await sync_all_notes(session, limit, folder)
    
    background_tasks.add_task(run_sync)
    
    return {
        "status": "started",
        "message": "Note sync running in background",
        "vault_path": str(BRAIN_VAULT_ROOT)
    }


@router.get("/vault/status")
async def get_vault_status():
    """Get brain vault status and git status."""
    vault_exists = BRAIN_VAULT_ROOT.exists()
    
    if vault_exists:
        git_status = get_git_status()
        file_count = sum(1 for _ in BRAIN_VAULT_ROOT.rglob("*.md") if _.name != "README.md")
    else:
        git_status = {"status": "not_initialized"}
        file_count = 0
    
    return {
        "vault_path": str(BRAIN_VAULT_ROOT),
        "vault_exists": vault_exists,
        "file_count": file_count,
        "git_status": git_status
    }


@router.post("/vault/git/init")
async def init_vault_git(remote_url: Optional[str] = None):
    """Initialize git repository for the brain vault."""
    try:
        result = init_git_repo(remote_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vault/git/commit")
async def commit_vault_changes(message: Optional[str] = None):
    """Commit vault changes to git."""
    try:
        result = commit_changes(message)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vault/git/push")
async def push_vault_to_git(branch: str = "main"):
    """Push vault changes to remote git repository."""
    try:
        result = push_to_remote(branch)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vault/git/sync")
async def sync_vault_to_git(
    background_tasks: BackgroundTasks,
    message: Optional[str] = None,
    branch: str = "main"
):
    """Commit and push vault changes to git."""
    async def run_sync():
        return sync_and_push(message, branch)
    
    background_tasks.add_task(run_sync)
    
    return {
        "status": "started",
        "message": "Vault git sync running in background",
        "branch": branch
    }


# Entity Endpoints
@router.get("/entities")
async def list_entities(entity_type: Optional[str] = None, limit: int = 50):
    """List entities in the brain."""
    async with get_session() as session:
        try:
            query = select(BrainEntity)
            
            if entity_type:
                query = query.where(BrainEntity.entity_type == entity_type)
            
            query = query.order_by(BrainEntity.mention_count.desc()).limit(limit)
            
            result = await session.execute(query)
            entities = result.scalars().all()
            
            return {
                "entities": [
                    {
                        "id": e.id,
                        "name": e.name,
                        "entity_type": e.entity_type,
                        "canonical_name": e.canonical_name,
                        "aliases": e.aliases,
                        "mention_count": e.mention_count,
                        "importance": e.importance,
                        "first_seen": e.first_seen.isoformat(),
                        "last_seen": e.last_seen.isoformat()
                    }
                    for e in entities
                ],
                "count": len(entities)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_id}")
async def get_entity(entity_id: str):
    """Get a specific entity with related memories."""
    async with get_session() as session:
        try:
            result = await session.execute(
                select(BrainEntity).where(BrainEntity.id == entity_id)
            )
            entity = result.scalar_one_or_none()
            
            if not entity:
                raise HTTPException(status_code=404, detail="Entity not found")
            
            # Get related memories
            memories = []
            if entity.related_entity_ids:
                result = await session.execute(
                    select(BrainMemory).where(BrainMemory.id.in_(entity.related_entity_ids))
                )
                memories = result.scalars().all()
            
            return {
                "id": entity.id,
                "name": entity.name,
                "entity_type": entity.entity_type,
                "canonical_name": entity.canonical_name,
                "aliases": entity.aliases,
                "description": entity.description,
                "attributes": entity.attributes,
                "mention_count": entity.mention_count,
                "importance": entity.importance,
                "related_memory_ids": entity.related_entity_ids,
                "related_memories": [
                    {
                        "id": m.id,
                        "content": m.content,
                        "memory_type": m.memory_type
                    }
                    for m in memories
                ],
                "first_seen": entity.first_seen.isoformat(),
                "last_seen": entity.last_seen.isoformat()
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
