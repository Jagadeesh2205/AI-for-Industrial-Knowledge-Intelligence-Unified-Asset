"""
Hybrid Retriever — Merges vector similarity with graph traversal.

RETRIEVAL FLOW:
1. Parse query intent
2. If entity-anchored: pull entity history from graph → filter vector search
3. Run vector search (full or filtered)
4. Rerank for diversity (MMR)
5. Format context for LLM with source metadata

Context format per chunk:
  [SOURCE: {doc_title} | {doc_type} | Page {page} | {date}]
  {chunk_content}
"""

from dataclasses import dataclass, field
from typing import Optional
from backend.retrieval.query_parser import parse_query_intent, QueryIntent
from backend.retrieval.reranker import mmr_rerank, category_diversify
from backend.knowledge.vector_store import VectorStore
from backend.knowledge.graph_store import GraphStore


@dataclass
class ContextChunk:
    """A retrieved chunk ready for LLM context."""
    content: str
    source_label: str          # Formatted source citation
    doc_id: str = ""
    doc_title: str = ""
    doc_type: str = ""
    page_num: int = 0
    relevance_score: float = 0.0
    from_graph: bool = False   # Whether this came from graph traversal


class HybridRetriever:
    """
    Hybrid retrieval engine combining vector search with graph traversal.
    """

    def __init__(self, vector_store: VectorStore, graph_store: GraphStore):
        self.vector = vector_store
        self.graph = graph_store

    def retrieve(self, query: str, top_k: int = 8, agent_type: str = "copilot") -> dict:
        """
        Retrieve relevant context for a query.
        
        Returns:
            {
                "chunks": list[ContextChunk],
                "intent": QueryIntent,
                "graph_context": dict | None,
                "total_sources": int,
            }
        """
        intent = parse_query_intent(query)
        graph_context = None
        chunks = []

        if intent.type == "ENTITY_ANCHORED":
            chunks, graph_context = self._entity_anchored_retrieval(query, intent, top_k)
        
        elif intent.type == "COMPLIANCE":
            chunks = self._compliance_retrieval(query, intent, top_k)
        
        elif intent.type == "PATTERN_MATCHING":
            chunks, graph_context = self._pattern_retrieval(query, intent, top_k)
        
        else:
            # Pure semantic search
            chunks = self._semantic_retrieval(query, top_k)

        return {
            "chunks": chunks,
            "intent": intent,
            "graph_context": graph_context,
            "total_sources": len(set(c.doc_id for c in chunks)),
        }

    def _entity_anchored_retrieval(self, query: str, intent: QueryIntent, 
                                    top_k: int) -> tuple[list[ContextChunk], dict]:
        """
        Graph-first retrieval for entity-anchored queries.
        1. Get entity history from graph
        2. Filter vector search to related documents
        3. Merge results
        """
        graph_context = {}
        graph_chunks = []
        related_doc_ids = set()

        # Get graph context for each equipment tag
        for tag in intent.entities:
            history = self.graph.get_equipment_history(tag)
            if history:
                graph_context[tag] = history
                
                # Collect doc IDs from graph
                for doc in history.get("documents", []):
                    doc_id = doc.get("doc_id", "")
                    if doc_id:
                        related_doc_ids.add(doc_id)
                
                # Create summary chunk from graph data
                summary = self._format_graph_summary(tag, history)
                if summary:
                    graph_chunks.append(ContextChunk(
                        content=summary,
                        source_label=f"[SOURCE: Knowledge Graph | Equipment History | {tag}]",
                        doc_id="graph",
                        doc_title="Knowledge Graph",
                        doc_type="graph_summary",
                        relevance_score=1.0,
                        from_graph=True,
                    ))

        # Vector search — filter to related docs if we found any
        filter_ids = list(related_doc_ids) if related_doc_ids else None
        vector_results = self.vector.search(query, top_k=top_k, filter_doc_ids=filter_ids)
        
        # If filtered search returned too few results, also do unfiltered
        if len(vector_results) < top_k // 2:
            unfiltered = self.vector.search(query, top_k=top_k)
            # Merge, avoiding duplicates
            seen_ids = {r.get("id") for r in vector_results}
            for r in unfiltered:
                if r.get("id") not in seen_ids:
                    vector_results.append(r)

        # Rerank for diversity
        vector_results = mmr_rerank(vector_results, top_k=top_k)

        # Convert to ContextChunks
        vector_chunks = [self._result_to_chunk(r) for r in vector_results]

        # Merge: graph chunks first, then vector chunks
        all_chunks = graph_chunks + vector_chunks
        return all_chunks[:top_k + 2], graph_context  # Allow extra for graph context

    def _compliance_retrieval(self, query: str, intent: QueryIntent,
                               top_k: int) -> list[ContextChunk]:
        """
        Compliance-focused retrieval.
        1. Find regulations in graph
        2. Get compliance gaps
        3. Search for related procedures
        """
        chunks = []

        # Get compliance gaps from graph
        for reg_code in intent.regulations:
            gaps = self.graph.get_compliance_gaps(reg_code)
            if gaps:
                summary = self._format_compliance_summary(reg_code, gaps)
                chunks.append(ContextChunk(
                    content=summary,
                    source_label=f"[SOURCE: Knowledge Graph | Compliance Analysis | {reg_code}]",
                    doc_id="graph",
                    doc_title="Compliance Analysis",
                    doc_type="compliance",
                    relevance_score=1.0,
                    from_graph=True,
                ))

        # Vector search for compliance documents
        vector_results = self.vector.search(
            query, top_k=top_k,
            filter_category="regulatory"
        )
        
        # Also search procedures
        procedure_results = self.vector.search(
            query, top_k=top_k // 2,
            filter_category="safety_procedure"
        )
        
        all_results = vector_results + procedure_results
        all_results = mmr_rerank(all_results, top_k=top_k)
        
        chunks.extend([self._result_to_chunk(r) for r in all_results])
        return chunks[:top_k + 2]

    def _pattern_retrieval(self, query: str, intent: QueryIntent,
                            top_k: int) -> tuple[list[ContextChunk], dict]:
        """
        Pattern-matching retrieval for recurring issues.
        Uses SIMILAR_TO graph edges for cross-equipment learning.
        """
        graph_context = {}
        chunks = []

        # Search for failure patterns in graph
        # Extract failure-related terms from query
        failure_terms = ["failure", "vibration", "leak", "corrosion", "bearing",
                        "seal", "crack", "overheating"]
        
        for term in failure_terms:
            if term in query.lower():
                patterns = self.graph.get_failure_patterns(term)
                if patterns:
                    graph_context[term] = patterns
                    summary = self._format_pattern_summary(term, patterns)
                    chunks.append(ContextChunk(
                        content=summary,
                        source_label=f"[SOURCE: Knowledge Graph | Pattern Analysis | {term}]",
                        doc_id="graph",
                        doc_title="Failure Pattern Analysis",
                        doc_type="pattern_analysis",
                        relevance_score=0.95,
                        from_graph=True,
                    ))

        # Vector search for incident reports
        vector_results = self.vector.search(query, top_k=top_k)
        vector_results = mmr_rerank(vector_results, top_k=top_k)
        chunks.extend([self._result_to_chunk(r) for r in vector_results])

        return chunks[:top_k + 2], graph_context

    def _semantic_retrieval(self, query: str, top_k: int) -> list[ContextChunk]:
        """Pure vector search for semantic queries."""
        results = self.vector.search(query, top_k=top_k)
        results = mmr_rerank(results, top_k=top_k)
        results = category_diversify(results)
        return [self._result_to_chunk(r) for r in results]

    # ── Formatting Helpers ─────────────────────────────────────────────

    def _result_to_chunk(self, result: dict) -> ContextChunk:
        """Convert a vector search result to a ContextChunk."""
        metadata = result.get("metadata", {})
        doc_id = metadata.get("doc_id", "")
        doc_category = metadata.get("doc_category", "document")
        page_num = metadata.get("page_num", 0)
        section = metadata.get("section_path", "")
        
        source_label = f"[SOURCE: {doc_id[:20]} | {doc_category} | Page {page_num}]"
        if section:
            source_label = f"[SOURCE: {doc_id[:20]} | {doc_category} | {section} | Page {page_num}]"
        
        return ContextChunk(
            content=result.get("content", ""),
            source_label=source_label,
            doc_id=doc_id,
            doc_title=doc_id,
            doc_type=doc_category,
            page_num=page_num,
            relevance_score=result.get("relevance_score", 0),
        )

    def _format_graph_summary(self, tag: str, history: dict) -> str:
        """Format graph equipment history as text context."""
        parts = [f"Equipment {tag} Knowledge Graph Summary:"]
        
        events = history.get("events", [])
        if events:
            parts.append(f"\nEvents ({len(events)}):")
            for event in events[:5]:
                parts.append(f"  - [{event.get('event_type', 'event')}] "
                           f"{event.get('description', 'N/A')} "
                           f"(Date: {event.get('date', 'N/A')})")
        
        docs = history.get("documents", [])
        if docs:
            parts.append(f"\nRelated Documents ({len(docs)}):")
            for doc in docs[:5]:
                parts.append(f"  - {doc.get('title', 'N/A')} ({doc.get('doc_type', 'N/A')})")
        
        personnel = history.get("personnel", [])
        if personnel:
            parts.append(f"\nPersonnel ({len(personnel)}):")
            for person in personnel[:3]:
                parts.append(f"  - {person.get('name', 'N/A')}")
        
        failure_modes = history.get("failure_modes", [])
        if failure_modes:
            parts.append(f"\nKnown Failure Modes ({len(failure_modes)}):")
            for fm in failure_modes[:3]:
                parts.append(f"  - {fm.get('description', 'N/A')}")
        
        return "\n".join(parts)

    def _format_compliance_summary(self, reg_code: str, gaps: list) -> str:
        """Format compliance gaps as text context."""
        parts = [f"Compliance Analysis for {reg_code}:"]
        parts.append(f"  Found {len(gaps)} potential compliance gap(s):")
        
        for gap in gaps[:5]:
            equip = gap.get("equipment", {})
            status = gap.get("status", "UNKNOWN")
            parts.append(f"  - Equipment {equip.get('tag', 'N/A')}: Status = {status}")
        
        return "\n".join(parts)

    def _format_pattern_summary(self, failure_term: str, patterns: list) -> str:
        """Format failure pattern analysis as text context."""
        parts = [f"Failure Pattern Analysis for '{failure_term}':"]
        parts.append(f"  Found {len(patterns)} similar incident(s) across equipment:")
        
        for pattern in patterns[:5]:
            equip = pattern.get("equipment", {})
            event = pattern.get("event", {})
            parts.append(f"  - Equipment {equip.get('tag', 'N/A')}: "
                        f"{event.get('description', 'N/A')}")
        
        return "\n".join(parts)

    def format_context_for_llm(self, chunks: list[ContextChunk]) -> str:
        """
        Format all chunks into a single context string for the LLM.
        Each chunk is labeled with its source for citation generation.
        """
        parts = []
        for i, chunk in enumerate(chunks):
            parts.append(f"\n--- Context {i+1} ---")
            parts.append(chunk.source_label)
            parts.append(chunk.content)
        
        return "\n".join(parts)
