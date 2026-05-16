"""
Brain Scheduler — Automated brain operations on schedule.

Runs periodic tasks:
  - Memory consolidation
  - Memory linking and connection strengthening
  - Vault indexing and note linking
  - Entity resolution updates
  - Memory decay and cleanup

Suggested frequencies:
  - Memory consolidation: Every 6 hours
  - Memory linking: Every 1 hour
  - Vault indexing: Every 30 minutes
  - Entity resolution: Every 2 hours
  - Memory decay: Daily at 2 AM
"""

import asyncio
import logging
from datetime import datetime, time
from typing import Optional
from sqlalchemy import select, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from atlas.db.brain_models import (
    BrainMemory, BrainNote, BrainEntity, BrainConnection,
    MemoryRegion, MemoryType
)
from atlas.services.brain_service import brain_service
from atlas.core.brain_indexer import brain_indexer
from atlas.core.vault_writer import sync_vault
from atlas.db.session import get_session

logger = logging.getLogger(__name__)


class BrainScheduler:
    """Scheduler for automated brain operations."""
    
    def __init__(self):
        self._running = False
        self._tasks = []
    
    async def start(self):
        """Start all scheduled tasks."""
        if self._running:
            logger.warning("Brain scheduler already running")
            return
        
        self._running = True
        logger.info("Starting brain scheduler")
        
        # Start scheduled tasks
        self._tasks = [
            asyncio.create_task(self._schedule_memory_consolidation(), name="memory_consolidation"),
            asyncio.create_task(self._schedule_memory_linking(), name="memory_linking"),
            asyncio.create_task(self._schedule_vault_indexing(), name="vault_indexing"),
            asyncio.create_task(self._schedule_entity_resolution(), name="entity_resolution"),
            asyncio.create_task(self._schedule_memory_decay(), name="memory_decay"),
        ]
        
        logger.info(f"Started {len(self._tasks)} scheduled tasks")
    
    async def stop(self):
        """Stop all scheduled tasks."""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping brain scheduler")
        
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        logger.info("Brain scheduler stopped")
    
    async def _schedule_memory_consolidation(self, interval_hours: int = 6):
        """Run memory consolidation every N hours."""
        logger.info(f"Starting memory consolidation (every {interval_hours} hours)")
        
        while self._running:
            try:
                async with get_session() as session:
                    consolidated = await brain_service.auto_consolidate(
                        session=session,
                        min_access_count=3,
                        min_importance=0.6,
                        days_threshold=7
                    )
                    logger.info(f"Auto-consolidated {len(consolidated)} memories")
                
                await asyncio.sleep(interval_hours * 3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Memory consolidation error: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retry
    
    async def _schedule_memory_linking(self, interval_minutes: int = 60):
        """Run memory linking every N minutes."""
        logger.info(f"Starting memory linking (every {interval_minutes} minutes)")
        
        while self._running:
            try:
                await self._link_related_memories()
                logger.info("Memory linking completed")
                
                await asyncio.sleep(interval_minutes * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Memory linking error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
    
    async def _link_related_memories(self):
        """Link related memories based on shared entities and semantic similarity."""
        async with get_session() as session:
            # Get recent memories from hippocampus
            result = await session.execute(
                select(BrainMemory)
                .where(BrainMemory.memory_region == MemoryRegion.HIPPOCAMPUS.value)
                .where(BrainMemory.created_at > datetime.utcnow().replace(hour=datetime.utcnow().hour - 24))
                .limit(100)
            )
            memories = result.scalars().all()
            
            linked_count = 0
            for i, mem1 in enumerate(memories):
                for mem2 in memories[i+1:]:
                    # Check for shared tags/entities
                    shared = set(mem1.tags) & set(mem2.tags)
                    
                    if shared:
                        # Check if connection already exists
                        existing = await session.execute(
                            select(BrainConnection).where(
                                and_(
                                    BrainConnection.source_id == mem1.id,
                                    BrainConnection.target_id == mem2.id
                                )
                            )
                        )
                        if not existing.scalar_one_or_none():
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
                            linked_count += 1
            
            logger.info(f"Created {linked_count} new memory connections")
    
    async def _schedule_vault_indexing(self, interval_minutes: int = 30):
        """Run vault indexing every N minutes."""
        logger.info(f"Starting vault indexing (every {interval_minutes} minutes)")
        
        while self._running:
            try:
                await sync_vault()
                logger.info("Vault indexing completed")
                
                await asyncio.sleep(interval_minutes * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Vault indexing error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
    
    async def _schedule_entity_resolution(self, interval_hours: int = 2):
        """Run entity resolution every N hours."""
        logger.info(f"Starting entity resolution (every {interval_hours} hours)")
        
        while self._running:
            try:
                await self._resolve_entities()
                logger.info("Entity resolution completed")
                
                await asyncio.sleep(interval_hours * 3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Entity resolution error: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retry
    
    async def _resolve_entities(self):
        """Update entity relationships and merge duplicates."""
        async with get_session() as session:
            # Get entities with high mention counts
            result = await session.execute(
                select(BrainEntity)
                .where(BrainEntity.mention_count > 5)
                .order_by(BrainEntity.mention_count.desc())
                .limit(50)
            )
            entities = result.scalars().all()
            
            # Update entity relationships based on shared memories
            for i, entity1 in enumerate(entities):
                for entity2 in entities[i+1:]:
                    # Check for shared related memories
                    shared = set(entity1.related_entity_ids) & set(entity2.related_entity_ids)
                    
                    if len(shared) > 2:  # If they share 3+ memories
                        # They might be related
                        if entity2.id not in entity1.related_entity_ids:
                            await session.execute(
                                update(BrainEntity)
                                .where(BrainEntity.id == entity1.id)
                                .values(
                                    related_entity_ids=entity1.related_entity_ids + [entity2.id]
                                )
                            )
            
            await session.commit()
            logger.info("Updated entity relationships")
    
    async def _schedule_memory_decay(self, target_hour: int = 2):
        """Run memory decay daily at specified hour."""
        logger.info(f"Starting memory decay (daily at {target_hour}:00)")
        
        while self._running:
            try:
                # Wait until target hour
                now = datetime.utcnow()
                target = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
                
                if now > target:
                    target = target.replace(day=now.day + 1)
                
                sleep_seconds = (target - now).total_seconds()
                logger.info(f"Memory decay scheduled in {sleep_seconds/3600:.1f} hours")
                await asyncio.sleep(sleep_seconds)
                
                # Run decay
                async with get_session() as session:
                    decayed = await brain_service.decay_memories(
                        session=session,
                        days_threshold=30,
                        max_importance=0.3,
                        decay_factor=0.1
                    )
                    logger.info(f"Decayed {len(decayed)} memories")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Memory decay error: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retry


# Global scheduler instance
brain_scheduler = BrainScheduler()
