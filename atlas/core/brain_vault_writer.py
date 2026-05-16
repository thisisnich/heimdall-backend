"""
Brain Vault Writer — Syncs brain database to Obsidian-compatible Markdown files.

Provides a bridge between the database-first brain system and Obsidian for:
  - Visual monitoring of Heimdall's memories
  - Manual editing and review
  - Git-based version control
  - Obsidian graph visualization

Vault Structure:
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
"""

import os
import re
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from atlas.db.brain_models import (
    BrainMemory, BrainNote, BrainEntity, BrainConnection,
    MemoryRegion, MemoryType
)

logger = logging.getLogger(__name__)

BRAIN_VAULT_ROOT = Path(os.getenv("BRAIN_VAULT_PATH", "/opt/heimdall/brain-vault"))

# Vault structure
VAULT_FOLDERS = {
    "memories": {
        "cortex": "Long-term semantic memory",
        "hippocampus": "Short-term episodic memory",
        "prefrontal": "Working memory",
        "amygdala": "Emotional memory"
    },
    "notes": {
        "general": "General notes",
        "code": "Code snippets",
        "reference": "Reference materials"
    },
    "entities": {
        "people": "People",
        "places": "Places",
        "concepts": "Concepts",
        "tools": "Tools",
        "organizations": "Organizations"
    }
}


def _ensure_vault():
    """Create vault folder structure if it doesn't exist."""
    BRAIN_VAULT_ROOT.mkdir(parents=True, exist_ok=True)
    
    for category, subfolders in VAULT_FOLDERS.items():
        category_path = BRAIN_VAULT_ROOT / category
        category_path.mkdir(exist_ok=True)
        
        for subfolder, description in subfolders.items():
            subfolder_path = category_path / subfolder
            subfolder_path.mkdir(exist_ok=True)
            
            # Create README for each folder
            readme_path = subfolder_path / "README.md"
            if not readme_path.exists():
                readme_path.write_text(f"# {subfolder.title()}\n\n{description}\n", encoding='utf-8')


def _slug(text: str) -> str:
    """Convert text to a safe filename slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:60].strip("-")


def _compute_checksum(content: str) -> str:
    """Compute SHA256 checksum for content integrity."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _get_memory_vault_path(memory: BrainMemory) -> Path:
    """Determine vault path for a memory based on its region."""
    region_folder = memory.memory_region or "cortex"
    folder_path = BRAIN_VAULT_ROOT / "memories" / region_folder
    folder_path.mkdir(parents=True, exist_ok=True)
    
    # Create filename from first 50 chars of content
    filename = f"{_slug(memory.content[:50])}-{memory.id[:8]}.md"
    return folder_path / filename


def _get_note_vault_path(note: BrainNote) -> Path:
    """Determine vault path for a note based on its folder."""
    folder = note.folder or "general"
    folder_path = BRAIN_VAULT_ROOT / "notes" / folder
    folder_path.mkdir(parents=True, exist_ok=True)
    
    filename = f"{_slug(note.title)}-{note.id[:8]}.md"
    return folder_path / filename


def _get_entity_vault_path(entity: BrainEntity) -> Path:
    """Determine vault path for an entity based on its type."""
    entity_type = entity.entity_type or "concepts"
    folder_path = BRAIN_VAULT_ROOT / "entities" / entity_type
    folder_path.mkdir(parents=True, exist_ok=True)
    
    filename = f"{_slug(entity.name)}.md"
    return folder_path / filename


def _format_memory_frontmatter(memory: BrainMemory) -> str:
    """Create YAML frontmatter for a memory."""
    return f"""---
id: {memory.id}
type: memory
memory_type: {memory.memory_type}
memory_region: {memory.memory_region}
importance: {memory.importance}
access_count: {memory.access_count}
source_type: {memory.source_type}
source_id: {memory.source_id or ''}
tags: {memory.tags}
categories: {memory.categories}
is_consolidated: {memory.is_consolidated}
created_at: {memory.created_at.isoformat()}
updated_at: {memory.updated_at.isoformat()}
last_accessed: {memory.last_accessed.isoformat() if memory.last_accessed else ''}
checksum: sha256:{_compute_checksum(memory.content)}
---

# {memory.content[:60]}...

> **Memory Type:** {memory.memory_type}
> **Region:** {memory.memory_region}
> **Importance:** {memory.importance:.2f}
> **Access Count:** {memory.access_count}
> **Created:** {memory.created_at.strftime('%Y-%m-%d %H:%M')}

## Content

{memory.content}

## Metadata

- **Source:** {memory.source_type}
- **Source ID:** {memory.source_id or 'N/A'}
- **Tags:** {', '.join(memory.tags)}
- **Categories:** {', '.join(memory.categories)}
- **Consolidated:** {'Yes' if memory.is_consolidated else 'No'}
- **Last Accessed:** {memory.last_accessed.strftime('%Y-%m-%d %H:%M') if memory.last_accessed else 'Never'}

---

*Synced from Heimdall Brain at {datetime.now().isoformat()}*
"""


