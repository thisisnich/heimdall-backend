"""Budget and financial tracking API endpoints."""
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from atlas.db.session import get_session
from atlas.services import budget_service

router = APIRouter(prefix="/budget", tags=["budget"])


# ======== Schemas ========

class BudgetCategoryCreate(BaseModel):
    name: str
    type: str = "expense"  # income, expense, savings
    color: str = "#2196F3"
    icon: str = "wallet"
    monthly_limit: Optional[float] = None
    annual_limit: Optional[float] = None
    alert_threshold: float = 80.0
    is_recurring: bool = False
    recurring_amount: Optional[float] = None
    recurring_day: Optional[int] = Field(None, ge=1, le=31)
    linked_goal_id: Optional[str] = None


class BudgetCategoryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    monthly_limit: Optional[float] = None
    annual_limit: Optional[float] = None
    alert_threshold: Optional[float] = None
    is_recurring: Optional[bool] = None
    recurring_amount: Optional[float] = None
    recurring_day: Optional[int] = Field(None, ge=1, le=31)
    linked_goal_id: Optional[str] = None
    is_active: Optional[bool] = None


class BudgetCategoryResponse(BaseModel):
    id: str
    name: str
    type: str
    color: str
    icon: str
    monthly_limit: Optional[float]
    annual_limit: Optional[float]
    alert_threshold: float
    is_recurring: bool
    recurring_amount: Optional[float]
    recurring_day: Optional[int]
    linked_goal_id: Optional[str]
    is_active: bool
    created_at: date
    
    class Config:
        from_attributes = True


class TransactionCreate(BaseModel):
    amount: float = Field(gt=0)
    type: str  # income, expense, transfer
    description: str
    category_id: Optional[str] = None
    transaction_date: date = Field(default_factory=date.today)
    payment_method: Optional[str] = None  # cash, card, transfer
    merchant: Optional[str] = None
    receipt_url: Optional[str] = None
    tags: list[str] = []
    is_recurring: bool = False
    linked_goal_id: Optional[str] = None


class TransactionUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    type: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    transaction_date: Optional[date] = None
    payment_method: Optional[str] = None
    merchant: Optional[str] = None
    receipt_url: Optional[str] = None
    tags: Optional[list[str]] = None
    is_recurring: Optional[bool] = None
    linked_goal_id: Optional[str] = None


class TransactionResponse(BaseModel):
    id: str
    amount: float
    type: str
    description: str
    category_id: Optional[str]
    transaction_date: date
    payment_method: Optional[str]
    merchant: Optional[str]
    tags: list
    is_recurring: bool
    linked_goal_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AffordabilityRequest(BaseModel):
    amount: float = Field(gt=0)


class AffordabilityResponse(BaseModel):
    can_afford: bool
    requested_amount: float
    current_month_net: float
    remaining_after_purchase: float
    percent_of_monthly_income: Optional[float]
    recommendation: str


# ======== Endpoints ========

@router.post("/categories", response_model=BudgetCategoryResponse)
async def create_category(category: BudgetCategoryCreate, user_id: str = Query(default="default")):
    """Create a new budget category."""
    async with get_session() as session:
        result = await budget_service.create_budget_category(
            session,
            user_id=user_id,
            name=category.name,
            type=category.type,
            color=category.color,
            icon=category.icon,
            monthly_limit=category.monthly_limit,
            annual_limit=category.annual_limit,
            alert_threshold=category.alert_threshold,
            is_recurring=category.is_recurring,
            recurring_amount=category.recurring_amount,
            recurring_day=category.recurring_day,
            linked_goal_id=category.linked_goal_id,
        )
        return result


@router.get("/categories", response_model=list[BudgetCategoryResponse])
async def list_categories(
    user_id: str = Query(default="default"),
    type: Optional[str] = None,
):
    """List budget categories."""
    async with get_session() as session:
        categories = await budget_service.list_budget_categories(session, user_id, type=type)
        return categories


