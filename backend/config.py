"""
Configuration module for Plant Brain backend.
Loads environment variables and provides constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
SAMPLE_DOCS_DIR = DATA_DIR / "sample_docs"
UPLOAD_DIR = DATA_DIR / "uploads"
GRAPH_PERSIST_PATH = DATA_DIR / "graph_store.json"
VECTOR_PERSIST_DIR = DATA_DIR / "chroma_db"
SQLITE_DB_PATH = DATA_DIR / "plant_brain.db"

# Create directories
for d in [DATA_DIR, SAMPLE_DOCS_DIR, UPLOAD_DIR, VECTOR_PERSIST_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── LLM Configuration ─────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "azure_foundry")  # gemini | openai | anthropic | openrouter | azure_foundry | mock
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

AZURE_FOUNDRY_ENDPOINT = os.getenv("AZURE_FOUNDRY_ENDPOINT", "")
AZURE_FOUNDRY_KEY = os.getenv("AZURE_FOUNDRY_KEY", "")
AZURE_FOUNDRY_MODEL = os.getenv("AZURE_FOUNDRY_MODEL", "gpt-5-mini")

# Model names per provider
LLM_MODELS = {
    "gemini": "gemini-1.5-flash",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-latest",
    "openrouter": "openai/gpt-oss-20b:free",
    "azure_foundry": AZURE_FOUNDRY_MODEL,
}

# ── Embedding Configuration ───────────────────────────────────────────────
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nvidia/nemotron-3-embed-1b:free")

# ── Chunking Configuration ────────────────────────────────────────────────
CHUNK_SIZE = 512          # tokens
CHUNK_OVERLAP = 50        # tokens
MIN_CHUNK_LENGTH = 50     # characters — skip tiny chunks

# ── Entity Extraction ─────────────────────────────────────────────────────
SPACY_MODEL = "en_core_web_sm"
EQUIPMENT_TAG_PATTERN = r'\b[A-Z]{1,4}-\d{3,4}[A-Z]?\b'

# ── Vector Store ───────────────────────────────────────────────────────────
CHROMA_COLLECTION_NAME = "industrial_knowledge"
VECTOR_SEARCH_TOP_K = 10

# ── API ────────────────────────────────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

# ── Database ───────────────────────────────────────────────────────────────
DATABASE_URL = f"sqlite+aiosqlite:///{SQLITE_DB_PATH}"
