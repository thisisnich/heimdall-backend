# Habits, Goals, Plans & Budget API Reference

**For AI Agents:** When the user mentions tasks, habits, goals, budgets, spending, savings, or progress tracking - refer to this document.

---

## Overview

This system provides comprehensive personal productivity and financial tracking with SMART goal methodology built-in.

**Key Concepts:**
- **Habits** - Recurring daily/weekly behaviors with SMART goal fields
- **Goals** - Long/short term objectives across life categories
- **Plans** - Structured collections of todos linked to goals
- **Todos** - Individual tasks with priorities and due dates
- **Budget** - Income/expense tracking with categories and affordability queries

---

## Life Categories

All habits and goals use consistent categories:

| Category | Use For | Examples |
|----------|---------|----------|
| `physical` | Fitness, exercise, sports | Run 5K, gym routine, lose weight |
| `education` | Learning, courses, reading | Learn Python, get certification |
| `financial` | Money goals, savings, debt | Save $10K, pay off credit card |
| `career` | Professional development | Get promotion, learn new skill |
| `health` | Wellness, medical, sleep | Sleep 8hrs, drink more water |
| `personal` | Self-improvement, hobbies | Meditate daily, journal |

---

## SMART Goals Framework

Every habit and goal should use SMART criteria when possible:

- **S**pecific - What exactly will you do?
- **M**easurable - How will you track progress?
- **A**chievable - Is this realistic?
- **R**elevant - Why does this matter to you?
- **T**ime-bound - When will you complete this?

### Example SMART Goal Breakdown

**Goal:** "Run a 5K marathon in 3 months"

```json
{
  "specific": "Run 5 kilometers without stopping at the city marathon",
  "measurable": "Track distance with running app, aim for under 30 min",
  "achievable": "Currently running 3K, increasing 500m weekly",
  "relevant": "Improves cardiovascular health and builds discipline",
  "time_bound": "Complete the city marathon on September 15, 2026"
}
```

---

## Habits API

Habits are recurring behaviors tracked daily/weekly with completion logging.

### Create a Habit

```bash
POST /habits
```

```json
{
  "name": "Morning Exercise",
  "description": "Daily cardio or strength training",
  "specific": "30 minutes of running, cycling, or gym workout",
  "measurable": "Track duration and type in fitness app",
  "achievable": "Wake up 30 min earlier, gym is 5 min away",
  "relevant": "Increases energy and improves health markers",
  "time_bound": "Daily at 7:00 AM, 5 days per week",
  "frequency": "daily",
  "target_days_per_week": 5,
  "category": "physical",
  "reminder_time": "06:45",
  "color": "#4CAF50",
  "icon": "dumbbell"
}
```

**Fields:**
- `name` (required) - Habit name
- `description` - Details about the habit
- `specific`, `measurable`, `achievable`, `relevant`, `time_bound` - SMART fields
- `frequency` - daily, weekly, monthly
- `target_days_per_week` - How many days per week (1-7)
- `category` - physical, education, financial, health, career, personal, general
- `reminder_time` - HH:MM format for notifications
- `color` - Hex color code for UI
- `icon` - Icon identifier

### List Habits

```bash
GET /habits?category=physical&is_active=true
```

### Log Habit Completion

```bash
POST /habits/{habit_id}/log
```

```json
{
  "log_date": "2026-05-11",
  "completed": true,
  "value": 30,
  "notes": "Felt great today, ran 5km",
  "mood": 5
}
```

**Fields:**
- `log_date` (required) - Date of completion
- `completed` - true/false
- `value` - Numeric value (minutes, pages, reps, etc.)
- `notes` - Journal entry
- `mood` - 1-5 scale (5=excellent)

### Get Today's Habits

```bash
GET /habits/today
```

Returns habits with completion status for today and weekly progress.

### Get Habit Statistics

```bash
GET /habits/{habit_id}/stats?days=30
```

Response:
```json
{
  "total_days": 30,
  "completed_days": 22,
  "completion_rate": 73.3,
  "current_streak": 5,
  "longest_streak": 8
}
```

### Update Habit

```bash
PATCH /habits/{habit_id}
```

```json
{
  "name": "Updated Name",
  "target_days_per_week": 6,
  "reminder_time": "07:00"
}
```

### Archive (Delete) Habit

```bash
DELETE /habits/{habit_id}
```

Soft-deletes (archives) the habit - keeps history but marks inactive.

---

## Goals API

