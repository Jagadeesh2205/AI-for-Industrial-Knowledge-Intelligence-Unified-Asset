# 🧠 Plant Brain — Industrial Knowledge Intelligence Platform

A **hybrid Graph-RAG system** that unifies industrial knowledge across maintenance logs, OEM manuals, inspection reports, safety procedures, and regulatory standards into a single AI-powered operations brain.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ 
- Node.js 18+

### 1. Backend Setup

```bash
# From project root
cd backend

# Activate virtual environment
# Windows:
..\venv\Scripts\activate
# Linux/Mac:
# source ../venv/bin/activate

# Start the API server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will automatically index the sample documents on first startup.

### 2. Frontend Setup

```bash
# From project root  
cd frontend

# Install dependencies (if not already done)
npm install

# Start dev server
npm run dev
```

### 3. Open the App
- **Desktop**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────┐
│  Frontend (React + Vite)                         │
│  Dashboard │ AI Copilot │ Knowledge Graph        │
│  Documents │ Maintenance RCA │ Compliance        │
└─────────────────────┬────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────┐
│  API Layer (FastAPI)                              │
│  REST + WebSocket Streaming                       │
└─────────────────────┬────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────┐
│  AI Agent Layer                                   │
│  Expert Copilot │ Maintenance RCA │ Compliance    │
└─────────────────────┬────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────┐
│  Hybrid Retrieval Engine                          │
│  Graph Traversal + Vector Search + MMR Reranking  │
└──────┬──────────────────────────────┬────────────┘
       │                              │
┌──────▼──────┐              ┌────────▼───────┐
│  ChromaDB   │              │  NetworkX      │
│  (Vectors)  │              │  (Graph)       │
└─────────────┘              └────────────────┘
```

## 📁 Project Structure

```
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── config.py                # Configuration
│   ├── ingestion/               # Document processing pipeline
│   ├── knowledge/               # Vector store + Knowledge graph
│   ├── retrieval/               # Hybrid retrieval engine
│   ├── agents/                  # AI agents (Copilot, RCA, Compliance)
│   ├── api/                     # REST & WebSocket routes
│   └── database/                # SQLAlchemy models
├── frontend/
│   └── src/
│       ├── pages/               # 6 page components
│       └── hooks/               # Data fetching hooks
├── data/
│   └── sample_docs/             # Demo industrial documents
├── venv/                        # Python virtual environment
└── .env                         # Configuration (LLM provider, API keys)
```

## 🤖 LLM Configuration

Edit `.env` to set your LLM provider:

```env
# Options: gemini | openai | anthropic | mock
LLM_PROVIDER=mock

# Set the API key for your chosen provider
GEMINI_API_KEY=your-key-here
```

The system works with `mock` mode for demos (no API key required).

## 📊 Demo Scenario: Pump P-101

The sample documents tell a connected story:

1. **Technician notices** high vibration on pump P-101
2. **AI Copilot retrieves**: maintenance history (bearing replacement 18 months ago), OEM manual (12-month bearing life), and past incident report
3. **Knowledge Graph** shows all connections between P-101, its events, documents, and related equipment
4. **Compliance Agent** flags OISD-116 gaps for the facility
5. **Maintenance RCA** identifies cross-equipment failure patterns (similar bearing failure on C-201)

## 🔑 Key Features

| Feature | Description |
|---------|-------------|
| **Hybrid Graph-RAG** | Combines vector similarity search with knowledge graph traversal |
| **3 AI Agents** | Expert Copilot, Maintenance RCA, Compliance Checker |
| **Knowledge Graph** | Interactive force-directed visualization of entity relationships |
| **Citation System** | Every AI claim cites its source document and page |
| **Mobile PWA** | Responsive design, installable as Progressive Web App |
| **Auto-Indexing** | Upload documents → automatic classification, chunking, entity extraction, graph building |