def _format_note_frontmatter(note: BrainNote) -> str:
    """Create YAML frontmatter for a note."""
    return f"""---
id: {note.id}
type: note
note_type: {note.note_type}
note_format: {note.note_format}
folder: {note.folder}
collection: {note.collection}
importance: {note.importance}
word_count: {note.word_count}
read_count: {note.read_count}
source_type: {note.source_type}
tags: {note.tags}
is_pinned: {note.is_pinned}
is_archived: {note.is_archived}
created_at: {note.created_at.isoformat()}
updated_at: {note.updated_at.isoformat()}
checksum: sha256:{_compute_checksum(note.content)}
---

# {note.title}

> **Type:** {note.note_type}
> **Folder:** {note.folder}
> **Importance:** {note.importance:.2f}
> **Words:** {note.word_count}
> **Created:** {note.created_at.strftime('%Y-%m-%d %H:%M')}

## Content

{note.content}

## Metadata

- **Note Type:** {note.note_type}
- **Collection:** {note.collection}
- **Tags:** {', '.join(note.tags)}
- **Linked Memories:** {len(note.linked_memory_ids)}
- **Read Count:** {note.read_count}
- **Pinned:** {'Yes' if note.is_pinned else 'No'}
- **Archived:** {'Yes' if note.is_archived else 'No'}

---

*Synced from Heimdall Brain at {datetime.now().isoformat()}*
"""


def _format_entity_frontmatter(entity: BrainEntity) -> str:
    """Create YAML frontmatter for an entity."""
    return f"""---
id: {entity.id}
type: entity
entity_type: {entity.entity_type}
canonical_name: {entity.canonical_name or ''}
aliases: {entity.aliases}
mention_count: {entity.mention_count}
importance: {entity.importance}
is_active: {entity.is_active}
created_at: {entity.created_at.isoformat()}
updated_at: {entity.updated_at.isoformat()}
---

# {entity.name}

> **Type:** {entity.entity_type}
> **Mentions:** {entity.mention_count}
> **Importance:** {entity.importance:.2f}
> **First Seen:** {entity.first_seen.strftime('%Y-%m-%d')}

## Description

{entity.description or 'No description available.'}

## Attributes

{chr(10).join(f"- **{k}**: {v}" for k, v in entity.attributes.items()) if entity.attributes else 'No attributes.'}

## Aliases

{', '.join(entity.aliases) if entity.aliases else 'No aliases.'}

## Related Entities

{len(entity.related_entity_ids)} related entities

## Statistics

- **Mention Count:** {entity.mention_count}
- **First Seen:** {entity.first_seen.strftime('%Y-%m-%d %H:%M')}
- **Last Seen:** {entity.last_seen.strftime('%Y-%m-%d %H:%M')}

---

*Synced from Heimdall Brain at {datetime.now().isoformat()}*
"""


async def sync_memory_to_vault(session: AsyncSession, memory: BrainMemory) -> dict:
    """Sync a single memory to the vault."""
    _ensure_vault()
    
    vault_path = _get_memory_vault_path(memory)
    content = _format_memory_frontmatter(memory)
    
    vault_path.write_text(content, encoding='utf-8')
    
    logger.debug(f"Synced memory {memory.id} to {vault_path}")
    
    return {
        "status": "synced",
        "memory_id": memory.id,
        "vault_path": str(vault_path.relative_to(BRAIN_VAULT_ROOT))
    }


async def sync_note_to_vault(session: AsyncSession, note: BrainNote) -> dict:
    """Sync a single note to the vault."""
    _ensure_vault()
    
    vault_path = _get_note_vault_path(note)
    content = _format_note_frontmatter(note)
    
    vault_path.write_text(content, encoding='utf-8')
    
    logger.debug(f"Synced note {note.id} to {vault_path}")
    
    return {
        "status": "synced",
        "note_id": note.id,
        "vault_path": str(vault_path.relative_to(BRAIN_VAULT_ROOT))
    }


async def sync_entity_to_vault(session: AsyncSession, entity: BrainEntity) -> dict:
    """Sync a single entity to the vault."""
    _ensure_vault()
    
    vault_path = _get_entity_vault_path(entity)
    content = _format_entity_frontmatter(entity)
    
    vault_path.write_text(content, encoding='utf-8')
    
    logger.debug(f"Synced entity {entity.id} to {vault_path}")
    
    return {
        "status": "synced",
        "entity_id": entity.id,
        "vault_path": str(vault_path.relative_to(BRAIN_VAULT_ROOT))
    }