@router.get("/categories/{category_id}", response_model=BudgetCategoryResponse)
async def get_category(category_id: str, user_id: str = Query(default="default")):
    """Get a budget category by ID."""
    async with get_session() as session:
        category = await budget_service.get_budget_category(session, category_id, user_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return category


@router.patch("/categories/{category_id}", response_model=BudgetCategoryResponse)
async def update_category(
    category_id: str,
    updates: BudgetCategoryUpdate,
    user_id: str = Query(default="default"),
):
    """Update a budget category."""
    async with get_session() as session:
        category = await budget_service.update_budget_category(
            session, category_id, user_id, **updates.model_dump(exclude_unset=True)
        )
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return category


@router.delete("/categories/{category_id}")
async def delete_category(category_id: str, user_id: str = Query(default="default")):
    """Delete a budget category."""
    async with get_session() as session:
        success = await budget_service.delete_budget_category(session, category_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Category not found")
        return {"message": "Category deleted successfully"}


@router.post("/transactions", response_model=TransactionResponse)
async def add_transaction(transaction: TransactionCreate, user_id: str = Query(default="default")):
    """Add a new transaction."""
    async with get_session() as session:
        result = await budget_service.add_transaction(
            session,
            user_id=user_id,
            amount=transaction.amount,
            type=transaction.type,
            description=transaction.description,
            category_id=transaction.category_id,
            transaction_date=transaction.transaction_date,
            payment_method=transaction.payment_method,
            merchant=transaction.merchant,
            receipt_url=transaction.receipt_url,
            tags=transaction.tags,
            is_recurring=transaction.is_recurring,
            linked_goal_id=transaction.linked_goal_id,
        )
        return result


@router.get("/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    user_id: str = Query(default="default"),
    type: Optional[str] = None,
    category_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=100, le=500),
):
    """List transactions with filtering."""
    async with get_session() as session:
        transactions = await budget_service.list_transactions(
            session, user_id, type, category_id, start_date, end_date, limit
        )
        return transactions


@router.get("/transactions/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: str, user_id: str = Query(default="default")):
    """Get a transaction by ID."""
    async with get_session() as session:
        transaction = await budget_service.get_transaction(session, transaction_id, user_id)
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return transaction


@router.patch("/transactions/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: str,
    updates: TransactionUpdate,
    user_id: str = Query(default="default"),
):
    """Update a transaction."""
    async with get_session() as session:
        transaction = await budget_service.update_transaction(
            session, transaction_id, user_id, **updates.model_dump(exclude_unset=True)
        )
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return transaction


@router.delete("/transactions/{transaction_id}")
async def delete_transaction(transaction_id: str, user_id: str = Query(default="default")):
    """Delete a transaction."""
    async with get_session() as session:
        success = await budget_service.delete_transaction(session, transaction_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return {"message": "Transaction deleted successfully"}


@router.get("/summary/monthly")
async def get_monthly_summary(
    user_id: str = Query(default="default"),
    year: Optional[int] = None,
    month: Optional[int] = None,
):
    """Get monthly budget summary."""
    async with get_session() as session:
        summary = await budget_service.get_monthly_summary(session, user_id, year, month)
        return summary


@router.post("/can-afford", response_model=AffordabilityResponse)
async def check_affordability(
    request: AffordabilityRequest,
    user_id: str = Query(default="default"),
):
    """Check if user can afford a purchase based on current month budget."""
    async with get_session() as session:
        result = await budget_service.can_afford(session, user_id, request.amount)
        return result


@router.get("/upcoming-payments")
async def get_upcoming_payments(
    user_id: str = Query(default="default"),
    days_ahead: int = Query(default=7, ge=1, le=30),
):
    """Get upcoming recurring payments in the next N days."""
    async with get_session() as session:
        payments = await budget_service.get_upcoming_payments(session, user_id, days_ahead)
        return {"upcoming_payments": payments, "count": len(payments)}
