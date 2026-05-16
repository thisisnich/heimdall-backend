"""
Brain Indexer — Intelligent note indexing and entity extraction.

Enhanced version of the existing indexer with:
  - Brain-specific memory types
  - Automatic entity resolution
  - Cross-referencing with existing memories
  - Importance scoring
  - Context-aware classification
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from atlas.db.brain_models import (
    BrainMemory, BrainNote, BrainEntity, BrainConnection,
    MemoryType, MemoryRegion
)
from atlas.services.brain_service import brain_service
from atlas.services.groq_service import chat as groq_chat

logger = logging.getLogger(__name__)

INDEX_MODEL = "groq-llama3-8b"

EXTRACT_PROMPT = """You are an advanced memory extractor for Heimdall's brain.
Given text, extract meaningful information worth storing in long-term memory.

Return a JSON array. Each item has:
- "text": the fact or memory (one clear sentence)
- "memory_type": one of: episodic | semantic | procedural | emotional
- "importance": 0.0-1.0 (how important this is to remember)
- "save": true if worth storing, false if trivial
- "entities": list of key entities mentioned (people, places, concepts)

Memory types:
- episodic: Events, experiences, conversations, "what happened"
- semantic: Facts, concepts, knowledge, "what is true"
- procedural: Skills, how-to, workflows, "how to do"
- emotional: Emotional states, preferences, feelings

Rules:
- Extract only substantive information worth remembering
- Assign higher importance to: user goals, important relationships, key decisions
- Skip: greetings, filler, test messages, trivial chat
- Include entities for cross-referencing

Respond ONLY with valid JSON array, no explanation.

Example:
[
  {"text": "User wants to learn Rust programming this summer", "memory_type": "semantic", "importance": 0.7, "save": true, "entities": ["Rust", "programming", "summer"]},
  {"text": "User met with Professor Smith about FYP project", "memory_type": "episodic", "importance": 0.8, "save": true, "entities": ["Professor Smith", "FYP project"]}
]

Text to analyze: """

ENTITY_RESOLUTION_PROMPT = """You are an entity resolver for Heimdall's brain.
Given a list of extracted entities, normalize and classify them.

Return a JSON array. Each item has:
- "name": the entity name (normalized, capitalized)
- "type": one of: person | place | concept | tool | organization | other
- "canonical": preferred name if this has aliases (null if same as name)
- "aliases": alternative names this might appear as

Rules:
- Normalize names (proper capitalization)
- Classify by type
- Identify canonical names for common variations
- Keep entities specific enough to be useful

Respond ONLY with valid JSON array.

Example input: ["professor smith", "fyp project", "rust programming"]
Example output:
[
  {"name": "Professor Smith", "type": "person", "canonical": null, "aliases": ["Prof Smith", "Smith"]},
  {"name": "FYP Project", "type": "concept", "canonical": "Final Year Project", "aliases": ["FYP"]},
  {"name": "Rust Programming", "type": "concept", "canonical": "Rust", "aliases": ["Rust"]}
]

