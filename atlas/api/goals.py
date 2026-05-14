"""Goals, plans, and todos API endpoints."""
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from atlas.db.session import get_session
from atlas.services import goal_service

router = APIRouter(prefix="/goals", tags=["goals"])


# ======== Schemas ========

class GoalCreate(BaseModel):
    title: str
    description: str = ""
    category: str  # physical, education, financial, career, personal, health
    timeframe: str = "short_term"  # short_term, long_term
    priority: int = Field(default=2, ge=1, le=3)
    specific: str = ""  # SMART
    measurable: str = ""  # SMART
    achievable: str = ""  # SMART
    relevant: str = ""  # SMART
    time_bound: str = ""  # SMART
    start_date: Optional[date] = None
    target_date: Optional[date] = None
    current_value: Optional[float] = None
    target_value: Optional[float] = None
    unit: Optional[str] = None  # kg, km, hours, dollars, etc.
    estimated_cost: Optional[float] = None
    color: str = "#9C27B0"
    icon: str = "target"
    parent_goal_id: Optional[str] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    timeframe: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=3)
    specific: Optional[str] = None
    measurable: Optional[str] = None
    achievable: Optional[str] = None
    relevant: Optional[str] = None
    time_bound: Optional[str] = None
    start_date: Optional[date] = None
    target_date: Optional[date] = None
    status: Optional[str] = None  # not_started, in_progress, on_hold, completed, abandoned
    current_value: Optional[float] = None
    target_value: Optional[float] = None
    unit: Optional[str] = None
    estimated_cost: Optional[float] = None
    saved_amount: Optional[float] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    parent_goal_id: Optional[str] = None
    linked_habit_ids: Optional[list] = None


class GoalProgressUpdate(BaseModel):
    current_value: float
    notes: str = ""


class GoalSavingsAdd(BaseModel):
    amount: float = Field(gt=0)


class GoalResponse(BaseModel):
    id: str
    title: str
    description: str
    category: str
    timeframe: str
    priority: int
    specific: str
    measurable: str
    achievable: str
    relevant: str
    time_bound: str
    start_date: Optional[date]
    target_date: Optional[date]
    completed_date: Optional[date]
    status: str
    progress_percent: float
    current_value: Optional[float]
    target_value: Optional[float]
    unit: Optional[str]
    estimated_cost: Optional[float]
    saved_amount: float
    color: str
    icon: str
    parent_goal_id: Optional[str]
    linked_habit_ids: list
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PlanCreate(BaseModel):
    title: str
    description: str = ""
    plan_type: str = "general"  # weekly, monthly, project, goal_based
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    linked_goal_ids: list[str] = []
    linked_habit_ids: list[str] = []


class PlanUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    plan_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None  # draft, active, completed, archived
    linked_goal_ids: Optional[list] = None
    linked_habit_ids: Optional[list] = None


class PlanResponse(BaseModel):
    id: str
    title: str
    description: str
    plan_type: str
    start_date: Optional[date]
    end_date: Optional[date]
    status: str
    progress_percent: float
    linked_goal_ids: list
    linked_habit_ids: list
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TodoCreate(BaseModel):
    title: str
    description: str = ""
    plan_id: Optional[str] = None
    category: str = "general"
    priority: int = Field(default=2, ge=1, le=3)
    due_date: Optional[date] = None
    due_time: Optional[str] = None  # HH:MM
    estimated_minutes: Optional[int] = None
    linked_goal_id: Optional[str] = None
    linked_habit_id: Optional[str] = None
    sort_order: int = 0


class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    plan_id: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=3)
    due_date: Optional[date] = None
    due_time: Optional[str] = None
    estimated_minutes: Optional[int] = None
    status: Optional[str] = None  # pending, in_progress, completed, cancelled
    linked_goal_id: Optional[str] = None
    linked_habit_id: Optional[str] = None
    sort_order: Optional[int] = None


class TodoResponse(BaseModel):
    id: str
    title: str
    description: str
    plan_id: Optional[str]
    category: str
    priority: int
    due_date: Optional[date]
    due_time: Optional[str]
    estimated_minutes: Optional[int]
    status: str
    completed_at: Optional[datetime]
    linked_goal_id: Optional[str]
    linked_habit_id: Optional[str]
    sort_order: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ======== GOAL Endpoints ========

