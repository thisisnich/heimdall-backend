"""
Heimdall Brain Service — Memory management and retrieval.

Provides high-level operations for:
  - Storing and retrieving memories
  - Memory consolidation (short-term → long-term)
  - Note indexing and search
  - Entity extraction and resolution
  - Context management
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from atlas.db.brain_models import (
    BrainMemory, BrainNote, BrainConnection, BrainEntity, 
    BrainContext, BrainConsolidationLog,
    MemoryType, MemoryRegion
)
from atlas.db.brain_vector import (
    init_brain_vector_tables,
    store_brain_memory, store_brain_note,
    search_brain_memory, search_brain_notes, search_brain_all,
    update_access, update_importance, get_decay_candidates,
    get_brain_stats
)

logger = logging.getLogger(__name__)


class BrainService:
    """Main service for Heimdall's brain operations."""
    
    def __init__(self):
        self._initialized = False
    
    async def initialize(self):
        """Initialize brain tables and vector indexes."""
        if not self._initialized:
            await init_brain_vector_tables()
            self._initialized = True
            logger.info("Heimdall Brain initialized")
    
    async def store_memory(
        self,
        session: AsyncSession,
        content: str,
        memory_type: str = MemoryType.SEMANTIC.value,
        memory_region: str = MemoryRegion.CORTEX.value,
        source_type: str = "manual",
        source_id: Optional[str] = None,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> BrainMemory:
        """
        Store a new memory in the brain.
        Automatically creates embedding and stores in vector table.
        """
        await self.initialize()
        
        memory = BrainMemory(
            content=content,
            memory_type=memory_type,
            memory_region=memory_region,
            source_type=source_type,
            source_id=source_id,
            importance=importance,
            tags=tags or [],
            categories=categories or [],
            metadata=metadata or {}
        )
        
        session.add(memory)
        await session.commit()
        await session.refresh(memory)
        
        # Store embedding in vector table
        await store_brain_memory(
            memory_id=memory.id,
            text=content,
            memory_type=memory_type,
            source_type=source_type,
            importance=importance
        )
        
        logger.info(f"Stored memory [{memory_type}]: {content[:60]}...")
        return memory
    
    async def retrieve_memory(
        self,
        session: AsyncSession,
        memory_id: str
    ) -> Optional[BrainMemory]:
        """Retrieve a specific memory by ID."""
        result = await session.execute(
            select(BrainMemory).where(BrainMemory.id == memory_id)
        )
        memory = result.scalar_one_or_none()
        
        if memory:
            # Update access tracking
            await update_access(memory_id, "vector_brain_memory")
            await session.execute(
                update(BrainMemory)
                .where(BrainMemory.id == memory_id)
                .values(
                    access_count=BrainMemory.access_count + 1,
                    last_accessed=datetime.utcnow()
                )
            )
            await session.commit()
        
        return memory
    
    async def search_memories(
        self,
        query: str,
        memory_type: Optional[str] = None,
        min_importance: float = 0.0,
        limit: int = 10
    ) -> List[Dict]:
        """
        Search memories semantically.
        Returns results from vector search with metadata.
        """
        await self.initialize()
        
        vector_results = await search_brain_memory(
            query=query,
            memory_type=memory_type,
            min_importance=min_importance,
            limit=limit
        )
        
        return vector_results
    
    async def store_note(
        self,
        session: AsyncSession,
        title: str,
        content: str,
        note_type: str = "general",
        note_format: str = "markdown",
        folder: str = "general",
        collection: str = "default",
        source_type: str = "manual",
        importance: float = 0.5,
        tags: Optional[List[str]] = None
    ) -> BrainNote:
        """
        Store a new note in the brain.
        Automatically creates embedding and indexes.
        """
        await self.initialize()
        
        # Calculate word count
        word_count = len(content.split())
        
        note = BrainNote(
            title=title,
            content=content,
            note_type=note_type,
            note_format=note_format,
            folder=folder,
            collection=collection,
            source_type=source_type,
            importance=importance,
            tags=tags or [],
            word_count=word_count
        )
        
        session.add(note)
        await session.commit()
        await session.refresh(note)
        
        # Store embedding
        await store_brain_note(
            note_id=note.id,
            text=f"{title}\n\n{content}",
            source_type=source_type,
            importance=importance
        )
        
        logger.info(f"Stored note [{note_type}]: {title}")
        return note
    
    async def search_notes(
        self,
        query: str,
        min_importance: float = 0.0,
        limit: int = 10
    ) -> List[Dict]:
        """Search notes semantically."""
        await self.initialize()
        
        return await search_brain_notes(
            query=query,
            min_importance=min_importance,
            limit=limit
        )
    
    async def search_all(
        self,
        query: str,
        limit: int = 10
    ) -> Dict:
        """Search across both memories and notes."""
        await self.initialize()
        
        return await search_brain_all(query=query, limit=limit)
    
    async def consolidate_memory(
        self,
        session: AsyncSession,
        memory_id: str,
        reason: str = "Manual consolidation"
    ) -> bool:
        """
        Consolidate a memory from short-term to long-term storage.
        Moves from hippocampus to cortex, marks as consolidated.
        """
        memory = await self.retrieve_memory(session, memory_id)
        if not memory:
            return False
        
        if memory.memory_region != MemoryRegion.HIPPOCAMPUS.value:
            logger.warning(f"Memory {memory_id} not in hippocampus, skipping consolidation")
            return False
        
        # Move to cortex
        await session.execute(
            update(BrainMemory)
            .where(BrainMemory.id == memory_id)
            .values(
                memory_region=MemoryRegion.CORTEX.value,
                is_consolidated=True,
                consolidation_date=datetime.utcnow()
            )
        )
        
        # Log consolidation
        log = BrainConsolidationLog(
            memory_id=memory_id,
            from_region=MemoryRegion.HIPPOCAMPUS.value,
            to_region=MemoryRegion.CORTEX.value,
            success=True,
            reason=reason
        )
        session.add(log)
        
        await session.commit()
        logger.info(f"Consolidated memory {memory_id}: {reason}")
        return True
    
    async def auto_consolidate(
        self,
        session: AsyncSession,
        min_access_count: int = 3,
        min_importance: float = 0.6,
        days_threshold: int = 7
    ) -> List[str]:
        """
        Automatically consolidate memories that meet criteria.
        Criteria: accessed multiple times, high importance, older than threshold.
        """
        threshold_date = datetime.utcnow() - timedelta(days=days_threshold)
        
        result = await session.execute(
            select(BrainMemory).where(
                and_(
                    BrainMemory.memory_region == MemoryRegion.HIPPOCAMPUS.value,
                    BrainMemory.is_consolidated == False,
                    BrainMemory.access_count >= min_access_count,
                    BrainMemory.importance >= min_importance,
                    BrainMemory.created_at < threshold_date
                )
            )
        )
        memories = result.scalars().all()
        
        consolidated_ids = []
        for memory in memories:
            success = await self.consolidate_memory(
                session, memory.id, reason="Auto-consolidation"
            )
            if success:
                consolidated_ids.append(memory.id)
        
        logger.info(f"Auto-consolidated {len(consolidated_ids)} memories")
        return consolidated_ids
    
    async def create_connection(
        self,
        session: AsyncSession,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        connection_type: str = "related",
        strength: float = 0.5,
        context: str = ""
    ) -> BrainConnection:
        """Create a connection between two brain items."""
        connection = BrainConnection(
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            connection_type=connection_type,
            strength=strength,
            context=context
        )
        
        session.add(connection)
        await session.commit()
        await session.refresh(connection)
        
        # Update related IDs on the items
        if source_type == "memory":
            await session.execute(
                update(BrainMemory)
                .where(BrainMemory.id == source_id)
                .values(related_memory_ids=BrainMemory.related_memory_ids + [target_id])
            )
        
        await session.commit()
        
        logger.info(f"Created connection: {source_type}:{source_id} -> {target_type}:{target_id}")
        return connection
    
    async def get_related_memories(
        self,
        session: AsyncSession,
        memory_id: str,
        max_depth: int = 2
    ) -> List[BrainMemory]:
        """Get memories related through connections."""
        # Get direct connections
        result = await session.execute(
            select(BrainConnection).where(
                or_(
                    and_(
                        BrainConnection.source_type == "memory",
                        BrainConnection.source_id == memory_id
                    ),
                    and_(
                        BrainConnection.target_type == "memory",
                        BrainConnection.target_id == memory_id
                    )
                )
            )
        )
        connections = result.scalars().all()
        
        # Extract related memory IDs
        related_ids = set()
        for conn in connections:
            if conn.source_type == "memory" and conn.source_id != memory_id:
                related_ids.add(conn.source_id)
            if conn.target_type == "memory" and conn.target_id != memory_id:
                related_ids.add(conn.target_id)
        
        if not related_ids:
            return []
        
        # Fetch related memories
        result = await session.execute(
            select(BrainMemory).where(BrainMemory.id.in_(related_ids))
        )
        return result.scalars().all()
    
    async def update_importance(
        self,
        session: AsyncSession,
        memory_id: str,
        new_importance: float
    ):
        """Update importance score for a memory."""
        await session.execute(
            update(BrainMemory)
            .where(BrainMemory.id == memory_id)
            .values(importance=new_importance)
        )
        await session.commit()
        
        await update_importance(memory_id, new_importance, "vector_brain_memory")
    
    async def decay_memories(
        self,
        session: AsyncSession,
        days_threshold: int = 30,
        max_importance: float = 0.3,
        decay_factor: float = 0.1
    ) -> List[str]:
        """
        Apply decay to old, low-importance memories.
        Reduces importance and potentially removes very low importance memories.
        """
        candidates = await get_decay_candidates(
            days_threshold=days_threshold,
            max_importance=max_importance
        )
        
        decayed_ids = []
        for candidate in candidates:
            memory_id = candidate["id"]
            current_importance = candidate["importance"]
            new_importance = max(0.0, current_importance - decay_factor)
            
            await self.update_importance(session, memory_id, new_importance)
            decayed_ids.append(memory_id)
            
            # Remove if importance is now 0
            if new_importance <= 0.0:
                await session.execute(
                    delete(BrainMemory).where(BrainMemory.id == memory_id)
                )
                await session.commit()
                logger.info(f"Removed decayed memory {memory_id}")
        
        logger.info(f"Decayed {len(decayed_ids)} memories")
        return decayed_ids
    
    async def get_stats(self) -> Dict:
        """Get brain statistics."""
        await self.initialize()
        
        vector_stats = await get_brain_stats()
        return {
            "vector_tables": vector_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def set_context(
        self,
        session: AsyncSession,
        context_type: str,
        context_name: str,
        active_memory_ids: Optional[List[str]] = None,
        active_note_ids: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        expires_in_hours: int = 24
    ) -> BrainContext:
        """Set current working context."""
        context = BrainContext(
            context_type=context_type,
            context_name=context_name,
            active_memory_ids=active_memory_ids or [],
            active_note_ids=active_note_ids or [],
            session_id=session_id,
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours)
        )
        
        session.add(context)
        await session.commit()
        await session.refresh(context)
        
        logger.info(f"Set context: {context_type}/{context_name}")
        return context
    
    async def get_active_context(
        self,
        session: AsyncSession,
        context_type: str = None,
        session_id: str = None
    ) -> Optional[BrainContext]:
        """Get active context for a type or session."""
        query = select(BrainContext).where(
            BrainContext.expires_at > datetime.utcnow()
        )
        
        if context_type:
            query = query.where(BrainContext.context_type == context_type)
        if session_id:
            query = query.where(BrainContext.session_id == session_id)
        
        query = query.order_by(BrainContext.created_at.desc())
        
        result = await session.execute(query)
        return result.scalar_one_or_none()


# Global brain service instance
brain_service = BrainService()
