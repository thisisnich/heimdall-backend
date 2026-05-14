"""Check actual link source/target paths in KnowledgeLink."""
import asyncio
from atlas.db.session import get_session
from atlas.db.models import KnowledgeLink
from sqlalchemy import select

async def check_links():
    async with get_session() as session:
        result = await session.execute(
            select(KnowledgeLink.source, KnowledgeLink.target).limit(20)
        )
        links = result.all()
        print(f'Link source/target pairs ({len(links)}):')
        for source, target in links:
            print(f'  {source} -> {target}')

if __name__ == "__main__":
    asyncio.run(check_links())
