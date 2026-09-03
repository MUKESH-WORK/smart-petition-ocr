from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from models.schemas import SearchRequest, SearchResultItem
from services.vector_store import vector_store

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("", response_model=List[SearchResultItem])
async def search_documents(
    req: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Search document chunks using pgvector similarity search, GIN full-text search, or RRF hybrid search
    """
    source_id_str = str(req.source_id) if req.source_id else None

    if req.search_type == "vector":
        results = await vector_store.similarity_search(db, query=req.query, source_id=source_id_str, top_k=req.top_k)
        return [
            SearchResultItem(
                id=r["id"],
                chunk_text=r["chunk_text"],
                page_number=r.get("page_number", 1),
                score=round(float(r.get("similarity", 0.0)), 4),
                metadata=r.get("metadata")
            )
            for r in results
        ]
    elif req.search_type == "fulltext":
        results = await vector_store.fulltext_search(db, query=req.query, source_id=source_id_str, top_k=req.top_k)
        return [
            SearchResultItem(
                id=r["id"],
                chunk_text=r["chunk_text"],
                page_number=r.get("page_number", 1),
                score=round(float(r.get("rank", 0.0)), 4),
                metadata=r.get("metadata")
            )
            for r in results
        ]
    else:  # hybrid
        results = await vector_store.hybrid_search(db, query=req.query, source_id=source_id_str, top_k=req.top_k)
        return [
            SearchResultItem(
                id=r["id"],
                chunk_text=r["chunk_text"],
                page_number=r.get("page_number", 1),
                score=round(float(r.get("score", 0.0)), 4),
                metadata=r.get("metadata")
            )
            for r in results
        ]
