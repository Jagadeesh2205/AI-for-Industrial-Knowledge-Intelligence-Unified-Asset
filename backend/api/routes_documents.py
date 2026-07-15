"""
Document Routes — Document listing, preview, and deletion.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


@router.get("/api/documents")
async def list_documents():
    """List all indexed documents with stats."""
    from backend.main import get_graph_store, get_vector_store
    
    graph_store = get_graph_store()
    vector_store = get_vector_store()
    
    documents = []
    
    for node_id, data in graph_store.graph.nodes(data=True):
        if data.get("type") == "Document":
            doc_id = data.get("doc_id", node_id.replace("document:", ""))
            
            # Count chunks for this document
            chunks = vector_store.get_document_chunks(doc_id)
            
            # Count connected entities
            connected_entities = 0
            for pred in graph_store.graph.predecessors(node_id):
                connected_entities += 1
            for succ in graph_store.graph.successors(node_id):
                connected_entities += 1
            
            documents.append({
                "doc_id": doc_id,
                "title": data.get("title", data.get("filename", "Unknown")),
                "filename": data.get("filename", ""),
                "doc_type": data.get("doc_type", "general"),
                "page_count": data.get("page_count", 0),
                "chunk_count": len(chunks),
                "entity_count": connected_entities,
                "date": data.get("date", ""),
            })
    
    return {
        "documents": documents,
        "total": len(documents),
    }


@router.get("/api/documents/{doc_id}/preview")
async def document_preview(doc_id: str):
    """Return document chunks for preview."""
    from backend.main import get_vector_store
    
    vector_store = get_vector_store()
    chunks = vector_store.get_document_chunks(doc_id)
    
    # Combine chunks into preview text
    preview_text = "\n\n---\n\n".join([c.get("content", "") for c in chunks])
    
    return {
        "doc_id": doc_id,
        "preview": preview_text,
        "chunk_count": len(chunks),
        "chunks": chunks[:10],  # Limit preview chunks
    }


@router.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Remove a document from all stores."""
    from backend.main import get_graph_store, get_vector_store
    
    graph_store = get_graph_store()
    vector_store = get_vector_store()
    
    # Remove from vector store
    chunks_deleted = vector_store.delete_document(doc_id)
    
    # Remove from graph
    nodes_deleted = graph_store.remove_document(doc_id)
    graph_store.save()
    
    return {
        "doc_id": doc_id,
        "chunks_deleted": chunks_deleted,
        "graph_nodes_deleted": nodes_deleted,
        "status": "deleted",
    }
