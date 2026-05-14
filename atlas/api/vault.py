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
    full_path = VAULT_ROOT / file_path
    try:
        full_path.resolve().relative_to(VAULT_ROOT.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    # Security: only allow .md files
    if not full_path.suffix.lower() == ".md":
        raise HTTPException(status_code=400, detail="Only .md files can be updated")
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        full_path.write_text(update.content, encoding="utf-8")
        return {"status": "success", "path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest")
async def ingest_file(upload: FileUpload):
    """Ingest a file and convert it to markdown in the vault."""
    from markitdown import MarkItDown
    from datetime import date
    import re
    import tempfile
    import os
    
    # Course mapping
    COURSE_MAP = {
        "EGE353": "EGE353 Autonomous Robotics",
        "EGE320": "EGE320 Embedded System Design &Technology",
        "EGE321": "EGE321 Wireless Communication & Networking",
        "EGE351": "EGE351 Automatino Systems & Control",
        "EGE322": "EGE322 IOT System Project",
        "EGE301": "EGE301 Communication & Workplace Success",
    }
    
    COURSE_PATTERNS = [r"EGE\d{3}", r"EGE\d{3}[A-Z]?"]
    
    def detect_course(content: str) -> str:
        """Detect course code from content."""
        for pattern in COURSE_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                course = matches[0].upper()
                if course in COURSE_MAP:
                    return course
        return "FILL_IN"
    
    def format_markdown(content: str) -> str:
        """Format markdown content with better structure."""
        lines = content.split('\n')
        formatted = []
        in_frontmatter = False
        
        for line in lines:
            # Skip existing frontmatter
            if line.strip() == '---':
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    in_frontmatter = False
                    continue
            if in_frontmatter:
                continue
            
            stripped = line.strip()
            
            # Detect and format headers based on common patterns
            if stripped.isupper() and len(stripped) < 50 and stripped and not stripped.startswith('Page'):
                if any(keyword in stripped.lower() for keyword in ['objectives', 'equipment', 'components', 'tasks', 'understandings', 'questions']):
                    formatted.append(f"\n## {stripped}\n")
                elif any(keyword in stripped.lower() for keyword in ['task', 'question']):
                    formatted.append(f"\n### {stripped}\n")
                else:
                    formatted.append(f"\n# {stripped}\n")
            elif stripped and len(stripped) > 1 and stripped[0].isdigit() and stripped[1] in [')', '.']:
                # Numbered list items
                formatted.append(f"- {stripped}")
            elif stripped.startswith(('a)', 'b)', 'c)', 'd)')):
                # Lettered list items
                formatted.append(f"- {stripped}")
            elif stripped:
                formatted.append(stripped)
        
        return '\n'.join(formatted)
    
    try:
        # Create temporary file for conversion
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(upload.filename)[1]) as tmp_file:
            tmp_file.write(upload.content.encode('utf-8'))
            tmp_path = tmp_file.name
        
        # Convert to markdown
        md = MarkItDown()
        result = md.convert(tmp_path)
        body = result.text_content or ""
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        # Detect course from content
        course = detect_course(body)
        
        # Format the markdown content
        formatted_body = format_markdown(body)
        
        # Create frontmatter
        frontmatter = f"""---
tags:
  - {course}
  - FILL_IN
course: {course}
topic: FILL_IN
source: {upload.filename}
converted: {date.today().isoformat()}
---

"""
        
        # Determine output path
        folder_name = COURSE_MAP.get(course)
        if folder_name:
            dest_folder = VAULT_ROOT / folder_name
            if dest_folder.exists():
                # Save to course folder
                stem = os.path.splitext(upload.filename)[0]
                out_path = dest_folder / (stem + ".md")
                counter = 1
                while out_path.exists():
                    out_path = dest_folder / f"{stem}_{counter}.md"
                    counter += 1
                out_path.write_text(frontmatter + formatted_body, encoding="utf-8")
                return {
                    "status": "success",
                    "path": str(out_path.relative_to(VAULT_ROOT)),
                    "course": course,
                    "message": f"Converted and saved to {folder_name}"
                }
        
        # Fall back to work/fyp if course folder not found
        dest_folder = VAULT_ROOT / "work" / "fyp"
        dest_folder.mkdir(parents=True, exist_ok=True)
        stem = os.path.splitext(upload.filename)[0]
        out_path = dest_folder / (stem + ".md")
        counter = 1
        while out_path.exists():
            out_path = dest_folder / f"{stem}_{counter}.md"
            counter += 1
        out_path.write_text(frontmatter + formatted_body, encoding="utf-8")
        
        return {
            "status": "success",
            "path": str(out_path.relative_to(VAULT_ROOT)),
            "course": course,
            "message": f"Converted and saved to work/fyp (course folder not found)"
        }
        
    except ImportError:
        raise HTTPException(status_code=500, detail="markitdown not installed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
