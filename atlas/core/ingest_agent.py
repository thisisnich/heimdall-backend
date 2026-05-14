"""
Ingest Agent — takes ExtractedContent and decides how to classify, chunk,
embed, store to pgvector, and write to the vault.

Flow:
  1. Ask LLM to classify the content → returns a ClassificationPlan
  2. If content purpose is unclear → return a clarification question (no filing)
  3. If clear → chunk, embed each chunk, store to pgvector, write to vault

ClassificationPlan:
{
  "clear": true,
  "vault_folder": "wiki",
  "title": "React Hooks Notes",
  "source_type": "note",
  "tags": ["react", "programming"],
  "summary": "One paragraph summary of the content",
  "clarification_question": ""   ← populated only if clear=false
}
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field

from atlas.services.groq_service import chat as groq_chat
from atlas.services.ingest_service import ExtractedContent
from atlas.db.vector_store import store as vector_store
from atlas.core.vault_writer import VAULT_ROOT, _ensure_vault
from atlas.core.personality import HEIMDALL_BASE
from pathlib import Path
from datetime import date, datetime

logger = logging.getLogger(__name__)

CLASSIFIER_MODEL = "groq-llama4-scout"

CLASSIFIER_SYSTEM = HEIMDALL_BASE + """

CURRENT TASK: Personal knowledge classifier and entity extractor.
Given content, return a JSON plan. Be proactive — ask when anything is unclear or could be richer.
JSON only — no markdown, no explanation.

Schema:
{
  "clear": true,
  "vault": "<vault>",
  "subfolder": "<subfolder-slug>",
  "title": "<short descriptive title>",
  "source_type": "<type>",
  "tags": ["<tag1>", "<tag2>"],
  "summary": "<1-2 sentence summary>",
  "clarification_questions": [],
  "entities": []
}

vault options: work | personal | kb

subfolder: Use the best-fit slug. Standard ones:
  work: fyp, courses, projects
  personal: goals, journal, health
  kb: concepts, tools, people, entities
You MAY invent a new subfolder slug if none fit (e.g. work/algorithms, work/internship, kb/books, personal/finance).
Use lowercase-hyphenated slugs. Keep them short and clear.

source_type: note | goal | course | project | person | concept | tool | journal | media | assignment | learning-journey | idea

entities: Extract any named things that deserve their own file:
  - People (classmates, professors, contacts, anyone named)
  - Projects (any project mentioned by name)
  - Courses (any course code or name)
  - Tools/technologies mentioned
  - Places or organisations
For each entity:
  {"name": "<name>", "type": "person|project|course|tool|place|org", "vault": "kb", "subfolder": "people|entities|tools", "context": "<one line about how they relate to this note>"}

clarification_questions: A LIST of specific questions to flesh out the file.
ASK when:
  - The note mentions something by name without enough detail (who is X? what is this project about?)
  - The purpose/context is ambiguous
  - There are dates, goals, or deadlines that could be captured
  - A new entity was mentioned and you want more context
Aim for 1-3 targeted questions. Empty list only if content is completely self-contained.
Set clear=false if you MUST have answers before filing. Set clear=true with questions if you can file now but want more detail.

Examples:
Content: "Started working on Heimdall today, it's a personal AI server"
→ {"clear":false,"vault":"work","subfolder":"projects","title":"Heimdall","source_type":"project","tags":["ai","personal-project"],"summary":"Personal AI server project.","clarification_questions":["What stack is Heimdall built on?","What's the main goal of this project?","Is there a target deadline?"],"entities":[{"name":"Heimdall","type":"project","vault":"work","subfolder":"projects","context":"Personal AI server project"}]}

Content: "Met James at CS3219 lecture today, he's doing his FYP on LLMs"
→ {"clear":true,"vault":"personal","subfolder":"journal","title":"Met James at CS3219","source_type":"journal","tags":["cs3219","people"],"summary":"Met classmate James at CS3219, working on LLM FYP.","clarification_questions":["What's James' last name or student ID?","Is CS3219 a module you're taking this semester?"],"entities":[{"name":"James","type":"person","vault":"kb","subfolder":"people","context":"Met at CS3219, doing FYP on LLMs"},{"name":"CS3219","type":"course","vault":"work","subfolder":"courses","context":"Course where James was met"}]}

