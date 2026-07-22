"""
Vector Store — ChromaDB interface for semantic search.

Stores document chunks with embeddings and metadata.
Supports filtered search by doc_id, doc_type, equipment_tag.
"""

import os
import time
import chromadb
from chromadb.config import Settings
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from pathlib import Path
from typing import Optional
from backend.config import CHROMA_COLLECTION_NAME, VECTOR_PERSIST_DIR, VECTOR_SEARCH_TOP_K


class EmbeddingError(Exception):
    """Raised when embeddings cannot be produced. Never silently degrade to
    zero vectors — a zero vector poisons the index (chunks become unsearchable
    while indexing appears to 'succeed')."""


class GeminiEmbeddingFunction(EmbeddingFunction):
    """Use Gemini API for embeddings instead of local ONNX models to save RAM.

    - Reuses a single genai.Client across calls (no per-call HTTP setup).
    - Retries transient failures (429 rate limits, 5xx) with exponential backoff.
    - Raises EmbeddingError on persistent failure instead of returning zero
      vectors, so callers can fail loudly / retry the document.
    """

    _client = None  # shared across instances

    # Free-tier friendly: smaller batches, retry hard on rate limits
    BATCH_SIZE = 25
    MAX_RETRIES = 6
    BASE_DELAY = 2.0  # seconds; doubles each retry (2, 4, 8, 16, 32, 64)

    @classmethod
    def _get_client(cls):
        if cls._client is None:
            from google import genai
            api_key = os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                raise EmbeddingError(
                    "GEMINI_API_KEY is not set — cannot generate embeddings. "
                    "Set it in the environment (Render dashboard / .env)."
                )
            cls._client = genai.Client(api_key=api_key)
        return cls._client

    def _embed_batch_with_retry(self, batch: list[str]) -> list[list[float]]:
        client = self._get_client()
        last_err = None
        for attempt in range(self.MAX_RETRIES):
            try:
                res = client.models.embed_content(
                    model="gemini-embedding-2", contents=batch
                )
                embeddings = [e.values for e in (res.embeddings or [])]
                if len(embeddings) != len(batch):
                    # Some API tiers only return one embedding per request —
                    # fall back to embedding each text individually
                    if len(batch) > 1:
                        print(f"[GeminiEmbedding] batch of {len(batch)} returned "
                              f"{len(embeddings)} embeddings — falling back to per-item requests")
                        result = []
                        for text in batch:
                            result.extend(self._embed_batch_with_retry([text]))
                            time.sleep(0.3)
                        return result
                    raise EmbeddingError(
                        f"API returned {len(embeddings)} embeddings for {len(batch)} texts"
                    )
                return embeddings
            except Exception as e:
                last_err = e
                msg = str(e)
                # Retry on rate limits / transient server errors
                retryable = any(s in msg for s in ("429", "RESOURCE_EXHAUSTED", "500", "503", "UNAVAILABLE", "DEADLINE"))
                if not retryable and attempt >= 1:
                    break  # non-transient error, don't burn retries
                delay = self.BASE_DELAY * (2 ** attempt)
                print(f"[GeminiEmbedding] attempt {attempt + 1}/{self.MAX_RETRIES} failed ({msg[:120]}) — retrying in {delay:.0f}s")
                time.sleep(delay)
        raise EmbeddingError(f"Embedding failed after {self.MAX_RETRIES} attempts: {last_err}")

    def __call__(self, input: Documents) -> Embeddings:
        all_embeddings = []
        for i in range(0, len(input), self.BATCH_SIZE):
            batch = list(input[i : i + self.BATCH_SIZE])
            embeddings = self._embed_batch_with_retry(batch)
            all_embeddings.extend(embeddings)
            print(f"[GeminiEmbedding] OK: {len(batch)} texts embedded (dim={len(embeddings[0])})")
            # Gentle pacing between batches to stay under free-tier RPM limits
            if i + self.BATCH_SIZE < len(input):
                time.sleep(0.5)
        return all_embeddings




