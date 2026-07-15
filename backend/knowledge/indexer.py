"""
Indexer — Orchestrates the full ingestion pipeline.

Pipeline: classify → parse → chunk → extract entities → store vectors → build graph
Returns indexing statistics for each document processed.
"""

import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime

from backend.ingestion.document_classifier import DocumentClassifier
from backend.ingestion.pdf_parser import PDFParser, TextParser
from backend.ingestion.excel_parser import ExcelParser
from backend.ingestion.chunker import SemanticChunker
from backend.ingestion.entity_extractor import IndustrialNER
from backend.knowledge.vector_store import VectorStore
from backend.knowledge.graph_store import GraphStore


class Indexer:
    """
    Orchestrates document ingestion from raw file to indexed knowledge.
    """

    def __init__(self, vector_store: VectorStore, graph_store: GraphStore):
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.classifier = DocumentClassifier()
        self.pdf_parser = PDFParser()
        self.text_parser = TextParser()
        self.excel_parser = ExcelParser()
        self.chunker = SemanticChunker()
        self.ner = IndustrialNER()

    def index_document(self, filepath: str, doc_id: str = None) -> dict:
        """
        Full indexing pipeline for a single document.
        
        Args:
            filepath: Path to the document file
            doc_id: Optional document ID (generated if not provided)
            
        Returns:
            {
                "doc_id": str,
                "filename": str,
                "classification": dict,
                "chunks_created": int,
                "entities_extracted": int,
                "graph_nodes_created": int,
                "graph_edges_created": int,
                "status": "completed" | "failed",
                "error": str | None,
            }
        """
        doc_id = doc_id or str(uuid.uuid4())
        filename = Path(filepath).name
        
        result = {
            "doc_id": doc_id,
            "filename": filename,
            "classification": {},
            "chunks_created": 0,
            "entities_extracted": 0,
            "graph_nodes_created": 0,
            "graph_edges_created": 0,
            "status": "completed",
            "error": None,
        }

        try:
            # Step 1: Classify
            parsed_doc = self._parse_file(filepath)
            content_sample = parsed_doc.get("full_text", "")[:2000]
            classification = self.classifier.classify(filepath, content_sample)
            result["classification"] = classification

            # Step 2: Chunk
            chunks = self.chunker.chunk_document(
                parsed_doc, doc_id, classification["doc_category"]
            )
            result["chunks_created"] = len(chunks)

            # Step 3: Extract entities from full text
            entities = self.ner.extract_entities(parsed_doc.get("full_text", ""))
            result["entities_extracted"] = len(entities)

            # Step 4: Store chunks in vector store
            self.vector_store.add_chunks(chunks)

            # Step 5: Build knowledge graph
            nodes, edges = self._build_graph(
                doc_id, filename, classification, parsed_doc, entities, chunks
            )
            result["graph_nodes_created"] = nodes
            result["graph_edges_created"] = edges

            # Step 6: Persist graph
            self.graph_store.save()

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            import traceback
            traceback.print_exc()

        return result

    def _parse_file(self, filepath: str) -> dict:
        """Parse file using appropriate parser."""
        ext = Path(filepath).suffix.lower()
        
        if ext == ".pdf":
            return self.pdf_parser.parse(filepath)
        elif ext in (".xlsx", ".xls", ".csv"):
            return self.excel_parser.parse(filepath)
        else:
            return self.text_parser.parse(filepath)

    def _build_graph(self, doc_id: str, filename: str,
                     classification: dict, parsed_doc: dict,
                     entities: list, chunks: list) -> tuple[int, int]:
        """
        Build knowledge graph nodes and edges from extracted data.
        Returns (nodes_created, edges_created).
        """
        nodes_created = 0
        edges_created = 0

        # 1. Add Document node
        doc_node_id = f"document:{doc_id}"
        self.graph_store.add_entity(doc_node_id, "Document", {
            "doc_id": doc_id,
            "title": parsed_doc.get("metadata", {}).get("title", filename),
            "doc_type": classification["doc_category"],
            "filename": filename,
            "page_count": parsed_doc.get("metadata", {}).get("page_count", 0),
            "date": parsed_doc.get("metadata", {}).get("creation_date", ""),
        })
        nodes_created += 1

        # 2. Add entity nodes and edges
        equipment_tags = set()
        personnel = set()
        regulations = set()
        failure_modes = set()

        for entity in entities:
            if entity.entity_type == "EQUIPMENT_TAG":
                tag = entity.text.upper()
                if tag not in equipment_tags:
                    equipment_tags.add(tag)
                    equip_node_id = f"equipment:{tag}"
                    
                    self.graph_store.add_entity(equip_node_id, "Equipment", {
                        "tag": tag,
                        "equipment_type": self._guess_equipment_type(tag),
                    })
                    nodes_created += 1
                    
                    # Equipment → Document edge
                    self.graph_store.add_relationship(
                        equip_node_id, doc_node_id,
                        "DOCUMENTED_IN", {"doc_category": classification["doc_category"]}
                    )
                    edges_created += 1

            elif entity.entity_type == "PERSONNEL":
                name = entity.text.strip()
                if name and name not in personnel and len(name) > 2:
                    personnel.add(name)
                    person_node_id = f"person:{name.lower().replace(' ', '_')}"
                    
                    self.graph_store.add_entity(person_node_id, "Person", {
                        "name": name,
                    })
                    nodes_created += 1
                    
                    # Document → Person edge
                    self.graph_store.add_relationship(
                        doc_node_id, person_node_id,
                        "AUTHORED_BY"
                    )
                    edges_created += 1

            elif entity.entity_type == "REGULATION":
                code = entity.text.upper()
                if code not in regulations:
                    regulations.add(code)
                    reg_node_id = f"regulation:{code.lower().replace(' ', '_')}"
                    
                    self.graph_store.add_entity(reg_node_id, "Regulation", {
                        "code": code,
                        "title": code,
                    })
                    nodes_created += 1
                    
                    # Equipment → Regulation edges (for each equipment in this doc)
                    for tag in equipment_tags:
                        self.graph_store.add_relationship(
                            f"equipment:{tag}", reg_node_id,
                            "SUBJECT_TO", {"compliance_status": "AMBER"}
                        )
                        edges_created += 1

            elif entity.entity_type == "FAILURE_MODE":
                desc = entity.text.lower()
                if desc not in failure_modes:
                    failure_modes.add(desc)
                    fm_node_id = f"failure_mode:{desc.replace(' ', '_')}"
                    
                    self.graph_store.add_entity(fm_node_id, "FailureMode", {
                        "description": desc,
                    })
                    nodes_created += 1
                    
                    # Create event and link failure mode
                    event_node_id = f"event:{doc_id}:{desc.replace(' ', '_')}"
                    self.graph_store.add_entity(event_node_id, "Event", {
                        "event_type": "failure",
                        "date": parsed_doc.get("metadata", {}).get("creation_date", ""),
                        "description": f"Failure: {desc}",
                    })
                    nodes_created += 1
                    
                    self.graph_store.add_relationship(
                        event_node_id, fm_node_id, "CAUSED_BY"
                    )
                    edges_created += 1
                    
                    # Link equipment to event
                    for tag in equipment_tags:
                        self.graph_store.add_relationship(
                            f"equipment:{tag}", event_node_id, "EXPERIENCED"
                        )
                        edges_created += 1
                    
                    # Event documented in document
                    self.graph_store.add_relationship(
                        event_node_id, doc_node_id, "DOCUMENTED_IN"
                    )
                    edges_created += 1

        return nodes_created, edges_created

    def _guess_equipment_type(self, tag: str) -> str:
        """Guess equipment type from tag prefix."""
        prefix_map = {
            "P": "pump",
            "V": "vessel",
            "HX": "heat_exchanger",
            "E": "heat_exchanger",
            "C": "compressor",
            "T": "tank",
            "R": "reactor",
            "D": "drum",
            "F": "filter",
            "B": "boiler",
            "G": "generator",
            "M": "motor",
        }
        
        # Extract prefix (letters before the dash)
        import re
        match = re.match(r'^([A-Z]+)', tag)
        if match:
            prefix = match.group(1)
            return prefix_map.get(prefix, "equipment")
        return "equipment"

    def index_directory(self, dir_path: str) -> list[dict]:
        """Index all documents in a directory."""
        results = []
        path = Path(dir_path)
        
        supported_extensions = {'.pdf', '.txt', '.docx', '.xlsx', '.xls', '.csv'}
        
        for filepath in sorted(path.iterdir()):
            if filepath.suffix.lower() in supported_extensions:
                result = self.index_document(str(filepath))
                results.append(result)
        
        return results
