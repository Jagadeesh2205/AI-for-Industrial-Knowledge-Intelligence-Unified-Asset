"""
Industrial NER — Entity extraction using spaCy + regex patterns.

Dual-layer approach:
  Layer 1 - spaCy + Regex: Fast extraction of equipment tags, dates, personnel
  Layer 2 - LLM (optional): Complex contextual entities when spaCy confidence is low

Entity Types:
  EQUIPMENT_TAG, PROCESS_PARAM, PERSONNEL, DATE_EVENT, 
  REGULATION, LOCATION, MATERIAL, FAILURE_MODE
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Entity:
    """Represents an extracted entity."""
    text: str
    entity_type: str
    start: int = 0
    end: int = 0
    confidence: float = 1.0
    attributes: dict = field(default_factory=dict)
    source: str = "regex"  # regex | spacy | llm


# ── Regex Patterns for Industrial Entities ──────────────────────────────

PATTERNS = {
    "EQUIPMENT_TAG": [
        r'\b([A-Z]{1,4}-\d{3,4}[A-Z]?)\b',           # P-101, HX-301A, V-201
        r'\b(TAG[:\s]+[A-Z0-9-]+)\b',                   # TAG: P-101
    ],
    "PROCESS_PARAM": [
        r'\b((?:pressure|temperature|flow\s*rate|speed|rpm|vibration|level)\s*[=:]\s*[\d.]+\s*(?:bar|psi|°[CF]|m3/hr|rpm|mm/s|%)?)\b',
        r'\b([\d.]+\s*(?:bar|psi|°C|°F|m3/hr|m³/hr|rpm|mm/s|kg/cm2|MPa))\b',
    ],
    "REGULATION": [
        r'\b(OISD[-\s]*\d{3})\b',                       # OISD-116
        r'\b(IS[-\s]*\d{4,5})\b',                        # IS-2148
        r'\b(PESO\s+[A-Za-z\s]+)\b',                     # PESO regulation
        r'\b(Factory\s+Act\s+\d{4})\b',                  # Factory Act 1948
        r'\b(ASME\s+[A-Z]+\s*\d*)\b',                    # ASME standards
        r'\b(API\s+\d{3,4})\b',                           # API standards
    ],
    "FAILURE_MODE": [
        r'\b(seal\s+failure|bearing\s+(?:failure|wear|damage)|corrosion|erosion|'
        r'cavitation|vibration|leakage|crack(?:ing)?|fatigue|overheating|'
        r'misalignment|imbalance|dry\s+running|blockage)\b',
    ],
    "MATERIAL": [
        r'\b((?:SS|CS|A[S]?)\s*\d{3}[A-Z]?)\b',        # SS 316, CS 106
        r'\b((?:carbon\s+steel|stainless\s+steel|alloy\s+steel|cast\s+iron))\b',
    ],
    "LOCATION": [
        r'\b(Unit[-\s]*\d+)\b',                          # Unit-3
        r'\b(Area[-\s]*\d+)\b',                           # Area-5
        r'\b(Plant[-\s]*\d+)\b',                          # Plant-2
        r'\b(Block[-\s]*[A-Z0-9]+)\b',                    # Block-A
    ],
    "DATE_EVENT": [
        r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b',         # 15/03/2024
        r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b',            # 2024-03-15
        r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b',
    ],
}


class IndustrialNER:
    """
    Industrial Named Entity Recognition.
    Extracts equipment tags, parameters, regulations, failure modes, etc.
    """

    def __init__(self):
        self._spacy_nlp = None

    def _get_spacy(self):
        """Lazy-load spaCy model."""
        if self._spacy_nlp is None:
            try:
                import spacy
                try:
                    self._spacy_nlp = spacy.load("en_core_web_sm")
                except OSError:
                    # Model not installed — use blank model
                    self._spacy_nlp = spacy.blank("en")
            except ImportError:
                self._spacy_nlp = None
        return self._spacy_nlp

    def extract_entities(self, text: str, use_llm: bool = False) -> list[Entity]:
        """
        Extract all entities from text.
        
        Args:
            text: Input text to extract entities from
            use_llm: Whether to use LLM for complex entity extraction
            
        Returns:
            List of Entity objects, deduplicated.
        """
        entities = []
        
        # Layer 1: Regex-based extraction (fast, high precision)
        regex_entities = self._regex_extract(text)
        entities.extend(regex_entities)
        
        # Layer 1b: spaCy NER (for PERSON, ORG, DATE)
        spacy_entities = self._spacy_extract(text)
        entities.extend(spacy_entities)
        
        # Deduplicate
        entities = self._deduplicate(entities)
        
        return entities

    def _regex_extract(self, text: str) -> list[Entity]:
        """Extract entities using regex patterns."""
        entities = []
        
        for entity_type, patterns in PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entity_text = match.group(1) if match.lastindex else match.group(0)
                    entities.append(Entity(
                        text=entity_text.strip(),
                        entity_type=entity_type,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.9,
                        source="regex",
                    ))
        
        return entities

    def _spacy_extract(self, text: str) -> list[Entity]:
        """Extract entities using spaCy NER."""
        nlp = self._get_spacy()
        if nlp is None:
            return []
        
        # Limit text length for spaCy (performance)
        doc = nlp(text[:10000])
        
        # Map spaCy labels to our entity types
        label_map = {
            "PERSON": "PERSONNEL",
            "ORG": "PERSONNEL",  # Organizations involved
            "DATE": "DATE_EVENT",
            "GPE": "LOCATION",
            "LOC": "LOCATION",
        }
        
        entities = []
        for ent in doc.ents:
            mapped_type = label_map.get(ent.label_)
            if mapped_type:
                entities.append(Entity(
                    text=ent.text,
                    entity_type=mapped_type,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=0.75,
                    source="spacy",
                ))
        
        return entities

    def _deduplicate(self, entities: list[Entity]) -> list[Entity]:
        """
        Deduplicate entities. Keep higher confidence version when duplicates exist.
        """
        seen = {}
        for entity in entities:
            key = (entity.text.upper(), entity.entity_type)
            if key not in seen or entity.confidence > seen[key].confidence:
                seen[key] = entity
        
        return list(seen.values())

    def extract_equipment_tags(self, text: str) -> list[str]:
        """Quick extraction of just equipment tags."""
        tags = set()
        for pattern in PATTERNS["EQUIPMENT_TAG"]:
            for match in re.finditer(pattern, text):
                tag = match.group(1) if match.lastindex else match.group(0)
                tags.add(tag.strip().upper())
        return sorted(tags)

    def extract_regulations(self, text: str) -> list[str]:
        """Quick extraction of regulation references."""
        regs = set()
        for pattern in PATTERNS["REGULATION"]:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                reg = match.group(1) if match.lastindex else match.group(0)
                regs.add(reg.strip().upper())
        return sorted(regs)
