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
    """Index sample documents on startup.

    - Uses deterministic doc IDs (uuid5 of filename) so re-runs update the
      same graph nodes instead of accumulating duplicates.
    - Skips docs whose chunks are already in the vector store (saves Gemini
      API quota on local restarts; on Render the ephemeral store is empty,
      so everything re-indexes).
    """
    import uuid as _uuid

    sample_dir = SAMPLE_DOCS_DIR
    if not sample_dir.exists():
        print(f"⚠ Sample docs dir not found: {sample_dir}")
        return

    supported = {'.pdf', '.txt', '.docx', '.xlsx', '.xls', '.csv'}
    files = [f for f in sample_dir.iterdir() if f.suffix.lower() in supported]

    if not files:
        print("⚠ No sample documents found.")
        return

    print(f"📄 Indexing {len(files)} sample documents...")
    indexer = get_indexer()
    vector_store = get_vector_store()
    success, failed, skipped = 0, 0, 0

    for filepath in files:
        # Deterministic ID: same file always maps to the same doc node
        doc_id = str(_uuid.uuid5(_uuid.NAMESPACE_URL, f"sample:{filepath.name}"))
        try:
            if vector_store.get_document_chunks(doc_id):
                skipped += 1
                continue
            result = indexer.index_document(str(filepath), doc_id=doc_id)
            status = "✓" if result["status"] == "completed" else "✗"
            chunks = result.get("chunks_created", 0)
            entities = result.get("entities_extracted", 0)
            print(f"  {status} {filepath.name}: {chunks} chunks, {entities} entities")
            if result["status"] == "completed":
                success += 1
            else:
                failed += 1
                print(f"    error: {result.get('error')}")
        except Exception as e:
            print(f"  ✗ {filepath.name}: {e}")
            failed += 1

    graph_store = get_graph_store()
    stats = vector_store.get_stats()
    graph_stats = graph_store.get_stats()
    print(f"\n✓ Indexed {success} new, {skipped} already indexed, {failed} failed: "
          f"{stats['total_chunks']} chunks, "
          f"{graph_stats['total_nodes']} nodes, "
          f"{graph_stats['total_edges']} edges")
    if failed:
        print(f"⚠ {failed} documents failed to index — check logs above")



# ── App Lifecycle ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    import threading

    print("\n🧠 Plant Brain — Industrial Knowledge Intelligence Platform")
    print("=" * 60)

    # Initialize stores
    print("⚡ Initializing stores...")
    get_vector_store()
    get_graph_store()
    get_retriever()
    get_agents()

    # Index sample docs in the background so the server binds its port
    # immediately — platform health checks (DigitalOcean/Render) fail the
    # deploy if the port isn't open within ~2 min, and embedding all docs
    # takes longer than that.
    def _index_in_background():
        try:
            load_sample_docs()
            app.state.indexing_complete = True
        except Exception as e:
            print(f"⚠ Background indexing failed: {e}")

    app.state.indexing_complete = False
    threading.Thread(target=_index_in_background, daemon=True).start()

    print(f"\n🚀 Server ready at http://localhost:{API_PORT} (indexing continues in background)")
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

# CORS — allow all for deployment (demo platform, no auth required)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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
        "indexing_complete": getattr(app.state, "indexing_complete", True),
    }


@app.get("/api/stats")
async def stats():
    """System statistics."""
    from backend.config import LLM_PROVIDER
    from backend.activity import get_activity
    vector_store = get_vector_store()
    graph_store = get_graph_store()

    return {
        "vector_store": vector_store.get_stats(),
        "graph_store": graph_store.get_stats(),
        "llm_provider": LLM_PROVIDER,
        "query_count": get_activity()["query_count"],
    }


@app.get("/api/activity")
async def activity():
    """Real system activity feed (queries, ingests) for the dashboard."""
    from backend.activity import get_activity
    return get_activity()


@app.get("/api/equipment/status")
async def equipment_status():
    """Equipment status derived from the knowledge graph.

    critical: equipment with failure events recorded in incident reports
    warn:     equipment with any recorded failure events
    safe:     no failure events on record
    """
    graph_store = get_graph_store()
    g = graph_store.graph
    equipment = []

    for node_id, data in g.nodes(data=True):
        if data.get("type") != "Equipment":
            continue
        tag = data.get("tag", node_id.replace("equipment:", ""))
        failure_descriptions = []
        has_incident = False

        for succ in g.successors(node_id):
            succ_data = g.nodes[succ]
            if succ_data.get("type") != "Event":
                continue
            edge = g.get_edge_data(node_id, succ) or {}
            if edge.get("relation") != "EXPERIENCED":
                continue
            desc = succ_data.get("description", "")
            if desc:
                failure_descriptions.append(desc.replace("Failure: ", ""))
            # Event → Document edges tell us the evidence type
            for doc_succ in g.successors(succ):
                if g.nodes[doc_succ].get("type") == "Document" and \
                   g.nodes[doc_succ].get("doc_type") == "incident_report":
                    has_incident = True

        if has_incident:
            status = "critical"
        elif failure_descriptions:
            status = "warn"
        else:
            status = "safe"

        equipment.append({
            "tag": tag,
            "equipment_type": data.get("equipment_type", "equipment"),
            "status": status,
            "desc": failure_descriptions[0][:30] if failure_descriptions else "Running",
            "failure_count": len(failure_descriptions),
        })

    order = {"critical": 0, "warn": 1, "safe": 2}
    equipment.sort(key=lambda e: (order[e["status"]], e["tag"]))
    return {"equipment": equipment, "total": len(equipment)}


# ── Entry Point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
    )
