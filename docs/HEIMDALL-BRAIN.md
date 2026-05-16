# Heimdall Brain Documentation

## Overview

Heimdall Brain is a database-first memory system designed specifically for Heimdall to remember things, keep memories, and index notes. It provides a more efficient alternative to the file-based Obsidian vault system.

## Architecture

### Brain Regions

The brain is organized into four main regions, inspired by neuroscience:

- **Cortex** (`cortex`): Long-term semantic memory (facts, concepts, knowledge)
- **Hippocampus** (`hippocampus`): Short-term episodic memory (events, conversations)
- **Prefrontal** (`prefrontal`): Working memory (active context, current tasks)
- **Amygdala** (`amygdala`): Emotional memory (emotional associations)

### Memory Types

Memories are classified into four types:

- **Episodic** (`episodic`): Events, experiences, conversations
- **Semantic** (`semantic`): Facts, concepts, knowledge
- **Procedural** (`procedural`): Skills, how-to, workflows
- **Emotional** (`emotional`): Emotional states, preferences, feelings

### Database Schema

#### Core Tables

- **brain_memory**: Core memory entries with embeddings
- **brain_notes**: Indexed notes with cross-references
- **brain_connections**: Synaptic connections between memories/notes
- **brain_entities**: Extracted and resolved entities
- **brain_context**: Current working context
- **brain_consolidation_log**: Memory consolidation tracking

#### Vector Tables

- **vector_brain_memory**: Embeddings for semantic search
- **vector_brain_notes**: Embeddings for note search

## Key Features

### 1. Database-First Approach

Unlike the file-based vault system, Heimdall Brain stores everything in PostgreSQL with pgvector. This provides:

- Direct database queries (no file I/O overhead)
- ACID transactions and data integrity
- Efficient indexing and search
- Automatic backups and replication

### 2. Semantic Search

All memories and notes are automatically embedded using nomic-embed-text via Ollama. This enables:

- Semantic similarity search
- Context-aware retrieval
- Cross-domain discovery

### 3. Memory Consolidation

The brain automatically consolidates memories from short-term to long-term storage:

- **Criteria**: High importance, multiple accesses, age threshold
- **Process**: Moves from hippocampus to cortex
- **Tracking**: Logged in consolidation_log table

### 4. Entity Resolution

Automatically extracts and resolves entities from memories:

- Normalizes entity names
- Classifies by type (person, place, concept, tool, organization)
- Tracks mention frequency
- Links entities to related memories

### 5. Importance Scoring & Decay

Memories have importance scores (0.0-1.0) that determine:

- Search ranking
- Consolidation eligibility
- Decay resistance

Old, low-importance memories are periodically decayed and eventually removed.

### 6. Context Management

Tracks active working context for sessions:

- Active memories and notes
- Session-specific state
- Automatic expiration

## API Endpoints

### Memory Operations

#### Store Memory
```http
POST /brain/memories
Content-Type: application/json

{
  "content": "User wants to learn Rust this summer",
  "memory_type": "semantic",
  "importance": 0.7,
  "tags": ["Rust", "programming", "summer"]
}
```

#### Get Memory
```http
GET /brain/memories/{memory_id}
```

#### Search Memories
```http
POST /brain/memories/search
Content-Type: application/json

{
  "query": "programming goals",
  "memory_type": "semantic",
  "min_importance": 0.5,
  "limit": 10
}
```

#### Update Importance
```http
PUT /brain/memories/{memory_id}/importance
Content-Type: application/json

{
  "importance": 0.8
}
```

### Note Operations

#### Store Note
```http
POST /brain/notes
Content-Type: application/json

{
  "title": "Rust Learning Plan",
  "content": "Steps to learn Rust...",
  "note_type": "general",
  "folder": "learning",
  "importance": 0.6
}
```

#### Get Note
```http
GET /brain/notes/{note_id}
```

#### Search Notes
```http
POST /brain/notes/search
Content-Type: application/json

{
  "query": "learning plan",
  "limit": 10
}
```

#### Re-index Note
```http
POST /brain/notes/{note_id}/reindex
```

### Indexing Operations