Entities to resolve: """


class BrainIndexer:
    """Enhanced indexer for Heimdall's brain."""
    
    def __init__(self):
        self._initialized = False
    
    async def initialize(self):
        """Initialize brain service."""
        if not self._initialized:
            await brain_service.initialize()
            self._initialized = True
    
    async def extract_memories(
        self,
        text: str,
        source_type: str = "manual",
        source_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Extract memories from text using LLM.
        Returns list of extracted memory data.
        """
        if len(text.strip()) < 10:
            return []
        
        await self.initialize()
        
        try:
            prompt = EXTRACT_PROMPT + json.dumps(text)
            messages = [
                {"role": "system", "content": "You are a JSON-only memory extractor."},
                {"role": "user", "content": prompt}
            ]
            
            raw = await groq_chat(messages, model=INDEX_MODEL)
            
            # Strip markdown fences
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            
            memories = json.loads(raw)
            assert isinstance(memories, list)
            
            # Add source info
            for memory in memories:
                memory["source_type"] = source_type
                memory["source_id"] = source_id
            
            return memories
            
        except Exception as e:
            logger.warning(f"Memory extraction failed: {e}")
            return []
    
    async def resolve_entities(
        self,
        entities: List[str]
    ) -> List[Dict]:
        """
        Resolve and normalize entities using LLM.
        Returns list of resolved entity data.
        """
        if not entities:
            return []
        
        await self.initialize()
        
        try:
            prompt = ENTITY_RESOLUTION_PROMPT + json.dumps(entities)
            messages = [
                {"role": "system", "content": "You are a JSON-only entity resolver."},
                {"role": "user", "content": prompt}
            ]
            
            raw = await groq_chat(messages, model=INDEX_MODEL)
            
            # Strip markdown fences
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            
            resolved = json.loads(raw)
            assert isinstance(resolved, list)
            
            return resolved
            
        except Exception as e:
            logger.warning(f"Entity resolution failed: {e}")
            return []
    
    async def store_extracted_memories(
        self,
        session: AsyncSession,
        memories: List[Dict],
        auto_connect: bool = True
    ) -> List[BrainMemory]:
        """
        Store extracted memories in the brain.
        Optionally creates connections between related memories.
        """
        await self.initialize()
        
        stored_memories = []
        
        for memory_data in memories:
            if not memory_data.get("save", False):
                continue
            
            text = memory_data.get("text", "").strip()
            if not text:
                continue
            
            memory_type = memory_data.get("memory_type", MemoryType.SEMANTIC.value)
            importance = memory_data.get("importance", 0.5)
            entities = memory_data.get("entities", [])
            
            # Determine memory region based on type
            if memory_type == MemoryType.EPISODIC.value:
                memory_region = MemoryRegion.HIPPOCAMPUS.value
            else:
                memory_region = MemoryRegion.CORTEX.value
            
            # Store memory
            memory = await brain_service.store_memory(
                session=session,
                content=text,
                memory_type=memory_type,
                memory_region=memory_region,
                source_type=memory_data.get("source_type", "manual"),
                source_id=memory_data.get("source_id"),
                importance=importance,
                tags=entities
            )
            
            stored_memories.append(memory)
            
            # Resolve and store entities
            if entities:
                await self._process_entities(session, entities, memory.id)
        
        # Auto-connect related memories
        if auto_connect and len(stored_memories) > 1:
            await self._connect_related_memories(session, stored_memories)
        
        logger.info(f"Stored {len(stored_memories)} memories")
        return stored_memories
    
    async def _process_entities(
        self,
        session: AsyncSession,
        entity_names: List[str],
        memory_id: str
    ):
        """Process and store entities, linking to memory."""
        resolved = await self.resolve_entities(entity_names)
        
        for entity_data in resolved:
            name = entity_data.get("name", "")
            entity_type = entity_data.get("type", "other")
            
            if not name:
                continue
            
            # Check if entity already exists
            result = await session.execute(
                select(BrainEntity).where(
                    or_(
                        BrainEntity.name == name,
                        BrainEntity.canonical_name == name
                    )
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing entity
                await session.execute(
                    update(BrainEntity)
                    .where(BrainEntity.id == existing.id)
                    .values(
                        mention_count=BrainEntity.mention_count + 1,
                        last_seen=datetime.utcnow()
                    )
                )
                
                # Link memory to entity
                if memory_id not in existing.related_entity_ids:
                    await session.execute(
                        update(BrainEntity)
                        .where(BrainEntity.id == existing.id)
                        .values(
                            related_entity_ids=BrainEntity.related_entity_ids + [memory_id]
                        )
                    )
            else:
                # Create new entity
                entity = BrainEntity(
                    name=name,
                    entity_type=entity_type,
                    canonical_name=entity_data.get("canonical") or name,
                    aliases=entity_data.get("aliases", []),
                    mention_count=1
                )
                session.add(entity)
                await session.commit()
                await session.refresh(entity)
                
                # Link memory to entity
                await session.execute(
                    update(BrainEntity)
                    .where(BrainEntity.id == entity.id)
                    .values(
                        related_entity_ids=[memory_id]
                    )
                )
            
            await session.commit()
    
    async def _connect_related_memories(
        self,
        session: AsyncSession,
        memories: List[BrainMemory]
    ):
        """Create connections between related memories based on shared entities."""
        for i, mem1 in enumerate(memories):
            for mem2 in memories[i+1:]:
                # Check for shared tags/entities
                shared = set(mem1.tags) & set(mem2.tags)
                
                if shared:
                    # Create connection
                    await brain_service.create_connection(
                        session=session,
                        source_type="memory",
                        source_id=mem1.id,
                        target_type="memory",
                        target_id=mem2.id,
                        connection_type="related",
                        strength=0.5,
                        context=f"Shared entities: {', '.join(shared)}"
                    )
    
    async def index_note(
        self,
        session: AsyncSession,
        title: str,
        content: str,
        source_type: str = "manual",
        folder: str = "general"
    ) -> BrainNote:
        """
        Index a note with automatic entity extraction and memory creation.
        """
        await self.initialize()
        
        # Extract memories from note content
        memories = await self.extract_memories(
            text=content,
            source_type=source_type,
            source_id=title
        )
        
        # Store the note
        note = await brain_service.store_note(
            session=session,
            title=title,
            content=content,
            source_type=source_type,
            folder=folder,
            importance=0.6  # Notes are moderately important
        )
        
        # Store extracted memories
        if memories:
            await self.store_extracted_memories(
                session=session,
                memories=memories,
                auto_connect=True
            )
            
            # Link note to memories
            memory_ids = [m.id for m in memories]
            await session.execute(
                update(BrainNote)
                .where(BrainNote.id == note.id)
                .values(linked_memory_ids=memory_ids)
            )
            await session.commit()
        
        logger.info(f"Indexed note: {title} with {len(memories)} memories")
        return note
    
    async def index_chat_turn(
        self,
        session: AsyncSession,
        user_message: str,
        assistant_reply: str,
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Index a chat turn, extracting memories and updating context.
        """
        await self.initialize()
        
        # Extract memories from user message
        memories = await self.extract_memories(
            text=user_message,
            source_type="chat",
            source_id=session_id
        )
        
        # Store memories
        stored_memories = []
        if memories:
            stored_memories = await self.store_extracted_memories(
                session=session,
                memories=memories,
                auto_connect=True
            )
        
        # Update context if session_id provided
        if session_id and stored_memories:
            context = await brain_service.get_active_context(
                session=session,
                session_id=session_id
            )
            
            if context:
                # Add new memories to context
                new_memory_ids = [m.id for m in stored_memories]
                await session.execute(
                    update(BrainContext)
                    .where(BrainContext.id == context.id)
                    .values(
                        active_memory_ids=context.active_memory_ids + new_memory_ids,
                        updated_at=datetime.utcnow()
                    )
                )
                await session.commit()
        
        return {
            "memories_stored": len(stored_memories),
            "memory_ids": [m.id for m in stored_memories]
        }
    
    async def reindex_note(
        self,
        session: AsyncSession,
        note_id: str
    ) -> Optional[BrainNote]:
        """
        Re-index an existing note (update embeddings and re-extract memories).
        """
        await self.initialize()
        
        # Get the note
        result = await session.execute(
            select(BrainNote).where(BrainNote.id == note_id)
        )
        note = result.scalar_one_or_none()
        
        if not note:
            return None
        
        # Update embedding
        from atlas.db.brain_vector import store_brain_note
        await store_brain_note(
            note_id=note.id,
            text=f"{note.title}\n\n{note.content}",
            source_type=note.source_type,
            importance=note.importance
        )
        
        # Re-extract memories
        memories = await self.extract_memories(
            text=note.content,
            source_type=note.source_type,
            source_id=note.title
        )
        
        # Store new memories
        if memories:
            await self.store_extracted_memories(
                session=session,
                memories=memories,
                auto_connect=True
            )
        
        # Update note timestamp
        await session.execute(
            update(BrainNote)
            .where(BrainNote.id == note_id)
            .values(updated_at=datetime.utcnow())
        )
        await session.commit()
        await session.refresh(note)
        
        logger.info(f"Re-indexed note: {note.title}")
        return note


# Global indexer instance
brain_indexer = BrainIndexer()
