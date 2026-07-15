"""
Document Classifier — Routes incoming documents to the right parser.

Classifies by:
1. File extension (pdf, xlsx, docx, txt, csv, jpg/png)
2. Content analysis (text extraction check for scanned PDFs)
3. Category detection via keyword matching
"""

import os
import re
from pathlib import Path
from typing import Optional


# Category keywords — matched against first ~2000 chars of content
CATEGORY_KEYWORDS = {
    "maintenance_record": [
        "work order", "wo#", "wo #", "maintenance", "repair", "corrective",
        "preventive maintenance", "pm schedule", "bearing replacement",
        "lubrication", "overhaul", "service report"
    ],
    "safety_procedure": [
        "sop", "loto", "lockout", "tagout", "ptw", "permit to work",
        "safety", "procedure", "precaution", "ppe", "hazard"
    ],
    "inspection_report": [
        "inspection", "ndt", "thickness measurement", "corrosion",
        "finding", "ultrasonic", "radiography", "visual inspection",
        "fitness for service"
    ],
    "piid_drawing": [
        "p&id", "pfd", "process flow", "instrument diagram",
        "drawing", "dwg", "line diagram", "piping"
    ],
    "oem_manual": [
        "oem", "manufacturer", "installation manual", "commissioning",
        "model", "operating manual", "technical manual", "spare parts",
        "grundfos", "siemens", "abb"
    ],
    "regulatory": [
        "oisd", "peso", "factory act", "compliance", "regulation",
        "standard", "is-", "statutory", "legal requirement",
        "cpcb", "environmental"
    ],
    "incident_report": [
        "incident", "near miss", "accident", "rca", "root cause",
        "investigation", "failure analysis", "trip", "emergency",
        "safety incident"
    ],
    "operating_procedure": [
        "startup", "shutdown", "normal operation", "step",
        "operator", "operating procedure", "op procedure",
        "process description"
    ],
}

# File extension to file type mapping
EXTENSION_MAP = {
    ".pdf": "pdf",
    ".txt": "text",
    ".docx": "docx",
    ".doc": "docx",
    ".xlsx": "excel",
    ".xls": "excel",
    ".csv": "csv",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".tiff": "image",
    ".tif": "image",
}


class DocumentClassifier:
    """Classifies documents by type and category for routing to the correct parser."""

    def classify(self, filepath: str, content_sample: Optional[str] = None) -> dict:
        """
        Classify a document.
        
        Args:
            filepath: Path to the file
            content_sample: Optional pre-extracted text sample (first ~2000 chars)
            
        Returns:
            {
                "file_type": str,      # pdf, text, docx, excel, csv, image
                "doc_category": str,   # maintenance_record, safety_procedure, etc.
                "needs_ocr": bool,     # True if scanned/image-based
                "confidence": float    # 0.0-1.0
            }
        """
        ext = Path(filepath).suffix.lower()
        filename = Path(filepath).name.lower()
        
        file_type = EXTENSION_MAP.get(ext, "unknown")
        needs_ocr = file_type == "image"
        
        # For PDFs, check if text-extractable
        if file_type == "pdf" and content_sample is not None:
            if len(content_sample.strip()) < 100:
                needs_ocr = True
        
        # Determine category from filename and content
        doc_category, confidence = self._detect_category(filename, content_sample or "")
        
        return {
            "file_type": file_type,
            "doc_category": doc_category,
            "needs_ocr": needs_ocr,
            "confidence": confidence,
        }

    def _detect_category(self, filename: str, content: str) -> tuple[str, float]:
        """
        Detect document category by keyword matching.
        Returns (category, confidence).
        """
        combined_text = f"{filename} {content[:2000]}".lower()
        
        scores = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in combined_text)
            if score > 0:
                scores[category] = score
        
        if not scores:
            return "general", 0.3
        
        best_category = max(scores, key=scores.get)
        max_possible = len(CATEGORY_KEYWORDS[best_category])
        confidence = min(scores[best_category] / max(max_possible * 0.3, 1), 1.0)
        
        return best_category, round(confidence, 2)

    def get_parser_type(self, classification: dict) -> str:
        """Return which parser to use based on classification."""
        file_type = classification["file_type"]
        
        if file_type in ("pdf", "text", "docx"):
            if classification["needs_ocr"]:
                return "ocr"
            return "text"
        elif file_type in ("excel", "csv"):
            return "excel"
        elif file_type == "image":
            return "ocr"
        else:
            return "text"  # fallback
