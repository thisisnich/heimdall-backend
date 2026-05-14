"""
Backlink extraction and knowledge graph management for multi-vault system.

Extracts links from markdown content and maintains bidirectional
relationships between notes across all vaults.
"""

import re
import yaml
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# Link extraction patterns
LINK_PATTERNS = [
    # Wiki-style links: [[Note Name]] or [[Note Name|Display Text]]
    (r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", "wiki"),
    # Markdown links to other vault files: [text](../other-brain/note.md) or [text](./note.md)
    (r"\[([^\]]+)\]\(([^)]+\.md)\)", "markdown"),
    # Reference patterns: "as discussed in [X]", "see also [Y]"
    (r"(?:see also|as discussed in|refer to|read more about)[:\s]+([^,.\n]+)", "reference"),
]

# Entity patterns - common tech/life terms that should become entity pages
ENTITY_CANDIDATES = [
    r"\b(Claude Code|Claude|ChatGPT|GPT-4|OpenAI|Anthropic)\b",
    r"\b(React|Vue|Angular|Svelte|Next\.js|Node\.js|FastAPI|Django|Flask)\b",
    r"\b(Docker|Kubernetes|K8s|AWS|GCP|Azure|Vercel|Netlify)\b",
    r"\b(Python|JavaScript|TypeScript|Rust|Go|Rust)\b",
    r"\b(Obsidian|Notion|Logseq|Roam Research)\b",
    r"\b(GTD|Zettelkasten|PARA|Second Brain)\b",
]

# Cross-vault linking rules
ALLOWED_LINKS = {
    "work":     ["kb", "personal"],
    "personal": ["kb", "work"],
    "kb":        ["kb", "work", "personal"],
    "inbox":     [],  # Inbox is staging only — items get moved, not linked
}


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    return re.sub(r'[^\w\s-]', '', text.lower()).strip().replace(' ', '-')


def parse_frontmatter(content: str) -> Tuple[Dict, str]:
    """Extract YAML frontmatter from markdown content."""
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
                return frontmatter, parts[2].strip()
            except yaml.YAMLError:
                pass
    return {}, content


def extract_wiki_links(content: str, source_vault: str) -> List[Dict]:
    """Extract [[Wiki Style]] links from content."""
    links = []
    pattern = r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]"
    
    for match in re.finditer(pattern, content):
        target_name = match.group(1).strip()
        display_text = match.group(2) if match.group(2) else target_name
        
        # Convert to vault path
        target_slug = slugify(target_name)
        target_path = f"{source_vault}/{target_slug}.md"
        
        links.append({
            "type": "wiki",
            "source": f"{source_vault}/",
            "target": target_path,
            "display": display_text,
            "original": match.group(0),
        })
    
    return links


def extract_markdown_links(content: str, source_vault: str) -> List[Dict]:
    """Extract [text](path.md) style links."""
    links = []
    pattern = r"\[([^\]]+)\]\(([^)]+\.md)\)"
    
    for match in re.finditer(pattern, content):
        display_text = match.group(1)
        target_path = match.group(2)
        
        # Handle relative paths
        if target_path.startswith('../'):
            # Cross-vault link: ../other-vault/note.md
            parts = target_path.replace('../', '').split('/', 1)
            if len(parts) == 2:
                target_vault, subpath = parts
                target_path = f"{target_vault}/{subpath}"
            else:
                target_path = parts[0]
        elif target_path.startswith('./'):
            # Same directory link
            target_path = f"{source_vault}/{target_path.replace('./', '')}"
        elif not target_path.startswith('/'):
            # Relative to vault root
            target_path = f"{source_vault}/{target_path}"
        
        # Determine if cross-vault
        target_vault = target_path.split('/')[0] if '/' in target_path else ""
        is_cross_vault = target_vault != source_vault
        
        if is_cross_vault and not validate_cross_vault_link(source_vault, target_vault):
            continue  # Skip invalid cross-vault links
        
        links.append({
            "type": "cross_vault" if is_cross_vault else "markdown",
            "source": f"{source_vault}/",
            "target": target_path,
            "display": display_text,
            "original": match.group(0),
        })
    
    return links


def extract_entities(content: str, source_vault: str, known_entities: List[str] = None) -> List[Dict]:
    """Extract entity mentions that match or create entity pages."""
    links = []
    known_entities = known_entities or []
    
    for pattern in ENTITY_CANDIDATES:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            entity = match.group(1)
            entity_slug = slugify(entity)
            
            # Entity pages live in wiki/entities/
            entity_path = f"wiki/entities/{entity_slug}.md"
            
            links.append({
                "type": "entity",
                "source": f"{source_vault}/",
                "target": entity_path,
                "entity": entity,
                "display": entity,
                "original": match.group(0),
            })
    
    return links


def extract_frontmatter_links(frontmatter: Dict, source_vault: str) -> List[Dict]:
    """Extract explicit links from frontmatter 'links' field."""
    links = []
    fm_links = frontmatter.get('links', [])
    
    if isinstance(fm_links, list):
        for link in fm_links:
            if isinstance(link, dict):
                target = link.get('target', '')
                link_type = link.get('type', 'related')
                
                if target:
                    # Validate cross-vault if needed
                    target_vault = target.split('/')[0] if '/' in target else ""
                    if target_vault and target_vault != source_vault:
                        if not validate_cross_vault_link(source_vault, target_vault):
                            continue
                    
                    links.append({
                        "type": link_type,
                        "source": f"{source_vault}/",
                        "target": target,
                        "display": link.get('display', target),
                        "from_frontmatter": True,
                    })
    
    return links


