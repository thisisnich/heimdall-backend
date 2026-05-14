"""Create wiki entity stubs in VaultNote table."""
import asyncio
from sqlalchemy import select
from atlas.db.session import get_session
from atlas.db.models import VaultNote

async def create_wiki_entities():
    """Create VaultNote entries for wiki entities referenced in links."""
    
    # Common wiki entities from your links
    wiki_entities = [
        "angular", "docker", "python", "obsidian",
    ]
    
    async with get_session() as session:
        # Get existing wiki paths
        existing = await session.execute(
            select(VaultNote.path).where(VaultNote.vault == 'wiki')
        )
        existing_paths = {row[0] for row in existing.all()}
        print(f"Existing wiki entries: {len(existing_paths)}")
        
        new_entries = 0
        for entity in wiki_entities:
            path = f"wiki/entities/{entity}.md"
            if path in existing_paths:
                print(f"  Skipping (exists): {path}")
                continue
            
            note = VaultNote(
                path=path,
                title=entity.replace('-', ' ').title(),
                vault='wiki',
                node_type='entity'
            )
            session.add(note)
            new_entries += 1
            print(f"  Adding: {path}")
        
        if new_entries > 0:
            await session.commit()
            print(f"Added {new_entries} new wiki entity entries")
        else:
            print("No new wiki entities needed")

if __name__ == "__main__":
    asyncio.run(create_wiki_entities())
