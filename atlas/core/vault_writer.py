"""
Vault Writer — syncs pgvector memory to Obsidian-compatible Markdown files.

Three-Vault Architecture:
  vault/
  ├── work/           ← Uni, FYP, courses, job, side projects
  │   ├── fyp/
  │   ├── courses/
  │   └── projects/
  ├── personal/       ← Life: goals, journal, health, finance
  │   ├── goals/
  │   ├── journal/
  │   └── health/
  ├── kb/             ← Knowledge base: concepts, tools, people, references
  │   ├── concepts/
  │   ├── tools/
  │   ├── people/
  │   └── entities/
  └── inbox/          ← Drop zone — auto-classified and moved by process_inbox.py

Each file uses YAML frontmatter + Markdown body.
Entries are appended/updated — never duplicated.
Links are extracted and stored for knowledge graph visualization.
"""

import os
import re
import logging
import hashlib
from datetime import date, datetime
from pathlib import Path
from typing import Optional
from atlas.db.vector_store import browse, counts

logger = logging.getLogger(__name__)

VAULT_ROOT = Path(os.getenv("VAULT_PATH", "/opt/heimdall/vault"))

# Three-vault structure
VAULTS = {
    "work":     ["fyp", "courses", "projects"],
    "personal": ["goals", "journal", "health"],
    "kb":        ["concepts", "tools", "people", "entities"],
    "inbox":     [],  # Drop zone — items get classified and moved
}

# Maps source_type → (vault, subfolder)
TYPE_TO_PATH = {
    "person":     ("kb",       "people"),
    "goal":       ("personal", "goals"),
    "place":      ("kb",       "concepts"),
    "idea":       ("personal", "goals"),
    "project":    ("work",     "projects"),
    "daily_log":  ("personal", "journal"),
    "event":      ("personal", "journal"),
    "preference": ("kb",       "concepts"),
    "fact":       ("kb",       "concepts"),
    "chat_input": ("personal", "journal"),
    "youtube":    ("kb",       "concepts"),
    "transcript": ("kb",       "concepts"),
    "entity":     ("kb",       "entities"),
    "course":     ("work",     "courses"),
    "tool":       ("kb",       "tools"),
    "vault_note": ("kb",       "concepts"),
}


def _ensure_vault():
    """Create all vault folders if they don't exist."""
    VAULT_ROOT.mkdir(parents=True, exist_ok=True)
    
    for vault_name, subfolders in VAULTS.items():
        vault_path = VAULT_ROOT / vault_name
        vault_path.mkdir(exist_ok=True)
        for subfolder in subfolders:
            (vault_path / subfolder).mkdir(exist_ok=True)
    


def _slug(text: str) -> str:
    """Convert text to a safe filename slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:60].strip("-")


def _extract_subject(text: str, source_type: str) -> str:
    """
    Try to extract a subject/title from the fact text.
    Falls back to a truncated slug of the text itself.
    """
    text = text.strip()

    # "User's friend James works at..." → "james"
    name_patterns = [
        r"user(?:'s)?\s+(?:friend|colleague|contact|brother|sister|mother|father|partner|boss)\s+(\w+)",
        r"^(\w+)\s+(?:is|was|works|lives|went|said|told)",
        r"person named\s+(\w+)",
    ]
    if source_type == "person":
        for pat in name_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1).capitalize()

    # For goals: extract verb phrase
    if source_type == "goal":
        m = re.search(r"wants? to (.{5,40}?)(?:\.|,|$)", text, re.IGNORECASE)
        if m:
            return _slug(m.group(1))[:40]

    # Default: use first 5 words
    words = text.split()[:5]
    return _slug(" ".join(words))


def _compute_checksum(content: str) -> str:
    """Compute SHA256 checksum for content integrity."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _extract_frontmatter(content: str) -> tuple:
    """Extract YAML frontmatter from markdown if present."""
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            return parts[1].strip(), parts[2].strip()
    return "", content


def _get_vault_path(entry: dict) -> tuple:
    """
    Determine the vault and file path for a given entry.
    Returns (vault_name, relative_path, full_path)
    """
    source_type = entry.get("source_type", "fact")
    
    # Check if entry specifies explicit vault
    explicit_vault = entry.get("vault", "")
    if explicit_vault and explicit_vault in VAULTS:
        vault = explicit_vault
        subfolder = entry.get("folder", "")
    else:
        # Use type mapping
        vault, subfolder = TYPE_TO_PATH.get(source_type, ("wiki", "concepts"))
    
    # Build folder path
    if subfolder:
        folder = VAULT_ROOT / vault / subfolder
    else:
        folder = VAULT_ROOT / vault
    
    folder.mkdir(parents=True, exist_ok=True)
    
    # Determine filename
    if source_type in ("daily_log", "event", "chat_input"):
        # Journal files are per-day
        source_path = entry.get("source_path", "")
        m = re.search(r"(\d{4}-\d{2}-\d{2})", source_path)
        day = m.group(1) if m else date.today().isoformat()
        filename = f"{day}.md"
        relative_path = f"{subfolder}/{filename}" if subfolder else filename
    else:
        subject = _extract_subject(entry["text"], source_type)
        filename = f"{subject}.md"
        relative_path = f"{subfolder}/{filename}" if subfolder else filename
    
    full_path = folder / filename
    
    return vault, relative_path, full_path


