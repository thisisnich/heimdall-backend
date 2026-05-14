"""Clean up duplicate budget categories."""
import asyncio
from atlas.db.session import get_session
from atlas.services.budget_service import list_budget_categories, delete_budget_category

async def cleanup_duplicates():
    """Remove duplicate budget categories, keeping the ones with limits."""
    async with get_session() as session:
        user_id = "default"
        
        # List all categories
        categories = await list_budget_categories(session, user_id)
        print(f"All categories: {[(c.id, c.name, c.monthly_limit) for c in categories]}")
        
        # Group by name
        from collections import defaultdict
        by_name = defaultdict(list)
        for cat in categories:
            by_name[cat.name.lower()].append(cat)
        
        # For each duplicate group, keep the one with a limit, delete others
        for name, cats in by_name.items():
            if len(cats) > 1:
                # Sort by: has limit first, then by created_at (newer first)
                cats.sort(key=lambda c: (c.monthly_limit is not None, c.created_at), reverse=True)
                keep = cats[0]
                to_delete = cats[1:]
                print(f"\nDuplicate {name}:")
                print(f"  Keep: {keep.id} (limit: {keep.monthly_limit})")
                for cat in to_delete:
                    print(f"  Delete: {cat.id} (limit: {cat.monthly_limit})")
                    await delete_budget_category(session, cat.id, user_id)
        
        print("\nCleanup complete!")

if __name__ == "__main__":
    asyncio.run(cleanup_duplicates())
