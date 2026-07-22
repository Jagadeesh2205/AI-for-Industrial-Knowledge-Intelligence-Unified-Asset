"""
Ingest Routes — Document upload and processing endpoints.
"""

import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from backend.config import UPLOAD_DIR

router = APIRouter()

# In-memory job tracker (prototype — use Redis/DB in production)
ingest_jobs: dict = {}


class IngestResponse(BaseModel):
    job_id: str
    files_received: int
    status: str = "processing"


class IngestStatus(BaseModel):
    job_id: str
    status: str
    total_files: int = 0
    processed_files: int = 0
    results: list = []
    errors: list = []


@router.post("/api/ingest", response_model=IngestResponse)
async def ingest_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...)
):
    """
    Upload and process documents.
    Returns a job_id for status polling.
    """
    job_id = str(uuid.uuid4())
    
    # Save uploaded files
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    saved_paths = []
    for file in files:
        # Sanitize filename — prevent path traversal (e.g. "../../evil")
        safe_name = Path(file.filename or "upload").name
        filepath = job_dir / safe_name
        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)
        saved_paths.append(str(filepath))
    
    # Initialize job status
    ingest_jobs[job_id] = {
        "status": "processing",
        "total_files": len(saved_paths),
        "processed_files": 0,
        "results": [],
        "errors": [],
    }
    
    # Process in background
    background_tasks.add_task(process_documents, job_id, saved_paths)
    
    return IngestResponse(
        job_id=job_id,
        files_received=len(saved_paths),
        status="processing",
    )


@router.get("/api/ingest/status/{job_id}", response_model=IngestStatus)
async def get_ingest_status(job_id: str):
    """Poll for document processing status."""
    if job_id not in ingest_jobs:
        return IngestStatus(
            job_id=job_id,
            status="not_found",
        )
    
    job = ingest_jobs[job_id]
    return IngestStatus(
        job_id=job_id,
        status=job["status"],
        total_files=job["total_files"],
        processed_files=job["processed_files"],
        results=job["results"],
        errors=job["errors"],
    )


async def process_documents(job_id: str, file_paths: list[str]):
    """Background task: process each document through the indexing pipeline."""
    from backend.main import get_indexer
    from backend.activity import log_event

    indexer = get_indexer()
    job = ingest_jobs[job_id]

    for filepath in file_paths:
        try:
            doc_id = str(uuid.uuid4())
            result = indexer.index_document(filepath, doc_id)
            job["results"].append(result)
            job["processed_files"] += 1
            if result.get("status") == "completed":
                log_event("INGEST", f"Indexed {Path(filepath).name}: "
                          f"{result.get('chunks_created', 0)} chunks, "
                          f"{result.get('entities_extracted', 0)} entities")
            else:
                log_event("ERROR", f"Failed to index {Path(filepath).name}: "
                          f"{result.get('error', 'unknown error')}")
        except Exception as e:
            job["errors"].append({
                "file": Path(filepath).name,
                "error": str(e),
            })
            job["processed_files"] += 1
            log_event("ERROR", f"Failed to index {Path(filepath).name}: {e}")

    job["status"] = "completed" if not job["errors"] else "completed_with_errors"
