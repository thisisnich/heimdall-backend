"""Goals, plans, and todos service with SMART goal support."""
from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from atlas.db.models import Goal, Plan, Todo


# ==================== GOALS ====================

async def create_goal(
    session: AsyncSession,
    user_id: str,
    title: str,
    description: str = "",
    category: str = "personal",  # physical, education, financial, career, personal, health
    timeframe: str = "short_term",  # short_term, long_term
    priority: int = 2,
    specific: str = "",
    measurable: str = "",
    achievable: str = "",
    relevant: str = "",
    time_bound: str = "",
    start_date: Optional[date] = None,
    target_date: Optional[date] = None,
    current_value: Optional[float] = None,
    target_value: Optional[float] = None,
    unit: Optional[str] = None,
    estimated_cost: Optional[float] = None,
    color: str = "#9C27B0",
    icon: str = "target",
    parent_goal_id: Optional[str] = None,
) -> Goal:
    """Create a new SMART goal."""
    goal = Goal(
        user_id=user_id,
        title=title,
        description=description,
        category=category,
        timeframe=timeframe,
        priority=priority,
        specific=specific,
        measurable=measurable,
        achievable=achievable,
        relevant=relevant,
        time_bound=time_bound,
        start_date=start_date,
        target_date=target_date,
        current_value=current_value,
        target_value=target_value,
        unit=unit,
        estimated_cost=estimated_cost,
        color=color,
        icon=icon,
        parent_goal_id=parent_goal_id,
    )
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    return goal


async def get_goal(session: AsyncSession, goal_id: str, user_id: str) -> Optional[Goal]:
    """Get a goal by ID."""
    result = await session.execute(
        select(Goal).where(and_(Goal.id == goal_id, Goal.user_id == user_id))
    )
    return result.scalar_one_or_none()


async def list_goals(
    session: AsyncSession,
    user_id: str,
    category: Optional[str] = None,
    timeframe: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[int] = None,
) -> list[Goal]:
    """List goals with filtering."""
    query = select(Goal).where(Goal.user_id == user_id)
    if category:
        query = query.where(Goal.category == category)
    if timeframe:
        query = query.where(Goal.timeframe == timeframe)
    if status:
        query = query.where(Goal.status == status)
    if priority:
        query = query.where(Goal.priority == priority)
    query = query.order_by(Goal.priority, Goal.target_date)
    result = await session.execute(query)
    return result.scalars().all()


async def update_goal(session: AsyncSession, goal_id: str, user_id: str, **updates) -> Optional[Goal]:
    """Update a goal."""
    goal = await get_goal(session, goal_id, user_id)
    if not goal:
        return None
    for key, value in updates.items():
        if hasattr(goal, key):
            setattr(goal, key, value)
    
    # Recalculate progress percentage if values changed
    if goal.target_value and goal.current_value is not None:
        goal.progress_percent = min(100, round(goal.current_value / goal.target_value * 100, 1))
    
    await session.commit()
    await session.refresh(goal)
    return goal


async def update_goal_progress(
    session: AsyncSession,
    goal_id: str,
    user_id: str,
    current_value: float,
    notes: str = "",
) -> Optional[Goal]:
    """Update goal progress and check for completion."""
    goal = await get_goal(session, goal_id, user_id)
    if not goal:
        return None
    
    goal.current_value = current_value
    if goal.target_value:
        goal.progress_percent = min(100, round(current_value / goal.target_value * 100, 1))
        if goal.progress_percent >= 100:
            goal.status = "completed"
            goal.completed_date = date.today()
    
    await session.commit()
    await session.refresh(goal)
    return goal


async def add_goal_savings(session: AsyncSession, goal_id: str, user_id: str, amount: float) -> Optional[Goal]:
    """Add savings toward a financial goal."""
    goal = await get_goal(session, goal_id, user_id)
    if not goal:
        return None
    
    goal.saved_amount = (goal.saved_amount or 0) + amount
    if goal.estimated_cost:
        goal.progress_percent = min(100, round(goal.saved_amount / goal.estimated_cost * 100, 1))
        if goal.progress_percent >= 100:
            goal.status = "completed"
            goal.completed_date = date.today()
    
    await session.commit()
    await session.refresh(goal)
    return goal


