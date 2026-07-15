"""
SQLAlchemy models for Plant Brain metadata storage.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, Enum
from sqlalchemy.orm import DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class DocStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)          # pdf, xlsx, docx, txt
    doc_category = Column(String, nullable=True)         # maintenance_record, safety_procedure, etc.
    file_size = Column(Integer, default=0)
    page_count = Column(Integer, default=0)
    status = Column(String, default=DocStatus.PENDING)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    entity_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    source_path = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=True)          # Extra metadata


class Entity(Base):
    __tablename__ = "entities"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)         # EQUIPMENT_TAG, PERSONNEL, etc.
    doc_id = Column(String, nullable=False)
    confidence = Column(Float, default=1.0)
    positions = Column(JSON, nullable=True)              # [{page, start, end}]
    attributes = Column(JSON, nullable=True)


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True)
    doc_id = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, default=0)
    page_num = Column(Integer, nullable=True)
    section_path = Column(String, nullable=True)
    equipment_tags = Column(JSON, nullable=True)         # List of tags found in chunk
    date_range = Column(String, nullable=True)
    token_count = Column(Integer, default=0)


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(String, primary_key=True)
    query = Column(Text, nullable=False)
    agent_type = Column(String, default="copilot")
    intent_type = Column(String, nullable=True)
    response_summary = Column(Text, nullable=True)
    sources_used = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    session_id = Column(String, nullable=True)
