from fastapi import APIRouter, Query
from pydantic import BaseModel
from atlas.db.vector_store import store, search, search_all, browse, counts, VECTOR_TABLES

router = APIRouter(prefix="/memory", tags=["memory"])


class StoreRequest(BaseModel):
    text: str
    table: str = "vector_memory"
    source_type: str = "fact"
    source_path: str = ""


class StoreResponse(BaseModel):
    id: str
    table: str


class SearchResult(BaseModel):
    id: str
    text: str
    source_type: str
    source_path: str
    distance: float
    table: str = ""


@router.post("/store", response_model=StoreResponse)
async def store_memory(req: StoreRequest):
    entry_id = await store(req.table, req.text, req.source_type, req.source_path)
    return StoreResponse(id=entry_id, table=req.table)


@router.get("/search", response_model=list[SearchResult])
async def search_memory(
    q: str = Query(..., description="Search query"),
    table: str = Query("__all__", description="Table to search or '__all__'"),
    limit: int = Query(5, ge=1, le=20),
):
    if table == "__all__":
        results = await search_all(q, limit=limit)
        for r in results:
            r.setdefault("table", "")
    else:
        results = await search(table, q, limit=limit)
        for r in results:
            r["table"] = table
    return results


@router.get("/tables")
async def list_tables():
    return {"tables": VECTOR_TABLES}


@router.get("/counts")
async def table_counts():
    return await counts()


@router.get("/browse")
async def browse_memory(
    table: str = Query("vector_memory"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    rows = await browse(table, limit=limit, offset=offset)
    return rows