def validate_cross_vault_link(source_vault: str, target_vault: str) -> bool:
    """Check if link between vaults is allowed."""
    if source_vault == target_vault:
        return True
    allowed = ALLOWED_LINKS.get(source_vault, [])
    return target_vault in allowed


def extract_all_links(content: str, source_vault: str, source_path: str = "") -> List[Dict]:
    """Extract all types of links from content."""
    frontmatter, body = parse_frontmatter(content)
    
    all_links = []
    
    # Extract from frontmatter
    all_links.extend(extract_frontmatter_links(frontmatter, source_vault))
    
    # Extract from body
    all_links.extend(extract_wiki_links(body, source_vault))
    all_links.extend(extract_markdown_links(body, source_vault))
    all_links.extend(extract_entities(body, source_vault))
    
    # Add full source path to each link
    for link in all_links:
        link['source'] = f"{source_vault}/{source_path}"
    
    # Deduplicate by source+target combination
    seen = set()
    unique_links = []
    for link in all_links:
        key = (link['source'], link['target'])
        if key not in seen:
            seen.add(key)
            unique_links.append(link)
    
    return unique_links


async def store_links_in_db(links: List[Dict], db_session, source_note_id: str = None):
    """Store extracted links in database with bidirectional entries."""
    from atlas.db.models import KnowledgeLink
    
    for link in links:
        # Create forward link
        forward = KnowledgeLink(
            source=link['source'],
            target=link['target'],
            link_type=link.get('type', 'wiki'),
            is_backlink=False,
            context=link.get('context', link.get('display', ''))[:500],  # Limit context length
        )
        db_session.add(forward)
        
        # Create backlink (reverse direction)
        backlink = KnowledgeLink(
            source=link['target'],
            target=link['source'],
            link_type=link.get('type', 'wiki'),
            is_backlink=True,
            context=link.get('context', link.get('display', ''))[:500],
        )
        db_session.add(backlink)
    
    await db_session.commit()


async def get_related_notes(note_path: str, db_session, limit: int = 10) -> List[Dict]:
    """Get notes linked to/from this note (bidirectional)."""
    from sqlalchemy import select, union_all
    from atlas.db.models import KnowledgeLink, VaultNote
    
    # Forward links (this note links to others)
    forward_query = select(
        KnowledgeLink.target.label('path'),
        KnowledgeLink.link_type,
        KnowledgeLink.is_backlink,
        VaultNote.title,
        VaultNote.vault
    ).join(
        VaultNote, KnowledgeLink.target == VaultNote.path
    ).where(
        KnowledgeLink.source == note_path
    )
    
    # Backward links (other notes link to this)
    backward_query = select(
        KnowledgeLink.source.label('path'),
        KnowledgeLink.link_type,
        KnowledgeLink.is_backlink,
        VaultNote.title,
        VaultNote.vault
    ).join(
        VaultNote, KnowledgeLink.source == VaultNote.path
    ).where(
        KnowledgeLink.target == note_path
    )
    
    # Union both directions
    combined = union_all(forward_query, backward_query).limit(limit)
    
    result = await db_session.execute(combined)
    rows = result.all()
    
    return [
        {
            "path": row.path,
            "title": row.title,
            "vault": row.vault,
            "link_type": row.link_type,
            "is_backlink": row.is_backlink,
        }
        for row in rows
    ]


async def find_entity_page(entity_name: str, db_session) -> Optional[str]:
    """Find the vault path for an entity page if it exists."""
    from sqlalchemy import select
    from atlas.db.models import VaultNote
    
    entity_slug = slugify(entity_name)
    entity_path = f"wiki/entities/{entity_slug}.md"
    
    result = await db_session.execute(
        select(VaultNote).where(VaultNote.path == entity_path)
    )
    note = result.scalar_one_or_none()
    
    return entity_path if note else None


async def create_entity_page_if_missing(entity_name: str, db_session, vault_root: Path):
    """Create an entity page in wiki/entities/ if it doesn't exist."""
    from sqlalchemy import select
    from atlas.db.models import VaultNote
    
    entity_slug = slugify(entity_name)
    entity_path = f"wiki/entities/{entity_slug}.md"
    
    # Check if exists in DB
    result = await db_session.execute(
        select(VaultNote).where(VaultNote.path == entity_path)
    )
    if result.scalar_one_or_none():
        return entity_path
    
    # Create the file
    entity_file = vault_root / entity_path
    entity_file.parent.mkdir(parents=True, exist_ok=True)
    
    content = f"""---
id: "{entity_slug}"
type: entity
created: {datetime.now().strftime('%Y-%m-%d')}
aliases: ["{entity_name}"]
---

# {entity_name}

Entity page for **{entity_name}**.

## Linked Notes

{{backlinks}}

## Related Entities

{{related_entities}}
"""
    
    entity_file.write_text(content)
    
    # Add to database
    note = VaultNote(
        vault="wiki",
        path=entity_path,
        title=entity_name,
        content=content,
        node_type="entity",
        note_id=entity_slug,
    )
    db_session.add(note)
    await db_session.commit()
    
    return entity_path


def get_vault_structure(vault_root: Path) -> Dict[str, List[str]]:
    """Scan vault directory and return structure of all vaults."""
    structure = {}
    
    for vault_dir in vault_root.iterdir():
        if vault_dir.is_dir() and not vault_dir.name.startswith('.'):
            md_files = list(vault_dir.rglob("*.md"))
            structure[vault_dir.name] = [
                str(f.relative_to(vault_root))
                for f in md_files
            ]
    
    return structure