#### Index Text
```http
POST /brain/index
Content-Type: application/json

{
  "text": "User met with Professor Smith about FYP",
  "source_type": "chat",
  "source_id": "session_123"
}
```

#### Index Chat Turn
```http
POST /brain/index/chat
Content-Type: application/json

{
  "user_message": "I want to learn Rust",
  "assistant_reply": "Great choice! Here's how to start...",
  "session_id": "session_123"
}
```

#### Index Note
```http
POST /brain/index/note
Content-Type: application/json

{
  "title": "Meeting Notes",
  "content": "Discussed project timeline...",
  "folder": "work"
}
```

### Consolidation Operations

#### Manual Consolidation
```http
POST /brain/consolidate/{memory_id}
Content-Type: application/json

{
  "reason": "Important goal"
}
```

#### Auto Consolidation
```http
POST /brain/consolidate/auto
Content-Type: application/json

{
  "min_access_count": 3,
  "min_importance": 0.6,
  "days_threshold": 7
}
```

### Context Operations

#### Set Context
```http
POST /brain/context
Content-Type: application/json

{
  "context_type": "chat",
  "context_name": "Project Planning",
  "active_memory_ids": ["mem_1", "mem_2"],
  "session_id": "session_123",
  "expires_in_hours": 24
}
```

#### Get Active Context
```http
GET /brain/context?context_type=chat&session_id=session_123
```

### Statistics

#### Get Brain Stats
```http
GET /brain/stats
```

Returns statistics about memory counts, importance scores, and access patterns.

#### Trigger Memory Decay
```http
POST /brain/decay
Content-Type: application/json

{
  "days_threshold": 30,
  "max_importance": 0.3,
  "decay_factor": 0.1
}
```

### Entity Operations

#### List Entities
```http
GET /brain/entities?entity_type=person&limit=50
```

#### Get Entity
```http
GET /brain/entities/{entity_id}
```

## Comparison with Heimdall Vault

| Feature | Heimdall Vault | Heimdall Brain |
|---------|---------------|----------------|
| Storage | File-based Markdown | Database (PostgreSQL) |
| Search | File system + basic grep | pgvector semantic search |
| Indexing | Manual classification | Automatic entity extraction |
| Memory Types | Basic types | 4 memory types + regions |
| Consolidation | None | Automatic hippocampus→cortex |
| Importance | None | Scoring + decay system |
| Context | None | Working context tracking |
| Relationships | Wiki links | Structured connections |
| Performance | File I/O limited | Database optimized |

## Usage Examples

### Basic Memory Storage

```python
from atlas.services.brain_service import brain_service
from atlas.db.session import get_session

async with get_session() as session:
    memory = await brain_service.store_memory(
        session=session,
        content="User wants to achieve 4.0 GPA this semester",
        memory_type="semantic",
        importance=0.8,
        tags=["GPA", "academic", "goal"]
    )
```

### Semantic Search

```python
results = await brain_service.search_memories(
    query="academic goals",
    min_importance=0.5,
    limit=10
)
```

### Note Indexing

```python
from atlas.core.brain_indexer import brain_indexer

async with get_session() as session:
    note = await brain_indexer.index_note(
        session=session,
        title="Project Meeting Notes",
        content="Discussed timeline and milestones...",
        folder="work"
    )
```

### Chat Turn Indexing

```python
result = await brain_indexer.index_chat_turn(
    session=session,
    user_message="I need to finish the FYP report",
    assistant_reply="I'll help you organize the report structure",
    session_id="chat_123"
)
```

## Initialization

Run the initialization script to create all database tables:

```bash
python init_brain.py
```

This will:
1. Create brain database tables
2. Initialize pgvector tables
3. Set up indexes for efficient queries

## Migration from Vault

To migrate existing vault notes to the brain system:

```python
from atlas.core.brain_indexer import brain_indexer
from pathlib import Path

async def migrate_vault_notes(vault_path: str):
    vault = Path(vault_path)
    
    for md_file in vault.rglob("*.md"):
        content = md_file.read_text()
        
        async with get_session() as session:
            await brain_indexer.index_note(
                session=session,
                title=md_file.stem,
                content=content,
                folder=str(md_file.parent.relative_to(vault))
            )
```

