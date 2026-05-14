#!/usr/bin/env python3
"""
Inbox Processor — watches /opt/heimdall/vault/inbox/ and auto-classifies files.

Drop ANY .md file (or folder of .md files) into the inbox and run this.
Groq classifies each note and moves it to the right vault + subfolder.
Also embeds into vector_notes and registers in vault_notes DB.

Usage:
  # Process everything in inbox now:
  python scripts/process_inbox.py

  # Dry run (see where things would go, no writes):
  python scripts/process_inbox.py --dry-run

  # Watch mode (process as files arrive):
  python scripts/process_inbox.py --watch
"""

import asyncio
import argparse
import json
import logging
import os
import shutil
import sys
import time
import uuid
import hashlib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

import asyncpg
from atlas.core.backlinks import parse_frontmatter, extract_all_links

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("inbox")

_RAW_URL = os.getenv("DATABASE_URL", "postgresql://heimdall:heimdall_secure_2026@localhost:5432/heimdall")
DATABASE_URL = _RAW_URL.replace("+asyncpg", "")
VAULT_ROOT = Path(os.getenv("VAULT_PATH", "/opt/heimdall/vault"))
INBOX_DIR = VAULT_ROOT / "inbox"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.1-8b-instant"

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 150

# Valid destinations
VAULT_SUBFOLDERS = {
    "work":     ["fyp", "courses", "projects"],
    "personal": ["goals", "journal", "health"],
    "kb":        ["concepts", "tools", "people", "entities"],
}

CLASSIFY_PROMPT = """You are a personal knowledge manager. Classify this note into the correct vault and subfolder.

Vaults and their subfolders:
- work/fyp        → Final Year Project notes, research, code decisions
- work/courses    → University courses, lecture notes, assignments, study notes
- work/projects   → Side projects, job work, freelance, coding projects
- personal/goals  → Goals, habits, ideas, plans, things you want to achieve
- personal/journal → Daily logs, reflections, events, what happened today
- personal/health  → Health, fitness, sleep, food, medical notes
- kb/concepts     → Concepts, theories, frameworks, anything you learned (YouTube, books, articles)
- kb/tools        → Tools, software, apps, services, workflows
- kb/people       → People: friends, contacts, professionals, anyone notable
- kb/entities     → Companies, places, organizations, products

Return a JSON object with:
- "vault": one of work, personal, kb
- "subfolder": the subfolder name (e.g. "courses", "concepts", "goals")
- "reason": one sentence why

Rules:
- YouTube/video notes → kb/concepts
- Chat exports, conversation logs → personal/journal
- Lecture notes, study guides → work/courses
- If genuinely unclear → kb/concepts (safe default)

Return ONLY valid JSON, no markdown.

Note title: {title}
Note preview (first 500 chars):
{preview}"""


async def _classify(title: str, content: str) -> tuple[str, str]:
    """Ask Groq to classify a note. Returns (vault, subfolder)."""
    import httpx
    preview = content[:500].replace("\n", " ")
    prompt = CLASSIFY_PROMPT.format(title=title, preview=preview)

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a JSON-only classifier. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 150,
    }

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post("https://api.groq.com/openai/v1/chat/completions",
                         headers=headers, json=payload)
        r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"].strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    result = json.loads(raw)
    vault = result.get("vault", "kb")
    subfolder = result.get("subfolder", "concepts")
    reason = result.get("reason", "")

    # Validate
    if vault not in VAULT_SUBFOLDERS:
        vault = "kb"
    if subfolder not in VAULT_SUBFOLDERS.get(vault, []):
        subfolder = VAULT_SUBFOLDERS[vault][0]

    log.info(f"  → {vault}/{subfolder}  ({reason})")
    return vault, subfolder


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


async def _embed(text: str) -> list[float]:
    import httpx
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{OLLAMA_URL}/api/embeddings",
                         json={"model": EMBED_MODEL, "prompt": text})
        r.raise_for_status()
        return r.json()["embedding"]


async def _upsert_vault_note(conn, vault: str, rel_path: str, title: str, content: str):
    word_count = len(content.split())
    cs = hashlib.sha256(content.encode()).hexdigest()[:16]
    now = datetime.utcnow()

    existing = await conn.fetchrow("SELECT id, checksum FROM vault_notes WHERE path=$1", rel_path)
    if existing:
        if existing["checksum"] == cs:
            return
        await conn.execute(
            "UPDATE vault_notes SET title=$2, content=$3, checksum=$4, word_count=$5, updated_at=$6 WHERE path=$1",
            rel_path, title, content, cs, word_count, now,
        )
    else:
        await conn.execute(
            """INSERT INTO vault_notes (id, vault, path, title, content, node_type, entities, checksum, word_count, connection_count, created_at, updated_at)
               VALUES ($1,$2,$3,$4,$5,'note','[]',$6,$7,0,$8,$9)""",
            str(uuid.uuid4()), vault, rel_path, title, content, cs, word_count, now, now,
        )


