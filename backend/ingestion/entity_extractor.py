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
        # Negative lookbehind: don't match sub-parts of longer codes like
        # PROC-EM-008, OISD-STD-105, SOP-CWT-001
        r'(?<![A-Za-z0-9-])([A-Z]{1,4}-\d{2,4}[A-Z]?)\b',  # P-101, HX-301A, V-201
    ],
    "PROCESS_PARAM": [
        r'\b((?:discharge\s+|suction\s+|inlet\s+|outlet\s+|return\s+water\s+)?'
        r'(?:pressure|temperature|flow\s*rate|speed|rpm|vibration|level|current\s+draw)'
        r'\s*[=:]\s*[\d.]+\s*(?:bar|psi|°[CF]|m3/hr|m³/hr|rpm|mm/s|A|%)?)\b',
        r'\b([\d.]+\s*(?:bar|psi|°C|°F|m3/hr|m³/hr|rpm|mm/s|kg/cm2|MPa))\b',
    ],
    "REGULATION": [
        r'\b(OISD[-\s]*(?:STD[-\s]*|GDN[-\s]*)?\d{3})\b',  # OISD-116, OISD-STD-105
        r'\b(IS[-\s]*\d{4,5})\b',                        # IS-2148
        r'\b(PESO\s+[A-Za-z\s]+)\b',                     # PESO regulation
        r'\b(Factory\s+Act\s+\d{4})\b',                  # Factory Act 1948
        r'\b(ASME\s+[A-Z]+\s*\d*)\b',                    # ASME standards
        r'\b(API[-\s]+\d{3,4})\b',                        # API 570, API-510
        r'\b(ANSI\s+[A-Z]?\d+(?:\.\d+)?(?:-\d{4})?)\b',  # ANSI Z358.1-2014
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
    # Names appearing after explicit role labels — high precision.
    # Label match is case-insensitive (PREPARED_BY:), name part is not.
    "PERSONNEL": [
        r'(?i:(?:Prepared|Reviewed|Approved|Verified|Investigated|Reported|'
        r'Inspected|Witnessed|Authored)[_\s]?By)[:\s]+((?:Dr\.|Mr\.|Ms\.|Mrs\.)?\s*[A-Z][A-Za-z.\- ]{2,40})',
        r'(?i:Operator|Technician|Engineer|Supervisor|Inspector|Auditor|'
        r'Lead\s+Auditor|Responsible\s+Person|Assigned\s+To|Lead)[:\s]+'
        r'((?:Dr\.|Mr\.|Ms\.|Mrs\.)?\s*[A-Z][A-Za-z.\- ]{2,40})',
    ],
}

# ── Validation: keep noisy regex/NER matches out of the knowledge graph ──

# Real plant equipment prefixes (P-101 pump, HX-301 exchanger, CT-101
# cooling tower...). Report numbers (IR-2022), procedures (SOP-045,
# EM-008), standards (OISD-116, API-510) and month codes (DEC-2023)
# must NOT become Equipment nodes.
ALLOWED_EQUIPMENT_PREFIXES = {
    "P", "V", "HX", "E", "C", "CT", "CWP", "T", "TK", "R", "D", "F",
    "B", "G", "M", "K", "AG", "DV", "MOV", "PSV", "PRV", "ESV",
    "FV", "PV", "TV", "LV", "CV", "EM",  # EM = electrical motor
}
# ...except these prefixes when the tag is really a doc/procedure code
_TAG_RE = re.compile(r'^([A-Z]{1,4})-(\d{2,4})([A-Z]?)$')

# Role/department words — a "name" containing one is not a person
_NON_PERSON_WORDS = {
    "manager", "engineer", "engineering", "supervisor", "technician",
    "operator", "operations", "inspector", "inspection", "auditor",
    "team", "department", "dept", "records", "record", "training",
    "maintenance", "reliability", "chief", "plant", "safety", "quality",
    "hse", "dcs", "management", "committee", "section", "unit", "shift",
    "board", "authority", "services", "systems", "limited", "ltd",
    "pvt", "inc", "corp", "corporation", "company", "industries",
    "internal", "external", "responsible", "person", "log", "logs",
    "rounds", "report", "review", "audit", "daily", "weekly", "monthly",
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct",
    "nov", "dec",
}

_NAME_TOKEN = re.compile(r"^(?:[A-Z][a-z]+|[A-Z]\.|Dr\.|Mr\.|Ms\.|Mrs\.)$")


def is_valid_equipment_tag(tag: str) -> bool:
    """True only for tags that look like real plant equipment."""
    m = _TAG_RE.match(tag.strip().upper())
    if not m:
        return False
    prefix, num = m.group(1), int(m.group(2))
    if prefix not in ALLOWED_EQUIPMENT_PREFIXES:
        return False
    if 1900 <= num <= 2099:  # year-like → report/date code, not equipment
        return False
    return True


def is_valid_person_name(name: str) -> bool:
    """True for plausible human names: 'Rajesh Kumar', 'S. Jenkins',
    'Dr. Priya Sharma'. Rejects orgs, roles, acronyms, doc titles."""
    name = name.strip()
    if not (3 <= len(name) <= 40):
        return False
    if any(ch.isdigit() for ch in name):
        return False
    tokens = name.replace("-", " ").split()
    if not (2 <= len(tokens) <= 4):
        return False
    if any(t.lower().rstrip(".,") in _NON_PERSON_WORDS for t in tokens):
        return False
    return all(_NAME_TOKEN.match(t) for t in tokens)


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
                # Equipment tags and personnel are case-sensitive patterns;
                # matching them case-insensitively creates junk (e.g. "in-2024")
                flags = 0 if entity_type in ("EQUIPMENT_TAG", "PERSONNEL") else re.IGNORECASE
                for match in re.finditer(pattern, text, flags):
                    entity_text = match.group(1) if match.lastindex else match.group(0)
                    entity_text = entity_text.strip()

                    # Validation gates — precision over recall for graph quality
                    if entity_type == "EQUIPMENT_TAG" and not is_valid_equipment_tag(entity_text):
                        continue
                    if entity_type == "PERSONNEL" and not is_valid_person_name(entity_text):
                        continue

                    entities.append(Entity(
                        text=entity_text,
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

        # Map spaCy labels to our entity types.
        # NOTE: ORG is intentionally NOT mapped — companies/standards bodies
        # were flooding the graph with hundreds of fake Person nodes.
        label_map = {
            "PERSON": "PERSONNEL",
            "DATE": "DATE_EVENT",
            "GPE": "LOCATION",
            "LOC": "LOCATION",
        }

        entities = []
        for ent in doc.ents:
            mapped_type = label_map.get(ent.label_)
            if not mapped_type:
                continue
            # spaCy PERSON is noisy on industrial text — validate names
            if mapped_type == "PERSONNEL" and not is_valid_person_name(ent.text):
                continue
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
                tag = tag.strip().upper()
                if is_valid_equipment_tag(tag):
                    tags.add(tag)
        return sorted(tags)

    def extract_regulations(self, text: str) -> list[str]:
        """Quick extraction of regulation references."""
        regs = set()
        for pattern in PATTERNS["REGULATION"]:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                reg = match.group(1) if match.lastindex else match.group(0)
                regs.add(reg.strip().upper())
        return sorted(regs)
