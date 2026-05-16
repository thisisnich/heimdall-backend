import asyncio
from atlas.db.session import get_session
from atlas.services import budget_service

async def check_budget():
    async with get_session() as session:
        # Get budget categories
        categories = await budget_service.list_budget_categories(session, 'default')
        print('=== BUDGET CATEGORIES ===')
        for cat in categories:
            print(f'{cat.name}: monthly_limit={cat.monthly_limit}, type={cat.type}')
        
        # Get monthly summary
        from datetime import date
        summary = await budget_service.get_monthly_summary(session, 'default')
        print('\n=== MONTHLY SUMMARY ===')
        print(f'Income: {summary["income"]}')
        print(f'Expenses: {summary["expenses"]}')
        print(f'Net: {summary["net"]}')
        print(f'Transaction count: {summary["transaction_count"]}')
        
        # Get recent transactions
        transactions = await budget_service.list_transactions(session, 'default', limit=20)
        print('\n=== RECENT TRANSACTIONS ===')
        for tx in transactions:
            print(f'{tx.transaction_date} | {tx.type} | ${tx.amount} | {tx.description} | category_id={tx.category_id}')

asyncio.run(check_budget())
