# Quick Reference: Habits, Goals & Budget API

## Common Operations

### Create a Habit with SMART Goals
```bash
curl -X POST http://localhost:8000/habits \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Read Books",
    "specific": "Read 20 pages of non-fiction",
    "measurable": "Track pages in reading app",
    "achievable": "20 pages takes ~30 min before bed",
    "relevant": "Expands knowledge and improves focus",
    "time_bound": "Daily for 3 months to complete 12 books",
    "frequency": "daily",
    "category": "education"
  }'
```

### Log Habit Completion Today
```bash
curl -X POST http://localhost:8000/habits/{habit_id}/log \
  -H "Content-Type: application/json" \
  -d '{"log_date":"2026-05-11","completed":true,"value":20}'
```

### Create a SMART Goal
```bash
curl -X POST http://localhost:8000/goals \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Save Emergency Fund",
    "category": "financial",
    "specific": "Save 6 months expenses",
    "measurable": "Track in savings account",
    "achievable": "Save $500/month",
    "relevant": "Financial security",
    "time_bound": "Complete by Dec 2026",
    "target_value": 15000,
    "unit": "dollars"
  }'
```

### Create a Todo
```bash
curl -X POST http://localhost:8000/goals/todos \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Call dentist",
    "due_date": "2026-05-15",
    "priority": 2,
    "estimated_minutes": 15
  }'
```

### Mark Todo Complete
```bash
curl -X POST http://localhost:8000/goals/todos/{todo_id}/complete
```

### Add Budget Category
```bash
curl -X POST http://localhost:8000/budget/categories \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dining Out",
    "type": "expense",
    "monthly_limit": 300
  }'
```

### Add Transaction
```bash
curl -X POST http://localhost:8000/budget/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 45.50,
    "type": "expense",
    "description": "Lunch with team",
    "category_id": "{category_uuid}"
  }'
```

### Check Affordability
```bash
curl -X POST http://localhost:8000/budget/can-afford \
  -H "Content-Type: application/json" \
  -d '{"amount": 200}'
```

## Query Endpoints

| What | Endpoint |
|------|----------|
| Today's habits | `GET /habits/today` |
| Habit stats | `GET /habits/{id}/stats` |
| All goals | `GET /goals` |
| Goals by category | `GET /goals?category=physical` |
| Goal summary | `GET /goals/summary` |
| Today's todos | `GET /goals/todos/today` |
| Monthly budget | `GET /budget/summary/monthly` |
| Upcoming payments | `GET /budget/upcoming-payments` |

## Update Operations

```bash
# Update habit
curl -X PATCH http://localhost:8000/habits/{id} \
  -d '{"target_days_per_week": 6}'

# Update goal progress
curl -X POST http://localhost:8000/goals/{id}/progress \
  -d '{"current_value": 25}'

# Add savings to goal
curl -X POST http://localhost:8000/goals/{id}/add-savings \
  -d '{"amount": 500}'
```

## SMART Goal Template

When creating goals/habits, fill these fields:

```json
{
  "specific": "What exactly? (action, location, context)",
  "measurable": "How much/many? How will you track?",
  "achievable": "Is this realistic given current resources?",
  "relevant": "Why does this matter? What benefit?",
  "time_bound": "By when? What milestones?"
}
```

## Category Colors

| Category | Color Code |
|----------|------------|
| physical | #F44336 (red) |
| education | #2196F3 (blue) |
| financial | #4CAF50 (green) |
| career | #9C27B0 (purple) |
| health | #E91E63 (pink) |
| personal | #FF9800 (orange) |
