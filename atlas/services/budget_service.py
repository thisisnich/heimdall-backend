"""Budget and financial tracking service."""
from datetime import date, datetime, timedelta
from typing import Optional
from decimal import Decimal
from sqlalchemy import select, and_, func, extract
from sqlalchemy.ext.asyncio import AsyncSession
from atlas.db.models import BudgetCategory, Transaction


async def create_budget_category(
    session: AsyncSession,
    user_id: str,
    name: str,
    type: str = "expense",  # income, expense, savings
    color: str = "#2196F3",
    icon: str = "wallet",
    monthly_limit: Optional[float] = None,
    annual_limit: Optional[float] = None,
    alert_threshold: float = 80.0,
    is_recurring: bool = False,
    recurring_amount: Optional[float] = None,
    recurring_day: Optional[int] = None,
    linked_goal_id: Optional[str] = None,
) -> BudgetCategory:
    """Create a new budget category."""
    category = BudgetCategory(
        user_id=user_id,
        name=name,
        type=type,
        color=color,
        icon=icon,
        monthly_limit=monthly_limit,
        annual_limit=annual_limit,
        alert_threshold=alert_threshold,
        is_recurring=is_recurring,
        recurring_amount=recurring_amount,
        recurring_day=recurring_day,
        linked_goal_id=linked_goal_id,
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


async def get_budget_category(session: AsyncSession, category_id: str, user_id: str) -> Optional[BudgetCategory]:
    """Get a budget category by ID."""
    result = await session.execute(
        select(BudgetCategory).where(
            and_(BudgetCategory.id == category_id, BudgetCategory.user_id == user_id)
        )
    )
    return result.scalar_one_or_none()


async def list_budget_categories(
    session: AsyncSession,
    user_id: str,
    type: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> list[BudgetCategory]:
    """List budget categories with optional filtering."""
    query = select(BudgetCategory).where(BudgetCategory.user_id == user_id)
    if type:
        query = query.where(BudgetCategory.type == type)
    if is_active is not None:
        query = query.where(BudgetCategory.is_active == is_active)
    query = query.order_by(BudgetCategory.type, BudgetCategory.name)
    result = await session.execute(query)
    return result.scalars().all()


async def update_budget_category(
    session: AsyncSession, category_id: str, user_id: str, **updates
) -> Optional[BudgetCategory]:
    """Update a budget category."""
    category = await get_budget_category(session, category_id, user_id)
    if not category:
        return None
    for key, value in updates.items():
        if hasattr(category, key):
            setattr(category, key, value)
    await session.commit()
    await session.refresh(category)
    return category


async def delete_budget_category(session: AsyncSession, category_id: str, user_id: str) -> bool:
    """Soft delete a budget category."""
    category = await get_budget_category(session, category_id, user_id)
    if not category:
        return False
    category.is_active = False
    await session.commit()
    return True


async def add_transaction(
    session: AsyncSession,
    user_id: str,
    amount: float,
    type: str,  # income, expense, transfer
    description: str,
    category_id: Optional[str] = None,
    transaction_date: Optional[date] = None,
    payment_method: Optional[str] = None,
    merchant: Optional[str] = None,
    receipt_url: Optional[str] = None,
    tags: Optional[list] = None,
    is_recurring: bool = False,
    linked_goal_id: Optional[str] = None,
) -> Transaction:
    """Add a new transaction."""
    transaction = Transaction(
        user_id=user_id,
        amount=amount,
        type=type,
        description=description,
        category_id=category_id,
        transaction_date=transaction_date or date.today(),
        payment_method=payment_method,
        merchant=merchant,
        receipt_url=receipt_url,
        tags=tags or [],
        is_recurring=is_recurring,
        linked_goal_id=linked_goal_id,
    )
    session.add(transaction)
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def get_transaction(session: AsyncSession, transaction_id: str, user_id: str) -> Optional[Transaction]:
    """Get a transaction by ID."""
    result = await session.execute(
        select(Transaction).where(
            and_(Transaction.id == transaction_id, Transaction.user_id == user_id)
        )
    )
    return result.scalar_one_or_none()


async def list_transactions(
    session: AsyncSession,
    user_id: str,
    type: Optional[str] = None,
    category_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 100,
) -> list[Transaction]:
    """List transactions with filtering."""
    query = select(Transaction).where(Transaction.user_id == user_id)
    if type:
        query = query.where(Transaction.type == type)
    if category_id:
        query = query.where(Transaction.category_id == category_id)
    if start_date:
        query = query.where(Transaction.transaction_date >= start_date)
    if end_date:
        query = query.where(Transaction.transaction_date <= end_date)
    query = query.order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
    query = query.limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


async def update_transaction(
    session: AsyncSession, transaction_id: str, user_id: str, **updates
) -> Optional[Transaction]:
    """Update a transaction."""
    transaction = await get_transaction(session, transaction_id, user_id)
    if not transaction:
        return None
    for key, value in updates.items():
        if hasattr(transaction, key):
            setattr(transaction, key, value)
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def delete_transaction(session: AsyncSession, transaction_id: str, user_id: str) -> bool:
    """Delete a transaction."""
    transaction = await get_transaction(session, transaction_id, user_id)
    if not transaction:
        return False
    await session.delete(transaction)
    await session.commit()
    return True


async def get_monthly_summary(
    session: AsyncSession,
    user_id: str,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> dict:
    """Get monthly budget summary."""
    if year is None:
        year = date.today().year
    if month is None:
        month = date.today().month
    
    # Get all transactions for the month
    transactions = await list_transactions(
        session, user_id, start_date=date(year, month, 1),
        end_date=date(year, month, 1) + timedelta(days=32),  # Roughly next month
    )
    
    # Filter to actual month
    month_transactions = [
        t for t in transactions if t.transaction_date.year == year and t.transaction_date.month == month
    ]
    
    income = sum(t.amount for t in month_transactions if t.type == "income")
    expenses = sum(t.amount for t in month_transactions if t.type == "expense")
    savings = sum(t.amount for t in month_transactions if t.type == "transfer")
    
    # Get category breakdown
    categories = await list_budget_categories(session, user_id, is_active=True)
    category_spending = {}
    
    for cat in categories:
        cat_spent = sum(
            t.amount for t in month_transactions 
            if t.category_id == cat.id and t.type == "expense"
        )
        if cat_spent > 0 or cat.monthly_limit:
            category_spending[cat.id] = {
                "name": cat.name,
                "type": cat.type,
                "color": cat.color,
                "spent": cat_spent,
                "limit": cat.monthly_limit,
                "percent_used": round(cat_spent / cat.monthly_limit * 100, 1) if cat.monthly_limit else None,
                "alert": cat.monthly_limit and (cat_spent / cat.monthly_limit * 100) >= cat.alert_threshold,
            }
    
    return {
        "year": year,
        "month": month,
        "income": income,
        "expenses": expenses,
        "savings": savings,
        "net": income - expenses,
        "transaction_count": len(month_transactions),
        "category_breakdown": category_spending,
    }


async def can_afford(
    session: AsyncSession,
    user_id: str,
    amount: float,
) -> dict:
    """Check if user can afford a purchase based on current month budget."""
    summary = await get_monthly_summary(session, user_id)
    
    remaining = summary["net"] - amount
    can_afford = remaining >= 0
    
    # Get average monthly income from last 3 months for context
    avg_income = summary["income"]  # Simplified - could calculate 3-month average
    
    return {
        "can_afford": can_afford,
        "requested_amount": amount,
        "current_month_net": summary["net"],
        "remaining_after_purchase": remaining,
        "percent_of_monthly_income": round(amount / avg_income * 100, 1) if avg_income else None,
        "recommendation": "affordable" if can_afford else "exceeds_budget",
    }


async def get_recurring_transactions(session: AsyncSession, user_id: str) -> list[Transaction]:
    """Get all recurring transactions."""
    result = await session.execute(
        select(Transaction).where(
            and_(Transaction.user_id == user_id, Transaction.is_recurring == True)
        )
    )
    return result.scalars().all()


async def get_upcoming_payments(session: AsyncSession, user_id: str, days_ahead: int = 7) -> list[dict]:
    """Get upcoming recurring payments in the next N days."""
    today = date.today()
    end_date = today + timedelta(days=days_ahead)
    
    categories = await list_budget_categories(session, user_id, is_active=True)
    upcoming = []
    
    for cat in categories:
        if cat.is_recurring and cat.recurring_day and cat.recurring_amount:
            # Check if recurring day falls within range
            for day_offset in range(days_ahead + 1):
                check_date = today + timedelta(days=day_offset)
                if check_date.day == cat.recurring_day:
                    upcoming.append({
                        "category_id": cat.id,
                        "category_name": cat.name,
                        "amount": cat.recurring_amount,
                        "due_date": check_date,
                        "type": cat.type,
                        "color": cat.color,
                        "icon": cat.icon,
                    })
    
    return sorted(upcoming, key=lambda x: x["due_date"])
