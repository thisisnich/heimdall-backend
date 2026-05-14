"""Habit tracker service with SMART goals support."""
from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from atlas.db.models import Habit, HabitLog


async def create_habit(
    session: AsyncSession,
    user_id: str,
    name: str,
    description: str = "",
    specific: str = "",
    measurable: str = "",
    achievable: str = "",
    relevant: str = "",
    time_bound: str = "",
    target_date: Optional[date] = None,
    frequency: str = "daily",
    target_days_per_week: int = 7,
    category: str = "general",
    reminder_time: Optional[str] = None,
    color: str = "#4CAF50",
    icon: str = "check",
) -> Habit:
    """Create a new habit with SMART goal fields."""
    habit = Habit(
        user_id=user_id,
        name=name,
        description=description,
        specific=specific,
        measurable=measurable,
        achievable=achievable,
        relevant=relevant,
        time_bound=time_bound,
        target_date=target_date,
        frequency=frequency,
        target_days_per_week=target_days_per_week,
        category=category,
        reminder_time=reminder_time,
        color=color,
        icon=icon,
    )
    session.add(habit)
    await session.commit()
    await session.refresh(habit)
    return habit


async def get_habit(session: AsyncSession, habit_id: str, user_id: str) -> Optional[Habit]:
    """Get a habit by ID for a specific user."""
    result = await session.execute(
        select(Habit).where(and_(Habit.id == habit_id, Habit.user_id == user_id))
    )
    return result.scalar_one_or_none()


async def list_habits(
    session: AsyncSession,
    user_id: str,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> list[Habit]:
    """List habits with optional filtering."""
    query = select(Habit).where(Habit.user_id == user_id)
    if category:
        query = query.where(Habit.category == category)
    if is_active is not None:
        query = query.where(Habit.is_active == is_active)
    query = query.order_by(Habit.created_at.desc())
    result = await session.execute(query)
    return result.scalars().all()


async def update_habit(session: AsyncSession, habit_id: str, user_id: str, **updates) -> Optional[Habit]:
    """Update a habit."""
    habit = await get_habit(session, habit_id, user_id)
    if not habit:
        return None
    for key, value in updates.items():
        if hasattr(habit, key):
            setattr(habit, key, value)
    await session.commit()
    await session.refresh(habit)
    return habit


async def delete_habit(session: AsyncSession, habit_id: str, user_id: str) -> bool:
    """Soft delete (archive) a habit."""
    habit = await get_habit(session, habit_id, user_id)
    if not habit:
        return False
    habit.is_active = False
    habit.archived_at = datetime.utcnow()
    await session.commit()
    return True


async def log_habit(
    session: AsyncSession,
    habit_id: str,
    user_id: str,
    log_date: date,
    completed: bool = True,
    value: Optional[float] = None,
    notes: str = "",
    mood: Optional[int] = None,
) -> HabitLog:
    """Log a habit completion for a specific date."""
    # Check if log already exists for this date
    existing = await session.execute(
        select(HabitLog).where(
            and_(
                HabitLog.habit_id == habit_id,
                HabitLog.user_id == user_id,
                HabitLog.log_date == log_date,
            )
        )
    )
    existing_log = existing.scalar_one_or_none()
    
    if existing_log:
        existing_log.completed = completed
        existing_log.value = value
        existing_log.notes = notes
        existing_log.mood = mood
        await session.commit()
        await session.refresh(existing_log)
        return existing_log
    
    log = HabitLog(
        habit_id=habit_id,
        user_id=user_id,
        log_date=log_date,
        completed=completed,
        value=value,
        notes=notes,
        mood=mood,
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log


async def get_habit_logs(
    session: AsyncSession,
    habit_id: str,
    user_id: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[HabitLog]:
    """Get habit logs for a date range."""
    query = select(HabitLog).where(
        and_(HabitLog.habit_id == habit_id, HabitLog.user_id == user_id)
    )
    if start_date:
        query = query.where(HabitLog.log_date >= start_date)
    if end_date:
        query = query.where(HabitLog.log_date <= end_date)
    query = query.order_by(HabitLog.log_date.desc())
    result = await session.execute(query)
    return result.scalars().all()


async def get_habit_stats(
    session: AsyncSession,
    habit_id: str,
    user_id: str,
    days: int = 30,
) -> dict:
    """Get habit completion statistics."""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    logs = await get_habit_logs(session, habit_id, user_id, start_date, end_date)
    completed_count = sum(1 for log in logs if log.completed)
    
    # Get current streak
    streak = 0
    check_date = end_date
    while True:
        day_log = next((l for l in logs if l.log_date == check_date), None)
        if day_log and day_log.completed:
            streak += 1
            check_date -= timedelta(days=1)
        elif check_date == end_date:
            # No log for today yet, check yesterday
            check_date -= timedelta(days=1)
        else:
            break
    
    # Get longest streak in period
    longest_streak = 0
    current_streak = 0
    sorted_logs = sorted(logs, key=lambda l: l.log_date)
    
    for i, log in enumerate(sorted_logs):
        if log.completed:
            if i == 0 or (log.log_date - sorted_logs[i-1].log_date).days == 1:
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
            else:
                current_streak = 1
        else:
            current_streak = 0
    
    return {
        "total_days": days,
        "completed_days": completed_count,
        "completion_rate": round(completed_count / days * 100, 1) if days > 0 else 0,
        "current_streak": streak,
        "longest_streak": longest_streak,
        "total_logs": len(logs),
    }


async def get_today_habits(session: AsyncSession, user_id: str) -> list[dict]:
    """Get all habits for today with completion status."""
    habits = await list_habits(session, user_id, is_active=True)
    today = date.today()
    
    result = []
    for habit in habits:
        # Check if already logged today
        log_result = await session.execute(
            select(HabitLog).where(
                and_(
                    HabitLog.habit_id == habit.id,
                    HabitLog.user_id == user_id,
                    HabitLog.log_date == today,
                )
            )
        )
        today_log = log_result.scalar_one_or_none()
        
        # Get weekly progress
        week_start = today - timedelta(days=today.weekday())
        week_logs = await get_habit_logs(session, habit.id, user_id, week_start, today)
        week_completed = sum(1 for log in week_logs if log.completed)
        
        result.append({
            "habit": habit,
            "completed_today": today_log.completed if today_log else False,
            "today_value": today_log.value if today_log else None,
            "today_notes": today_log.notes if today_log else "",
            "week_progress": f"{week_completed}/{habit.target_days_per_week}",
            "week_completed": week_completed,
        })
    
    return result
