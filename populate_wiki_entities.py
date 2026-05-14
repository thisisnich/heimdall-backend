"""Populate VaultNote table for wiki entities."""
import asyncio
from pathlib import Path
from sqlalchemy import select
from atlas.db.session import get_session
from atlas.db.models import VaultNote

async def populate_wiki_entities():
    """Scan wiki/entities and populate VaultNote table."""
    vault_root = Path("/opt/heimdall/vault")
    wiki_entities_dir = vault_root / "wiki" / "entities"
    
    if not wiki_entities_dir.exists():
        print("wiki/entities directory not found")
        return
    
    async with get_session() as session:
        # Get existing paths
        existing = await session.execute(
            select(VaultNote.path).where(VaultNote.vault == 'wiki')
        )
        existing_paths = {row[0] for row in existing.all()}
        print(f"Existing wiki entries: {len(existing_paths)}")
        
        # Scan wiki/entities
        new_entries = 0
        for md_file in wiki_entities_dir.glob("*.md"):
            relative_path = md_file.relative_to(vault_root)
            full_path = str(relative_path).replace('\\', '/')
            
            if full_path in existing_paths:
                continue
            
            # Extract title from filename (remove .md)
            title = md_file.stem
            
            note = VaultNote(
                path=full_path,
                title=title,
                vault='wiki',
                node_type='entity'
            )
            session.add(note)
            new_entries += 1
            print(f"  Adding: {full_path}")
        
        if new_entries > 0:
            await session.commit()
            print(f"\nAdded {new_entries} new wiki entity entries")
        else:
            print("\nNo new wiki entities needed")

if __name__ == "__main__":
    asyncio.run(populate_wiki_entities())