Goals are objectives with target values, timelines, and progress tracking.

### Create a Goal

```bash
POST /goals
```

**Physical Goal Example:**
```json
{
  "title": "Run a 5K Marathon",
  "description": "Complete my first 5K race",
  "category": "physical",
  "timeframe": "short_term",
  "priority": 1,
  "specific": "Run 5 kilometers without stopping at the city marathon",
  "measurable": "Finish race under 30 minutes, tracked via running app",
  "achievable": "Currently running 3K, adding 500m weekly",
  "relevant": "Improves cardiovascular health and builds mental toughness",
  "time_bound": "Complete by September 15, 2026",
  "target_value": 5,
  "unit": "km",
  "target_date": "2026-09-15",
  "color": "#F44336",
  "icon": "running"
}
```

**Financial Goal Example:**
```json
{
  "title": "Emergency Fund",
  "description": "Build 6-month emergency savings",
  "category": "financial",
  "timeframe": "long_term",
  "priority": 1,
  "specific": "Save 6 months of living expenses",
  "measurable": "Track monthly savings deposits",
  "achievable": "Saving $500/month from salary",
  "relevant": "Provides financial security for unexpected events",
  "time_bound": "Complete by December 2026",
  "target_value": 15000,
  "unit": "dollars",
  "estimated_cost": 15000,
  "color": "#4CAF50",
  "icon": "piggy-bank"
}
```

**Fields:**
- `title` (required) - Goal name
- `category` (required) - physical, education, financial, career, personal, health
- `timeframe` - short_term or long_term
- `priority` - 1 (high), 2 (medium), 3 (low)
- `specific`, `measurable`, `achievable`, `relevant`, `time_bound` - SMART fields
- `target_value`, `current_value`, `unit` - Progress tracking (e.g., 5 km, $1000)
- `estimated_cost`, `saved_amount` - For financial goals
- `target_date` - When to complete
- `parent_goal_id` - For sub-goals

### List Goals

```bash
GET /goals?category=physical&timeframe=short_term&status=in_progress
```

### Update Goal Progress

```bash
POST /goals/{goal_id}/progress
```

```json
{
  "current_value": 4.2,
  "notes": "Ran 4.2km today, feeling stronger"
}
```

Progress percentage auto-calculates from current/target values.

### Add Savings to Financial Goal

```bash
POST /goals/{goal_id}/add-savings
```

```json
{
  "amount": 500
}
```

### Get Goal Summary

```bash
GET /goals/summary
```

Returns aggregated stats across all goals by category and status.

---

## Plans API

Plans are structured collections of todos linked to goals and habits.

### Create a Plan

```bash
POST /goals/plans
```

```json
{
  "title": "Weekly Fitness Plan",
  "description": "My workout schedule for this week",
  "plan_type": "weekly",
  "start_date": "2026-05-11",
  "end_date": "2026-05-17",
  "linked_goal_ids": ["goal-uuid-here"],
  "linked_habit_ids": ["habit-uuid-here"]
}
```

Plan types: `weekly`, `monthly`, `project`, `goal_based`

### List Plans

```bash
GET /goals/plans/list?status=active
```

---

## Todos API

Todos are individual tasks with due dates and priority.

### Create a Todo

```bash
POST /goals/todos
```

```json
{
  "title": "Monday Morning Run",
  "description": "5km easy pace run",
  "plan_id": "plan-uuid-here",
  "category": "physical",
  "priority": 1,
  "due_date": "2026-05-12",
  "due_time": "07:00",
  "estimated_minutes": 45,
  "linked_goal_id": "goal-uuid-here",
  "linked_habit_id": "habit-uuid-here"
}
```

**Priority:** 1=high, 2=medium, 3=low

### List Todos

```bash
GET /goals/todos/list?status=pending&priority=1
```

### Get Today's Todos

```bash
GET /goals/todos/today
```

Returns pending todos due today or overdue.

### Complete a Todo

```bash
POST /goals/todos/{todo_id}/complete
```

Marks todo complete and recalculates parent plan progress.

---

## Budget API

Track income, expenses, and savings with category budgets.

### Create Budget Category

```bash
POST /budget/categories
```

```json
{
  "name": "Monthly Savings",
  "type": "savings",
  "monthly_limit": 500,
  "color": "#4CAF50",
  "icon": "piggy-bank",
  "alert_threshold": 90
}
```

**Types:** `income`, `expense`, `savings`

