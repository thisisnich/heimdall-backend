"""
Knowledge Graph API for visualizing and querying multi-vault note relationships.

Provides endpoints for:
- Getting all nodes (notes) with their vault grouping
- Getting all edges (links between notes)
- Neighborhood queries (N-hop connections)
- Graph statistics and insights
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, union_all, text
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from atlas.db.session import get_db
from atlas.db.models import VaultNote, KnowledgeLink

router = APIRouter(prefix="/graph", tags=["knowledge_graph"])


# ==================== Pydantic Models ====================

class GraphNode(BaseModel):
    id: str
    label: str
    vault: str
    node_type: str
    connection_count: int
    
    class Config:
        from_attributes = True


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    is_backlink: bool
    
    class Config:
        from_attributes = True


class RelatedNote(BaseModel):
    path: str
    title: str
    vault: str
    link_type: str
    is_backlink: bool


class NeighborhoodResponse(BaseModel):
    center_node: str
    depth: int
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class GraphStats(BaseModel):
    total_notes: int
    total_links: int
    vault_breakdown: Dict[str, int]
    top_connected: List[Dict[str, Any]]
    isolated_nodes: int


# ==================== API Endpoints ====================

@router.get("/nodes", response_model=List[GraphNode])
async def get_graph_nodes(
    vault: Optional[str] = Query(None, description="Filter by vault (personal, youtube, wiki, projects, inbox)"),
    query: Optional[str] = Query(None, description="Search filter for note titles"),
    node_type: Optional[str] = Query(None, description="Filter by node type (note, entity, index)"),
    limit: int = Query(1000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db)
):
    """
    Return all nodes (notes) for D3.js force graph visualization.
    
    Each node includes:
    - id: vault/path format
    - label: note title
    - vault: which vault it belongs to (for color-coding)
    - node_type: note, entity, or index
    - connection_count: number of links (for node sizing)
    """
    # Build query with optional filters
    sql = select(
        VaultNote.path.label('id'),
        VaultNote.title.label('label'),
        VaultNote.vault,
        VaultNote.node_type,
        func.count(KnowledgeLink.source).label('connection_count')
    ).outerjoin(
        KnowledgeLink,
        (VaultNote.path == KnowledgeLink.source) | (VaultNote.path == KnowledgeLink.target)
    ).group_by(VaultNote.path, VaultNote.title, VaultNote.vault, VaultNote.node_type)
    
    # Apply filters
    if vault:
        sql = sql.where(VaultNote.vault == vault)
    if query:
        sql = sql.where(VaultNote.title.ilike(f'%{query}%'))
    if node_type:
        sql = sql.where(VaultNote.node_type == node_type)
    
    sql = sql.limit(limit)
    
    result = await db.execute(sql)
    rows = result.all()
    
    return [
        GraphNode(
            id=row.id,
            label=row.label,
            vault=row.vault,
            node_type=row.node_type,
            connection_count=row.connection_count or 0
        )
        for row in rows
    ]


@router.get("/edges", response_model=List[GraphEdge])
async def get_graph_edges(
    vault: Optional[str] = Query(None, description="Filter by vault (shows links involving this vault)"),
    link_type: Optional[str] = Query(None, description="Filter by link type"),
    include_backlinks: bool = Query(True, description="Include reverse-direction links"),
    limit: int = Query(5000, ge=1, le=10000),
    db: AsyncSession = Depends(get_db)
):
    """
    Return all edges (links between notes) for graph visualization.
    
    By default includes all links. Set include_backlinks=false to get
    only forward-direction links (reduces clutter).
    """
    sql = select(
        KnowledgeLink.source,
        KnowledgeLink.target,
        KnowledgeLink.link_type.label('type'),
        KnowledgeLink.is_backlink
    )
    
    # Apply filters
    if vault:
        sql = sql.where(
            (KnowledgeLink.source.like(f'{vault}/%')) |
            (KnowledgeLink.target.like(f'{vault}/%'))
        )
    
    if link_type:
        sql = sql.where(KnowledgeLink.link_type == link_type)
    
    if not include_backlinks:
        sql = sql.where(KnowledgeLink.is_backlink == False)
    
    sql = sql.limit(limit)
    
    result = await db.execute(sql)
    rows = result.all()
    
    return [
        GraphEdge(
            source=row.source,
            target=row.target,
            type=row.type,
            is_backlink=row.is_backlink
        )
        for row in rows
    ]


@router.get("/neighborhood/{node_id:path}", response_model=NeighborhoodResponse)
async def get_neighborhood(
    node_id: str,  # Accepts full path like "personal/goals/fyp.md"
    depth: int = Query(1, ge=1, le=3, description="How many hops to traverse (1-3)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get N-hop neighborhood around a specific node.
    
    Returns all nodes and edges within N steps of the center node.
    Useful for "focus + context" views in the graph visualization.
    """
    # Use recursive CTE to find connected nodes
    cte_sql = text("""
        WITH RECURSIVE neighborhood AS (
            -- Base case: the starting node
            SELECT :start_node as node_path, 0 as depth
            
            UNION
            
            -- Recursive step: follow links from current nodes
            SELECT 
                CASE 
                    WHEN kl.source = n.node_path THEN kl.target 
                    ELSE kl.source 
                END as node_path,
                n.depth + 1
            FROM knowledge_links kl
            JOIN neighborhood n ON kl.source = n.node_path OR kl.target = n.node_path
            WHERE n.depth < :max_depth
        )
        SELECT DISTINCT node_path FROM neighborhood
    """)
    
    result = await db.execute(cte_sql, {"start_node": node_id, "max_depth": depth})
    neighbor_paths = [row[0] for row in result.all()]
    
    if not neighbor_paths:
        # Return just the center node if no neighbors
        center_result = await db.execute(
            select(VaultNote).where(VaultNote.path == node_id)
        )
        center = center_result.scalar_one_or_none()
        if center:
            return NeighborhoodResponse(
                center_node=node_id,
                depth=depth,
                nodes=[GraphNode(
                    id=center.path,
                    label=center.title,
                    vault=center.vault,
                    node_type=center.node_type,
                    connection_count=0
                )],
                edges=[]
            )
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Fetch all neighbor nodes
    nodes_result = await db.execute(
        select(VaultNote).where(VaultNote.path.in_(neighbor_paths))
    )
    notes = nodes_result.scalars().all()
    
    # Calculate connection counts for these nodes
    connection_counts = {}
    for path in neighbor_paths:
        count_result = await db.execute(
            select(func.count()).where(
                (KnowledgeLink.source == path) | (KnowledgeLink.target == path)
            )
        )
        connection_counts[path] = count_result.scalar() or 0
    
    nodes = [
        GraphNode(
            id=note.path,
            label=note.title,
            vault=note.vault,
            node_type=note.node_type,
            connection_count=connection_counts.get(note.path, 0)
        )
        for note in notes
    ]
    
    # Fetch edges between neighbors (only forward links to avoid duplicates)
    edges_result = await db.execute(
        select(KnowledgeLink).where(
            KnowledgeLink.source.in_(neighbor_paths),
            KnowledgeLink.target.in_(neighbor_paths),
            KnowledgeLink.is_backlink == False
        )
    )
    links = edges_result.scalars().all()
    
    edges = [
        GraphEdge(
            source=link.source,
            target=link.target,
            type=link.link_type,
            is_backlink=link.is_backlink
        )
        for link in links
    ]
    
    return NeighborhoodResponse(
        center_node=node_id,
        depth=depth,
        nodes=nodes,
        edges=edges
    )