@router.post("", response_model=GoalResponse)
async def create_goal(goal: GoalCreate, user_id: str = Query(default="default")):
    """Create a new SMART goal."""
    async with get_session() as session:
        result = await goal_service.create_goal(
            session,
            user_id=user_id,
            title=goal.title,
            description=goal.description,
            category=goal.category,
            timeframe=goal.timeframe,
            priority=goal.priority,
            specific=goal.specific,
            measurable=goal.measurable,
            achievable=goal.achievable,
            relevant=goal.relevant,
            time_bound=goal.time_bound,
            start_date=goal.start_date,
            target_date=goal.target_date,
            current_value=goal.current_value,
            target_value=goal.target_value,
            unit=goal.unit,
            estimated_cost=goal.estimated_cost,
            color=goal.color,
            icon=goal.icon,
            parent_goal_id=goal.parent_goal_id,
        )
        return result


@router.get("", response_model=list[GoalResponse])
async def list_goals(
    user_id: str = Query(default="default"),
    category: Optional[str] = None,
    timeframe: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[int] = None,
):
    """List goals with filtering."""
    async with get_session() as session:
        goals = await goal_service.list_goals(session, user_id, category, timeframe, status, priority)
        return goals


@router.get("/summary")
async def get_goal_summary(user_id: str = Query(default="default")):
    """Get summary of goals by category."""
    async with get_session() as session:
        return await goal_service.get_goal_summary(session, user_id)


@router.get("/categories")
async def get_goal_categories():
    """Get available goal categories with descriptions."""
    return {
        "categories": [
            {"id": "physical", "name": "Physical Fitness", "icon": "dumbbell", "color": "#F44336", "examples": ["Lose 10kg", "Run 5km", "Build muscle"]},
            {"id": "education", "name": "Education & Learning", "icon": "book", "color": "#2196F3", "examples": ["Learn Python", "Get certification", "Read 24 books"]},
            {"id": "financial", "name": "Financial", "icon": "dollar-sign", "color": "#4CAF50", "examples": ["Save $10,000", "Pay off debt", "Build emergency fund"]},
            {"id": "career", "name": "Career & Professional", "icon": "briefcase", "color": "#9C27B0", "examples": ["Get promotion", "Learn new skill", "Network events"]},
            {"id": "personal", "name": "Personal Development", "icon": "user", "color": "#FF9800", "examples": ["Meditate daily", "Journal", "Wake up early"]},
            {"id": "health", "name": "Health & Wellness", "icon": "heart", "color": "#E91E63", "examples": ["Sleep 8 hours", "Drink water", "Regular checkups"]},
        ]
    }


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(goal_id: str, user_id: str = Query(default="default")):
    """Get a goal by ID."""
    async with get_session() as session:
        goal = await goal_service.get_goal(session, goal_id, user_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        return goal


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: str,
    updates: GoalUpdate,
    user_id: str = Query(default="default"),
):
    """Update a goal."""
    async with get_session() as session:
        goal = await goal_service.update_goal(
            session, goal_id, user_id, **updates.model_dump(exclude_unset=True)
        )
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        return goal


@router.post("/{goal_id}/progress")
async def update_goal_progress(
    goal_id: str,
    progress: GoalProgressUpdate,
    user_id: str = Query(default="default"),
):
    """Update goal progress (current_value)."""
    async with get_session() as session:
        goal = await goal_service.update_goal_progress(session, goal_id, user_id, progress.current_value)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        return {
            "id": goal.id,
            "current_value": goal.current_value,
            "progress_percent": goal.progress_percent,
            "status": goal.status,
            "completed_date": goal.completed_date,
        }


@router.post("/{goal_id}/add-savings")
async def add_goal_savings(
    goal_id: str,
    savings: GoalSavingsAdd,
    user_id: str = Query(default="default"),
):
    """Add savings toward a financial goal."""
    async with get_session() as session:
        goal = await goal_service.add_goal_savings(session, goal_id, user_id, savings.amount)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        return {
            "id": goal.id,
            "saved_amount": goal.saved_amount,
            "estimated_cost": goal.estimated_cost,
            "progress_percent": goal.progress_percent,
            "status": goal.status,
        }