**Recurring Category Example:**
```json
{
  "name": "Rent",
  "type": "expense",
  "monthly_limit": 1200,
  "is_recurring": true,
  "recurring_amount": 1200,
  "recurring_day": 1,
  "color": "#FF5722",
  "icon": "home"
}
```

### Add Transaction

```bash
POST /budget/transactions
```

```json
{
  "amount": 45.67,
  "type": "expense",
  "description": "Grocery shopping at Whole Foods",
  "category_id": "category-uuid-here",
  "transaction_date": "2026-05-11",
  "payment_method": "card",
  "merchant": "Whole Foods",
  "tags": ["groceries", "organic"]
}
```

**Types:** `income`, `expense`, `transfer`

### Get Monthly Summary

```bash
GET /budget/summary/monthly?year=2026&month=5
```

Response:
```json
{
  "year": 2026,
  "month": 5,
  "income": 5000,
  "expenses": 3200,
  "savings": 1000,
  "net": 1800,
  "category_breakdown": {
    "category-id": {
      "name": "Groceries",
      "spent": 450,
      "limit": 600,
      "percent_used": 75,
      "alert": false
    }
  }
}
```

### Check Affordability

```bash
POST /budget/can-afford
```

```json
{
  "amount": 200
}
```

Response:
```json
{
  "can_afford": true,
  "requested_amount": 200,
  "current_month_net": 1800,
  "remaining_after_purchase": 1600,
  "percent_of_monthly_income": 4,
  "recommendation": "affordable"
}
```

Use this when user asks "Can I afford X?" or "Should I buy Y?"

### Get Upcoming Payments

```bash
GET /budget/upcoming-payments?days_ahead=7
```

Returns recurring payments due in next N days.

---

## Agent Guidelines

### When User Mentions Tasks

1. **Create actionable todos** linked to relevant goals
2. **Set realistic due dates** and priorities
3. **Estimate time** needed to complete
4. **Link to habits** if it's a recurring task

Example user request:
> "I need to finish my presentation by Friday"

Agent action:
- Create todo: "Complete presentation slides"
- Due date: Friday
- Priority: 1 (high)
- Estimated: 120 minutes
- Linked to career goal if exists

### When User Mentions Goals

1. **Help define SMART criteria** - ask for specifics if unclear
2. **Suggest target values** and units for measurable progress
3. **Set realistic timelines** based on current state
4. **Create supporting habits** for ongoing goals
5. **Break into sub-goals** for large objectives

Example user request:
> "I want to get fit"

Agent action:
- Ask: "What does 'fit' mean to you specifically?" (measurable)
- Suggest: "Run 5K" or "Bench press bodyweight"
- Set target date 3-6 months out
- Create habits: "Daily exercise", "Track meals"
- Link habit to goal

### When User Mentions Money

1. **Categorize transactions** appropriately
2. **Alert on overspending** when category threshold hit
3. **Calculate affordability** for purchase questions
4. **Track progress** toward savings goals

Example user request:
> "Should I buy this $300 headset?"

Agent action:
- Call `/budget/can-afford` with amount 300
- If affordable: "Yes, that's 6% of your monthly income"
- If not: "That would exceed your budget by $X"
- Suggest: "You need $Y more to afford this comfortably"

### When User Mentions Progress

1. **Fetch current stats** from relevant endpoints
2. **Calculate trends** (completion rate, streaks)
3. **Celebrate milestones** (50%, 75%, 100%)
4. **Suggest adjustments** if behind schedule

Example user request:
> "How am I doing with my goals?"

Agent action:
- Call `/goals/summary`
- Call `/habits/today` for habit status
- Report: "You're at 73% completion rate for habits, 2 goals in progress"

---

## Error Handling

Common HTTP status codes:
- `200` - Success
- `404` - Resource not found (wrong ID)
- `422` - Validation error (check field types)
- `500` - Server error (check logs)

Always validate:
- UUIDs are properly formatted
- Dates are ISO format (YYYY-MM-DD)
- Required fields are present
- Enums match allowed values

---

## Integration with Chat

When user sends task/goal/budget related messages in chat, the planner should:

1. Detect intent (create, update, query, delete)
2. Extract entities (what, when, how much)
3. Call appropriate API
4. Summarize result in natural language

Example:
```
User: "I just finished my 30 minute run"
→ Planner detects: log_habit
→ API: POST /habits/{id}/log with value=30
→ Response: "Great job! Logged 30 minutes for Morning Exercise. 
             You're on a 3-day streak!"
```