class VectorStore:
    """
    ChromaDB-based vector store for document chunks.
    Uses Google Gemini API for embeddings — no local model needed.
    On Render free tier (RENDER env var set), uses EphemeralClient since
    there is no persistent disk storage.
    """

    def __init__(self, persist_dir: str = None, collection_name: str = None):
        self.persist_dir = persist_dir or str(VECTOR_PERSIST_DIR)
        self.collection_name = collection_name or CHROMA_COLLECTION_NAME

        # The repo ships a prebuilt chroma_db (data/chroma_db) with Gemini
        # embeddings already computed — PersistentClient reads it directly,
        # so startup makes ZERO embedding API calls even on ephemeral hosts
        # (Render/Cloud Run). Writes work too (container fs is writable);
        # they just don't survive restarts, same as before.
        self.client = chromadb.PersistentClient(path=self.persist_dir)

        # Only clear the collection if its embedding dimension doesn't match
        # Gemini's 3072-dim output (e.g. leftover 768-dim ONNX embeddings).
        # Unconditional wiping destroyed user-uploaded documents on every boot.
        from backend.config import LLM_PROVIDER
        if LLM_PROVIDER in ("openrouter", "azure_foundry"):
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
            emb_fn = DefaultEmbeddingFunction()
            expected_dim = 384
        else:
            emb_fn = GeminiEmbeddingFunction()
            expected_dim = 3072

        try:
            existing = self.client.get_collection(name=self.collection_name)
            peek = existing.peek(limit=1)
            embs = peek.get("embeddings")
            has_embeddings = embs is not None and len(embs) > 0
            if has_embeddings and len(embs[0]) != expected_dim:
                self.client.delete_collection(name=self.collection_name)
                print(f"[VectorStore] Dimension mismatch ({len(embs[0])} != {expected_dim}) — recreated collection")
        except Exception:
            pass  # Collection didn't exist yet — that's fine

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=emb_fn,
            metadata={"hnsw:space": "cosine"},
        )
        print(f"[VectorStore] Collection '{self.collection_name}' ready")

    def add_chunks(self, chunks: list[dict], embeddings: list[list[float]] = None):
        """
        Add document chunks to the vector store.
        
        Args:
            chunks: List of chunk dicts from SemanticChunker
            embeddings: Optional pre-computed embeddings. If None, ChromaDB will
                       use its default embedding function.
        """
        if not chunks:
            return
        
        ids = [chunk["id"] for chunk in chunks]
        documents = [chunk["content"] for chunk in chunks]
        metadatas = []
        
        for chunk in chunks:
            metadata = {
                "doc_id": chunk.get("doc_id", ""),
                "doc_title": chunk.get("doc_title", ""),
                "doc_category": chunk.get("doc_category", ""),
                "page_num": chunk.get("page_num", 0),
                "section_path": chunk.get("section_path", ""),
                "equipment_tags": ",".join(chunk.get("equipment_tags", [])),
                "date_range": chunk.get("date_range", ""),
                "chunk_index": chunk.get("chunk_index", 0),
                "token_count": chunk.get("token_count", 0),
            }
            # ChromaDB metadata values must be str, int, float, or bool
            metadatas.append(metadata)
        
        kwargs = {
            "ids": ids,
            "documents": documents,
            "metadatas": metadatas,
        }
        
        if embeddings:
            kwargs["embeddings"] = embeddings
        
        # Upsert in batches (ChromaDB has limits)
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch_kwargs = {
                k: v[i:i+batch_size] if isinstance(v, list) else v
                for k, v in kwargs.items()
            }
            self.collection.upsert(**batch_kwargs)

    def search(self, query: str, top_k: int = None,
               filter_doc_ids: list[str] = None,
               filter_category: str = None,
               query_embedding: list[float] = None) -> list[dict]:
        """
        Search for similar chunks.
        
        Args:
            query: Search query text
            top_k: Number of results
            filter_doc_ids: Optional list of doc_ids to restrict search to
            filter_category: Optional document category filter
            query_embedding: Optional pre-computed query embedding
            
        Returns:
            List of {content, metadata, distance} sorted by relevance.
        """
        top_k = top_k or VECTOR_SEARCH_TOP_K
        
        # Build where filter
        where = None
        where_conditions = []
        
        if filter_doc_ids:
            if len(filter_doc_ids) == 1:
                where_conditions.append({"doc_id": filter_doc_ids[0]})
            else:
                where_conditions.append({"doc_id": {"$in": filter_doc_ids}})
        
        if filter_category:
            where_conditions.append({"doc_category": filter_category})
        
        if len(where_conditions) == 1:
            where = where_conditions[0]
        elif len(where_conditions) > 1:
            where = {"$and": where_conditions}
        
        # Execute query
        try:
            kwargs = {"n_results": min(top_k, self.collection.count() or top_k)}
            
            if query_embedding:
                kwargs["query_embeddings"] = [query_embedding]
            else:
                kwargs["query_texts"] = [query]
            
            if where:
                kwargs["where"] = where
            
            results = self.collection.query(**kwargs)
        except Exception as e:
            print(f"Vector search error: {e}")
            return []
        
        # Format results
        formatted = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0
                
                formatted.append({
                    "content": doc,
                    "metadata": metadata,
                    "distance": distance,
                    "relevance_score": 1.0 - distance,  # cosine: lower distance = more similar
                    "id": results["ids"][0][i] if results["ids"] else "",
                })
        
        return formatted

    def delete_document(self, doc_id: str) -> int:
        """Remove all chunks for a document."""
        try:
            # Get all chunks for this document
            results = self.collection.get(
                where={"doc_id": doc_id}
            )
            
            if results and results["ids"]:
                self.collection.delete(ids=results["ids"])
                return len(results["ids"])
        except Exception as e:
            print(f"Delete error: {e}")
        
        return 0

    def get_document_chunks(self, doc_id: str) -> list[dict]:
        """Get all chunks for a specific document."""
        try:
            results = self.collection.get(
                where={"doc_id": doc_id},
                include=["documents", "metadatas"],
            )
            
            chunks = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"]):
                    chunks.append({
                        "content": doc,
                        "metadata": results["metadatas"][i] if results["metadatas"] else {},
                        "id": results["ids"][i],
                    })
            
            return sorted(chunks, key=lambda x: x["metadata"].get("chunk_index", 0))
        except Exception:
            return []

    def get_stats(self) -> dict:
        """Get vector store statistics."""
        return {
            "total_chunks": self.collection.count(),
            "collection_name": self.collection_name,
        }
