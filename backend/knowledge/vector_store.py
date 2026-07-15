"""
Vector Store — ChromaDB interface for semantic search.

Stores document chunks with embeddings and metadata.
Supports filtered search by doc_id, doc_type, equipment_tag.
"""

import chromadb
from chromadb.config import Settings
from pathlib import Path
from typing import Optional
from backend.config import CHROMA_COLLECTION_NAME, VECTOR_PERSIST_DIR, VECTOR_SEARCH_TOP_K


class VectorStore:
    """
    ChromaDB-based vector store for document chunks.
    Uses ChromaDB's built-in embedding function or external embeddings.
    """

    def __init__(self, persist_dir: str = None, collection_name: str = None):
        self.persist_dir = persist_dir or str(VECTOR_PERSIST_DIR)
        self.collection_name = collection_name or CHROMA_COLLECTION_NAME
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

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
