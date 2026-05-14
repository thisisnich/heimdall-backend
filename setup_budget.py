"""Setup budget categories with correct limits."""
import asyncio
from atlas.db.session import get_session
from atlas.services.budget_service import create_budget_category, list_budget_categories, update_budget_category

async def setup_budgets():
    """Set up budget categories with correct limits."""
    async with get_session() as session:
        user_id = "default"
        
        # List existing categories
        categories = await list_budget_categories(session, user_id)
        print(f"Existing categories: {[(c.id, c.name, c.monthly_limit) for c in categories]}")
        
        # Create or update Food category
        food_cat = next((c for c in categories if c.name.lower() == "food"), None)
        if food_cat:
            await update_budget_category(session, food_cat.id, user_id, monthly_limit=150.0)
            print(f"Updated Food category limit to $150")
        else:
            await create_budget_category(
                session, user_id, name="Food", type="expense",
                color="#FF5722", icon="utensils", monthly_limit=150.0
            )
            print(f"Created Food category with $150 limit")
        
        # Create or update Transport category
        transport_cat = next((c for c in categories if c.name.lower() == "transport"), None)
        if transport_cat:
            await update_budget_category(session, transport_cat.id, user_id, monthly_limit=29.0)
            print(f"Updated Transport category limit to $29")
        else:
            await create_budget_category(
                session, user_id, name="Transport", type="expense",
                color="#2196F3", icon="bus", monthly_limit=29.0
            )
            print(f"Created Transport category with $29 limit")
        
        print("Budget setup complete!")

if __name__ == "__main__":
    asyncio.run(setup_budgets())
