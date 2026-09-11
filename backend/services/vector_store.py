import uuid
import json
import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING
import numpy as np

# pyrefly: ignore [missing-import]
if TYPE_CHECKING:
    # pyrefly: ignore [missing-import]
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text
else:
    try:
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy import text
    except ImportError:
        AsyncSession = Any
        text = lambda x: x
from app.config import settings

logger = logging.getLogger(__name__)


class PGVectorStore:
    def __init__(self, model_name: str = settings.EMBEDDING_MODEL_NAME):
        self.model_name = model_name
        self._embedder = None

    def warmup(self):
        """Warm up embedding model locally so first user query has zero lag."""
        try:
            self._get_embedder()
            self.encode(["தமிழ்நாடு அரசு"])
        except Exception as e:
            logger.warning(f"Vector store warmup note: {e}")

    def _get_embedder(self):
        if self._embedder is None:
            try:
                import torch
                torch.set_num_threads(4)
                from sentence_transformers import SentenceTransformer
                try:
                    self._embedder = SentenceTransformer(self.model_name, local_files_only=True)
                except Exception:
                    self._embedder = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.warning(f"SentenceTransformer not loaded directly: {e}. Using deterministic normalized embedding generator.")
                self._embedder = "mock_embedder"
        return self._embedder

    def encode(self, texts: List[str]) -> List[List[float]]:
        embedder = self._get_embedder()
        if embedder != "mock_embedder" and embedder is not None:
            embeddings = embedder.encode(texts, normalize_embeddings=True)
            return embeddings.tolist()
        
        # Deterministic 384-dim normalized pseudo-embedding based on hash for zero-failure fallback
        vectors = []
        for t in texts:
            np.random.seed(abs(hash(t)) % (2**32))
            v = np.random.randn(384).astype(np.float32)
            norm = np.linalg.norm(v)
            v = v / norm if norm > 0 else v
            vectors.append(v.tolist())
        return vectors

    async def index_document(self, db: AsyncSession, source_id: str, chunks: List[Dict[str, Any]]):
        if not chunks:
            return

        from models.database import is_sqlite
        texts = [c["text"] for c in chunks]
        embeddings = self.encode(texts)

        for chunk, emb in zip(chunks, embeddings):
            chunk_id = str(uuid.uuid4())
            emb_list = emb.tolist() if hasattr(emb, "tolist") else list(emb)
            emb_val = json.dumps(emb_list) if is_sqlite else emb_list
            await db.execute(text("""
                INSERT INTO document_chunks (id, source_id, page_number, chunk_index, chunk_text, embedding, metadata)
                VALUES (CAST(:id AS UUID), CAST(:source_id AS UUID), :page_number, :chunk_index, :chunk_text, :embedding, :metadata)
            """), {
                "id": chunk_id,
                "source_id": str(source_id),
                "page_number": chunk.get("page_number", 1),
                "chunk_index": chunk.get("index", 0),
                "chunk_text": chunk["text"],
                "embedding": emb_val,
                "metadata": json.dumps(chunk.get("metadata", {}), ensure_ascii=False)
            })
        await db.commit()



    async def similarity_search(self, db: AsyncSession, query: str, source_id: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        from models.database import is_sqlite
        query_emb = self.encode([query])[0]

        # In PostgreSQL with pgvector, try native similarity search first
        if not is_sqlite:
            try:
                if source_id:
                    sql = """
                        SELECT id, chunk_text, metadata, page_number, 1 - (embedding <=> :query_embedding::vector) AS similarity
                        FROM document_chunks
                        WHERE source_id = CAST(:source_id AS UUID)
                        ORDER BY embedding <=> :query_embedding::vector
                        LIMIT :top_k
                    """
                    params = {"query_embedding": str(query_emb), "source_id": str(source_id), "top_k": top_k}
                else:
                    sql = """
                        SELECT id, chunk_text, metadata, page_number, 1 - (embedding <=> :query_embedding::vector) AS similarity
                        FROM document_chunks
                        ORDER BY embedding <=> :query_embedding::vector
                        LIMIT :top_k
                    """
                    params = {"query_embedding": str(query_emb), "top_k": top_k}
                result = await db.execute(text(sql), params)
                return [dict(r) for r in result.mappings()]
            except Exception:
                await db.rollback()

        # Portable In-Memory Cosine Similarity (SQLite & non-pgvector fallback)
        if source_id:
            sql = """
                SELECT id, chunk_text, metadata, page_number, embedding
                FROM document_chunks
                WHERE source_id = CAST(:source_id AS UUID)
            """
            result = await db.execute(text(sql), {"source_id": str(source_id)})
        else:
            sql = """
                SELECT id, chunk_text, metadata, page_number, embedding
                FROM document_chunks
            """
            result = await db.execute(text(sql))
        
        rows = [dict(r) for r in result.mappings()]
        q_vec = np.array(query_emb, dtype=np.float32)
        scored = []
        for r in rows:
            emb = r.get("embedding")
            if isinstance(emb, str):
                try:
                    emb = json.loads(emb)
                except Exception:
                    emb = None
            if emb is not None:
                e_vec = np.array(emb, dtype=np.float32)
                denom = (np.linalg.norm(q_vec) * np.linalg.norm(e_vec))
                sim = float(np.dot(q_vec, e_vec) / denom) if denom > 0 else 0.0
            else:
                sim = 0.0
            r["similarity"] = round(sim, 4)
            r.pop("embedding", None)
            scored.append(r)
        
        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:top_k]

    async def fulltext_search(self, db: AsyncSession, query: str, source_id: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        from models.database import is_sqlite
        if not is_sqlite:
            try:
                if source_id:
                    sql = """
                        SELECT id, chunk_text, metadata, page_number,
                            ts_rank(to_tsvector('simple', chunk_text), plainto_tsquery('simple', :query)) AS rank
                        FROM document_chunks
                        WHERE source_id = CAST(:source_id AS UUID)
                          AND to_tsvector('simple', chunk_text) @@ plainto_tsquery('simple', :query)
                        ORDER BY rank DESC
                        LIMIT :top_k
                    """
                    params = {"query": query, "source_id": str(source_id), "top_k": top_k}
                else:
                    sql = """
                        SELECT id, chunk_text, metadata, page_number,
                            ts_rank(to_tsvector('simple', chunk_text), plainto_tsquery('simple', :query)) AS rank
                        FROM document_chunks
                        WHERE to_tsvector('simple', chunk_text) @@ plainto_tsquery('simple', :query)
                        ORDER BY rank DESC
                        LIMIT :top_k
                    """
                    params = {"query": query, "top_k": top_k}
                result = await db.execute(text(sql), params)
                return [dict(r) for r in result.mappings()]
            except Exception:
                await db.rollback()

        # SQLite portable text search (substring match with ranking)
        try:
            if source_id:
                sql = """
                    SELECT id, chunk_text, metadata, page_number, 1.0 AS rank
                    FROM document_chunks
                    WHERE source_id = CAST(:source_id AS UUID)
                      AND chunk_text LIKE :q_like
                    LIMIT :top_k
                """
                params = {"q_like": f"%{query}%", "source_id": str(source_id), "top_k": top_k}
            else:
                sql = """
                    SELECT id, chunk_text, metadata, page_number, 1.0 AS rank
                    FROM document_chunks
                    WHERE chunk_text LIKE :q_like
                    LIMIT :top_k
                """
                params = {"q_like": f"%{query}%", "top_k": top_k}
            result = await db.execute(text(sql), params)
            return [dict(r) for r in result.mappings()]
        except Exception:
            return []


    async def hybrid_search(self, db: AsyncSession, query: str, source_id: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        v_results = await self.similarity_search(db, query, source_id, top_k * 2)
        t_results = await self.fulltext_search(db, query, source_id, top_k * 2)

        # Reciprocal Rank Fusion (RRF)
        scores = {}
        for rank, r in enumerate(v_results):
            r_id = str(r["id"])
            scores[r_id] = scores.get(r_id, 0.0) + 1.0 / (rank + 60)
            r["score"] = scores[r_id]

        for rank, r in enumerate(t_results):
            r_id = str(r["id"])
            scores[r_id] = scores.get(r_id, 0.0) + 1.0 / (rank + 60)
            r["score"] = scores[r_id]

        all_r = {str(r["id"]): r for r in v_results + t_results}
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        output = []
        for i in sorted_ids[:top_k]:
            item = all_r[i]
            item["score"] = round(scores[i], 4)
            output.append(item)
        return output


vector_store = PGVectorStore()