@router.get("/related/{note_path:path}", response_model=List[RelatedNote])
async def get_related_notes(
    note_path: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    Get notes that link to or from this note (bidirectional).
    
    Returns related notes with their vault and link type information.
    """
    # Forward links
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
    
    # Backward links
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
    
    # Combine with union
    combined = union_all(forward_query, backward_query).limit(limit)
    
    result = await db.execute(combined)
    rows = result.all()
    
    return [
        RelatedNote(
            path=row.path,
            title=row.title,
            vault=row.vault,
            link_type=row.link_type,
            is_backlink=row.is_backlink
        )
        for row in rows
    ]


@router.get("/stats", response_model=GraphStats)
async def get_graph_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Get statistics about the knowledge graph.
    
    Includes total notes, links, vault breakdown, and top connected nodes.
    """
    # Total notes
    notes_count = await db.execute(select(func.count()).select_from(VaultNote))
    total_notes = notes_count.scalar() or 0
    
    # Total links
    links_count = await db.execute(select(func.count()).select_from(KnowledgeLink))
    total_links = links_count.scalar() or 0
    
    # Vault breakdown
    vault_result = await db.execute(
        select(VaultNote.vault, func.count().label('count'))
        .group_by(VaultNote.vault)
    )
    vault_breakdown = {row.vault: row.count for row in vault_result.all()}
    
    # Top connected nodes
    top_query = select(
        VaultNote.path,
        VaultNote.title,
        VaultNote.vault,
        func.count().label('connection_count')
    ).join(
        KnowledgeLink,
        (VaultNote.path == KnowledgeLink.source) | (VaultNote.path == KnowledgeLink.target)
    ).group_by(
        VaultNote.path, VaultNote.title, VaultNote.vault
    ).order_by(
        func.count().desc()
    ).limit(10)
    
    top_result = await db.execute(top_query)
    top_connected = [
        {
            "path": row.path,
            "title": row.title,
            "vault": row.vault,
            "connections": row.connection_count
        }
        for row in top_result.all()
    ]
    
    # Isolated nodes (no connections)
    isolated_query = select(func.count()).select_from(VaultNote).where(
        ~VaultNote.path.in_(
            select(KnowledgeLink.source).union(
                select(KnowledgeLink.target)
            )
        )
    )
    isolated_result = await db.execute(isolated_query)
    isolated_count = isolated_result.scalar() or 0
    
    return GraphStats(
        total_notes=total_notes,
        total_links=total_links,
        vault_breakdown=vault_breakdown,
        top_connected=top_connected,
        isolated_nodes=isolated_count
    )


@router.get("/vaults")
async def get_vault_structure(
    db: AsyncSession = Depends(get_db)
):
    """
    Get the structure of all vaults with note counts.
    
    Returns list of vaults with metadata and note counts.
    """
    result = await db.execute(
        select(
            VaultNote.vault,
            func.count().label('note_count'),
            func.min(VaultNote.created_at).label('oldest_note'),
            func.max(VaultNote.updated_at).label('newest_note')
        ).group_by(VaultNote.vault)
    )
    
    rows = result.all()
    
    vault_info = {
        "work":     {"name": "Work",     "description": "Uni, FYP, courses, job, projects", "color": "#FF9800"},
        "personal": {"name": "Personal", "description": "Life, goals, journal, health, finance", "color": "#2196F3"},
        "kb":        {"name": "Knowledge", "description": "Concepts, tools, people, references", "color": "#4CAF50"},
        "inbox":     {"name": "Inbox",    "description": "Drop zone — unprocessed items", "color": "#9E9E9E"},
    }
    
    return [
        {
            "id": row.vault,
            "name": vault_info.get(row.vault, {}).get("name", row.vault),
            "description": vault_info.get(row.vault, {}).get("description", ""),
            "color": vault_info.get(row.vault, {}).get("color", "#757575"),
            "note_count": row.note_count,
            "oldest_note": row.oldest_note.isoformat() if row.oldest_note else None,
            "newest_note": row.newest_note.isoformat() if row.newest_note else None,
        }
        for row in rows
    ]


@router.post("/reindex")
async def reindex_vault_links(
    vault: Optional[str] = Query(None, description="Specific vault to reindex, or all if not specified"),
    db: AsyncSession = Depends(get_db)
):
    """
    Re-scan vault files and rebuild all link relationships.
    
    Useful after bulk imports or if links get out of sync.
    """
    from atlas.core.backlinks import extract_all_links, store_links_in_db
    from pathlib import Path
    
    vault_root = Path("/opt/heimdall/vault")
    
    # Clear existing links for specified vault(s)
    if vault:
        await db.execute(
            KnowledgeLink.__table__.delete().where(
                (KnowledgeLink.source.like(f'{vault}/%')) |
                (KnowledgeLink.target.like(f'{vault}/%'))
            )
        )
        vaults_to_scan = [vault_root / vault] if (vault_root / vault).exists() else []
    else:
        await db.execute(KnowledgeLink.__table__.delete())
        vaults_to_scan = [d for d in vault_root.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    await db.commit()
    
    # Re-scan and extract links
    total_links = 0
    for vault_dir in vaults_to_scan:
        vault_name = vault_dir.name
        
        for md_file in vault_dir.rglob("*.md"):
            try:
                content = md_file.read_text()
                relative_path = md_file.relative_to(vault_root)
                source_vault = relative_path.parts[0]
                source_path = "/".join(relative_path.parts[1:])
                
                # Extract links
                links = extract_all_links(content, source_vault, source_path)
                
                if links:
                    await store_links_in_db(links, db)
                    total_links += len(links)
                    
            except Exception as e:
                # Log error but continue
                print(f"Error processing {md_file}: {e}")
                continue
    
    return {
        "status": "success",
        "vaults_scanned": len(vaults_to_scan),
        "total_links_created": total_links
    }
