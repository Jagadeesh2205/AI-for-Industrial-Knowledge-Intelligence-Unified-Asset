"""
Plant Brain — FastAPI Application Entry Point.

Industrial Knowledge Intelligence Platform.
Hybrid Graph-RAG system with conversational AI agents.
"""

import os
import io
import sys

# Fix Windows console encoding for emoji/unicode
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
from contextlib import asynccontextmanager
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import (
    CORS_ORIGINS, API_HOST, API_PORT,
    VECTOR_PERSIST_DIR, GRAPH_PERSIST_PATH, CHROMA_COLLECTION_NAME,
    SAMPLE_DOCS_DIR,
)

# ── Global Singletons ─────────────────────────────────────────────────
_vector_store = None
_graph_store = None
_indexer = None
_retriever = None
_agents = None


def get_vector_store():
    global _vector_store
    if _vector_store is None:
        from backend.knowledge.vector_store import VectorStore
        _vector_store = VectorStore(
            persist_dir=str(VECTOR_PERSIST_DIR),
            collection_name=CHROMA_COLLECTION_NAME,
        )
    return _vector_store


def get_graph_store():
    global _graph_store
    if _graph_store is None:
        from backend.knowledge.graph_store import GraphStore
        _graph_store = GraphStore(persist_path=str(GRAPH_PERSIST_PATH))
    return _graph_store


def get_indexer():
    global _indexer
    if _indexer is None:
        from backend.knowledge.indexer import Indexer
        _indexer = Indexer(get_vector_store(), get_graph_store())
    return _indexer


def get_retriever():
    global _retriever
    if _retriever is None:
        from backend.retrieval.hybrid_retriever import HybridRetriever
        _retriever = HybridRetriever(get_vector_store(), get_graph_store())
    return _retriever


def get_agents():
    global _agents
    if _agents is None:
        from backend.agents.expert_copilot import ExpertCopilot
        from backend.agents.maintenance_agent import MaintenanceAgent
        from backend.agents.compliance_agent import ComplianceAgent
        
        retriever = get_retriever()
        _agents = {
            "copilot": ExpertCopilot(retriever),
            "maintenance": MaintenanceAgent(retriever),
            "compliance": ComplianceAgent(retriever),
        }
    return _agents


def load_sample_docs():
    """Load sample documents if they exist and haven't been indexed."""
    sample_dir = SAMPLE_DOCS_DIR
    if not sample_dir.exists():
        return
    
    # Check if already indexed
    vector_store = get_vector_store()
    if vector_store.get_stats().get("total_chunks", 0) > 0:
        print(f"✓ Knowledge base already contains {vector_store.get_stats()['total_chunks']} chunks")
        return
    
    # Index sample documents
    supported = {'.pdf', '.txt', '.docx', '.xlsx', '.xls', '.csv'}
    files = [f for f in sample_dir.iterdir() if f.suffix.lower() in supported]
    
    if files:
        print(f"📄 Indexing {len(files)} sample documents...")
        indexer = get_indexer()
        for filepath in files:
            try:
                result = indexer.index_document(str(filepath))
                status = "✓" if result["status"] == "completed" else "✗"
                print(f"  {status} {filepath.name}: {result['chunks_created']} chunks, "
                      f"{result['entities_extracted']} entities")
            except Exception as e:
                print(f"  ✗ {filepath.name}: {e}")
        
        stats = vector_store.get_stats()
        graph_stats = get_graph_store().get_stats()
        print(f"\n✓ Indexing complete: {stats['total_chunks']} chunks, "
              f"{graph_stats['total_nodes']} graph nodes, "
              f"{graph_stats['total_edges']} graph edges")


# ── App Lifecycle ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print("\n🧠 Plant Brain — Industrial Knowledge Intelligence Platform")
    print("=" * 60)
    
    # Initialize stores
    print("⚡ Initializing stores...")
    get_vector_store()
    get_graph_store()
    get_retriever()
    get_agents()
    
    # Load sample documents
    load_sample_docs()
    
    print(f"\n🚀 Server ready at http://localhost:{API_PORT}")
    print(f"📚 API docs at http://localhost:{API_PORT}/docs")
    print("=" * 60 + "\n")
    
    yield
    
    # Cleanup
    graph_store = get_graph_store()
    graph_store.save()
    print("\n✓ Graph saved. Shutting down.")


# ── FastAPI App ────────────────────────────────────────────────────────

app = FastAPI(
    title="Plant Brain",
    description="Industrial Knowledge Intelligence Platform — Hybrid Graph-RAG",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["*"],  # Allow all for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routes ────────────────────────────────────────────────────

from backend.api.routes_query import router as query_router
from backend.api.routes_ingest import router as ingest_router
from backend.api.routes_graph import router as graph_router
from backend.api.routes_documents import router as documents_router

app.include_router(query_router, tags=["Query"])
app.include_router(ingest_router, tags=["Ingest"])
app.include_router(graph_router, tags=["Graph"])
app.include_router(documents_router, tags=["Documents"])


# ── Health & Stats ─────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    from backend.config import LLM_PROVIDER, LLM_MODELS
    return {
        "status": "healthy",
        "service": "plant-brain",
        "llm_provider": LLM_PROVIDER,
        "llm_model": LLM_MODELS.get(LLM_PROVIDER, "unknown"),
    }


@app.get("/api/stats")
async def stats():
    """System statistics."""
    vector_store = get_vector_store()
    graph_store = get_graph_store()
    
    return {
        "vector_store": vector_store.get_stats(),
        "graph_store": graph_store.get_stats(),
        "llm_provider": os.getenv("LLM_PROVIDER", "mock"),
    }


# ── Entry Point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
    )
