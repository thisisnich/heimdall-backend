from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, relationship
from sqlalchemy import String, Text, DateTime, Boolean, Float, JSON, ForeignKey, Integer, Numeric, UniqueConstraint
from datetime import datetime, date
import uuid

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True)
    hashed_password: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Chat(Base):
    __tablename__ = "chats"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String, default="New chat")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id: Mapped[str] = mapped_column(ForeignKey("chats.id"))
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    model_used: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")
    subtasks: Mapped[dict] = mapped_column(JSON, default=list)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    linked_chat_id: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MemoryEntry(Base):
    __tablename__ = "memory_entries"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String)
    source_id: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class UsageLog(Base):
    __tablename__ = "usage_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=True)
    model: Mapped[str] = mapped_column(String)
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0)
    task_type: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Machine(Base):
    __tablename__ = "machines"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    state: Mapped[str] = mapped_column(String, default="offline")
    toolchains: Mapped[list] = mapped_column(JSON, default=list)
    active_repos: Mapped[list] = mapped_column(JSON, default=list)
    available_models: Mapped[list] = mapped_column(JSON, default=list)
    gpu_info: Mapped[str] = mapped_column(String, nullable=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Entity(Base):
    __tablename__ = "entities"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)  # person/project/location/goal
    notes: Mapped[str] = mapped_column(Text, default="")
    related_ids: Mapped[list] = mapped_column(JSON, default=list)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==================== HABIT TRACKER ====================

class Habit(Base):
    """SMART goal-based habit definitions."""
    __tablename__ = "habits"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    
    # SMART goal fields
    specific: Mapped[str] = mapped_column(Text, default="")  # What exactly will you do?
    measurable: Mapped[str] = mapped_column(Text, default="")  # How will you measure success?
    achievable: Mapped[str] = mapped_column(Text, default="")  # Is this realistic?
    relevant: Mapped[str] = mapped_column(Text, default="")  # Why does this matter?
    time_bound: Mapped[str] = mapped_column(Text, default="")  # When will you achieve this?
    target_date: Mapped[date] = mapped_column(DateTime, nullable=True)
    
    # Habit configuration
    frequency: Mapped[str] = mapped_column(String, default="daily")  # daily, weekly, monthly
    target_days_per_week: Mapped[int] = mapped_column(Integer, default=7)
    category: Mapped[str] = mapped_column(String, default="general")  # physical, education, financial, health, career
    reminder_time: Mapped[str] = mapped_column(String, nullable=True)  # HH:MM format
    color: Mapped[str] = mapped_column(String, default="#4CAF50")
    icon: Mapped[str] = mapped_column(String, default="check")
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    archived_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class HabitLog(Base):
    """Daily habit completion tracking."""
    __tablename__ = "habit_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    habit_id: Mapped[str] = mapped_column(ForeignKey("habits.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    log_date: Mapped[date] = mapped_column(DateTime)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    value: Mapped[float] = mapped_column(Float, nullable=True)  # For measurable habits (minutes, pages, etc.)
    notes: Mapped[str] = mapped_column(Text, default="")
    mood: Mapped[int] = mapped_column(Integer, nullable=True)  # 1-5 scale
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==================== BUDGET SYSTEM ====================