Content: "React useEffect runs after every render by default..."
→ {"clear":true,"vault":"kb","subfolder":"concepts","title":"React useEffect Notes","source_type":"concept","tags":["react","programming"],"summary":"Notes on React useEffect hook behaviour.","clarification_questions":[],"entities":[{"name":"React","type":"tool","vault":"kb","subfolder":"tools","context":"JavaScript UI library"}]}
"""

REFORMAT_SYSTEM = """You are a personal knowledge assistant. Reformat the following raw note into clean, well-structured Markdown.

Rules:
- Preserve ALL information — do not drop anything
- Add a clear H1 title if missing
- Use H2/H3 headings to organise sections logically
- Convert bullet walls into structured lists
- Bold key terms
- If the note has [[wiki links]], preserve them exactly
- Add a short TL;DR blockquote at the top if the note is longer than 200 words
- Do NOT add new information or opinions — only reformat
- Output clean Markdown only, no commentary"""


ENTITY_TEMPLATES = {
    "person": """---
title: "{name}"
type: person
vault: kb
subfolder: people
created: {today}
updated: {today}
tags: []
context: "{context}"
---

# {name}

> {context}

## About

*Fill in more details here.*

## Linked Notes

- [[{source_title}]]

## Notes

""",
    "project": """---
title: "{name}"
type: project
vault: work
subfolder: projects
created: {today}
updated: {today}
tags: []
status: active
context: "{context}"
---

# {name}

> {context}

## Overview

*What is this project? What problem does it solve?*

## Goals

## Stack / Tools

## Progress

## Linked Notes

- [[{source_title}]]

""",
    "course": """---
title: "{name}"
type: course
vault: work
subfolder: courses
created: {today}
updated: {today}
tags: []
status: active
context: "{context}"
---

# {name}

> {context}

## Overview

## Key Topics

## Assignments

## Resources

## Linked Notes

- [[{source_title}]]

""",
    "tool": """---
title: "{name}"
type: tool
vault: kb
subfolder: tools
created: {today}
updated: {today}
tags: []
context: "{context}"
---

# {name}

> {context}

## What it does

## How I use it

## Linked Notes

- [[{source_title}]]

""",
    "place": """---
title: "{name}"
type: place
vault: kb
subfolder: entities
created: {today}
updated: {today}
tags: []
context: "{context}"
---

# {name}

> {context}

## Notes

## Linked Notes

- [[{source_title}]]

""",
    "org": """---
title: "{name}"
type: organisation
vault: kb
subfolder: entities
created: {today}
updated: {today}
tags: []
context: "{context}"
---

# {name}

> {context}

## About

## Linked Notes

- [[{source_title}]]

