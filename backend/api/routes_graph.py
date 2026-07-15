"""
Graph Routes — Knowledge graph data endpoints.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


@router.get("/api/graph")
async def get_graph():
    """Returns full knowledge graph in react-force-graph format."""
    from backend.main import get_graph_store
    
    graph_store = get_graph_store()
    graph_data = graph_store.serialize_for_frontend()
    stats = graph_store.get_stats()
    
    return {
        "graph": graph_data,
        "stats": stats,
    }


@router.get("/api/graph/equipment/{tag}")
async def get_equipment_subgraph(tag: str):
    """Subgraph centered on specific equipment tag."""
    from backend.main import get_graph_store
    
    graph_store = get_graph_store()
    
    # Get subgraph
    subgraph = graph_store.get_subgraph(f"equipment:{tag.upper()}", depth=2)
    
    # Get equipment history
    history = graph_store.get_equipment_history(tag)
    
    return {
        "graph": subgraph,
        "history": history,
        "equipment_tag": tag.upper(),
    }


@router.get("/api/graph/stats")
async def get_graph_stats():
    """Knowledge graph statistics."""
    from backend.main import get_graph_store
    
    graph_store = get_graph_store()
    return graph_store.get_stats()


@router.get("/api/graph/compliance")
async def get_compliance_gaps(regulation: Optional[str] = None):
    """Get compliance gaps from knowledge graph."""
    from backend.main import get_graph_store
    
    graph_store = get_graph_store()
    gaps = graph_store.get_compliance_gaps(regulation)
    
    return {
        "regulation": regulation,
        "gaps": gaps,
        "total_gaps": len(gaps),
    }


@router.get("/api/graph/failures")
async def get_failure_patterns(failure_mode: Optional[str] = None):
    """Get failure patterns across equipment."""
    from backend.main import get_graph_store
    
    graph_store = get_graph_store()
    
    if failure_mode:
        patterns = graph_store.get_failure_patterns(failure_mode)
    else:
        # Get all failure modes
        patterns = []
        for node_id, data in graph_store.graph.nodes(data=True):
            if data.get("type") == "FailureMode":
                mode_patterns = graph_store.get_failure_patterns(data.get("description", ""))
                patterns.extend(mode_patterns)
    
    return {
        "failure_mode": failure_mode,
        "patterns": patterns,
        "total_patterns": len(patterns),
    }
