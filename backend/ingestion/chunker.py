"""
Semantic Chunker — Splits documents into retrieval-optimized chunks.

Rules:
1. Target chunk size: 512 tokens, overlap: 50 tokens
2. Never split mid-sentence (sentence tokenization)
3. Tables kept as atomic units
4. Section path prepended to each chunk for retrieval precision
5. Maintenance logs chunked per work order entry
6. Each chunk carries full metadata for citation generation
"""

import re
import uuid
from typing import Optional


def simple_sent_tokenize(text: str) -> list[str]:
    """
    Simple sentence tokenizer that doesn't require NLTK downloads.
    Splits on sentence-ending punctuation followed by whitespace.
    """
    # Split on period, question mark, or exclamation followed by space/newline
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token for English text."""
    return len(text) // 4


class SemanticChunker:
    """
    Chunk documents into retrieval-optimized segments with metadata.
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50, min_chunk_length: int = 50):
        self.chunk_size = chunk_size          # target tokens
        self.chunk_overlap = chunk_overlap    # overlap tokens
        self.min_chunk_length = min_chunk_length  # min chars

    def chunk_document(self, parsed_doc: dict, doc_id: str, doc_category: str = "general") -> list[dict]:
        """
        Chunk a parsed document into retrieval-ready segments.
        
        Args:
            parsed_doc: Output from PDFParser/TextParser/ExcelParser
            doc_id: Unique document identifier
            doc_category: Document category from classifier
            
        Returns:
            List of chunk dicts with content and metadata.
        """
        # For maintenance records, chunk by work order entry
        if doc_category == "maintenance_record":
            return self._chunk_by_work_order(parsed_doc, doc_id, doc_category)
        
        # Standard chunking by page, then by sentences
        all_chunks = []
        
        for page in parsed_doc.get("pages", []):
            page_num = page["page_num"]
            text = page["text"]
            section_header = page.get("section_header")
            tables = page.get("tables", [])
            
            # Add tables as atomic chunks
            for table in tables:
                if table and len(table) > self.min_chunk_length:
                    section_path = self._format_section_path(section_header)
                    chunk_content = f"{section_path}\n{table}" if section_path else table
                    
                    all_chunks.append(self._make_chunk(
                        content=chunk_content,
                        doc_id=doc_id,
                        doc_category=doc_category,
                        page_num=page_num,
                        section_header=section_header,
                        chunk_index=len(all_chunks),
                    ))
            
            # Chunk text by sentences
            if text:
                text_chunks = self._chunk_text(text, section_header)
                for chunk_text in text_chunks:
                    if len(chunk_text) < self.min_chunk_length:
                        continue
                    
                    all_chunks.append(self._make_chunk(
                        content=chunk_text,
                        doc_id=doc_id,
                        doc_category=doc_category,
                        page_num=page_num,
                        section_header=section_header,
                        chunk_index=len(all_chunks),
                    ))
        
        return all_chunks

    def _chunk_text(self, text: str, section_header: Optional[dict] = None) -> list[str]:
        """
        Split text into chunks respecting sentence boundaries.
        """
        sentences = simple_sent_tokenize(text)
        if not sentences:
            return [text] if text.strip() else []
        
        section_path = self._format_section_path(section_header)
        prefix = f"[Section: {section_path}]\n" if section_path else ""
        prefix_tokens = estimate_tokens(prefix)
        
        chunks = []
        current_sentences = []
        current_tokens = prefix_tokens
        
        for sentence in sentences:
            sent_tokens = estimate_tokens(sentence)
            
            if current_tokens + sent_tokens > self.chunk_size and current_sentences:
                # Save current chunk
                chunk_text = prefix + " ".join(current_sentences)
                chunks.append(chunk_text)
                
                # Overlap: keep last few sentences
                overlap_sentences = []
                overlap_tokens = prefix_tokens
                for s in reversed(current_sentences):
                    s_tokens = estimate_tokens(s)
                    if overlap_tokens + s_tokens > self.chunk_overlap:
                        break
                    overlap_sentences.insert(0, s)
                    overlap_tokens += s_tokens
                
                current_sentences = overlap_sentences
                current_tokens = overlap_tokens
            
            current_sentences.append(sentence)
            current_tokens += sent_tokens
        
        # Don't forget the last chunk
        if current_sentences:
            chunk_text = prefix + " ".join(current_sentences)
            chunks.append(chunk_text)
        
        return chunks

    def _chunk_by_work_order(self, parsed_doc: dict, doc_id: str, doc_category: str) -> list[dict]:
        """
        For maintenance records, chunk by work order entry.
        Each work order is a semantic unit.
        """
        full_text = parsed_doc.get("full_text", "")
        
        # Split on work order patterns
        wo_pattern = r'(?=(?:Work Order|WO\s*#|WO\s*:)\s*\w+)'
        entries = re.split(wo_pattern, full_text, flags=re.IGNORECASE)
        
        if len(entries) <= 1:
            # No work order pattern found — fall back to standard chunking
            return self.chunk_document(
                {**parsed_doc},
                doc_id,
                "general"  # Override category to prevent recursion
            )
        
        chunks = []
        for i, entry in enumerate(entries):
            entry = entry.strip()
            if len(entry) < self.min_chunk_length:
                continue
            
            # If entry is too long, sub-chunk it
            if estimate_tokens(entry) > self.chunk_size * 2:
                sub_chunks = self._chunk_text(entry)
                for sub_chunk in sub_chunks:
                    chunks.append(self._make_chunk(
                        content=sub_chunk,
                        doc_id=doc_id,
                        doc_category=doc_category,
                        page_num=1,
                        section_header={"number": f"WO-{i+1}", "title": "Work Order Entry"},
                        chunk_index=len(chunks),
                    ))
            else:
                chunks.append(self._make_chunk(
                    content=entry,
                    doc_id=doc_id,
                    doc_category=doc_category,
                    page_num=1,
                    section_header={"number": f"WO-{i+1}", "title": "Work Order Entry"},
                    chunk_index=len(chunks),
                ))
        
        return chunks

    def _make_chunk(self, content: str, doc_id: str, doc_category: str,
                    page_num: int, section_header: Optional[dict],
                    chunk_index: int) -> dict:
        """Create a chunk dict with full metadata."""
        from backend.ingestion.entity_extractor import IndustrialNER
        
        # Extract equipment tags from chunk content
        equipment_tags = re.findall(r'\b[A-Z]{1,4}-\d{3,4}[A-Z]?\b', content)
        
        # Extract dates
        date_pattern = r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b'
        dates = re.findall(date_pattern, content)
        date_range = f"{dates[0]} to {dates[-1]}" if len(dates) > 1 else (dates[0] if dates else "")
        
        return {
            "id": str(uuid.uuid4()),
            "doc_id": doc_id,
            "content": content,
            "doc_category": doc_category,
            "page_num": page_num,
            "section_path": self._format_section_path(section_header),
            "equipment_tags": list(set(equipment_tags)),
            "date_range": date_range,
            "chunk_index": chunk_index,
            "token_count": estimate_tokens(content),
        }

    def _format_section_path(self, section_header: Optional[dict]) -> str:
        """Format section header into a path string."""
        if not section_header:
            return ""
        
        number = section_header.get("number", "")
        title = section_header.get("title", "")
        
        if number and title:
            return f"{number} {title}"
        return title or number