## Obsidian Integration

The brain system includes a vault writer that syncs the database to Obsidian-compatible Markdown files for visual monitoring.

### Setup

Run the setup script to initialize the brain vault with git:

```bash
python setup_brain_vault.py --remote https://github.com/user/heimdall-brain.git
```

This creates:
- `/opt/heimdall/brain-vault/` - Vault directory
- Folder structure for memories, notes, entities
- Git repository with remote configured

### Vault Structure

```
brain-vault/
├── memories/
│   ├── cortex/           # Long-term semantic memory
│   ├── hippocampus/      # Short-term episodic memory
│   ├── prefrontal/       # Working memory
│   └── amygdala/         # Emotional memory
├── notes/
│   ├── general/
│   ├── code/
│   └── reference/
├── entities/
│   ├── people/
│   ├── places/
│   └── concepts/
└── _index.md             # Brain overview
```

### Syncing to Vault

**Sync entire brain to vault:**
```bash
curl -X POST http://localhost:8000/brain/vault/sync
```

**Sync with automatic git push:**
```bash
curl -X POST 'http://localhost:8000/brain/vault/sync?push_to_git=true'
```

**Sync specific types:**
```bash
# Memories only
curl -X POST http://localhost:8000/brain/vault/sync/memories

# Notes only
curl -X POST http://localhost:8000/brain/vault/sync/notes
```

### Git Operations

**Initialize git repository:**
```bash
curl -X POST 'http://localhost:8000/brain/vault/git/init?remote_url=https://github.com/user/heimdall-brain.git'
```

**Commit changes:**
```bash
curl -X POST 'http://localhost:8000/brain/vault/git/commit?message=Brain sync 2026-05-16'
```

**Push to remote:**
```bash
curl -X POST http://localhost:8000/brain/vault/git/push
```

**Commit and push in one step:**
```bash
curl -X POST 'http://localhost:8000/brain/vault/git/sync?message=Auto sync&branch=main'
```

**Get vault status:**
```bash
curl http://localhost:8000/brain/vault/status
```

### Opening in Obsidian

After syncing, open the vault in Obsidian:

```bash
obsidian://open?vault=/opt/heimdall/brain-vault
```

Or manually:
1. Open Obsidian
2. Click "Open folder as vault"
3. Select `/opt/heimdall/brain-vault`

### Features in Obsidian

- **Graph View**: Visualize connections between memories and notes
- **Search**: Full-text search across all brain content
- **Tags**: Filter by memory type, region, importance
- **Backlinks**: See what references each memory/note
- **Properties**: View metadata (importance, access count, etc.)

### Scheduled Auto-Sync

To enable automatic syncing, add a cron job:

```bash
# Sync every hour
0 * * * * curl -X POST 'http://localhost:8000/brain/vault/sync?push_to_git=true'
```

Or use the brain service programmatically:

```python
from atlas.core.brain_vault_writer import sync_full_brain
from atlas.core.brain_git import sync_and_push
from atlas.db.session import get_session

async def scheduled_sync():
    async with get_session() as session:
        # Sync to vault
        await sync_full_brain(session)
        
        # Push to git
        sync_and_push("Scheduled sync")
```

## Performance Considerations

- **Embedding Generation**: First-time storage requires embedding generation (Ollama)
- **Vector Search**: pgvector provides fast approximate nearest neighbor search
- **Consolidation**: Runs in background, doesn't block operations
- **Decay**: Scheduled job, can be tuned based on memory growth

## Future Enhancements

- [x] Obsidian vault integration
- [x] Git-based version control
- [x] Automated scheduler
- [x] Telegram reminders
- [x] Proactive check-ins
- [ ] Graph-based memory visualization
- [ ] Temporal memory queries (e.g., "what did I learn last week?")
- [ ] Cross-brain synchronization (multiple users)
- [ ] Memory export/import (JSON, Markdown)
- [ ] Advanced decay strategies (spaced repetition)
- [ ] Emotional context tracking
- [ ] Procedural memory execution (workflow automation)
