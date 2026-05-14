"""Habit tracker API endpoints."""
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from atlas.db.session import get_session
from atlas.services import habit_service

router = APIRouter(prefix="/habits", tags=["habits"])


# ======== Schemas ========

class HabitCreate(BaseModel):
    name: str
    description: str = ""
    specific: str = ""  # SMART: What exactly will you do?
    measurable: str = ""  # SMART: How will you measure success?
    achievable: str = ""  # SMART: Is this realistic?
    relevant: str = ""  # SMART: Why does this matter?
    time_bound: str = ""  # SMART: When will you achieve this?
    target_date: Optional[date] = None
    frequency: str = "daily"  # daily, weekly, monthly
    target_days_per_week: int = 7
    category: str = "general"  # physical, education, financial, health, career
    reminder_time: Optional[str] = None  # HH:MM
    color: str = "#4CAF50"
    icon: str = "check"


class HabitUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    specific: Optional[str] = None
    measurable: Optional[str] = None
    achievable: Optional[str] = None
    relevant: Optional[str] = None
    time_bound: Optional[str] = None
    target_date: Optional[date] = None
    frequency: Optional[str] = None
    target_days_per_week: Optional[int] = None
    category: Optional[str] = None
    reminder_time: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None


class HabitLogCreate(BaseModel):
    log_date: date
    completed: bool = True
    value: Optional[float] = None
    notes: str = ""
    mood: Optional[int] = Field(None, ge=1, le=5)


class HabitLogUpdate(BaseModel):
    completed: Optional[bool] = None
    value: Optional[float] = None
    notes: Optional[str] = None
    mood: Optional[int] = Field(None, ge=1, le=5)


class HabitResponse(BaseModel):
    id: str
    name: str
    description: str
    specific: str
    measurable: str
    achievable: str
    relevant: str
    time_bound: str
    target_date: Optional[date]
    frequency: str
    target_days_per_week: int
    category: str
    reminder_time: Optional[str]
    color: str
    icon: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class HabitWithProgress(BaseModel):
    habit: HabitResponse
    completed_today: bool
    today_value: Optional[float]
    today_notes: str
    week_progress: str
    week_completed: int


# ======== Endpoints ========

@router.post("", response_model=HabitResponse)
async def create_habit(habit: HabitCreate, user_id: str = Query(default="default")):
    """Create a new habit with SMART goal fields."""
    async with get_session() as session:
        result = await habit_service.create_habit(
            session,
            user_id=user_id,
            name=habit.name,
            description=habit.description,
            specific=habit.specific,
            measurable=habit.measurable,
            achievable=habit.achievable,
            relevant=habit.relevant,
            time_bound=habit.time_bound,
            target_date=habit.target_date,
            frequency=habit.frequency,
            target_days_per_week=habit.target_days_per_week,
            category=habit.category,
            reminder_time=habit.reminder_time,
            color=habit.color,
            icon=habit.icon,
        )
        return result


@router.get("", response_model=list[HabitResponse])
async def list_habits(
    user_id: str = Query(default="default"),
    category: Optional[str] = None,
    is_active: Optional[bool] = True,
):
    """List habits with optional filtering."""
    async with get_session() as session:
        habits = await habit_service.list_habits(session, user_id, category, is_active)
        return habits


@router.get("/today", response_model=list[HabitWithProgress])
async def get_today_habits(user_id: str = Query(default="default")):
    """Get all habits for today with completion status."""
    async with get_session() as session:
        return await habit_service.get_today_habits(session, user_id)


@router.get("/{habit_id}", response_model=HabitResponse)
async def get_habit(habit_id: str, user_id: str = Query(default="default")):
    """Get a habit by ID."""
    async with get_session() as session:
        habit = await habit_service.get_habit(session, habit_id, user_id)
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found")
        return habit


@router.patch("/{habit_id}", response_model=HabitResponse)
async def update_habit(
    habit_id: str,
    updates: HabitUpdate,
    user_id: str = Query(default="default"),
):
    """Update a habit."""
    async with get_session() as session:
        habit = await habit_service.update_habit(session, habit_id, user_id, **updates.model_dump(exclude_unset=True))
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found")
        return habit


@router.delete("/{habit_id}")
async def delete_habit(habit_id: str, user_id: str = Query(default="default")):
    """Archive (soft delete) a habit."""
    async with get_session() as session:
        success = await habit_service.delete_habit(session, habit_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Habit not found")
        return {"message": "Habit archived successfully"}


@router.post("/{habit_id}/log")
async def log_habit(
    habit_id: str,
    log: HabitLogCreate,
    user_id: str = Query(default="default"),
):
    """Log a habit completion for a specific date."""
    async with get_session() as session:
        # Verify habit exists
        habit = await habit_service.get_habit(session, habit_id, user_id)
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found")
        
        result = await habit_service.log_habit(
            session,
            habit_id=habit_id,
            user_id=user_id,
            log_date=log.log_date,
            completed=log.completed,
            value=log.value,
            notes=log.notes,
            mood=log.mood,
        )
        return {
            "id": result.id,
            "habit_id": result.habit_id,
            "log_date": result.log_date,
            "completed": result.completed,
            "value": result.value,
            "notes": result.notes,
            "mood": result.mood,
        }


@router.get("/{habit_id}/logs")
async def get_habit_logs(
    habit_id: str,
    user_id: str = Query(default="default"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """Get habit logs for a date range."""
    async with get_session() as session:
        logs = await habit_service.get_habit_logs(session, habit_id, user_id, start_date, end_date)
        return [
            {
                "id": log.id,
                "log_date": log.log_date,
                "completed": log.completed,
                "value": log.value,
                "notes": log.notes,
                "mood": log.mood,
            }
            for log in logs
        ]


@router.get("/{habit_id}/stats")
async def get_habit_stats(
    habit_id: str,
    user_id: str = Query(default="default"),
    days: int = Query(default=30, ge=1, le=365),
):
    """Get habit completion statistics."""
    async with get_session() as session:
        stats = await habit_service.get_habit_stats(session, habit_id, user_id, days)
        return stats


@router.get("/categories/list")
async def get_habit_categories():
    """Get list of available habit categories."""
    return {
        "categories": [
            {"id": "physical", "name": "Physical Fitness", "icon": "dumbbell", "color": "#F44336"},
            {"id": "education", "name": "Education & Learning", "icon": "book", "color": "#2196F3"},
            {"id": "financial", "name": "Financial", "icon": "dollar-sign", "color": "#4CAF50"},
            {"id": "health", "name": "Health & Wellness", "icon": "heart", "color": "#E91E63"},
            {"id": "career", "name": "Career & Professional", "icon": "briefcase", "color": "#9C27B0"},
            {"id": "personal", "name": "Personal Development", "icon": "user", "color": "#FF9800"},
            {"id": "general", "name": "General", "icon": "check", "color": "#607D8B"},
        ]
    }