async def sync_all_memories(
    session: AsyncSession,
    limit: int = 1000,
    memory_type: Optional[str] = None,
    memory_region: Optional[str] = None
) -> dict:
    """Sync all memories to the vault."""
    _ensure_vault()
    
    query = select(BrainMemory)
    
    if memory_type:
        query = query.where(BrainMemory.memory_type == memory_type)
    if memory_region:
        query = query.where(BrainMemory.memory_region == memory_region)
    
    query = query.order_by(BrainMemory.created_at.desc()).limit(limit)
    
    result = await session.execute(query)
    memories = result.scalars().all()
    
    synced = 0
    for memory in memories:
        await sync_memory_to_vault(session, memory)
        synced += 1
    
    logger.info(f"Synced {synced} memories to vault")
    
    return {
        "status": "success",
        "synced": synced,
        "total": len(memories)
    }


async def sync_all_notes(
    session: AsyncSession,
    limit: int = 1000,
    folder: Optional[str] = None
) -> dict:
    """Sync all notes to the vault."""
    _ensure_vault()
    
    query = select(BrainNote)
    
    if folder:
        query = query.where(BrainNote.folder == folder)
    
    query = query.order_by(BrainNote.created_at.desc()).limit(limit)
    
    result = await session.execute(query)
    notes = result.scalars().all()
    
    synced = 0
    for note in notes:
        await sync_note_to_vault(session, note)
        synced += 1
    
    logger.info(f"Synced {synced} notes to vault")
    
    return {
        "status": "success",
        "synced": synced,
        "total": len(notes)
    }


async def sync_all_entities(
    session: AsyncSession,
    limit: int = 1000,
    entity_type: Optional[str] = None
) -> dict:
    """Sync all entities to the vault."""
    _ensure_vault()
    
    query = select(BrainEntity)
    
    if entity_type:
        query = query.where(BrainEntity.entity_type == entity_type)
    
    query = query.order_by(BrainEntity.mention_count.desc()).limit(limit)
    
    result = await session.execute(query)
    entities = result.scalars().all()
    
    synced = 0
    for entity in entities:
        await sync_entity_to_vault(session, entity)
        synced += 1
    
    logger.info(f"Synced {synced} entities to vault")
    
    return {
        "status": "success",
        "synced": synced,
        "total": len(entities)
    }


async def sync_full_brain(session: AsyncSession) -> dict:
    """Sync the entire brain to the vault."""
    _ensure_vault()
    
    memories_result = await sync_all_memories(session)
    notes_result = await sync_all_notes(session)
    entities_result = await sync_all_entities(session)
    
    # Update index
    await write_brain_index(session)
    
    total_synced = memories_result["synced"] + notes_result["synced"] + entities_result["synced"]
    
    logger.info(f"Full brain sync complete: {total_synced} items")
    
    return {
        "status": "success",
        "memories": memories_result,
        "notes": notes_result,
        "entities": entities_result,
        "total_synced": total_synced
    }


async def write_brain_index(session: AsyncSession):
    """Write the main index file for the brain vault."""
    _ensure_vault()
    
    # Get counts
    memory_count = await session.execute(select(BrainMemory).where(BrainMemory.is_consolidated == True))
    memory_count = len(memory_count.scalars().all())
    
    note_count = await session.execute(select(BrainNote))
    note_count = len(note_count.scalars().all())
    
    entity_count = await session.execute(select(BrainEntity))
    entity_count = len(entity_count.scalars().all())
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    index_content = f"""---
title: Heimdall Brain Index
updated: {now}
type: index
---

# Heimdall Brain

> Last synced: {now}

## Overview

This vault contains a synchronized view of Heimdall's brain database. All memories, notes, and entities are exported here for visualization in Obsidian.

## Statistics

- **Memories:** {memory_count}
- **Notes:** {note_count}
- **Entities:** {entity_count}

## Sections

### 🧠 Memories

- [[memories/cortex|Cortex]] - Long-term semantic memory
- [[memories/hippocampus|Hippocampus]] - Short-term episodic memory
- [[memories/prefrontal|Prefrontal]] - Working memory
- [[memories/amygdala|Amygdala]] - Emotional memory

### 📝 Notes

- [[notes/general|General Notes]]
- [[notes/code|Code Snippets]]
- [[notes/reference|Reference Materials]]

### 👥 Entities

- [[entities/people|People]]
- [[entities/places|Places]]
- [[entities/concepts|Concepts]]
- [[entities/tools|Tools]]
- [[entities/organizations|Organizations]]

## Usage

This vault is automatically synced from the Heimdall brain database. Changes made here are not synced back to the database - this is a read-only view for monitoring and visualization.

To trigger a sync, use the Heimdall API:
```bash
curl -X POST http://localhost:8000/brain/vault/sync
```

---

*Auto-generated by Heimdall Brain Vault Writer*
"""
    
    index_path = BRAIN_VAULT_ROOT / "_index.md"
    index_path.write_text(index_content, encoding='utf-8')
    
    logger.info("Brain vault index updated")