async def delete_goal(session: AsyncSession, goal_id: str, user_id: str) -> bool:
    """Delete a goal."""
    goal = await get_goal(session, goal_id, user_id)
    if not goal:
        return False
    await session.delete(goal)
    await session.commit()
    return True


async def get_goal_summary(session: AsyncSession, user_id: str) -> dict:
    """Get summary of goals by category."""
    goals = await list_goals(session, user_id)
    
    summary = {
        "total": len(goals),
        "by_category": {},
        "by_status": {},
        "by_timeframe": {},
    }
    
    categories = ["physical", "education", "financial", "career", "personal", "health"]
    for cat in categories:
        cat_goals = [g for g in goals if g.category == cat]
        if cat_goals:
            completed = len([g for g in cat_goals if g.status == "completed"])
            summary["by_category"][cat] = {
                "total": len(cat_goals),
                "completed": completed,
                "in_progress": len([g for g in cat_goals if g.status == "in_progress"]),
                "avg_progress": round(sum(g.progress_percent for g in cat_goals) / len(cat_goals), 1),
            }
    
    for status in ["not_started", "in_progress", "completed", "on_hold"]:
        count = len([g for g in goals if g.status == status])
        if count > 0:
            summary["by_status"][status] = count
    
    for timeframe in ["short_term", "long_term"]:
        count = len([g for g in goals if g.timeframe == timeframe])
        if count > 0:
            summary["by_timeframe"][timeframe] = count
    
    return summary


# ==================== PLANS ====================