def _get_file_path(entry: dict) -> Path:
    """Legacy function for backward compatibility."""
    _, _, full_path = _get_vault_path(entry)
    return full_path


def _entry_already_in_file(file_path: Path, entry_id: str, text: str) -> bool:
    """Check if this entry is already written to the file (by id or text prefix)."""
    if not file_path.exists():
        return False
    content = file_path.read_text(encoding="utf-8")
    if entry_id in content:
        return True
    # Also dedup by first 60 chars of text
    if text[:60].lower() in content.lower():
        return True
    return False


def _write_entry_to_file(file_path: Path, entry: dict, source_type: str, vault: str = "wiki"):
    """
    Append this entry to the target .md file, creating it with frontmatter if new.
    Also extracts and stores links for knowledge graph.
    """
    text = entry["text"]
    entry_id = entry["id"]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Compute relative path for this file
    relative_path = str(file_path.relative_to(VAULT_ROOT))

    if not file_path.exists():
        # Create file with YAML frontmatter
        subject_display = file_path.stem.replace("-", " ").title()
        frontmatter = f"""---
id: "{entry_id}"
title: "{subject_display}"
type: {source_type}
vault: {vault}
created: {date.today().isoformat()}
updated: {date.today().isoformat()}
checksum: ""
source: heimdall/auto
---

# {subject_display}

"""
        file_path.write_text(frontmatter, encoding="utf-8")
        is_new_file = True
    else:
        # Update the 'updated' field in frontmatter
        content = file_path.read_text(encoding="utf-8")
        content = re.sub(
            r"^updated: .+$",
            f"updated: {date.today().isoformat()}",
            content,
            flags=re.MULTILINE,
        )
        file_path.write_text(content, encoding="utf-8")
        is_new_file = False

    # Append the entry
    with file_path.open("a", encoding="utf-8") as f:
        if source_type in ("daily_log", "event", "chat_input"):
            # Journal entries: plain timestamped lines
            f.write(f"- {ts}: {text}\n")
        else:
            # Fact entries: bullet with metadata comment
            f.write(f"- {text} <!-- id:{entry_id} ts:{ts} -->\n")
    
    # Update checksum in frontmatter
    new_content = file_path.read_text(encoding="utf-8")
    checksum = _compute_checksum(new_content)
    new_content = re.sub(
        r"^checksum: .*$",
        f'checksum: "sha256:{checksum}"',
        new_content,
        flags=re.MULTILINE,
    )
    file_path.write_text(new_content, encoding="utf-8")
    
    return is_new_file, relative_path


def _write_index(written: int, table_counts: dict):
    """Write/overwrite vault/_index.md with a vault overview."""
    index_path = VAULT_ROOT / "_index.md"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = sum(table_counts.values())

    lines = [
        "---",
        "title: Heimdall Vault Index",
        f"updated: {now}",
        "---",
        "",
        "# Heimdall Vault",
        "",
        f"> Last synced: {now} — {total} total memory entries across {len(table_counts)} tables",
        "",
        "## Sections",
        "",
    ]

    section_map = {
        "people":  ("👤", "People", "people/"),
        "goals":   ("🎯", "Goals", "goals/"),
        "ideas":   ("💡", "Ideas & Projects", "ideas/"),
        "places":  ("📍", "Places", "places/"),
        "journal": ("📓", "Journal", "journal/"),
        "wiki":    ("📚", "Wiki / Facts", "wiki/"),
    }

    for folder, (icon, label, path) in section_map.items():
        folder_path = VAULT_ROOT / folder
        file_count = len(list(folder_path.glob("*.md"))) if folder_path.exists() else 0
        lines.append(f"- {icon} **[[{path}|{label}]]** — {file_count} file(s)")

    lines += [
        "",
        "## Memory Table Counts",
        "",
    ]
    for table, count in table_counts.items():
        lines.append(f"- `{table}`: {count} entries")

    lines += ["", f"*Auto-generated by Heimdall vault writer. Do not edit manually.*", ""]
    index_path.write_text("\n".join(lines), encoding="utf-8")