async def _store_vector(conn, text: str, source_path: str, embedding: list[float]):
    vector_str = "[" + ",".join(map(str, embedding)) + "]"
    await conn.execute(
        """INSERT INTO vector_notes (id, text, source_type, source_path, embedding, created_at)
           VALUES ($1,$2,'vault_note',$3,$4::vector,$5) ON CONFLICT DO NOTHING""",
        str(uuid.uuid4()), text, source_path, vector_str, datetime.utcnow(),
    )


async def _store_links(conn, links: list[dict]):
    now = datetime.utcnow()
    for link in links:
        for is_bl, src, tgt in [(False, link["source"], link["target"]),
                                  (True,  link["target"], link["source"])]:
            await conn.execute(
                """INSERT INTO knowledge_links (id, source, target, link_type, is_backlink, context, created_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7)
                   ON CONFLICT ON CONSTRAINT uix_link_direction DO NOTHING""",
                str(uuid.uuid4()), src, tgt, link.get("type", "wiki"),
                is_bl, (link.get("display") or "")[:500], now,
            )


async def process_file(md_file: Path, conn, dry_run: bool = False, skip_move: bool = False) -> bool:
    """Process a single file. skip_move=True for files already in their vault location."""
    try:
        raw = md_file.read_text(encoding="utf-8", errors="replace")
        frontmatter, body = parse_frontmatter(raw)

        # Determine title
        title = frontmatter.get("title", "")
        if not title:
            for line in raw.splitlines():
                line = line.strip()
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        if not title:
            title = md_file.stem.replace("-", " ").replace("_", " ").title()

        log.info(f"Processing: {md_file.name}  [{title}]")

        if skip_move:
            # File is already in vault — infer vault/subfolder from path
            parts = md_file.relative_to(VAULT_ROOT).parts
            vault = parts[0] if len(parts) >= 1 else "kb"
            subfolder = parts[1] if len(parts) >= 2 else "concepts"
            dest_file = md_file
        else:
            # Classify
            vault, subfolder = await _classify(title, body or raw)

            if dry_run:
                log.info(f"  [DRY] Would move to vault/{vault}/{subfolder}/{md_file.name}")
                return True

            # Destination path
            dest_dir = VAULT_ROOT / vault / subfolder
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Handle filename collisions
            dest_file = dest_dir / md_file.name
            if dest_file.exists() and dest_file != md_file:
                stem = md_file.stem
                dest_file = dest_dir / f"{stem}-{str(uuid.uuid4())[:8]}.md"

            # Move file
            shutil.move(str(md_file), str(dest_file))
            log.info(f"  Moved → vault/{vault}/{subfolder}/{dest_file.name}")

        # DB rel_path
        rel_path = f"{vault}/{subfolder}/{dest_file.name}"

        # Upsert vault_notes
        await _upsert_vault_note(conn, vault, rel_path, title, raw)

        # Embed chunks → vector_notes
        chunks = _chunk(body or raw)
        for chunk in chunks:
            try:
                emb = await _embed(chunk)
                await _store_vector(conn, chunk, rel_path, emb)
            except Exception as e:
                log.warning(f"  Embed failed: {e}")

        # Extract + store links
        links = extract_all_links(raw, vault, f"{subfolder}/{dest_file.name}")
        if links:
            await _store_links(conn, links)
            log.debug(f"  Links: {len(links)}")

        return True

    except Exception as e:
        log.error(f"  FAILED {md_file.name}: {e}")
        return False


async def run(dry_run: bool = False, watch: bool = False, reindex: bool = False):
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    conn = None if dry_run else await asyncpg.connect(DATABASE_URL)

    try:
        if reindex:
            # Re-register files already in vault (no classification, no moving)
            vault_files = []
            for vault in ["work", "personal", "kb"]:
                vault_files += list((VAULT_ROOT / vault).rglob("*.md"))
            log.info(f"Reindexing {len(vault_files)} vault file(s) (no moving)")
            ok, fail = 0, 0
            for f in vault_files:
                success = await process_file(f, conn, dry_run=dry_run, skip_move=True)
                if success:
                    ok += 1
                else:
                    fail += 1
            log.info(f"Done: {ok} reindexed, {fail} failed")
            return

        while True:
            md_files = sorted(INBOX_DIR.rglob("*.md"))
            if not md_files:
                if not watch:
                    log.info("Inbox is empty — nothing to process.")
                    break
            else:
                log.info(f"Found {len(md_files)} file(s) in inbox")
                ok, fail = 0, 0
                for f in md_files:
                    success = await process_file(f, conn, dry_run=dry_run)
                    if success:
                        ok += 1
                    else:
                        fail += 1

                log.info(f"Done: {ok} processed, {fail} failed")

            if not watch:
                break

            log.info("Watching inbox for new files (Ctrl+C to stop)...")
            time.sleep(10)

    finally:
        if conn:
            await conn.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Process Heimdall inbox drop zone")
    p.add_argument("--dry-run", action="store_true", help="Preview only, no writes or moves")
    p.add_argument("--watch", action="store_true", help="Keep running and process files as they arrive")
    p.add_argument("--reindex", action="store_true", help="Re-register all files already in vault (no moving)")
    args = p.parse_args()

    asyncio.run(run(dry_run=args.dry_run, watch=args.watch, reindex=args.reindex))
