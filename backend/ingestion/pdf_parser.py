"""
PDF Parser — Extracts text, tables, and metadata from PDF documents.

Uses PyMuPDF (fitz) for fast text extraction with page-level metadata.
Tables are detected and serialized as markdown for LLM readability.
Section headers are extracted for hierarchical chunking.
"""

import fitz  # PyMuPDF
import re
from pathlib import Path
from typing import Optional


class PDFParser:
    """Extract structured content from PDF files."""

    # Common section header patterns in industrial documents
    SECTION_PATTERNS = [
        r'^(\d+\.[\d.]*)\s+(.+)$',           # "1.2.3 Section Title"
        r'^(Section\s+\d+)\s*[:\-]\s*(.+)$',  # "Section 3: Title"
        r'^(PART\s+[IVX\d]+)\s*[:\-]\s*(.+)$',# "PART III: Title"
        r'^([A-Z][A-Z\s]{3,})$',               # "ALL CAPS HEADERS"
    ]

    def parse(self, filepath: str) -> dict:
        """
        Parse a PDF file and extract structured content.
        
        Returns:
            {
                "pages": [
                    {
                        "page_num": int,
                        "text": str,
                        "tables": [str],       # Markdown-formatted tables
                        "section_header": str | None,
                        "has_images": bool,
                    }
                ],
                "metadata": {
                    "title": str,
                    "author": str,
                    "page_count": int,
                    "file_size": int,
                },
                "full_text": str,
                "sections": [{"number": str, "title": str, "page": int}],
            }
        """
        doc = fitz.open(filepath)
        
        pages = []
        sections = []
        full_text_parts = []
        current_section = None

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            
            # Detect section headers in the text
            section_header = self._detect_section_header(text)
            if section_header:
                current_section = section_header
                sections.append({
                    "number": section_header.get("number", ""),
                    "title": section_header.get("title", ""),
                    "page": page_num + 1,
                })

            # Extract tables
            tables = self._extract_tables(page)

            # Check for images
            has_images = len(page.get_images()) > 0

            pages.append({
                "page_num": page_num + 1,
                "text": text.strip(),
                "tables": tables,
                "section_header": current_section,
                "has_images": has_images,
            })
            
            full_text_parts.append(text)

        # Get document metadata
        meta = doc.metadata or {}
        
        result = {
            "pages": pages,
            "metadata": {
                "title": meta.get("title", Path(filepath).stem),
                "author": meta.get("author", "Unknown"),
                "page_count": len(doc),
                "file_size": Path(filepath).stat().st_size,
                "creation_date": meta.get("creationDate", ""),
            },
            "full_text": "\n\n".join(full_text_parts),
            "sections": sections,
        }

        doc.close()
        return result

    def _detect_section_header(self, text: str) -> Optional[dict]:
        """Detect section headers in page text."""
        lines = text.strip().split("\n")
        
        for line in lines[:5]:  # Check first 5 lines of page
            line = line.strip()
            if not line:
                continue
                
            for pattern in self.SECTION_PATTERNS:
                match = re.match(pattern, line)
                if match:
                    groups = match.groups()
                    if len(groups) >= 2:
                        return {"number": groups[0], "title": groups[1]}
                    else:
                        return {"number": "", "title": groups[0]}
        
        return None

    def _extract_tables(self, page) -> list[str]:
        """
        Extract tables from a PDF page and convert to markdown format.
        Uses PyMuPDF's built-in table detection.
        """
        tables = []
        
        try:
            # PyMuPDF 1.23+ has built-in table extraction
            page_tables = page.find_tables()
            
            for table in page_tables:
                md_table = self._table_to_markdown(table.extract())
                if md_table:
                    tables.append(md_table)
        except Exception:
            # Fallback: no table extraction if not supported
            pass
        
        return tables

    def _table_to_markdown(self, table_data: list[list]) -> Optional[str]:
        """Convert a 2D table array to markdown format."""
        if not table_data or len(table_data) < 2:
            return None
        
        # Clean cells
        cleaned = []
        for row in table_data:
            cleaned_row = [str(cell).strip().replace("\n", " ") if cell else "" for cell in row]
            cleaned.append(cleaned_row)
        
        # Build markdown
        header = "| " + " | ".join(cleaned[0]) + " |"
        separator = "| " + " | ".join(["---"] * len(cleaned[0])) + " |"
        rows = []
        for row in cleaned[1:]:
            # Pad row if shorter than header
            while len(row) < len(cleaned[0]):
                row.append("")
            rows.append("| " + " | ".join(row[:len(cleaned[0])]) + " |")
        
        return "\n".join([header, separator] + rows)


class TextParser:
    """Parse plain text and DOCX files."""

    def parse(self, filepath: str) -> dict:
        """Parse a text file."""
        path = Path(filepath)
        
        if path.suffix.lower() in ('.docx', '.doc'):
            return self._parse_docx(filepath)
        
        # Plain text
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return {
            "pages": [{"page_num": 1, "text": content, "tables": [], "section_header": None, "has_images": False}],
            "metadata": {
                "title": path.stem,
                "author": "Unknown",
                "page_count": 1,
                "file_size": path.stat().st_size,
            },
            "full_text": content,
            "sections": [],
        }

    def _parse_docx(self, filepath: str) -> dict:
        """Parse a DOCX file using python-docx."""
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(filepath)
            
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            
            content = "\n\n".join(paragraphs)
            
            return {
                "pages": [{"page_num": 1, "text": content, "tables": [], "section_header": None, "has_images": False}],
                "metadata": {
                    "title": Path(filepath).stem,
                    "author": doc.core_properties.author or "Unknown",
                    "page_count": 1,
                    "file_size": Path(filepath).stat().st_size,
                },
                "full_text": content,
                "sections": [],
            }
        except ImportError:
            # Fallback to text parser
            return self.parse(filepath)
