"""
Heimdall Brain Models — Database-first memory architecture.

Brain Structure:
  - cortex: Long-term semantic memory (facts, concepts, knowledge)
  - hippocampus: Short-term episodic memory (events, conversations)
  - prefrontal: Working memory (active context, current tasks)
  - amygdala: Emotional memory (emotional associations)
  - notes_index: Indexed notes with cross-references

More efficient than file-based vault:
  - Direct database queries (no file I/O)
  - Automatic embeddings via pgvector
  - Memory consolidation (short-term → long-term)
  - Importance scoring and decay
  - Context-aware retrieval
"""

from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy import String, Text, DateTime, Boolean, Float, JSON, ForeignKey, Integer, Enum
from datetime import datetime, timedelta
import uuid
import enum


class MemoryType(enum.Enum):
    """Types of memory stored in the brain."""
    EPISODIC = "episodic"      # Events, experiences, conversations
    SEMANTIC = "semantic"      # Facts, concepts, knowledge
    PROCEDURAL = "procedural"  # Skills, how-to, workflows
    WORKING = "working"        # Active context, current tasks
    EMOTIONAL = "emotional"    # Emotional associations


class MemoryRegion(enum.Enum):
    """Brain regions for memory storage."""
    CORTEX = "cortex"              # Long-term semantic memory
    HIPPOCAMPUS = "hippocampus"    # Short-term episodic memory
    PREFRONTAL = "prefrontal"      # Working memory
    AMYGDALA = "amygdala"          # Emotional memory


class Base(DeclarativeBase):
    pass


class BrainMemory(Base):
    """
    Core memory entry in Heimdall's brain.
    Replaces file-based vault with database-first approach.
    """
    __tablename__ = "brain_memory"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(String, default="")  # Auto-generated summary
    
    # Memory classification
    memory_type: Mapped[str] = mapped_column(String, default=MemoryType.SEMANTIC.value)
    memory_region: Mapped[str] = mapped_column(String, default=MemoryRegion.CORTEX.value)
    
    # Source tracking
    source_type: Mapped[str] = mapped_column(String, default="manual")  # chat, ingest, manual, system
    source_id: Mapped[str] = mapped_column(String, nullable=True)  # Reference to source
    source_path: Mapped[str] = mapped_column(String, default="")
    
    # Importance and decay
    importance: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0-1.0 importance score
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    decay_rate: Mapped[float] = mapped_column(Float, default=0.01)  # Memory decay rate
    
    # Temporal context
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    temporal_context: Mapped[dict] = mapped_column(JSON, default=dict)  # Time-related metadata
    
    # Emotional context
    emotional_valence: Mapped[float] = mapped_column(Float, nullable=True)  # -1.0 (negative) to 1.0 (positive)
    emotional_arousal: Mapped[float] = mapped_column(Float, nullable=True)  # 0.0-1.0 intensity
    emotional_tags: Mapped[list] = mapped_column(JSON, default=list)
    
    # Associations and connections
    related_memory_ids: Mapped[list] = mapped_column(JSON, default=list)  # Connected memories
    entity_ids: Mapped[list] = mapped_column(JSON, default=list)  # Linked entities (people, places, etc.)
    
    # Tags and categories
    tags: Mapped[list] = mapped_column(JSON, default=list)
    categories: Mapped[list] = mapped_column(JSON, default=list)
    
    # Consolidation status
    is_consolidated: Mapped[bool] = mapped_column(Boolean, default=False)  # Moved to long-term
    consolidation_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Embedding for semantic search (managed by pgvector)
    # Embedding stored in separate vector_brain_memory table
    
    # Metadata
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BrainNote(Base):
    """
    Indexed notes in the brain.
    More efficient than vault files - direct DB access with full-text search.
    """
    __tablename__ = "brain_notes"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Note content
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(String, default="")
    
    # Note type and structure
    note_type: Mapped[str] = mapped_column(String, default="general")  # general, code, reference, log
    note_format: Mapped[str] = mapped_column(String, default="markdown")  # markdown, json, plain
    
    # Organization
    folder: Mapped[str] = mapped_column(String, default="general")
    collection: Mapped[str] = mapped_column(String, default="default")
    
    # Source
    source_type: Mapped[str] = mapped_column(String, default="manual")
    source_id: Mapped[str] = mapped_column(String, nullable=True)
    
    # Indexing
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    entities: Mapped[list] = mapped_column(JSON, default=list)  # Extracted entities
    topics: Mapped[list] = mapped_column(JSON, default=list)
    
    # Cross-references
    referenced_note_ids: Mapped[list] = mapped_column(JSON, default=list)
    backlinked_note_ids: Mapped[list] = mapped_column(JSON, default=list)
    linked_memory_ids: Mapped[list] = mapped_column(JSON, default=list)
    
    # Statistics
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    read_count: Mapped[int] = mapped_column(Integer, default=0)
    last_read: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Importance
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Embedding for semantic search
    # Stored in separate vector_brain_notes table


class BrainConnection(Base):
    """
    Connections between memories and notes (synapses).
    Enables associative memory and knowledge graph.
    """
    __tablename__ = "brain_connections"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Connection endpoints
    source_type: Mapped[str] = mapped_column(String)  # memory, note
    source_id: Mapped[str] = mapped_column(String)
    target_type: Mapped[str] = mapped_column(String)  # memory, note
    target_id: Mapped[str] = mapped_column(String)
    
    # Connection properties
    connection_type: Mapped[str] = mapped_column(String, default="related")  # related, references, contains, precedes, contradicts
    strength: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0-1.0 connection strength
    direction: Mapped[str] = mapped_column(String, default="bidirectional")  # forward, backward, bidirectional
    
    # Context
    context: Mapped[str] = mapped_column(Text, default="")
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_strengthened: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class BrainEntity(Base):
    """
    Entities extracted from memories and notes (people, places, concepts).
    Central entity resolution and tracking.
    """
    __tablename__ = "brain_entities"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Entity identity
    name: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, default="unknown")  # person, place, concept, tool, organization
    
    # Canonicalization
    canonical_name: Mapped[str] = mapped_column(String, default="")
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    
    # Entity knowledge
    description: Mapped[str] = mapped_column(Text, default="")
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Relationships
    related_entity_ids: Mapped[list] = mapped_column(JSON, default=list)
    
    # Statistics
    mention_count: Mapped[int] = mapped_column(Integer, default=0)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Importance
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BrainContext(Base):
    """
    Current working context and state.
    Replaces working memory files with dynamic context tracking.
    """
    __tablename__ = "brain_context"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Context identification
    context_type: Mapped[str] = mapped_column(String, default="general")  # chat, task, session
    context_name: Mapped[str] = mapped_column(String, default="")
    
    # Active memory
    active_memory_ids: Mapped[list] = mapped_column(JSON, default=list)
    active_note_ids: Mapped[list] = mapped_column(JSON, default=list)
    
    # Current state
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Session info
    session_id: Mapped[str] = mapped_column(String, nullable=True)
    user_id: Mapped[str] = mapped_column(String, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class BrainConsolidationLog(Base):
    """
    Log of memory consolidation operations.
    Tracks promotion from short-term to long-term memory.
    """
    __tablename__ = "brain_consolidation_log"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Consolidation details
    memory_id: Mapped[str] = mapped_column(String, nullable=False)
    from_region: Mapped[str] = mapped_column(String, default=MemoryRegion.HIPPOCAMPUS.value)
    to_region: Mapped[str] = mapped_column(String, default=MemoryRegion.CORTEX.value)
    
    # Consolidation result
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    reason: Mapped[str] = mapped_column(String, default="")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
