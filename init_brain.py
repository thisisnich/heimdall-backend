"""
Initialize Heimdall Brain Database Tables.

This script creates the database tables for the brain system:
  - brain_memory: Core memory entries
  - brain_notes: Indexed notes
  - brain_connections: Memory/note relationships
  - brain_entities: Extracted entities
  - brain_context: Working context
  - brain_consolidation_log: Consolidation tracking

Also initializes pgvector tables for semantic search.
"""

import asyncio
from atlas.db.session import engine
from atlas.db.brain_models import (
    Base, BrainMemory, BrainNote, BrainConnection, 
    BrainEntity, BrainContext, BrainConsolidationLog
)
from atlas.db.brain_vector import init_brain_vector_tables


async def init_brain_tables():
    """Create all brain database tables."""
    print("Creating brain database tables...")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✓ Brain database tables created")


async def init_vector_tables():
    """Initialize pgvector tables for semantic search."""
    print("Initializing brain vector tables...")
    
    await init_brain_vector_tables()
    
    print("✓ Brain vector tables initialized")


async def main():
    """Run complete brain initialization."""
    print("=" * 50)
    print("Heimdall Brain Initialization")
    print("=" * 50)
    
    await init_brain_tables()
    await init_vector_tables()
    
    print("=" * 50)
    print("Brain initialization complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
