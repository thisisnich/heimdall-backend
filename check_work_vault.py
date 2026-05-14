"""Check VaultNote entries for work vault."""
import asyncio
from atlas.db.session import get_session
from atlas.db.models import VaultNote
from sqlalchemy import select

async def check_work_vault():
    async with get_session() as session:
        result = await session.execute(
            select(VaultNote.path).where(VaultNote.vault == 'work')
        )
        paths = [row[0] for row in result.all()]
        print(f'Work vault paths ({len(paths)}):')
        for p in paths[:20]:
            print(f'  {p}')

if __name__ == "__main__":
    asyncio.run(check_work_vault())
