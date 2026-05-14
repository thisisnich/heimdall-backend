#!/usr/bin/env python3
"""
Bulk Vault Importer — import existing Markdown notes into Heimdall.

Usage:
  # Import from a folder of notes (auto-detects best vault):
  python scripts/import_vault.py --source /path/to/your/notes --vault wiki

  # Import directly into a specific vault subfolder:
  python scripts/import_vault.py --source /path/to/notes --vault personal

  # Dry run (no writes):
  python scripts/import_vault.py --source /path/to/notes --vault wiki --dry-run

  # Skip embedding (graph only, fast):
  python scripts/import_vault.py --source /path/to/notes --vault wiki --no-embed

What it does:
  1. Copies .md files into /opt/heimdall/vault/<vault>/
  2. Registers each file in vault_notes table (graph node)
  3. Chunks + embeds content → vector_notes (semantic search)
  4. Extracts [[wiki links]] → knowledge_links (graph edges + backlinks)
  5. Prints a summary of what was imported

Both stores are updated so you get:
  - Fast semantic search (pgvector)
  - Knowledge graph with your existing links preserved
  - Obsidian-compatible vault files
"""

import asyncio
import argparse
import hashlib
import logging
import re
import shutil
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import asyncpg
from atlas.core.backlinks import (
    parse_frontmatter,
    extract_all_links,
    store_links_in_db,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("import_vault")

_RAW_URL = os.getenv("DATABASE_URL", "postgresql://heimdall:heimdall_secure_2026@localhost:5432/heimdall")
DATABASE_URL = _RAW_URL.replace("+asyncpg", "")
VAULT_ROOT = Path(os.getenv("VAULT_PATH", "/opt/heimdall/vault"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

VALID_VAULTS = {"personal", "wiki", "projects", "youtube", "inbox"}

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 150


# ── helpers ───────────────────────────────────────────────────────────────────

def _chunk(text: str) -> list[str]:
    text = text.strip()
    if len(text) <= CHUNK_SIZE:
        return [text] if text else []
    chunks, start = [], 0
    while start < len(text):
        end = start + CHUNK_SIZE
        if end < len(text):
            bp = text.rfind(". ", start, end)
            if bp > start + CHUNK_SIZE // 2:
                end = bp + 1
        chunks.append(text[start:end].strip())
        start = end - CHUNK_OVERLAP
    return [c for c in chunks if c]


def _checksum(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _title_from(path: Path, frontmatter: dict) -> str:
    if frontmatter.get("title"):
        return str(frontmatter["title"])
    # Try first H1
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


async def _embed(text: str) -> list[float]:
    import httpx
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
        )
        r.raise_for_status()
        return r.json()["embedding"]


# ── DB helpers ────────────────────────────────────────────────────────────────

async def _upsert_vault_note(conn, vault: str, rel_path: str, title: str,
                              content: str, node_type: str, frontmatter: dict):
    """Insert or update vault_notes row."""
    import uuid
    word_count = len(content.split())
    cs = _checksum(content)
    now = datetime.utcnow()

    existing = await conn.fetchrow(
        "SELECT id, checksum FROM vault_notes WHERE path = $1", rel_path
    )
    if existing:
        if existing["checksum"] == cs:
            return "skip"
        await conn.execute(
            """UPDATE vault_notes
               SET title=$2, content=$3, checksum=$4, word_count=$5, updated_at=$6
               WHERE path=$1""",
            rel_path, title, content, cs, word_count, now,
        )
        return "update"
    else:
        note_id = str(uuid.uuid4())
        await conn.execute(
            """INSERT INTO vault_notes
               (id, vault, path, title, content, node_type, checksum, word_count, created_at, updated_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
            note_id, vault, rel_path, title, content, node_type,
            cs, word_count, now, now,
        )
        return "insert"


async def _store_vector(conn, text: str, source_type: str, source_path: str,
                         embedding: list[float]):
    """Store a chunk in vector_notes."""
    import uuid
    entry_id = str(uuid.uuid4())
    vector_str = "[" + ",".join(map(str, embedding)) + "]"
    now = datetime.utcnow()
    await conn.execute(
        """INSERT INTO vector_notes (id, text, source_type, source_path, embedding, created_at)
           VALUES ($1, $2, $3, $4, $5::vector, $6)
           ON CONFLICT DO NOTHING""",
        entry_id, text, source_type, source_path, vector_str, now,
    )


async def _already_embedded(conn, source_path: str) -> bool:
    row = await conn.fetchrow(
        "SELECT 1 FROM vector_notes WHERE source_path = $1 LIMIT 1", source_path
    )
    return row is not None


# ── link storage (raw asyncpg version) ───────────────────────────────────────

async def _store_links_raw(conn, links: list[dict]):
    import uuid
    now = datetime.utcnow()
    for link in links:
        fwd_id = str(uuid.uuid4())
        bk_id = str(uuid.uuid4())
        await conn.execute(
            """INSERT INTO knowledge_links (id, source, target, link_type, is_backlink, context, created_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7)
               ON CONFLICT ON CONSTRAINT uix_link_direction DO NOTHING""",
            fwd_id, link["source"], link["target"],
            link.get("type", "wiki"), False,
            (link.get("context") or link.get("display") or "")[:500], now,
        )
        await conn.execute(
            """INSERT INTO knowledge_links (id, source, target, link_type, is_backlink, context, created_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7)
               ON CONFLICT ON CONSTRAINT uix_link_direction DO NOTHING""",
            bk_id, link["target"], link["source"],
            link.get("type", "wiki"), True,
            (link.get("context") or link.get("display") or "")[:500], now,
        )


# ── main import logic ─────────────────────────────────────────────────────────

async def import_vault(
    source_dir: Path,
    target_vault: str,
    dry_run: bool = False,
    no_embed: bool = False,
    skip_copy: bool = False,
):
    if target_vault not in VALID_VAULTS:
        log.error(f"Invalid vault '{target_vault}'. Choose from: {', '.join(sorted(VALID_VAULTS))}")
        sys.exit(1)

    md_files = sorted(source_dir.rglob("*.md"))
    if not md_files:
        log.warning(f"No .md files found in {source_dir}")
        return

    log.info(f"Found {len(md_files)} markdown files in {source_dir}")
    log.info(f"Target vault: {target_vault}   Dry run: {dry_run}   No embed: {no_embed}")

    dest_vault = VAULT_ROOT / target_vault
    dest_vault.mkdir(parents=True, exist_ok=True)

    conn = None if dry_run else await asyncpg.connect(DATABASE_URL)

    stats = {"copied": 0, "skipped": 0, "inserted": 0, "updated": 0,
             "embedded": 0, "links": 0, "errors": 0}

    try:
        for md_file in md_files:
            try:
                # ── 1. Determine destination path ──────────────────────────
                # Preserve subfolder structure relative to source root
                rel = md_file.relative_to(source_dir)
                dest_file = dest_vault / rel
                dest_file.parent.mkdir(parents=True, exist_ok=True)

                # Relative path used as DB key: "personal/goals/fyp.md"
                rel_path = f"{target_vault}/{rel.as_posix()}"

                raw = md_file.read_text(encoding="utf-8", errors="replace")
                frontmatter, body = parse_frontmatter(raw)
                title = _title_from(md_file, frontmatter)

                # ── 2. Copy file into vault ────────────────────────────────
                if not skip_copy:
                    if not dry_run:
                        shutil.copy2(md_file, dest_file)
                    stats["copied"] += 1

                if dry_run:
                    log.info(f"  [DRY] {rel_path}  |  {title}")
                    continue

                # ── 3. Upsert vault_notes (graph node) ────────────────────
                result = await _upsert_vault_note(
                    conn, target_vault, rel_path, title,
                    raw, "note", frontmatter,
                )
                if result == "skip":
                    stats["skipped"] += 1
                    log.debug(f"  SKIP (unchanged): {rel_path}")
                    continue
                elif result == "insert":
                    stats["inserted"] += 1
                    log.info(f"  INSERT: {rel_path}")
                else:
                    stats["updated"] += 1
                    log.info(f"  UPDATE: {rel_path}")

                # ── 4. Embed → vector_notes ────────────────────────────────
                if not no_embed:
                    already = await _already_embedded(conn, rel_path)
                    if not already:
                        chunks = _chunk(body or raw)
                        for i, chunk in enumerate(chunks):
                            try:
                                emb = await _embed(chunk)
                                await _store_vector(conn, chunk, "vault_note", rel_path, emb)
                                stats["embedded"] += 1
                            except Exception as e:
                                log.warning(f"    Embed chunk {i} failed: {e}")
                    else:
                        log.debug(f"  EMBED skip (already done): {rel_path}")

                # ── 5. Extract links → knowledge_links ────────────────────
                source_subpath = "/".join(rel.parts[1:]) if len(rel.parts) > 1 else rel.name
                links = extract_all_links(raw, target_vault, rel.as_posix())
                if links:
                    await _store_links_raw(conn, links)
                    stats["links"] += len(links)
                    log.debug(f"  Links: {len(links)}")

            except Exception as e:
                stats["errors"] += 1
                log.error(f"  ERROR processing {md_file}: {e}")

    finally:
        if conn:
            await conn.close()

    log.info("─" * 60)
    log.info("Import complete:")
    log.info(f"  Files copied  : {stats['copied']}")
    log.info(f"  DB inserted   : {stats['inserted']}")
    log.info(f"  DB updated    : {stats['updated']}")
    log.info(f"  DB skipped    : {stats['skipped']}")
    log.info(f"  Vector chunks : {stats['embedded']}")
    log.info(f"  Links stored  : {stats['links']}")
    if stats["errors"]:
        log.warning(f"  Errors        : {stats['errors']}")
    log.info("─" * 60)
    if not dry_run and not no_embed:
        log.info("✓ Semantic search + knowledge graph both updated.")
        log.info("  Hit the Graph tab in Heimdall — your notes are linked.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Bulk import Markdown notes into Heimdall")
    p.add_argument("--source", required=True,
                   help="Folder containing your .md notes")
    p.add_argument("--vault", required=True,
                   choices=sorted(VALID_VAULTS),
                   help="Target vault to import into")
    p.add_argument("--dry-run", action="store_true",
                   help="Preview without writing anything")
    p.add_argument("--no-embed", action="store_true",
                   help="Skip vector embedding (graph only, much faster)")
    p.add_argument("--skip-copy", action="store_true",
                   help="Files already in vault, skip the copy step")
    args = p.parse_args()

    asyncio.run(import_vault(
        source_dir=Path(args.source).expanduser().resolve(),
        target_vault=args.vault,
        dry_run=args.dry_run,
        no_embed=args.no_embed,
        skip_copy=args.skip_copy,
    ))
