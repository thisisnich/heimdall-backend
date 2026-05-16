"""
Brain Reminder System — Telegram reminders based on temporal context.

Extracts temporal information from memories and sends reminders:
  - Time-based reminders ("remind me at 3pm")
  - Date-based reminders ("do this tomorrow")
  - Recurring reminders ("every Monday")
  - Goal tracking reminders
  - Proactive check-ins

Integrates with existing Telegram service.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta, time
from typing import List, Optional, Dict
from sqlalchemy import select, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from atlas.db.brain_models import (
    BrainMemory, BrainNote, BrainEntity, BrainContext,
    MemoryType, MemoryRegion
)
from atlas.services.telegram_service import send_telegram_message
from atlas.db.session import get_session

logger = logging.getLogger(__name__)


# Temporal patterns
TIME_PATTERNS = [
    r'(?:remind me|remind|don\'t forget)\s+(?:to\s+)?(.+?)\s+(?:at|by)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)',
    r'(?:remind me|remind|don\'t forget)\s+(?:to\s+)?(.+?)\s+(?:in|after)\s+(\d+)\s+(minutes?|hours?|days?)',
]

DATE_PATTERNS = [
    r'(?:do|remember|finish)\s+(.+?)\s+(?:tomorrow|today|tonight)',
    r'(?:this|next)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
]

GOAL_PATTERNS = [
    r'(?:i want|i need|i should|i plan to|i\'m going to)\s+(.+?)(?:\.|$)',
    r'(?:goal|target|objective)(?:\s+is|:)\s+(.+?)(?:\.|$)',
]


class BrainReminder:
    """Reminder system for temporal memories."""
    
    def __init__(self, chat_id: str = None):
        self.chat_id = chat_id
        self._running = False
        self._check_interval = 60  # Check every minute
    
    async def start(self):
        """Start reminder checking loop."""
        if self._running:
            logger.warning("Reminder system already running")
            return
        
        self._running = True
        logger.info("Starting brain reminder system")
        
        while self._running:
            try:
                await self._check_reminders()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reminder check error: {e}")
                await asyncio.sleep(60)
    
    async def stop(self):
        """Stop reminder checking loop."""
        self._running = False
        logger.info("Stopping brain reminder system")
    
    async def _check_reminders(self):
        """Check for due reminders and send them."""
        async with get_session() as session:
            now = datetime.utcnow()
            
            # Get temporal memories from hippocampus
            result = await session.execute(
                select(BrainMemory)
                .where(BrainMemory.memory_region == MemoryRegion.HIPPOCAMPUS.value)
                .where(BrainMemory.source_type == "chat")
                .order_by(BrainMemory.created_at.desc())
                .limit(100)
            )
            memories = result.scalars().all()
            
            reminders_sent = 0
            
            for memory in memories:
                # Extract temporal information
                reminder = self._extract_reminder(memory.content, memory.created_at)
                
                if reminder and self._is_reminder_due(reminder, now):
                    # Send reminder
                    await self._send_reminder(memory, reminder)
                    reminders_sent += 1
                    
                    # Mark as reminded
                    await session.execute(
                        update(BrainMemory)
                        .where(BrainMemory.id == memory.id)
                        .values(
                            metadata={**memory.metadata, "reminded": True, "reminded_at": now.isoformat()}
                        )
                    )
            
            if reminders_sent > 0:
                await session.commit()
                logger.info(f"Sent {reminders_sent} reminders")
    
    def _extract_reminder(self, content: str, created_at: datetime) -> Optional[Dict]:
        """Extract reminder information from memory content."""
        content_lower = content.lower()
        
        # Check for time-based reminders
        for pattern in TIME_PATTERNS:
            match = re.search(pattern, content_lower)
            if match:
                task = match.group(1).strip()
                time_str = match.group(2).strip()
                
                # Parse time
                reminder_time = self._parse_time(time_str, created_at)
                if reminder_time:
                    return {
                        "type": "time",
                        "task": task,
                        "reminder_time": reminder_time,
                        "original_content": content
                    }
        
        # Check for date-based reminders
        for pattern in DATE_PATTERNS:
            match = re.search(pattern, content_lower)
            if match:
                task = match.group(1).strip()
                date_str = match.group(2).strip()
                
                # Parse date
                reminder_time = self._parse_date(date_str, created_at)
                if reminder_time:
                    return {
                        "type": "date",
                        "task": task,
                        "reminder_time": reminder_time,
                        "original_content": content
                    }
        
        return None
    
    def _parse_time(self, time_str: str, created_at: datetime) -> Optional[datetime]:
        """Parse time string and return datetime."""
        try:
            # Simple time parsing (can be enhanced with dateparser)
            if "am" in time_str or "pm" in time_str:
                parts = time_str.replace("am", "").replace("pm", "").strip().split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
                
                if "pm" in time_str and hour != 12:
                    hour += 12
                elif "am" in time_str and hour == 12:
                    hour = 0
                
                reminder_time = created_at.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # If time is earlier than now, assume tomorrow
                if reminder_time < created_at:
                    reminder_time += timedelta(days=1)
                
                return reminder_time
        except Exception as e:
            logger.debug(f"Failed to parse time '{time_str}': {e}")
        
        return None
    
    def _parse_date(self, date_str: str, created_at: datetime) -> Optional[datetime]:
        """Parse date string and return datetime."""
        try:
            date_str = date_str.lower().strip()
            
            if date_str == "tomorrow":
                return created_at + timedelta(days=1)
            elif date_str == "today":
                return created_at.replace(hour=9, minute=0, second=0, microsecond=0)
            elif date_str == "tonight":
                return created_at.replace(hour=20, minute=0, second=0, microsecond=0)
            elif date_str in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                # Find next occurrence of this day
                target_day = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].index(date_str)
                current_day = created_at.weekday()
                
                days_until = (target_day - current_day) % 7
                if days_until == 0:
                    days_until = 7  # Next week
                
                return created_at + timedelta(days=days_until)
        except Exception as e:
            logger.debug(f"Failed to parse date '{date_str}': {e}")
        
        return None
    
    def _is_reminder_due(self, reminder: Dict, now: datetime) -> bool:
        """Check if reminder is due."""
        reminder_time = reminder.get("reminder_time")
        
        if not reminder_time:
            return False
        
        # Check if we're within 1 minute of reminder time
        time_diff = abs((now - reminder_time).total_seconds())
        
        return time_diff < 60  # Within 1 minute
    
    async def _send_reminder(self, memory: BrainMemory, reminder: Dict):
        """Send reminder via Telegram."""
        task = reminder.get("task", memory.content)
        reminder_time = reminder.get("reminder_time")
        
        message = f"⏰ **Reminder**\n\n"
        message += f"You wanted to: {task}\n"
        
        if reminder_time:
            message += f"Scheduled for: {reminder_time.strftime('%Y-%m-%d %H:%M')}\n"
        
        message += f"\nOriginal: {memory.content}"
        
        if self.chat_id:
            await send_telegram_message(self.chat_id, message)
            logger.info(f"Sent reminder: {task}")
        else:
            logger.warning(f"No chat_id configured, would send: {message}")


class ProactiveChecker:
    """Proactive checking and questioning system."""
    
    def __init__(self, chat_id: str = None):
        self.chat_id = chat_id
        self._running = False
        self._check_interval = 3600  # Check every hour
    
    async def start(self):
        """Start proactive checking loop."""
        if self._running:
            logger.warning("Proactive checker already running")
            return
        
        self._running = True
        logger.info("Starting proactive checker")
        
        while self._running:
            try:
                await self._proactive_check()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Proactive check error: {e}")
                await asyncio.sleep(300)
    
    async def stop(self):
        """Stop proactive checking loop."""
        self._running = False
        logger.info("Stopping proactive checker")
    
    async def _proactive_check(self):
        """Run proactive check and send question if appropriate."""
        # Randomly decide to ask a question (10% chance each hour)
        import random
        if random.random() > 0.1:
            return
        
        # Choose a question type
        question_type = random.choice([
            "activity",
            "goal_progress",
            "learning",
            "gap_filling"
        ])
        
        question = self._generate_question(question_type)
        
        if question and self.chat_id:
            await send_telegram_message(self.chat_id, question)
            logger.info(f"Sent proactive question: {question_type}")
    
    def _generate_question(self, question_type: str) -> str:
        """Generate a proactive question."""
        questions = {
            "activity": [
                "Hey! What are you working on right now?",
                "How's your day going? Anything interesting happening?",
                "What have you been up to lately?",
            ],
            "goal_progress": [
                "Remember any goals you wanted to work on? How's progress?",
                "Any tasks you've been meaning to tackle?",
                "Want me to help you review your current priorities?",
            ],
            "learning": [
                "Learned anything new recently? Want to save it?",
                "Interested in exploring any new topics?",
                "Found any good resources worth remembering?",
            ],
            "gap_filling": [
                "I noticed I'm missing some info about [topic]. Can you fill me in?",
                "Want to tell me more about [recent activity]?",
                "Any details about [topic] you want me to remember?",
            ],
        }
        
        options = questions.get(question_type, [])
        return random.choice(options) if options else None


# Global instances
brain_reminder = BrainReminder()
proactive_checker = ProactiveChecker()
