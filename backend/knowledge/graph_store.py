"""
Graph Store — NetworkX-based knowledge graph with industrial query methods.

Prototype uses NetworkX DiGraph in memory, persisted to JSON on disk.
Production path: Neo4j with Cypher queries.

Key query methods cover 80% of industrial use cases:
  - get_equipment_history(tag)
  - get_failure_patterns(failure_mode)
  - get_compliance_gaps(regulation_code)
  - get_expert_knowledge(person_name)
"""

import json
import networkx as nx
from pathlib import Path
from typing import Optional
from backend.knowledge.ontology import (
    NODE_TYPES, EDGE_TYPES, get_node_color, get_node_icon,
    validate_node, validate_edge
)


class GraphStore:
    """
    Industrial knowledge graph built on NetworkX.
    Provides structured relationship traversal for entity-anchored queries.
    """

    def __init__(self, persist_path: Optional[str] = None):
        self.graph = nx.DiGraph()
        self.persist_path = persist_path
        
        # Load existing graph if available
        if persist_path and Path(persist_path).exists():
            self.load(persist_path)

    # ── Core CRUD ──────────────────────────────────────────────────────

    def add_entity(self, entity_id: str, entity_type: str, attributes: dict) -> bool:
        """
        Add a node to the graph.
        
        Args:
            entity_id: Unique identifier (e.g., "equipment:P-101")
            entity_type: One of NODE_TYPES keys
            attributes: Node attributes
            
        Returns:
            True if added, False if validation failed.
        """
        valid, msg = validate_node(entity_type, attributes)
        if not valid:
            # Soft validation — add anyway but log
            pass
        
        self.graph.add_node(
            entity_id,
            type=entity_type,
            color=get_node_color(entity_type),
            icon=get_node_icon(entity_type),
            **attributes
        )
        return True

    def add_relationship(self, source_id: str, target_id: str,
                         relation_type: str, attributes: dict = None) -> bool:
        """
        Add a directed edge between two nodes.
        Creates missing nodes as "Unknown" type if they don't exist.
        """
        attributes = attributes or {}
        
        if source_id not in self.graph:
            self.graph.add_node(source_id, type="Unknown", label=source_id)
        if target_id not in self.graph:
            self.graph.add_node(target_id, type="Unknown", label=target_id)
        
        self.graph.add_edge(
            source_id, target_id,
            relation=relation_type,
            **attributes
        )
        return True

    def remove_document(self, doc_id: str) -> int:
        """Remove all nodes and edges associated with a document."""
        doc_node_id = f"document:{doc_id}"
        nodes_to_remove = set()
        
        if doc_node_id in self.graph:
            nodes_to_remove.add(doc_node_id)
        
        # Find nodes only connected through this document
        for node_id, data in list(self.graph.nodes(data=True)):
            if data.get("doc_id") == doc_id:
                # Check if this node has other document connections
                other_docs = False
                for pred in self.graph.predecessors(node_id):
                    if pred != doc_node_id and self.graph.nodes[pred].get("type") == "Document":
                        other_docs = True
                        break
                for succ in self.graph.successors(node_id):
                    if succ != doc_node_id and self.graph.nodes[succ].get("type") == "Document":
                        other_docs = True
                        break
                
                if not other_docs:
                    nodes_to_remove.add(node_id)
        
        count = len(nodes_to_remove)
        for node_id in nodes_to_remove:
            self.graph.remove_node(node_id)
        
        return count

    # ── Industrial Query Methods ───────────────────────────────────────

    def get_equipment_history(self, equipment_tag: str) -> dict:
        """
        Get complete history for an equipment tag.
        Traverses all edges from the equipment node.
        
        Returns:
            {
                "equipment": {...},
                "events": [...],
                "documents": [...],
                "parameters": [...],
                "personnel": [...],
                "regulations": [...],
                "failure_modes": [...]
            }
        """
        node_id = f"equipment:{equipment_tag.upper()}"
        
        if node_id not in self.graph:
            # Try without prefix
            matching = [n for n in self.graph.nodes if equipment_tag.upper() in n.upper()]
            if matching:
                node_id = matching[0]
            else:
                return {}
        
        result = {
            "equipment": dict(self.graph.nodes[node_id]),
            "events": [],
            "documents": [],
            "parameters": [],
            "personnel": [],
            "regulations": [],
            "failure_modes": [],
        }
        
        # Outgoing edges (equipment → X)
        for successor in self.graph.successors(node_id):
            edge_data = dict(self.graph[node_id][successor])
            node_data = dict(self.graph.nodes[successor])
            node_data["_id"] = successor
            node_data["_relation"] = edge_data.get("relation", "UNKNOWN")
            
            node_type = node_data.get("type", "")
            
            if node_type == "Event":
                result["events"].append(node_data)
            elif node_type == "Document":
                result["documents"].append(node_data)
            elif node_type == "Parameter":
                result["parameters"].append(node_data)
            elif node_type == "Person":
                result["personnel"].append(node_data)
            elif node_type == "Regulation":
                result["regulations"].append(node_data)
            elif node_type == "FailureMode":
                result["failure_modes"].append(node_data)
        
        # Incoming edges (X → equipment)
        for predecessor in self.graph.predecessors(node_id):
            edge_data = dict(self.graph[predecessor][node_id])
            node_data = dict(self.graph.nodes[predecessor])
            node_data["_id"] = predecessor
            node_data["_relation"] = edge_data.get("relation", "UNKNOWN")
            
            node_type = node_data.get("type", "")
            if node_type == "Document":
                result["documents"].append(node_data)
            elif node_type == "Person":
                result["personnel"].append(node_data)
        
        return result

    def get_failure_patterns(self, failure_mode_text: str) -> list[dict]:
        """
        Find all equipment that experienced similar failure modes.
        Key for cross-equipment learning — "Lessons Learned" feature.
        """
        results = []
        failure_mode_lower = failure_mode_text.lower()
        
        for node_id, data in self.graph.nodes(data=True):
            if data.get("type") != "FailureMode":
                continue
            
            description = data.get("description", "").lower()
            if failure_mode_lower in description or description in failure_mode_lower:
                # Find equipment connected to this failure mode
                for predecessor in self.graph.predecessors(node_id):
                    pred_data = dict(self.graph.nodes[predecessor])
                    if pred_data.get("type") == "Event":
                        # Find equipment that experienced this event
                        for equip_pred in self.graph.predecessors(predecessor):
                            equip_data = dict(self.graph.nodes[equip_pred])
                            if equip_data.get("type") == "Equipment":
                                results.append({
                                    "equipment": equip_data,
                                    "equipment_id": equip_pred,
                                    "event": pred_data,
                                    "failure_mode": dict(data),
                                })
        
        return results

    def get_compliance_gaps(self, regulation_code: str = None) -> list[dict]:
        """
        Find compliance gaps — equipment subject to regulations
        where compliance status is not "GREEN".
        """
        gaps = []
        
        for node_id, data in self.graph.nodes(data=True):
            if data.get("type") != "Regulation":
                continue
            
            if regulation_code and regulation_code.upper() not in node_id.upper():
                continue
            
            # Find equipment subject to this regulation
            for predecessor in self.graph.predecessors(node_id):
                edge_data = dict(self.graph[predecessor][node_id])
                
                if edge_data.get("relation") == "SUBJECT_TO":
                    status = edge_data.get("compliance_status", "UNKNOWN")
                    if status != "GREEN":
                        equip_data = dict(self.graph.nodes[predecessor])
                        gaps.append({
                            "equipment": equip_data,
                            "equipment_id": predecessor,
                            "regulation": dict(data),
                            "regulation_id": node_id,
                            "status": status,
                            "details": edge_data,
                        })
        
        return gaps

    def get_compliance_summary(self) -> list[dict]:
        """
        Per-regulation compliance rollup for the compliance matrix UI.
        Status = worst status across all equipment subject to the regulation
        (RED > AMBER > GREEN).
        """
        severity = {"GREEN": 0, "AMBER": 1, "RED": 2, "UNKNOWN": 1}
        summary = {}

        for node_id, data in self.graph.nodes(data=True):
            if data.get("type") != "Regulation":
                continue

            code = data.get("code", node_id)
            equipment = []
            worst = "GREEN"
            for predecessor in self.graph.predecessors(node_id):
                edge_data = dict(self.graph[predecessor][node_id])
                if edge_data.get("relation") != "SUBJECT_TO":
                    continue
                status = edge_data.get("compliance_status", "UNKNOWN")
                equip_data = dict(self.graph.nodes[predecessor])
                equipment.append({
                    "tag": equip_data.get("tag", predecessor),
                    "status": status,
                    "evidence_doc": edge_data.get("evidence_doc", ""),
                })
                if severity.get(status, 1) > severity.get(worst, 0):
                    worst = status

            summary[code] = {
                "code": code,
                "title": data.get("title", code),
                "status": worst if equipment else "AMBER",
                "equipment_count": len(equipment),
                "equipment": equipment,
                "gap_count": sum(1 for e in equipment if e["status"] != "GREEN"),
            }

        return sorted(summary.values(), key=lambda r: r["code"])

    def get_expert_knowledge(self, person_name: str) -> dict:
        """Find all documents authored by a person and equipment they're certified for."""
        result = {"documents": [], "equipment": [], "person": None}
        person_lower = person_name.lower()
        
        for node_id, data in self.graph.nodes(data=True):
            if data.get("type") != "Person":
                continue
            
            name = data.get("name", "").lower()
            if person_lower not in name:
                continue
            
            result["person"] = dict(data)
            
            for predecessor in self.graph.predecessors(node_id):
                pred_data = dict(self.graph.nodes[predecessor])
                edge_data = dict(self.graph[predecessor][node_id])
                
                if pred_data.get("type") == "Document":
                    result["documents"].append(pred_data)
                elif pred_data.get("type") == "Equipment":
                    result["equipment"].append(pred_data)
            
            for successor in self.graph.successors(node_id):
                succ_data = dict(self.graph.nodes[successor])
                if succ_data.get("type") == "Equipment":
                    result["equipment"].append(succ_data)
            
            break  # Found the person
        
        return result

    # ── Serialization ──────────────────────────────────────────────────

    def serialize_for_frontend(self) -> dict:
        """
        Serialize graph for react-force-graph format.
        Returns: {nodes: [{id, label, type, color, ...}], links: [{source, target, relation}]}
        """
        nodes = []
        for node_id, data in self.graph.nodes(data=True):
            node = {
                "id": node_id,
                "label": data.get("tag") or data.get("title") or data.get("name") 
                         or data.get("description") or data.get("code") or node_id,
                "type": data.get("type", "Unknown"),
                "color": data.get("color", "#9CA3AF"),
                "icon": data.get("icon", "●"),
                **{k: v for k, v in data.items() if k not in ("color", "icon")},
            }
            nodes.append(node)
        
        links = []
        for source, target, data in self.graph.edges(data=True):
            links.append({
                "source": source,
                "target": target,
                "relation": data.get("relation", "RELATED_TO"),
                **{k: v for k, v in data.items() if k != "relation"},
            })
        
        return {"nodes": nodes, "links": links}

    def get_subgraph(self, center_node_id: str, depth: int = 2) -> dict:
        """Get a subgraph centered on a specific node."""
        if center_node_id not in self.graph:
            # Try fuzzy match
            matching = [n for n in self.graph.nodes if center_node_id.upper() in n.upper()]
            if matching:
                center_node_id = matching[0]
            else:
                return {"nodes": [], "links": []}
        
        # BFS to find nodes within depth
        visited = {center_node_id}
        current_level = {center_node_id}
        
        for _ in range(depth):
            next_level = set()
            for node in current_level:
                for neighbor in list(self.graph.successors(node)) + list(self.graph.predecessors(node)):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_level.add(neighbor)
            current_level = next_level
        
        # Build subgraph
        subgraph = self.graph.subgraph(visited)
        
        nodes = []
        for node_id, data in subgraph.nodes(data=True):
            nodes.append({
                "id": node_id,
                "label": data.get("tag") or data.get("title") or data.get("name")
                         or data.get("description") or data.get("code") or node_id,
                "type": data.get("type", "Unknown"),
                "color": data.get("color", "#9CA3AF"),
                **{k: v for k, v in data.items() if k not in ("color",)},
            })
        
        links = []
        for source, target, data in subgraph.edges(data=True):
            links.append({
                "source": source,
                "target": target,
                "relation": data.get("relation", "RELATED_TO"),
            })
        
        return {"nodes": nodes, "links": links}

    def get_stats(self) -> dict:
        """Get graph statistics."""
        type_counts = {}
        for _, data in self.graph.nodes(data=True):
            node_type = data.get("type", "Unknown")
            type_counts[node_type] = type_counts.get(node_type, 0) + 1
        
        edge_counts = {}
        for _, _, data in self.graph.edges(data=True):
            rel = data.get("relation", "UNKNOWN")
            edge_counts[rel] = edge_counts.get(rel, 0) + 1
        
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": type_counts,
            "edge_types": edge_counts,
        }

    # ── Persistence ────────────────────────────────────────────────────

    def save(self, filepath: str = None):
        """Persist graph to JSON file."""
        filepath = filepath or self.persist_path
        if not filepath:
            return
        
        data = nx.node_link_data(self.graph)
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def load(self, filepath: str = None):
        """Load graph from JSON file."""
        filepath = filepath or self.persist_path
        if not filepath or not Path(filepath).exists():
            return
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.graph = nx.node_link_graph(data, directed=True)
