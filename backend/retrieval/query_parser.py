"""
Query Parser — Intent detection for incoming queries.

Classifies queries into 4 types:
  ENTITY_ANCHORED — Contains equipment tags, person names, specific dates
  SEMANTIC — General conceptual questions
  COMPLIANCE — Regulatory compliance questions
  PATTERN_MATCHING — Historical pattern / recurring issue queries
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QueryIntent:
    """Parsed query intent with extracted entities."""
    type: str               # ENTITY_ANCHORED | SEMANTIC | COMPLIANCE | PATTERN_MATCHING
    entities: list = field(default_factory=list)       # Equipment tags found
    regulations: list = field(default_factory=list)    # Regulation codes found
    keywords: list = field(default_factory=list)       # Significant keywords
    original_query: str = ""


# Keyword lists for intent detection
COMPLIANCE_KEYWORDS = [
    "oisd", "peso", "factory act", "compliant", "compliance", "audit",
    "regulation", "regulatory", "statutory", "inspection requirement",
    "is-", "asme", "api standard", "noncompliant", "gap analysis",
    "certification", "license"
]

PATTERN_KEYWORDS = [
    "before", "similar", "pattern", "recurring", "history", "again",
    "previous", "past", "repeat", "trend", "frequency", "how often",
    "last time", "ever happened", "common cause"
]

MAINTENANCE_KEYWORDS = [
    "maintenance", "repair", "replace", "overhaul", "lubrication",
    "bearing", "seal", "vibration", "temperature", "pressure",
    "failure", "breakdown", "troubleshoot", "diagnose", "rca",
    "root cause", "corrective", "preventive"
]

EQUIPMENT_TAG_PATTERN = r'\b[A-Z]{1,4}-\d{3,4}[A-Z]?\b'


def parse_query_intent(query: str) -> QueryIntent:
    """
    Parse a query to determine its intent and extract entities.
    
    Priority order:
    1. Entity-anchored (if equipment tags found)
    2. Compliance (if regulation keywords found)
    3. Pattern matching (if pattern keywords found)
    4. Semantic (default)
    """
    query_lower = query.lower()
    
    # Extract equipment tags
    equipment_tags = re.findall(EQUIPMENT_TAG_PATTERN, query)
    
    # Extract regulation codes
    regulation_patterns = [
        r'\b(OISD[-\s]*\d{3})\b',
        r'\b(IS[-\s]*\d{4,5})\b',
        r'\b(API[-\s]*\d{3,4})\b',
        r'\b(ASME\s+[A-Z]+\s*\d*)\b',
    ]
    regulations = []
    for pattern in regulation_patterns:
        regulations.extend(re.findall(pattern, query, re.IGNORECASE))
    
    # Check for compliance intent
    has_compliance = any(kw in query_lower for kw in COMPLIANCE_KEYWORDS) or len(regulations) > 0
    
    # Check for pattern matching intent
    has_pattern = any(kw in query_lower for kw in PATTERN_KEYWORDS)
    
    # Check for maintenance intent
    has_maintenance = any(kw in query_lower for kw in MAINTENANCE_KEYWORDS)
    
    # Determine primary intent
    if equipment_tags:
        intent_type = "ENTITY_ANCHORED"
    elif has_compliance:
        intent_type = "COMPLIANCE"
    elif has_pattern:
        intent_type = "PATTERN_MATCHING"
    else:
        intent_type = "SEMANTIC"
    
    # Collect keywords
    keywords = []
    if has_maintenance:
        keywords.append("maintenance")
    if has_pattern:
        keywords.append("pattern")
    if has_compliance:
        keywords.append("compliance")
    
    return QueryIntent(
        type=intent_type,
        entities=equipment_tags,
        regulations=regulations,
        keywords=keywords,
        original_query=query,
    )


def suggest_agent(intent: QueryIntent) -> str:
    """Suggest the best agent for a query intent."""
    if intent.type == "COMPLIANCE":
        return "compliance"
    
    if "maintenance" in intent.keywords or intent.type == "PATTERN_MATCHING":
        return "maintenance"
    
    return "copilot"