""",
}


@dataclass
class IngestResult:
    status: str                        # "indexed" | "needs_clarification" | "error"
    title: str = ""
    vault: str = ""
    subfolder: str = ""
    vault_folder: str = ""             # kept for API compat: vault/subfolder
    vault_file: str = ""
    chunks_stored: int = 0
    clarification_question: str = ""
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    error: str = ""


def _slug(text: str, max_len: int = 60) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:max_len].strip("-")


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    return json.loads(raw)


VALID_VAULTS = {"work", "personal", "kb"}


def _sanitize_subfolder(slug: str) -> str:
    """Ensure subfolder slug is safe for filesystem."""
    slug = re.sub(r"[^\w\s-]", "", slug.lower().strip())
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug[:40].strip("-") or "notes"


async def _classify(content: ExtractedContent, user_hint: str = "") -> dict:
    """Ask the LLM to classify the content. Returns a classification plan dict."""
    preview = content.text[:2000]
    if user_hint:
        preview = f"[User note: {user_hint}]\n\n{preview}"

    messages = [
        {"role": "system", "content": CLASSIFIER_SYSTEM},
        {"role": "user", "content": f"Classify this content:\n\n{preview}"},
    ]
    raw = await groq_chat(messages, model=CLASSIFIER_MODEL)
    if not raw or not raw.strip():
        raise ValueError("Empty classifier response")
    plan = _extract_json(raw)
    plan.setdefault("clear", True)
    plan.setdefault("vault", "kb")
    plan.setdefault("subfolder", "concepts")
    plan.setdefault("title", "Untitled")
    plan.setdefault("source_type", "note")
    plan.setdefault("tags", [])
    plan.setdefault("summary", "")
    plan.setdefault("clarification_questions", [])
    plan.setdefault("entities", [])
    # legacy compat
    if plan.get("clarification_question") and not plan["clarification_questions"]:
        plan["clarification_questions"] = [plan["clarification_question"]]

    # Validate vault — subfolder can be anything now
    if plan["vault"] not in VALID_VAULTS:
        plan["vault"] = "kb"
    plan["subfolder"] = _sanitize_subfolder(plan["subfolder"])
    plan["vault_folder"] = f"{plan['vault']}/{plan['subfolder']}"  # compat
    return plan


def _create_entity_file(entity: dict, source_title: str, today: str) -> tuple[Path, str]:
    """Create a structured entity file from template. Returns (path, content)."""
    etype = entity.get("type", "place")
    template = ENTITY_TEMPLATES.get(etype, ENTITY_TEMPLATES["place"])

    vault = entity.get("vault", "kb")
    if vault not in VALID_VAULTS:
        vault = "kb"
    subfolder = _sanitize_subfolder(entity.get("subfolder", "entities"))

    dest_dir = VAULT_ROOT / vault / subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)

    slug = _slug(entity["name"])
    file_path = dest_dir / f"{slug}.md"

    content = template.format(
        name=entity["name"],
        today=today,
        context=entity.get("context", ""),
        source_title=source_title,
    )
    return file_path, content


async def _spawn_entity_files(entities: list[dict], source_title: str,
                               plan: dict, conn_params: str):
    """Create entity files and register them in vault_notes DB."""
    import uuid, asyncpg, hashlib
    today = date.today().isoformat()

    try:
        conn = await asyncpg.connect(conn_params)
    except Exception as e:
        logger.warning(f"Entity DB connect failed: {e}")
        return

    try:
        for entity in entities:
            if not entity.get("name"):
                continue
            try:
                file_path, content = _create_entity_file(entity, source_title, today)

                # Only create if doesn't already exist (don't overwrite rich pages)
                if not file_path.exists():
                    file_path.write_text(content, encoding="utf-8")
                    logger.info(f"  Entity file created: {file_path.relative_to(VAULT_ROOT)}")
                else:
                    # Append backlink to existing entity file
                    existing = file_path.read_text(encoding="utf-8")
                    if f"[[{source_title}]]" not in existing:
                        existing = existing.rstrip() + f"\n- [[{source_title}]]\n"
                        file_path.write_text(existing, encoding="utf-8")

                vault = entity.get("vault", "kb")
                subfolder = _sanitize_subfolder(entity.get("subfolder", "entities"))
                rel_path = f"{vault}/{subfolder}/{file_path.name}"
                cs = hashlib.sha256(content.encode()).hexdigest()[:16]
                now = datetime.utcnow()

                existing_row = await conn.fetchrow(
                    "SELECT id FROM vault_notes WHERE path=$1", rel_path
                )
                if not existing_row:
                    await conn.execute(
                        """INSERT INTO vault_notes (id, vault, path, title, content, node_type, entities, checksum, word_count, connection_count, created_at, updated_at)
                           VALUES ($1,$2,$3,$4,$5,'entity','[]',$6,$7,0,$8,$9)""",
                        str(uuid.uuid4()), vault, rel_path, entity["name"],
                        content, cs, len(content.split()), now, now,
                    )
            except Exception as e:
                logger.warning(f"Entity file failed for {entity.get('name')}: {e}")
    finally:
        await conn.close()


async def _reformat(text: str) -> str:
    """Reformat raw note text into clean structured Markdown via LLM."""
    if len(text.strip()) < 100:
        return text  # too short to bother
    messages = [
        {"role": "system", "content": REFORMAT_SYSTEM},
        {"role": "user", "content": text[:6000]},
    ]
    try:
        result = await groq_chat(messages, model=CLASSIFIER_MODEL)
        return result.strip() if result.strip() else text
    except Exception as e:
        logger.warning(f"Reformat failed, using raw text: {e}")
        return text


async def _write_to_vault(plan: dict, content: ExtractedContent, formatted_body: str) -> Path:
    """Write the content as a structured, reformatted .md file in the vault."""
    _ensure_vault()

    vault = plan["vault"]
    subfolder = plan["subfolder"]
    folder = VAULT_ROOT / vault / subfolder
    folder.mkdir(parents=True, exist_ok=True)

    title = plan["title"]
    slug = _slug(title)
    file_path = folder / f"{slug}.md"

    today = date.today().isoformat()
    tags_str = ", ".join(f'"{t}"' for t in plan.get("tags", []))
    summary = plan.get("summary", "")
    original_filename = content.filename or content.url or "unknown"

    if not file_path.exists():
        body_to_write = formatted_body
        # Strip leading H1 if it duplicates the title (we add it in frontmatter block)
        first_line = body_to_write.lstrip().splitlines()[0] if body_to_write.strip() else ""
        if first_line.startswith("# "):
            body_to_write = "\n".join(body_to_write.lstrip().splitlines()[1:]).lstrip()

        content_md = f"""---
