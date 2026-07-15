"""
Industrial Ontology — Schema definitions for the knowledge graph.

Defines node types, edge types, and their validation rules.
This is the blueprint that everything else is built around.
"""

from dataclasses import dataclass, field
from typing import Optional


# ── Node Type Definitions ──────────────────────────────────────────────

NODE_TYPES = {
    "Equipment": {
        "required_attrs": ["tag", "equipment_type"],
        "optional_attrs": ["location", "manufacturer", "model", "install_date", "status"],
        "color": "#3B82F6",  # blue
        "icon": "⚙️",
    },
    "Document": {
        "required_attrs": ["doc_id", "title", "doc_type"],
        "optional_attrs": ["date", "author", "source_path", "page_count"],
        "color": "#10B981",  # green
        "icon": "📄",
    },
    "Person": {
        "required_attrs": ["name"],
        "optional_attrs": ["role", "department", "certifications", "employee_id"],
        "color": "#8B5CF6",  # purple
        "icon": "👤",
    },
    "Event": {
        "required_attrs": ["event_type", "date"],
        "optional_attrs": ["description", "outcome", "severity", "duration"],
        "color": "#F59E0B",  # amber
        "icon": "📅",
    },
    "Parameter": {
        "required_attrs": ["name", "value"],
        "optional_attrs": ["unit", "min_value", "max_value", "normal_range"],
        "color": "#06B6D4",  # cyan
        "icon": "📊",
    },
    "Regulation": {
        "required_attrs": ["code", "title"],
        "optional_attrs": ["issuing_body", "version", "applicable_to", "sections"],
        "color": "#EF4444",  # red
        "icon": "📋",
    },
    "FailureMode": {
        "required_attrs": ["description"],
        "optional_attrs": ["cause", "mechanism", "severity", "frequency", "detection_method"],
        "color": "#DC2626",  # dark red
        "icon": "⚠️",
    },
}


# ── Edge Type Definitions ──────────────────────────────────────────────

EDGE_TYPES = {
    "DOCUMENTED_IN": {
        "from_types": ["Equipment", "Event", "Person", "FailureMode"],
        "to_types": ["Document"],
        "description": "Entity is documented in this document",
        "attrs": ["page", "section"],
    },
    "EXPERIENCED": {
        "from_types": ["Equipment"],
        "to_types": ["Event"],
        "description": "Equipment experienced this event",
        "attrs": ["date", "duration"],
    },
    "CAUSED_BY": {
        "from_types": ["Event"],
        "to_types": ["FailureMode"],
        "description": "Event was caused by this failure mode",
        "attrs": ["confidence", "evidence"],
    },
    "SIMILAR_TO": {
        "from_types": ["FailureMode", "Event"],
        "to_types": ["FailureMode", "Event"],
        "description": "This failure mode is similar to another (cross-equipment learning)",
        "attrs": ["similarity_score", "common_factors"],
    },
    "MAINTAINED_BY": {
        "from_types": ["Equipment"],
        "to_types": ["Person"],
        "description": "Equipment is maintained by this person",
        "attrs": ["role", "since"],
    },
    "SUBJECT_TO": {
        "from_types": ["Equipment"],
        "to_types": ["Regulation"],
        "description": "Equipment is subject to this regulation",
        "attrs": ["sections", "compliance_status"],
    },
    "AUTHORED_BY": {
        "from_types": ["Document"],
        "to_types": ["Person"],
        "description": "Document was authored by this person",
        "attrs": ["date"],
    },
    "HAS_PARAMETER": {
        "from_types": ["Equipment"],
        "to_types": ["Parameter"],
        "description": "Equipment has this measured parameter",
        "attrs": ["measured_date", "within_spec"],
    },
    "CERTIFIED_FOR": {
        "from_types": ["Person"],
        "to_types": ["Equipment"],
        "description": "Person is certified to work on this equipment",
        "attrs": ["certification_type", "valid_until"],
    },
    "REFERENCES": {
        "from_types": ["Document"],
        "to_types": ["Document", "Regulation"],
        "description": "Document references another document or regulation",
        "attrs": ["context"],
    },
}


def validate_node(node_type: str, attributes: dict) -> tuple[bool, str]:
    """Validate that a node has required attributes for its type."""
    if node_type not in NODE_TYPES:
        return False, f"Unknown node type: {node_type}"
    
    schema = NODE_TYPES[node_type]
    for attr in schema["required_attrs"]:
        if attr not in attributes:
            return False, f"Missing required attribute '{attr}' for {node_type}"
    
    return True, "OK"


def validate_edge(edge_type: str, from_type: str, to_type: str) -> tuple[bool, str]:
    """Validate that an edge connects valid node types."""
    if edge_type not in EDGE_TYPES:
        return False, f"Unknown edge type: {edge_type}"
    
    schema = EDGE_TYPES[edge_type]
    if from_type not in schema["from_types"]:
        return False, f"Edge {edge_type} cannot start from {from_type}"
    if to_type not in schema["to_types"]:
        return False, f"Edge {edge_type} cannot end at {to_type}"
    
    return True, "OK"


def get_node_color(node_type: str) -> str:
    """Get the display color for a node type."""
    return NODE_TYPES.get(node_type, {}).get("color", "#9CA3AF")


def get_node_icon(node_type: str) -> str:
    """Get the display icon for a node type."""
    return NODE_TYPES.get(node_type, {}).get("icon", "●")
