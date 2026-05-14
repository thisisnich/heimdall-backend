"""Populate VaultNote table for all vault files."""
import asyncio
from pathlib import Path
from sqlalchemy import select, delete
from atlas.db.session import get_session
from atlas.db.models import VaultNote

async def populate_vault_notes():
    """Scan all vaults and populate VaultNote table for any missing files."""
    vault_root = Path("/opt/heimdall/vault")
    
    async with get_session() as session:
        # Get existing paths
        existing = await session.execute(select(VaultNote.path))
        existing_paths = {row[0] for row in existing.all()}
        print(f"Existing VaultNote entries: {len(existing_paths)}")
        
        # Scan all vaults
        new_entries = 0
        for vault_dir in vault_root.iterdir():
            if not vault_dir.is_dir() or vault_dir.name.startswith('.'):
                continue
            
            vault_name = vault_dir.name
            print(f"\nScanning vault: {vault_name}")
            
            for md_file in vault_dir.rglob("*.md"):
                relative_path = md_file.relative_to(vault_root)
                full_path = str(relative_path).replace('\\', '/')
                
                if full_path in existing_paths:
                    continue
                
                # Extract title from filename (remove .md)
                title = md_file.stem
                
                # Determine node type
                node_type = "note"
                if vault_name == "wiki" and "/" in full_path:
                    node_type = "entity"
                
                note = VaultNote(
                    path=full_path,
                    title=title,
                    vault=vault_name,
                    node_type=node_type
                )
                session.add(note)
                new_entries += 1
        
        if new_entries > 0:
            await session.commit()
            print(f"\nAdded {new_entries} new VaultNote entries")
        else:
            print("\nNo new entries needed")

if __name__ == "__main__":
    asyncio.run(populate_vault_notes())