async def sync_vault() -> dict:
    """
    Main entry point. Reads all vector_memory + vector_notes entries
    and writes them to the Obsidian vault. Idempotent — safe to run repeatedly.
    Returns a summary dict.
    """
    _ensure_vault()

    written = 0
    skipped = 0
    errors = 0

    # Sync vector_memory (facts, people, goals, ideas, places, preferences)
    try:
        memory_entries = await browse("vector_memory", limit=2000)
    except Exception as e:
        logger.error(f"Vault sync: could not browse vector_memory: {e}")
        memory_entries = []

    # Sync vector_notes (daily logs)
    try:
        notes_entries = await browse("vector_notes", limit=2000)
    except Exception as e:
        logger.error(f"Vault sync: could not browse vector_notes: {e}")
        notes_entries = []

    all_entries = memory_entries + notes_entries

    for entry in all_entries:
        try:
            file_path = _get_file_path(entry)
            if _entry_already_in_file(file_path, entry["id"], entry["text"]):
                skipped += 1
                continue
            _write_entry_to_file(file_path, entry, entry.get("source_type", "fact"))
            written += 1
        except Exception as e:
            logger.warning(f"Vault sync error on entry {entry.get('id', '?')}: {e}")
            errors += 1

    # Update index
    try:
        table_counts = await counts()
        _write_index(written, table_counts)
    except Exception as e:
        logger.warning(f"Vault index write failed: {e}")

    logger.info(f"Vault sync complete: written={written} skipped={skipped} errors={errors}")
    return {"written": written, "skipped": skipped, "errors": errors, "total": len(all_entries)}


async def sync_entry(entry: dict, db_session=None):
    """
    Write a single entry to the vault immediately.
    Called from the indexer after each chat turn for real-time sync.
    Also updates VaultNote table and extracts links if db_session provided.
    """
    from atlas.core.backlinks import extract_all_links, store_links_in_db
    from atlas.db.models import VaultNote
    
    _ensure_vault()
    try:
        vault, relative_path, file_path = _get_vault_path(entry)
        
        if _entry_already_in_file(file_path, entry["id"], entry["text"]):
            return {"status": "skipped", "path": str(file_path)}
        
        is_new, rel_path = _write_entry_to_file(
            file_path, entry, entry.get("source_type", "fact"), vault
        )
        
        # Update database if session provided
        if db_session:
            # Upsert VaultNote record
            full_path = f"{vault}/{relative_path}"
            
            # Check if note exists
            from sqlalchemy import select
            result = await db_session.execute(
                select(VaultNote).where(VaultNote.path == full_path)
            )
            existing = result.scalar_one_or_none()
            
            content = file_path.read_text(encoding="utf-8")
            checksum = _compute_checksum(content)
            
            if existing:
                existing.content = content
                existing.checksum = checksum
                existing.updated_at = datetime.utcnow()
            else:
                note = VaultNote(
                    vault=vault,
                    path=full_path,
                    title=entry.get("title", file_path.stem.replace("-", " ").title()),
                    content=content,
                    node_type=entry.get("source_type", "note"),
                    note_id=entry["id"],
                    checksum=checksum,
                )
                db_session.add(note)
            
            await db_session.commit()
            
            # Extract and store links
            links = extract_all_links(content, vault, relative_path)
            if links:
                await store_links_in_db(links, db_session)
        
        return {"status": "written", "path": str(file_path), "vault": vault}
        
    except Exception as e:
        logger.warning(f"Vault real-time sync failed for entry {entry.get('id', '?' )}: {e}")
        return {"status": "error", "error": str(e)}


async def write_note(
    vault: str,
    folder: str,
    filename: str,
    content: str,
    title: Optional[str] = None,
    source_type: str = "note",
    db_session=None
) -> dict:
    """
    Write a complete note file (not just append entry).
    Used for ingestion pipeline and entity pages.
    """
    from atlas.core.backlinks import extract_all_links, store_links_in_db
    from atlas.db.models import VaultNote
    from sqlalchemy import select
    
    _ensure_vault()
    
    # Ensure vault/folder exists
    folder_path = VAULT_ROOT / vault / folder if folder else VAULT_ROOT / vault
    folder_path.mkdir(parents=True, exist_ok=True)
    
    # Full file path
    file_path = folder_path / filename
    relative_path = f"{folder}/{filename}" if folder else filename
    full_vault_path = f"{vault}/{relative_path}"
    
    # Compute checksum
    checksum = _compute_checksum(content)
    
    # Write file
    file_path.write_text(content, encoding="utf-8")
    
    # Update database
    if db_session:
        result = await db_session.execute(
            select(VaultNote).where(VaultNote.path == full_vault_path)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.content = content
            existing.checksum = checksum
            existing.updated_at = datetime.utcnow()
        else:
            note = VaultNote(
                vault=vault,
                path=full_vault_path,
                title=title or file_path.stem.replace("-", " ").title(),
                content=content,
                node_type=source_type,
                checksum=checksum,
            )
            db_session.add(note)
        
        await db_session.commit()
        
        # Extract and store links
        links = extract_all_links(content, vault, relative_path)
        if links:
            await store_links_in_db(links, db_session)
    
    return {
        "status": "written",
        "path": full_vault_path,
        "vault": vault,
        "checksum": checksum
    }
