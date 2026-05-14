"""
Vault API — endpoints for triggering and inspecting the Obsidian vault sync.
"""
import os
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from atlas.core.vault_writer import sync_vault, VAULT_ROOT

router = APIRouter(prefix="/vault", tags=["vault"])


class FileUpdate(BaseModel):
    content: str


@router.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks):
    """Trigger a full vault sync in the background."""
    background_tasks.add_task(sync_vault)
    return {"status": "sync started", "vault_path": str(VAULT_ROOT)}


@router.post("/sync/now")
async def trigger_sync_blocking():
    """Trigger a full vault sync and wait for it to complete. Returns summary."""
    result = await sync_vault()
    return {"status": "done", "vault_path": str(VAULT_ROOT), **result}


@router.get("/status")
async def vault_status():
    """Return vault file counts per section."""
    folders = ["people", "goals", "places", "ideas", "journal", "wiki"]
    status = {}
    for folder in folders:
        path = VAULT_ROOT / folder
        if path.exists():
            files = list(path.glob("*.md"))
            status[folder] = {"files": len(files), "names": [f.stem for f in files]}
        else:
            status[folder] = {"files": 0, "names": []}
    index_exists = (VAULT_ROOT / "_index.md").exists()
    return {
        "vault_path": str(VAULT_ROOT),
        "index_exists": index_exists,
        "sections": status,
    }


@router.get("/files")
async def list_files(course: str = None, topic: str = None):
    """List markdown files in the vault, optionally filtered by course/topic."""
    files = []
    
    # Look in work/fyp directory for study materials
    study_path = VAULT_ROOT / "work/fyp"
    
    # If course specified, filter files by course code
    if course:
        # List all markdown files and filter by course code in filename
        if study_path.exists():
            for file in study_path.glob("*.md"):
                if course in file.name:
                    files.append({
                        "name": file.name,
                        "path": str(file.relative_to(VAULT_ROOT)),
                        "stem": file.stem,
                        "size": file.stat().st_size,
                        "modified": file.stat().st_mtime,
                    })
    else:
        # List all markdown files in study directory
        if study_path.exists():
            for file in study_path.glob("*.md"):
                # Skip hidden files
                if not file.name.startswith("."):
                    files.append({
                        "name": file.name,
                        "path": str(file.relative_to(VAULT_ROOT)),
                        "stem": file.stem,
                        "size": file.stat().st_size,
                        "modified": file.stat().st_mtime,
                    })
    
    # Sort by name
    files.sort(key=lambda x: x["name"])
    return {"files": files}


@router.get("/files/{file_path:path}")
async def get_file(file_path: str):
    """Get the content of a specific file from the vault."""
    # Security: ensure path doesn't escape vault root
    file_path = Path(file_path)
    if ".." in str(file_path) or file_path.is_absolute():
        raise HTTPException(status_code=400, detail="Invalid path")
    
    full_path = VAULT_ROOT / file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if not full_path.suffix == ".md":
        raise HTTPException(status_code=400, detail="Only markdown files supported")
    
    content = full_path.read_text(encoding="utf-8")
    return {
        "path": str(file_path),
        "name": file_path.name,
        "content": content,
        "size": full_path.stat().st_size,
        "modified": full_path.stat().st_mtime,
    }


@router.put("/files/{file_path:path}")
async def update_file(file_path: str, update: FileUpdate):
    """Update the content of a specific file in the vault."""
    # Security: ensure path doesn't escape vault root
    file_path = Path(file_path)
    if ".." in str(file_path) or file_path.is_absolute():
        raise HTTPException(status_code=400, detail="Invalid path")
    
    full_path = VAULT_ROOT / file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if not full_path.suffix == ".md":
        raise HTTPException(status_code=400, detail="Only markdown files supported")
    
    full_path.write_text(update.content, encoding="utf-8")
    return {
        "status": "updated",
        "path": str(file_path),
        "size": full_path.stat().st_size,
    }