title: "{title}"
type: {plan['source_type']}
vault: {vault}
subfolder: {subfolder}
created: {today}
updated: {today}
tags: [{tags_str}]
source: heimdall/ingest
original: "{original_filename}"
---

# {title}
"""
        if summary:
            content_md += f"\n> {summary}\n"
        content_md += f"\n*Ingested: {today} | Source: `{original_filename}`*\n\n"
        content_md += body_to_write
        file_path.write_text(content_md, encoding="utf-8")
    else:
        # File exists — append as a new dated section rather than overwriting
        existing = file_path.read_text(encoding="utf-8")
        existing = re.sub(r"^updated: .+$", f"updated: {today}", existing, flags=re.MULTILINE)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        existing += f"\n\n## Update — {now}\n\n*Source: `{original_filename}`*\n\n{formatted_body}\n\n---\n"
        file_path.write_text(existing, encoding="utf-8")

    return file_path


async def _register_in_db(plan: dict, vault_file: Path, content_text: str):
    """Register vault note in vault_notes DB and extract knowledge links."""
    import uuid, asyncpg, hashlib, os
    from atlas.core.backlinks import extract_all_links

    db_url = os.getenv("DATABASE_URL", "postgresql://heimdall:heimdall_secure_2026@localhost:5432/heimdall").replace("+asyncpg", "")
    vault = plan["vault"]
    subfolder = plan["subfolder"]
    rel_path = f"{vault}/{subfolder}/{vault_file.name}"
    title = plan["title"]
    cs = hashlib.sha256(content_text.encode()).hexdigest()[:16]
    word_count = len(content_text.split())
    now = datetime.utcnow()

    try:
        conn = await asyncpg.connect(db_url)
        try:
            existing = await conn.fetchrow("SELECT id FROM vault_notes WHERE path=$1", rel_path)
            if existing:
                await conn.execute(
                    "UPDATE vault_notes SET title=$2, content=$3, checksum=$4, word_count=$5, updated_at=$6 WHERE path=$1",
                    rel_path, title, content_text, cs, word_count, now,
                )
            else:
                await conn.execute(
                    """INSERT INTO vault_notes (id, vault, path, title, content, node_type, entities, checksum, word_count, connection_count, created_at, updated_at)
                       VALUES ($1,$2,$3,$4,$5,'note','[]',$6,$7,0,$8,$9)""",
                    str(uuid.uuid4()), vault, rel_path, title, content_text, cs, word_count, now, now,
                )

            # Extract and store links
            links = extract_all_links(content_text, vault, f"{subfolder}/{vault_file.name}")
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
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"DB registration failed (non-fatal): {e}")


async def ingest(
    content: ExtractedContent,
    user_hint: str = "",
    clarification_answer: str = "",
    force_folder: str = "",
) -> IngestResult:
    """
    Main agent entry point.

    Args:
        content:                ExtractedContent from ingest_service.extract()
        user_hint:              Optional note from user about what this is
        clarification_answer:   User's answer to a previous clarification question
        force_folder:           Skip classification, use this vault folder directly

    Returns IngestResult with status "indexed", "needs_clarification", or "error".
    """
    if not content.text.strip():
        return IngestResult(status="error", error="No text could be extracted from this content.")

    # Build hint from clarification answer if provided
    combined_hint = user_hint
    if clarification_answer:
        combined_hint = f"{user_hint} {clarification_answer}".strip()

    # Classify
    try:
        plan = await _classify(content, combined_hint)
    except Exception as e:
        logger.error(f"Ingest classification failed: {e}")
        return IngestResult(status="error", error=f"Classification failed: {e}")

    # Override folder if forced (accept "vault/subfolder" or legacy single-folder names)
    if force_folder:
        if "/" in force_folder:
            v, s = force_folder.split("/", 1)
            plan["vault"] = v
            plan["subfolder"] = s
        else:
            # Legacy single name — map to new structure
            legacy = {"wiki": ("kb", "concepts"), "goals": ("personal", "goals"),
                      "ideas": ("personal", "goals"), "journal": ("personal", "journal"),
                      "people": ("kb", "people"), "places": ("kb", "concepts")}
            plan["vault"], plan["subfolder"] = legacy.get(force_folder, ("kb", "concepts"))
        plan["vault_folder"] = f"{plan['vault']}/{plan['subfolder']}"
        plan["clear"] = True

    # Needs clarification? Return ALL questions at once
    questions = plan.get("clarification_questions", [])
    if not plan.get("clear", True) and questions:
        return IngestResult(
            status="needs_clarification",
            clarification_question="\n".join(f"{i+1}. {q}" for i, q in enumerate(questions)),
            title=plan.get("title", ""),
            vault_folder=plan.get("vault_folder", "kb/concepts"),
        )

    # Reformat the raw note into clean structured Markdown
    formatted_body = await _reformat(content.text)

    # Store each chunk in pgvector
    chunks_stored = 0
    source_path = f"{plan['vault']}/{plan['subfolder']}/{_slug(plan['title'])}"

    for i, chunk in enumerate(content.chunks or [content.text]):
        try:
            await vector_store(
                "vector_notes",
                chunk,
                source_type=plan["source_type"],
                source_path=source_path,
            )
            chunks_stored += 1
        except Exception as e:
            logger.warning(f"Failed to store chunk {i}: {e}")

    # Also store summary in vector_memory for quick retrieval
    if plan.get("summary"):
        try:
            await vector_store(
                "vector_memory",
                plan["summary"],
                source_type=plan["source_type"],
                source_path=source_path,
            )
        except Exception as e:
            logger.warning(f"Failed to store summary: {e}")

    # Write to vault (reformatted)
    vault_file_str = ""
    db_url = os.getenv("DATABASE_URL", "postgresql://heimdall:heimdall_secure_2026@localhost:5432/heimdall").replace("+asyncpg", "")
    try:
        vault_file = await _write_to_vault(plan, content, formatted_body)
        vault_file_str = str(vault_file)
        # Register in vault_notes DB + extract links
        await _register_in_db(plan, vault_file, vault_file.read_text(encoding="utf-8"))
        # Spawn entity files for any named entities detected
        if plan.get("entities"):
            await _spawn_entity_files(plan["entities"], plan["title"], plan, db_url)
    except Exception as e:
        logger.warning(f"Vault write failed: {e}")

    logger.info(f"Ingested: '{plan['title']}' → {plan['vault']}/{plan['subfolder']}/ ({chunks_stored} chunks)")

    return IngestResult(
        status="indexed",
        title=plan["title"],
        vault=plan["vault"],
        subfolder=plan["subfolder"],
        vault_folder=f"{plan['vault']}/{plan['subfolder']}",
        vault_file=vault_file_str,
        chunks_stored=chunks_stored,
        summary=plan.get("summary", ""),
        tags=plan.get("tags", []),
    )