async def create_plan(
    session: AsyncSession,
    user_id: str,
    title: str,
    description: str = "",
    plan_type: str = "general",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    linked_goal_ids: Optional[list] = None,
    linked_habit_ids: Optional[list] = None,
) -> Plan:
    """Create a new plan."""
    plan = Plan(
        user_id=user_id,
        title=title,
        description=description,
        plan_type=plan_type,
        start_date=start_date,
        end_date=end_date,
        linked_goal_ids=linked_goal_ids or [],
        linked_habit_ids=linked_habit_ids or [],
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


async def get_plan(session: AsyncSession, plan_id: str, user_id: str) -> Optional[Plan]:
    """Get a plan by ID."""
    result = await session.execute(
        select(Plan).where(and_(Plan.id == plan_id, Plan.user_id == user_id))
    )
    return result.scalar_one_or_none()


async def list_plans(
    session: AsyncSession,
    user_id: str,
    plan_type: Optional[str] = None,
    status: Optional[str] = None,
    linked_goal_id: Optional[str] = None,
) -> list[Plan]:
    """List plans with filtering."""
    query = select(Plan).where(Plan.user_id == user_id)
    if plan_type:
        query = query.where(Plan.plan_type == plan_type)
    if status:
        query = query.where(Plan.status == status)
    if linked_goal_id:
        query = query.where(Plan.linked_goal_ids.contains([linked_goal_id]))
    query = query.order_by(Plan.created_at.desc())
    result = await session.execute(query)
    return result.scalars().all()


async def update_plan(session: AsyncSession, plan_id: str, user_id: str, **updates) -> Optional[Plan]:
    """Update a plan."""
    plan = await get_plan(session, plan_id, user_id)
    if not plan:
        return None
    for key, value in updates.items():
        if hasattr(plan, key):
            setattr(plan, key, value)
    await session.commit()
    await session.refresh(plan)
    return plan


async def delete_plan(session: AsyncSession, plan_id: str, user_id: str) -> bool:
    """Delete a plan and its todos."""
    plan = await get_plan(session, plan_id, user_id)
    if not plan:
        return False
    
    # Delete associated todos
    todos = await list_todos(session, user_id, plan_id=plan_id)
    for todo in todos:
        await session.delete(todo)
    
    await session.delete(plan)
    await session.commit()
    return True


async def recalculate_plan_progress(session: AsyncSession, plan_id: str, user_id: str) -> Optional[Plan]:
    """Recalculate plan progress based on todos."""
    plan = await get_plan(session, plan_id, user_id)
    if not plan:
        return None
    
    todos = await list_todos(session, user_id, plan_id=plan_id)
    if todos:
        completed = len([t for t in todos if t.status == "completed"])
        plan.progress_percent = round(completed / len(todos) * 100, 1)
        
        if plan.progress_percent >= 100:
            plan.status = "completed"
    
    await session.commit()
    await session.refresh(plan)
    return plan


# ==================== TODOS ====================

async def create_todo(
    session: AsyncSession,
    user_id: str,
    title: str,
    description: str = "",
    plan_id: Optional[str] = None,
    category: str = "general",
    priority: int = 2,
    due_date: Optional[date] = None,
    due_time: Optional[str] = None,
    estimated_minutes: Optional[int] = None,
    linked_goal_id: Optional[str] = None,
    linked_habit_id: Optional[str] = None,
    sort_order: int = 0,
) -> Todo:
    """Create a new todo."""
    todo = Todo(
        user_id=user_id,
        plan_id=plan_id,
        title=title,
        description=description,
        category=category,
        priority=priority,
        due_date=due_date,
        due_time=due_time,
        estimated_minutes=estimated_minutes,
        linked_goal_id=linked_goal_id,
        linked_habit_id=linked_habit_id,
        sort_order=sort_order,
    )
    session.add(todo)
    await session.commit()
    await session.refresh(todo)
    return todo


async def get_todo(session: AsyncSession, todo_id: str, user_id: str) -> Optional[Todo]:
    """Get a todo by ID."""
    result = await session.execute(
        select(Todo).where(and_(Todo.id == todo_id, Todo.user_id == user_id))
    )
    return result.scalar_one_or_none()


async def list_todos(
    session: AsyncSession,
    user_id: str,
    plan_id: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    due_date: Optional[date] = None,
    priority: Optional[int] = None,
) -> list[Todo]:
    """List todos with filtering."""
    query = select(Todo).where(Todo.user_id == user_id)
    if plan_id:
        query = query.where(Todo.plan_id == plan_id)
    if status:
        query = query.where(Todo.status == status)
    if category:
        query = query.where(Todo.category == category)
    if due_date:
        query = query.where(Todo.due_date == due_date)
    if priority:
        query = query.where(Todo.priority == priority)
    query = query.order_by(Todo.priority, Todo.due_date, Todo.sort_order)
    result = await session.execute(query)
    return result.scalars().all()


async def list_todos_for_today(session: AsyncSession, user_id: str) -> list[Todo]:
    """Get todos due today or overdue."""
    today = date.today()
    todos = await list_todos(session, user_id, status="pending")
    
    result = []
    for todo in todos:
        if todo.due_date is None or todo.due_date <= today:
            result.append(todo)
    
    return sorted(result, key=lambda t: (t.priority, t.due_date or today))


async def update_todo(session: AsyncSession, todo_id: str, user_id: str, **updates) -> Optional[Todo]:
    """Update a todo."""
    todo = await get_todo(session, todo_id, user_id)
    if not todo:
        return None
    for key, value in updates.items():
        if hasattr(todo, key):
            setattr(todo, key, value)
    await session.commit()
    await session.refresh(todo)
    return todo


async def complete_todo(session: AsyncSession, todo_id: str, user_id: str) -> Optional[Todo]:
    """Mark a todo as completed."""
    todo = await get_todo(session, todo_id, user_id)
    if not todo:
        return None
    
    todo.status = "completed"
    todo.completed_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(todo)
    
    # Recalculate parent plan progress
    if todo.plan_id:
        await recalculate_plan_progress(session, todo.plan_id, user_id)
    
    return todo


async def delete_todo(session: AsyncSession, todo_id: str, user_id: str) -> bool:
    """Delete a todo."""
    todo = await get_todo(session, todo_id, user_id)
    if not todo:
        return False
    await session.delete(todo)
    await session.commit()
    return True


async def get_todo_stats(session: AsyncSession, user_id: str) -> dict:
    """Get todo statistics."""
    all_todos = await list_todos(session, user_id)
    
    total = len(all_todos)
    completed = len([t for t in all_todos if t.status == "completed"])
    pending = len([t for t in all_todos if t.status == "pending"])
    in_progress = len([t for t in all_todos if t.status == "in_progress"])
    
    today = date.today()
    overdue = len([t for t in all_todos if t.status == "pending" and t.due_date and t.due_date < today])
    due_today = len([t for t in all_todos if t.status == "pending" and t.due_date == today])
    
    return {
        "total": total,
        "completed": completed,
        "pending": pending,
        "in_progress": in_progress,
        "overdue": overdue,
        "due_today": due_today,
        "completion_rate": round(completed / total * 100, 1) if total > 0 else 0,
    }