class BudgetCategory(Base):
    """Budget categories with limits."""
    __tablename__ = "budget_categories"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String, default="expense")  # income, expense, savings
    color: Mapped[str] = mapped_column(String, default="#2196F3")
    icon: Mapped[str] = mapped_column(String, default="wallet")
    
    # Budget limits
    monthly_limit: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    annual_limit: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    alert_threshold: Mapped[float] = mapped_column(Numeric(5, 2), default=80.0)  # Alert at % of limit
    
    # Recurring
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurring_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    recurring_day: Mapped[int] = mapped_column(Integer, nullable=True)  # Day of month
    
    # SMART goal linkage
    linked_goal_id: Mapped[str] = mapped_column(String, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    """Income and expense transactions."""
    __tablename__ = "transactions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    category_id: Mapped[str] = mapped_column(ForeignKey("budget_categories.id"), nullable=True)
    
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    type: Mapped[str] = mapped_column(String)  # income, expense, transfer
    description: Mapped[str] = mapped_column(String)
    
    transaction_date: Mapped[date] = mapped_column(DateTime)
    
    # Metadata
    payment_method: Mapped[str] = mapped_column(String, nullable=True)  # cash, card, transfer
    merchant: Mapped[str] = mapped_column(String, nullable=True)
    receipt_url: Mapped[str] = mapped_column(String, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Goal linkage
    linked_goal_id: Mapped[str] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ==================== GOALS SYSTEM ====================

class Goal(Base):
    """Long and short term goals across categories."""
    __tablename__ = "goals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    
    # Goal classification
    category: Mapped[str] = mapped_column(String)  # physical, education, financial, career, personal, health
    timeframe: Mapped[str] = mapped_column(String)  # short_term, long_term
    priority: Mapped[int] = mapped_column(Integer, default=2)  # 1=high, 2=medium, 3=low
    
    # SMART goal fields
    specific: Mapped[str] = mapped_column(Text, default="")
    measurable: Mapped[str] = mapped_column(Text, default="")
    achievable: Mapped[str] = mapped_column(Text, default="")
    relevant: Mapped[str] = mapped_column(Text, default="")
    time_bound: Mapped[str] = mapped_column(Text, default="")
    
    # Timeline
    start_date: Mapped[date] = mapped_column(DateTime, nullable=True)
    target_date: Mapped[date] = mapped_column(DateTime, nullable=True)
    completed_date: Mapped[date] = mapped_column(DateTime, nullable=True)
    
    # Progress tracking
    status: Mapped[str] = mapped_column(String, default="not_started")  # not_started, in_progress, on_hold, completed, abandoned
    progress_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    current_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    target_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    unit: Mapped[str] = mapped_column(String, nullable=True)  # kg, km, hours, dollars, etc.
    
    # Financial linkage
    estimated_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    saved_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    
    # Visual
    color: Mapped[str] = mapped_column(String, default="#9C27B0")
    icon: Mapped[str] = mapped_column(String, default="target")
    
    # Relations
    parent_goal_id: Mapped[str] = mapped_column(String, nullable=True)  # For sub-goals
    linked_habit_ids: Mapped[list] = mapped_column(JSON, default=list)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== PLANS & TODOS ====================

class Plan(Base):
    """Structured plans containing todos, linked to goals."""
    __tablename__ = "plans"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    
    # Plan type
    plan_type: Mapped[str] = mapped_column(String, default="general")  # weekly, monthly, project, goal_based
    
    # Timeline
    start_date: Mapped[date] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[date] = mapped_column(DateTime, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String, default="active")  # draft, active, completed, archived
    progress_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    
    # Relations
    linked_goal_ids: Mapped[list] = mapped_column(JSON, default=list)
    linked_habit_ids: Mapped[list] = mapped_column(JSON, default=list)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Todo(Base):
    """Individual tasks within plans."""
    __tablename__ = "todos"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"), nullable=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    
    # Organization
    category: Mapped[str] = mapped_column(String, default="general")
    priority: Mapped[int] = mapped_column(Integer, default=2)  # 1=high, 2=medium, 3=low
    
    # Timeline
    due_date: Mapped[date] = mapped_column(DateTime, nullable=True)
    due_time: Mapped[str] = mapped_column(String, nullable=True)  # HH:MM format
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String, default="pending")  # pending, in_progress, completed, cancelled
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Relations
    linked_goal_id: Mapped[str] = mapped_column(String, nullable=True)
    linked_habit_id: Mapped[str] = mapped_column(String, nullable=True)
    
    # Ordering
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== KNOWLEDGE GRAPH ====================

class VaultNote(Base):
    """Represents a note/file in the vault system across all vaults."""
    __tablename__ = "vault_notes"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    # Vault location
    vault: Mapped[str] = mapped_column(String)  # personal, youtube, wiki, projects, inbox
    path: Mapped[str] = mapped_column(String, unique=True)  # e.g., "personal/goals/fyp.md"
    
    # Content metadata
    title: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text, default="")
    node_type: Mapped[str] = mapped_column(String, default="note")  # note, entity, index
    
    # Frontmatter fields
    note_id: Mapped[str] = mapped_column(String, nullable=True)  # UUID from frontmatter
    source_brain: Mapped[str] = mapped_column(String, nullable=True)
    entities: Mapped[list] = mapped_column(JSON, default=list)  # Extracted entities
    
    # Checksum for integrity
    checksum: Mapped[str] = mapped_column(String, nullable=True)
    
    # Stats
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    connection_count: Mapped[int] = mapped_column(Integer, default=0)  # Cached for quick access
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    file_modified_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class KnowledgeLink(Base):
    """Bidirectional links between vault notes (knowledge graph edges)."""
    __tablename__ = "knowledge_links"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Link endpoints
    source: Mapped[str] = mapped_column(String)  # vault/path format
    target: Mapped[str] = mapped_column(String)  # vault/path format
    
    # Link metadata
    link_type: Mapped[str] = mapped_column(String, default="wiki")  # wiki, cross_vault, entity, reference, applies_to, mentions_tool
    is_backlink: Mapped[bool] = mapped_column(Boolean, default=False)  # True if this is reverse direction
    
    # Context
    context: Mapped[str] = mapped_column(Text, nullable=True)  # Snippet around the link
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Unique constraint: one link per direction between two notes
    __table_args__ = (
        UniqueConstraint('source', 'target', name='uix_link_direction'),
    )