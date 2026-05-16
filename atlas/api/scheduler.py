"""
Scheduler API — Control brain scheduler and reminder system.

Endpoints for:
  - Starting/stopping scheduler
  - Triggering manual operations
  - Configuring reminder system
  - Viewing scheduler status
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from atlas.services.brain_scheduler import brain_scheduler
from atlas.services.brain_reminder import brain_reminder, proactive_checker

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


class SchedulerConfig(BaseModel):
    memory_consolidation_hours: int = 6
    memory_linking_minutes: int = 60
    vault_indexing_minutes: int = 30
    entity_resolution_hours: int = 2
    memory_decay_hour: int = 2


class ReminderConfig(BaseModel):
    chat_id: str
    check_interval_minutes: int = 60
    proactive_check_interval_hours: int = 1


@router.post("/start")
async def start_scheduler():
    """Start the brain scheduler."""
    try:
        await brain_scheduler.start()
        return {"status": "started", "message": "Brain scheduler started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_scheduler():
    """Stop the brain scheduler."""
    try:
        await brain_scheduler.stop()
        return {"status": "stopped", "message": "Brain scheduler stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_scheduler_status():
    """Get scheduler status."""
    return {
        "running": brain_scheduler._running,
        "tasks": len(brain_scheduler._tasks),
        "task_names": [task.get_name() for task in brain_scheduler._tasks]
    }


@router.post("/reminders/start")
async def start_reminders(config: ReminderConfig):
    """Start the reminder system."""
    try:
        brain_reminder.chat_id = config.chat_id
        brain_reminder._check_interval = config.check_interval_minutes * 60
        proactive_checker.chat_id = config.chat_id
        proactive_checker._check_interval = config.proactive_check_interval_hours * 3600
        
        # Start as background tasks
        import asyncio
        asyncio.create_task(brain_reminder.start())
        asyncio.create_task(proactive_checker.start())
        
        return {"status": "started", "message": "Reminder system started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reminders/stop")
async def stop_reminders():
    """Stop the reminder system."""
    try:
        await brain_reminder.stop()
        await proactive_checker.stop()
        return {"status": "stopped", "message": "Reminder system stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reminders/status")
async def get_reminders_status():
    """Get reminder system status."""
    return {
        "reminder_running": brain_reminder._running,
        "proactive_running": proactive_checker._running,
        "reminder_chat_id": brain_reminder.chat_id,
        "reminder_interval": brain_reminder._check_interval,
        "proactive_interval": proactive_checker._check_interval
    }


@router.post("/trigger/consolidation")
async def trigger_consolidation(background_tasks: BackgroundTasks):
    """Trigger memory consolidation manually."""
    async def run_consolidation():
        from atlas.db.session import get_session
        async with get_session() as session:
            from atlas.services.brain_service import brain_service
            consolidated = await brain_service.auto_consolidate(session=session)
            return {"consolidated": len(consolidated)}
    
    background_tasks.add_task(run_consolidation)
    return {"status": "started", "message": "Memory consolidation triggered"}


@router.post("/trigger/linking")
async def trigger_linking(background_tasks: BackgroundTasks):
    """Trigger memory linking manually."""
    async def run_linking():
        from atlas.db.session import get_session
        async with get_session() as session:
            from atlas.services.brain_scheduler import BrainScheduler
            scheduler = BrainScheduler()
            await scheduler._link_related_memories()
            return {"status": "completed"}
    
    background_tasks.add_task(run_linking)
    return {"status": "started", "message": "Memory linking triggered"}


@router.post("/trigger/vault-sync")
async def trigger_vault_sync(background_tasks: BackgroundTasks):
    """Trigger vault indexing manually."""
    async def run_sync():
        from atlas.core.vault_writer import sync_vault
        result = await sync_vault()
        return result
    
    background_tasks.add_task(run_sync)
    return {"status": "started", "message": "Vault sync triggered"}