@router.delete("/{goal_id}")
async def delete_goal(goal_id: str, user_id: str = Query(default="default")):
    """Delete a goal."""
    async with get_session() as session:
        success = await goal_service.delete_goal(session, goal_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Goal not found")
        return {"message": "Goal deleted successfully"}


# ======== PLAN Endpoints ========

@router.post("/plans", response_model=PlanResponse)
async def create_plan(plan: PlanCreate, user_id: str = Query(default="default")):
    """Create a new plan."""
    async with get_session() as session:
        result = await goal_service.create_plan(
            session,
            user_id=user_id,
            title=plan.title,
            description=plan.description,
            plan_type=plan.plan_type,
            start_date=plan.start_date,
            end_date=plan.end_date,
            linked_goal_ids=plan.linked_goal_ids,
            linked_habit_ids=plan.linked_habit_ids,
        )
        return result


@router.get("/plans/list", response_model=list[PlanResponse])
async def list_plans(
    user_id: str = Query(default="default"),
    plan_type: Optional[str] = None,
    status: Optional[str] = None,
    linked_goal_id: Optional[str] = None,
):
    """List plans with filtering."""
    async with get_session() as session:
        plans = await goal_service.list_plans(session, user_id, plan_type, status, linked_goal_id)
        return plans


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str, user_id: str = Query(default="default")):
    """Get a plan by ID."""
    async with get_session() as session:
        plan = await goal_service.get_plan(session, plan_id, user_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        return plan


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: str,
    updates: PlanUpdate,
    user_id: str = Query(default="default"),
):
    """Update a plan."""
    async with get_session() as session:
        plan = await goal_service.update_plan(
            session, plan_id, user_id, **updates.model_dump(exclude_unset=True)
        )
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        return plan


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: str, user_id: str = Query(default="default")):
    """Delete a plan and its associated todos."""
    async with get_session() as session:
        success = await goal_service.delete_plan(session, plan_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Plan not found")
        return {"message": "Plan deleted successfully"}


# ======== TODO Endpoints ========

@router.post("/todos", response_model=TodoResponse)
async def create_todo(todo: TodoCreate, user_id: str = Query(default="default")):
    """Create a new todo."""
    async with get_session() as session:
        result = await goal_service.create_todo(
            session,
            user_id=user_id,
            title=todo.title,
            description=todo.description,
            plan_id=todo.plan_id,
            category=todo.category,
            priority=todo.priority,
            due_date=todo.due_date,
            due_time=todo.due_time,
            estimated_minutes=todo.estimated_minutes,
            linked_goal_id=todo.linked_goal_id,
            linked_habit_id=todo.linked_habit_id,
            sort_order=todo.sort_order,
        )
        return result


@router.get("/todos/list", response_model=list[TodoResponse])
async def list_todos(
    user_id: str = Query(default="default"),
    plan_id: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    due_date: Optional[date] = None,
):
    """List todos with filtering."""
    async with get_session() as session:
        todos = await goal_service.list_todos(session, user_id, plan_id, status, category, due_date)
        return todos


@router.get("/todos/today")
async def get_todos_for_today(user_id: str = Query(default="default")):
    """Get todos due today or overdue."""
    async with get_session() as session:
        todos = await goal_service.list_todos_for_today(session, user_id)
        return todos


@router.get("/todos/stats")
async def get_todo_stats(user_id: str = Query(default="default")):
    """Get todo statistics."""
    async with get_session() as session:
        return await goal_service.get_todo_stats(session, user_id)


@router.get("/todos/{todo_id}", response_model=TodoResponse)
async def get_todo(todo_id: str, user_id: str = Query(default="default")):
    """Get a todo by ID."""
    async with get_session() as session:
        todo = await goal_service.get_todo(session, todo_id, user_id)
        if not todo:
            raise HTTPException(status_code=404, detail="Todo not found")
        return todo


@router.patch("/todos/{todo_id}", response_model=TodoResponse)
async def update_todo(
    todo_id: str,
    updates: TodoUpdate,
    user_id: str = Query(default="default"),
):
    """Update a todo."""
    async with get_session() as session:
        todo = await goal_service.update_todo(
            session, todo_id, user_id, **updates.model_dump(exclude_unset=True)
        )
        if not todo:
            raise HTTPException(status_code=404, detail="Todo not found")
        return todo


@router.post("/todos/{todo_id}/complete", response_model=TodoResponse)
async def complete_todo(todo_id: str, user_id: str = Query(default="default")):
    """Mark a todo as completed."""
    async with get_session() as session:
        todo = await goal_service.complete_todo(session, todo_id, user_id)
        if not todo:
            raise HTTPException(status_code=404, detail="Todo not found")
        return todo


@router.delete("/todos/{todo_id}")
async def delete_todo(todo_id: str, user_id: str = Query(default="default")):
    """Delete a todo."""
    async with get_session() as session:
        success = await goal_service.delete_todo(session, todo_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Todo not found")
        return {"message": "Todo deleted successfully"}
