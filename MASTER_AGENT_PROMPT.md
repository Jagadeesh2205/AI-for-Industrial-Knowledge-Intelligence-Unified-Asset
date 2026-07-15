

### What Has Been Built So Far

| Layer | Status | Key Files |
|---|---|---|
| Document Ingestion | ✅ Done | `ingestion/pdf_parser.py`, `chunker.py`, `entity_extractor.py` |
| Vector Store | ✅ Done | `knowledge/vector_store.py` → ChromaDB at `./data/chroma_db/` |
| Knowledge Graph | ✅ Done | `knowledge/graph_store.py` → NetworkX saved as `./data/graph_store.json` |
| Hybrid Retrieval | ✅ Done | `retrieval/hybrid_retriever.py` |
| AI Agents (3) | ✅ Done | `agents/expert_copilot.py`, `maintenance_agent.py`, `compliance_agent.py` |
| FastAPI Backend | ✅ Done | `main.py`, `api/routes/` |
| React Frontend | ✅ Done | `frontend/src/` — 6 pages |
| Demo Data (13 docs) | ✅ Done | `data/sample_docs/` |
| Gemini Integration | ✅ Done | `google-genai` SDK, `gemini-2.5-flash` |
| Mobile PWA | ✅ Done | `frontend/public/manifest.json` |

---
---

## PART 2 — VALIDATION CHECKLIST
### Verify Every Layer Works Before Judging / Demoing

---

### ✅ TIER 1: Backend Health (Run First)

```
□ 1.  GET  http://localhost:8000/api/health
      Expected: {"status": "healthy", "llm_provider": "gemini", ...}
      ✗ If "mock" appears: check .env → ANTHROPIC_API_KEY or LLM_PROVIDER

□ 2.  GET  http://localhost:8000/api/stats
      Expected: {documents: 13, chunks: 42, graph_nodes: 92, graph_edges: 324}
      ✗ If zeros: startup auto-indexing failed → check terminal logs

□ 3.  GET  http://localhost:8000/docs
      Expected: Swagger UI showing all routes
      ✗ If 404: uvicorn not running or wrong port

□ 4.  Terminal logs on startup should show:
      "Auto-indexing sample documents..."
      "Indexed: pump_p101_maintenance_log.txt"
      "Knowledge graph: 92 nodes, 324 edges"
      ✗ If missing: check SAMPLE_DOCS_DIR path in config.py
```

---

### ✅ TIER 2: Ingestion Pipeline

```
□ 5.  Upload a new PDF via POST /api/ingest (use Swagger UI or frontend Documents page)
      Expected: {job_id: "...", status: "queued"}

□ 6.  Poll GET /api/ingest/status/{job_id}
      Expected: status moves → "processing" → "completed"
      Check: document appears in GET /api/documents

□ 7.  Verify entity extraction ran on the new doc:
      GET /api/documents/{doc_id} → should show extracted entities
      ✗ If entity list empty: entity_extractor.py spaCy init may have failed

□ 8.  Upload a scanned image/PDF (non-text)
      Expected: OCR kicks in (pytesseract) OR graceful fallback with warning in logs
      ✗ If error: Tesseract binary not installed (optional — just log the skip)

□ 9.  Upload an Excel file (.xlsx)
      Expected: Parsed, tabular data chunked and indexed
      ✗ If error: check openpyxl import in excel_parser.py
```

---

### ✅ TIER 3: Retrieval Quality

Run these exact queries and verify the answers are correct:

```
□ 10. Query: "What maintenance was done on P-101?"
      Expected: Should pull work order dates, bearing replacement history
      Must cite: pump_p101_maintenance_log + incident_report_ir_2022_047
      ✗ Fail signal: Generic answer with no specific dates/WO numbers

□ 11. Query: "When did P-101 fail catastrophically?"
      Expected: References June 2022 failure, cites IR-2022-047
      Must cite: incident_report_ir_2022_047.txt
      ✗ Fail signal: Says "no information available"

□ 12. Query: "What does OISD-116 require for pump inspections?"
      Expected: Quotes specific section requirements, flags compliance gaps
      Must cite: regulatory_oisd_116_extract.txt
      ✗ Fail signal: Hallucinated answer or missing regulation details

□ 13. Query: "What are the common failure modes for centrifugal pumps?"
      Expected: Pulls from OEM manual AND incident reports AND maintenance logs
      Must use: MULTIPLE sources across different document types
      ✗ Fail signal: Only one source cited → hybrid retrieval may not be working

□ 14. Query: "Has V-201 ever had any issues?"
      Expected: References inspection_report_2024_q1.txt corrosion findings
      ✗ Fail signal: "No information found" → entity extraction missed V-201 tag

□ 15. Graph-specific test: GET /api/graph/equipment/P-101
      Expected: JSON with equipment node + connected events, docs, failure modes
      ✗ Fail signal: Empty graph or "node not found" → graph build failed
```

---

### ✅ TIER 4: AI Agent Quality

```
□ 16. Expert Copilot: Every response MUST contain [Source: ...] citation tags
      ✗ Fail: Response with no citations = system prompt not enforcing it

□ 17. Maintenance RCA Agent: Query "P-101 showing high vibration, what is the RCA?"
      Expected: Structured output with probable causes, evidence, recommendations
      Response should be >400 words (8192 token limit should prevent truncation)
      ✗ Fail: Truncated mid-sentence = token limit still too low

□ 18. Compliance Agent: Query "What are our OISD-116 compliance gaps?"
      Expected: RED/AMBER/GREEN status matrix or list of specific gaps
      Must reference: specific equipment + specific regulation section
      ✗ Fail: Generic compliance advice = compliance agent hitting wrong context

□ 19. Test follow-up questions:
      First ask: "Tell me about P-101"
      Then ask: "What about its last inspection?"  (no equipment tag in follow-up)
      Expected: Should understand "its" refers to P-101 from conversation history
      ✗ Fail: "Which equipment are you referring to?" = session context not passed

□ 20. Test confidence when knowledge is absent:
      Query: "What is the operating procedure for compressor C-999?"
      Expected: "This specific information isn't in the available documentation..."
      ✗ Fail: Hallucinated procedure = LLM not constrained to context only
```

---

### ✅ TIER 5: Frontend & UX

```
□ 21. Dashboard loads with live stats (not zeros) within 2 seconds
□ 22. Sidebar shows "LLM: gemini" not "LLM: mock"
□ 23. Knowledge Graph page renders the force-directed graph with nodes and edges
□ 24. Clicking a graph node opens the entity detail side panel
□ 25. Chat responses stream (tokens appear progressively, not all at once)
□ 26. Citations in chat are clickable chips that open the source document
□ 27. Document upload drag-and-drop works and shows progress
□ 28. On mobile viewport (375px): Layout switches to single-column field mode
□ 29. PWA installable: Chrome address bar shows install icon
□ 30. No console errors in DevTools on any of the 6 pages
```

---
---

## PART 3 — DOCUMENT TYPES FOR TESTING
### What to Feed the System to Prove It Works

---

### By Format Type (Test Each Processor)

| Document Format | How to Get Test Samples | What It Tests |
|---|---|---|
| **Text-rich PDF** | Any published technical report | PyMuPDF parser, chunker, NER |
| **Scanned PDF / Image** | Photograph a printed maintenance log | Tesseract OCR pipeline |
| **Excel (.xlsx)** | Equipment inspection data sheet | `excel_parser.py`, tabular chunking |
| **Word (.docx)** | Any SOP or procedure document | `python-docx` parser |
| **Image (P&ID)** | Engineering drawing as PNG/JPG | OpenCV + OCR pipeline |

---

### By Industrial Document Category (Test Domain Coverage)

```
CATEGORY 1 — MAINTENANCE RECORDS
  ├── Work Order (WO) register: columns for WO#, date, equipment, description, technician
  ├── Preventive Maintenance (PM) schedule: weekly/monthly/annual tasks by equipment tag
  └── Corrective Maintenance log: fault description → action taken → parts used

CATEGORY 2 — EQUIPMENT TECHNICAL FILES
  ├── OEM manual (pump, motor, compressor) — long PDF, tables of specs
  ├── Equipment data sheet: tag number, capacity, design pressure/temp, material
  └── Commissioning report: initial test results, performance baseline

CATEGORY 3 — SAFETY & PROCEDURES
  ├── Standard Operating Procedure (SOP): numbered steps, checkboxes
  ├── Permit to Work (PTW) form: signatures, isolation points, expiry
  ├── Lock-Out Tag-Out (LOTO) procedure: step-by-step isolation sequence
  └── Material Safety Data Sheet (MSDS): chemical properties, hazards

CATEGORY 4 — INSPECTION & QC
  ├── NDT (Non-Destructive Testing) report: ultrasonic, radiography results
  ├── Thickness measurement log: corrosion tracking table over time
  ├── Piping inspection register: line-by-line status
  └── Third-party inspection certificate: with stamp, expiry date

CATEGORY 5 — REGULATORY COMPLIANCE
  ├── OISD standard extract (publicly available at oisdindia.com)
  ├── Factory Act checklist: Section-by-section compliance table
  ├── Environmental consent conditions: stack emission limits
  └── Statutory inspection due dates register

CATEGORY 6 — INCIDENT & NEAR-MISS
  ├── Incident investigation report: timeline, root cause, corrective actions
  ├── Near-miss log: hazard, location, contributing factors
  └── Lessons learned bulletin: distributed after incident closure
```

---

### Professional Public Documents to Use as Real Test Data

These are publicly available and reflect real industrial quality:

```
1. OISD-116 (Oil Industry Safety Directorate)
   Source: https://www.oisdindia.com/pdf/OISD-STD-116.pdf
   Content: Pressure vessel inspection requirements, intervals, documentation
   Tests: Regulatory entity extraction, compliance gap detection

2. OISD-118 (Layout requirements)
   Source: Same domain — search "OISD 118 PDF"
   Tests: Cross-referencing regulations against equipment

3. IS 2825:1969 (BIS Code for Unfired Pressure Vessels)
   Source: Bureau of Indian Standards (bis.gov.in)
   Tests: Technical standard parsing, clause extraction

4. Grundfos CR-Series Pump Manual (Public OEM)
   Source: product.grundfos.com → search CR 95 → download installation manual
   Content: Technical specs, installation, troubleshooting, failure modes
   Tests: OEM manual entity extraction, failure mode mapping

5. Atlas Copco GA Compressor Manual (Public)
   Source: pdf.atlascopco.com → GA series user manual
   Tests: Compressor-specific NER, parameter extraction

6. CPCB Environment Compliance Report (Public)
   Source: cpcb.nic.in → Annual reports section
   Tests: Environmental regulatory document parsing

7. PESO (Petroleum and Explosives Safety Organisation)
   Source: peso.gov.in → Petroleum Rules PDF
   Tests: Multi-regulation cross-referencing

8. API 570 Piping Inspection Code (Excerpt)
   Source: Search "API 570 piping inspection code sample" (ASME distributes free excerpts)
   Tests: International standard clause extraction
```

---

### Synthetic Test Documents to Create Yourself

Create these as plain text files — they test specific system behaviours:

```python
# Test 1: MULTI-EQUIPMENT DOCUMENT (tests whether multiple entity tags are extracted)
"""
MONTHLY MAINTENANCE SUMMARY — JUNE 2024
Equipment P-101: Bearing inspection completed. Vibration at 4.2 mm/s — normal.
Equipment P-102: Oil change completed. Running at design flow of 95 m³/hr.
Equipment HX-301: Tube bundle cleaned. Fouling factor improved by 23%.
Equipment V-201: Level gauge replaced. Previous LG-201 faulty since May.
Prepared by: Ranjit Kumar, Mechanical Supervisor
"""
# This should create 4 equipment nodes connected to this document node in graph

# Test 2: CONFLICTING INFORMATION (tests whether system flags contradictions)
"""
OEM Manual: Replace seal every 6 months.
Maintenance Log Mar 2024: Seal replaced. Next due: Sep 2024.
Maintenance Log Aug 2024: Seal NOT replaced (postponed to Oct).
Maintenance Log Nov 2024: Seal failure. Pump offline 3 days.
"""
# System should flag: procedure not followed, failure followed → compliance gap

# Test 3: CROSS-EQUIPMENT FAILURE PATTERN (tests SIMILAR_TO graph edge)
"""
Incident #IR-2023-012: P-201 seal failure. Root cause: dry running during startup.
Incident #IR-2023-089: P-104 seal failure. Root cause: dry running during startup.
Incident #IR-2024-031: P-303 seal failure. Root cause: dry running during startup.
Corrective Action: Update startup procedure to verify priming before motor start.
"""
# After ingestion, querying "seal failures" should surface ALL THREE incidents
# and suggest systemic pattern → startup procedure SOP was not updated

# Test 4: NUMERIC PARAMETER EXTRACTION (tests unit extraction)
"""
Design data for Heat Exchanger HX-401:
Shell side: Design pressure 10 barg, Design temperature 250°C, Fluid: steam
Tube side: Design pressure 6 barg, Design temperature 180°C, Fluid: process water
Heat duty: 2.4 MW, Overall U-value: 850 W/m²K
Last hydro-test: 15.0 barg, Date: 12-Jan-2024, Result: PASS
"""
# System should extract: equipment tag, pressures, temperatures, U-value, test date

# Test 5: PROCEDURE DOCUMENT (tests step extraction)
"""
SOP-045: Centrifugal Pump Startup Procedure
Step 1: Verify isolation valves V-101A and V-101B are CLOSED
Step 2: Open cooling water valve CWV-14
Step 3: Prime the pump — open vent valve until water flows continuously
Step 4: Start motor. DO NOT run dry for more than 10 seconds.
Step 5: Slowly open discharge valve V-102 while monitoring flow indicator FI-201
Step 6: Verify suction pressure > 0.5 barg on PI-101
Step 7: Confirm vibration reading < 4.5 mm/s on local gauge
"""
# System should extract valve tags, instrument tags, numeric thresholds
```

---
---

## PART 4 — DASHBOARD REDESIGN BRIEF
### From Generic AI-Generated Page → Professional Industrial Intelligence Terminal

---

### What's Wrong With the Current Design

The current dashboard exhibits the classic "AI-generated UI" tells:
- Flat white/grey card backgrounds with rounded corners that look like a Material UI template
- Generic sans-serif body text with no typographic personality
- Stat cards that are indistinguishable from any SaaS dashboard
- No connection to the industrial world the product is meant to serve
- Static layout with no animation or life
- The colour scheme communicates "productivity app," not "industrial intelligence"

---

### The Design Direction: **Industrial Intelligence Terminal**

**Concept**: This is not a productivity dashboard. It is a command interface for an industrial plant's
nervous system. The aesthetic draws from industrial HMI (Human-Machine Interface) panels, real-time
SCADA systems, and the CRTs operators used to stare at in control rooms. Every design choice
must reinforce that this is serious, live, authoritative.

**Palette (6 exact values)**:
```
--bg-void:        #0A0C0F   /* near-black base — like an unlit monitor */
--bg-surface:     #111419   /* card backgrounds */
--bg-elevated:    #1A1F27   /* hover states, active panels */
--border-steel:   #252B35   /* dividers, card borders */
--text-primary:   #E8EBF0   /* primary readable text */
--text-secondary: #6B7890   /* metadata, labels, timestamps */
--accent-teal:    #00D4B8   /* primary action, live indicators, highlights */
--status-safe:    #22C55E   /* operational / compliant / normal */
--status-warn:    #F59E0B   /* warning / amber alert / due soon */
--status-critical:#EF4444   /* danger / overdue / non-compliant */
--status-neutral: #3B82F6   /* informational / in-progress */
--terminal-green: #4ADE80   /* activity feed monospace text */
```

**Typography**:
```
Display / KPI numbers:  'Space Grotesk' — condensed, technical, engineered feel
                        Use at 48px–72px for hero stats (weight 700)
Body / Descriptions:    'Inter' — clean, legible at small sizes
                        Use at 14px for body, 12px for metadata (weight 400)
Monospace / Terminal:   'JetBrains Mono' — activity feed, code-like elements
                        Use at 12px–13px for the live event stream
```

Load fonts via: `@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&family=Inter:wght@400;500;600&family=JetBrains+Mono&display=swap');`

**Layout Architecture**:
```
┌─────────────────────────────────────────────────────────────────────┐
│  TOPBAR: Logo mark + facility name + last-sync timestamp + LLM badge│
├────────┬────────────────────────────────────────────────────────────┤
│        │  HERO ROW: 4 KPI cards with live-counting numbers          │
│        │  [Docs Indexed] [Graph Nodes] [Queries Today] [Compliance] │
│ NAV    ├──────────────────────────────┬─────────────────────────────┤
│        │                              │                             │
│ (icons │  KNOWLEDGE GRAPH PREVIEW     │  LIVE ACTIVITY FEED         │
│  only) │  react-force-graph           │  (terminal aesthetic)       │
│        │  60% width, 350px height     │  40% width, 350px height    │
│        │                              │  monospace green on dark    │
│        ├──────────────────────────────┴─────────────────────────────┤
│        │  STATUS GRID: Equipment health matrix                      │
│        │  [P-101 ●WARN] [P-102 ●OK] [HX-301 ●OK] [V-201 ●CRIT]   │
│        ├─────────────────────────────────────────────────────────────┤
│        │  QUICK QUERY: Inline search bar — type and get answer      │
└────────┴─────────────────────────────────────────────────────────────┘
```

**The Signature Element: Live Activity Terminal**

The right panel of the dashboard is a live-scrolling activity feed that looks like a real system log.
New lines appear from the bottom and push old ones up. Text is monospaced, terminal-green, on near-black.
This single element grounds the entire design in operational reality. No other industrial AI dashboard
has this — it transforms the page from a "report" into a "control room."

```
Terminal display example:
────────────────────────────────────────────
[08:42:13] INDEXED  pump_p101_maintenance_log.pdf       28 chunks
[08:42:14] GRAPH    Equipment node P-101 linked 6 events
[08:42:15] INDEXED  oem_manual_grundfos_cr95.pdf        41 chunks
[08:43:02] QUERY    "What are P-101 failure modes?"     →  4 sources retrieved
[08:44:18] ALERT    P-101 bearing inspection overdue by 6 months
[08:51:07] INDEXED  inspection_report_2024_q3.pdf       19 chunks
[08:51:09] GRAPH    Compliance gap detected: OISD-116 §4.2 ← V-201
[now]_
────────────────────────────────────────────
```

**KPI Card Design (not generic boxes)**:
Each card has:
- A top-left 2-character system code in monospace (DO, GN, QR, CM)
- The number in Space Grotesk 64px, counting up from 0 on load
- A 1px bottom border that acts as a micro sparkline
- A delta from yesterday in small text (+3 today / -2%)
- A 2px left border in the relevant accent colour

**Equipment Status Grid**:
Replaces boring list with a grid of equipment "chips":
```
Each chip:
  ┌─────────────────┐
  │ ● P-101         │   ● = teal/amber/red pulsing dot
  │ Centrifugal     │   equipment type
  │ Pump | Unit-3   │   location
  │ 7 events linked │   graph connections
  └─────────────────┘
```
Clicking any chip opens a slide-in panel with that equipment's full history.

**Animations (deliberate, not decorative)**:
- KPI numbers count from 0 to value over 800ms on page load (CSS/JS counter)
- Activity feed new entries fade-in from bottom with 200ms transition
- Equipment status dots pulse (CSS animation) for WARN and CRITICAL states only
- Knowledge graph nodes appear with a 400ms spring animation on first render
- Navigation hover: left border grows from 0 to full height (100ms)

---
---

## PART 5 — COMPREHENSIVE AI AGENT EXECUTION PROMPT
### Copy everything from this section into the agent

---

```
SYSTEM CONTEXT:
You are working on "Operations Brain," an Industrial Knowledge Intelligence platform built
for the ET AI Hackathon 2026. The project is located at:
C:\Users\A JAGADEESH\Documents\Web applications\AI for Industrial Knowledge Intelligence Unified Asset\

ARCHITECTURE (already built — do not recreate):
- Backend: FastAPI (Python), running on http://localhost:8000
  - Virtual env at: .\venv\  (activate with .\venv\Scripts\activate)
  - Entry point: main.py (runs uvicorn)
  - Packages: fastapi, uvicorn, chromadb, networkx, anthropic, google-genai,
    pymupdf, spacy, sqlalchemy, python-dotenv, openpyxl, python-docx, pandas
  - LLM: Gemini 2.5 Flash via google-genai SDK (configured in .env)
  - Vector store: ChromaDB at ./data/chroma_db/
  - Knowledge graph: NetworkX, persisted at ./data/graph_store.json
  - Database: SQLite at ./data/plant_brain.db
  - Demo data: 13 documents at ./data/sample_docs/ (auto-indexed on startup)

- Frontend: React + Vite + TypeScript, running on http://localhost:5173
  - Source at: .\frontend\src\
  - 6 pages: Dashboard, Copilot, KnowledgeGraph, Documents, Maintenance, Compliance
  - Currently uses plain Tailwind CSS + lucide-react + react-force-graph-2d

YOUR TASK HAS FOUR PARTS. EXECUTE THEM IN ORDER.

══════════════════════════════════════════════════
TASK A: RUN VALIDATION CHECKLIST
══════════════════════════════════════════════════

Without modifying any code, verify the system is working correctly.

Step A1: Start the backend if not running:
  cd "C:\Users\A JAGADEESH\Documents\Web applications\AI for Industrial Knowledge Intelligence Unified Asset"
  .\venv\Scripts\activate
  python main.py
  Wait 30 seconds for auto-indexing to complete.

Step A2: Run these HTTP checks using curl or PowerShell Invoke-RestMethod:
  GET http://localhost:8000/api/health
    Assert: status = "healthy", llm_provider = "gemini"
  GET http://localhost:8000/api/stats
    Assert: documents >= 13, chunks >= 42, graph_nodes >= 92

Step A3: Run the 5 benchmark queries via POST http://localhost:8000/api/query:
  Payload: {"query": "<question>", "agent": "copilot"}

  Query 1: "What maintenance was done on P-101?"
    Assert: Response mentions specific WO numbers or dates + [Source: ...] citation
  Query 2: "When did P-101 fail catastrophically?"
    Assert: Cites incident_report_ir_2022_047 + mentions June 2022
  Query 3: "What does OISD-116 require for pump inspections?"
    Assert: References specific sections + cites regulatory_oisd_116_extract
  Query 4: "Has V-201 ever had any issues?"
    Assert: References inspection_report or NDT findings
  Query 5: "What is the operating procedure for compressor C-999?"
    Assert: States "not in available documentation" — does NOT hallucinate

Step A4: Verify graph endpoint:
  GET http://localhost:8000/api/graph/equipment/P-101
  Assert: Returns JSON with nodes array (length > 0) and links array

Step A5: Record results. If any check fails, note the error EXACTLY and fix it
before proceeding to the next task.

══════════════════════════════════════════════════
TASK B: ADD 5 ADDITIONAL TEST DOCUMENTS
══════════════════════════════════════════════════

Create these files in ./data/sample_docs/ as .txt files. Make the content
realistic, detailed, and technically accurate for an Indian industrial context.
Each file must be at least 400 words.

FILE 1: valve_register_unit3.txt
  A gate valve inspection register for Unit 3 of the plant.
  Include: 12 valves with tags (V-101 through V-112), type, size, rating,
  last inspection date, next due date, inspector name, condition (Good/Fair/Poor),
  any defects noted. At least 3 valves should show "PAST DUE" for inspection.
  Format: tabular with explanatory notes below each entry.

FILE 2: motor_electrical_log.txt
  Electrical maintenance log for motors in the pumping system.
  Include: Motor tags (M-101, M-102, M-201), insulation resistance readings (Megger test),
  winding temperature readings, vibration at bearing, current draw vs. nameplate,
  power factor, last predictive maintenance date.
  Note: M-101 (coupled to P-101) showing high winding temperature — potential connection
  to P-101's vibration issue.

FILE 3: water_treatment_procedure.txt
  Standard Operating Procedure for the plant's cooling water treatment system.
  Include: Purpose, scope, equipment list (CT-101 cooling tower, CWP-01 pump, chemical
  dosing pumps), step-by-step startup, normal operation monitoring (pH 7-8, conductivity
  <2500 µS/cm, TDS, Langelier Saturation Index), shutdown procedure, troubleshooting table.
  Reference OISD-116 for cooling system requirements.

FILE 4: annual_audit_findings_2024.txt
  Internal HSE Audit Report — Annual Audit 2024 findings.
  Include: Audit date, auditors, scope, findings in NCR (Non-Conformance Report) format.
  At least 6 findings:
  - NCR-2024-01: P-101 bearing inspection overdue (CRITICAL)
  - NCR-2024-02: V-201 corrosion not addressed from Q1 inspection (MAJOR)
  - NCR-2024-03: LOTO procedure not available at M-101 (MAJOR)
  - NCR-2024-04: Emergency shower test record missing for 2024 (MINOR)
  - NCR-2024-05: Contractor safety induction records incomplete (MINOR)
  - NCR-2024-06: Fire extinguisher at Pump Bay B expired (CRITICAL)
  Include target close dates and responsible persons.

FILE 5: lessons_learned_bulletin_2023.txt
  Lessons Learned Bulletin issued after multiple pump seal failures in 2023.
  Reference the 3 incidents (IR-2023-012, IR-2023-089, IR-2024-031 on pumps P-201, P-104, P-303).
  Include: Executive summary of pattern, root cause (dry running during startup),
  systemic fix (startup procedure updated), training requirement, verification method.
  This document should have explicit cross-references to other documents in the system.

After creating all 5 files, trigger reindexing:
  If the system has an admin route for this: POST http://localhost:8000/api/admin/reindex
  OR: restart the backend (it auto-indexes on startup)

Verify new stats: GET http://localhost:8000/api/stats → documents should now show 18.

Then run these 3 new validation queries:
  "What are the annual audit findings for 2024?" → should cite annual_audit_findings_2024.txt
  "What lessons were learned from pump seal failures?" → should cite lessons_learned_bulletin.txt
  "What NCRs are currently open?" → should list at least 6 items with NCR numbers

══════════════════════════════════════════════════
TASK C: COMPLETE DASHBOARD REDESIGN
══════════════════════════════════════════════════

Redesign frontend/src/pages/Dashboard.tsx and frontend/src/index.css following
the Industrial Intelligence Terminal design spec below. This is the highest
priority deliverable from a judging perspective.

DESIGN TOKENS — ADD TO frontend/src/index.css:
```css
:root {
  --bg-void:        #0A0C0F;
  --bg-surface:     #111419;
  --bg-elevated:    #1A1F27;
  --border-steel:   #252B35;
  --text-primary:   #E8EBF0;
  --text-secondary: #6B7890;
  --accent-teal:    #00D4B8;
  --status-safe:    #22C55E;
  --status-warn:    #F59E0B;
  --status-critical:#EF4444;
  --status-neutral: #3B82F6;
  --terminal-green: #4ADE80;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg-void);
  color: var(--text-primary);
  font-family: 'Inter', system-ui, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
```

Add Google Fonts to frontend/index.html <head>:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

DASHBOARD LAYOUT TO BUILD (Dashboard.tsx):

1. TOP BAR (sticky, height 56px):
   Left: A small hexagon SVG icon + "OPERATIONS BRAIN" in Space Grotesk weight 700
   Center: Facility name from stats API ("UNIT 3 — PROCESS PLANT")
   Right: 
     - A pulsing teal dot + "LIVE" label
     - "Last sync: {timestamp}" in secondary text
     - LLM badge: small chip showing "⚡ GEMINI 2.5" in teal border

2. KPI ROW (4 cards, full width):
   Each card is built identically with this structure:
   ```
   ┌──────────────────────────────────┐
   │ DO              +3 today ↑       │  ← system code + delta (right-aligned)
   │                                  │
   │        13                        │  ← Space Grotesk 64px, teal, counts up
   │                                  │
   │ Documents Indexed                │  ← Inter 12px, secondary color
   └──────────────────────────────────┘
   ```
   Cards: [Documents: DO] [Graph Nodes: GN] [Queries Today: QR] [Compliance: CM]
   System codes displayed in JetBrains Mono 11px uppercase secondary color.
   Left border: 2px solid var(--accent-teal) for all 4 cards.
   
   Implement number counting animation:
   - On component mount, use useEffect + setInterval
   - Count from 0 to target value over 1000ms
   - Use easeOut: value = target * (1 - Math.pow(1 - t/duration, 3))

3. MAIN CONTENT (two columns, 60/40 split):
   
   LEFT COLUMN (60%):
   
   A) Knowledge Graph Preview Panel:
      - Header: "KNOWLEDGE GRAPH" label + node/edge count badges
      - react-force-graph-2d component, height 300px
      - Dark background (--bg-void), nodes colored by type:
        Equipment=teal, Events=amber, Documents=blue, FailureModes=red
      - "View Full Graph →" link bottom right
      - On click of a node: show a small tooltip with entity name + type
   
   B) Equipment Status Grid:
      - Header: "EQUIPMENT STATUS" + "18 assets monitored" count
      - 3-column grid of equipment chips:
        Each chip:
        ```
        ┌───────────────────────────┐
        │ ● P-101  PUMP             │  ← status dot + tag + type
        │ Centrifugal | Unit-3      │  ← subtype + location
        │ 7 events  ▲ WARNING       │  ← event count + status label
        └───────────────────────────┘
        ```
        Status dot animation: for WARN/CRITICAL, use CSS @keyframes pulse
        Status derives from: if equipment has overdue inspection → WARN,
        if has open NCR marked CRITICAL → CRITICAL, else SAFE.
        
        Equipment list (hardcode for demo):
        P-101 (WARN), P-102 (SAFE), P-103 (SAFE),
        HX-301 (SAFE), HX-302 (SAFE),
        V-201 (CRITICAL), V-202 (SAFE),
        C-201 (SAFE), CT-101 (SAFE)

   RIGHT COLUMN (40%):
   
   A) Live Activity Feed (SIGNATURE ELEMENT):
      - Header: "SYSTEM LOG" in JetBrains Mono + blinking cursor "▌"
      - Dark panel (--bg-void border 1px --border-steel)
      - Height: 280px, overflow: hidden
      - Each log entry:
        ```
        [08:42:13] INDEXED  pump_p101_log.pdf        28 chunks
        ```
        Format: [timestamp] TYPE(fixed width) description right-align count
        Colors: timestamp=secondary, TYPE=teal/amber/red/blue based on type
        Types: INDEXED=teal, GRAPH=blue, QUERY=secondary, ALERT=amber/red
      - Simulate live entries: useEffect + setInterval, new entry every 4 seconds
      - New entries animate in from bottom (translateY from 20px, opacity 0→1, 200ms)
      - Feed auto-scrolls to bottom
      
      Initial entries to show (from real system state):
      Generate 8 fake-but-realistic entries using the actual document names in the system.
      Then add 2 new simulated entries every 4 seconds from a pool of realistic messages.
   
   B) Quick Query Panel:
      - Compact version of the chat interface
      - Single input bar: placeholder "Ask anything about your plant assets..."
      - On submit: POST /api/query → display response inline (truncated at 200 chars + "View full →")
      - Show the last 3 queries in a compact list below the input

4. BOTTOM STATUS BAR (full width, 40px):
   Left: "Operations Brain v1.0 — ET AI Hackathon 2026"
   Right: DB icons with status indicators (ChromaDB: ●OK, Graph: ●OK, SQLite: ●OK)
   All in secondary text color, 11px JetBrains Mono

CRITICAL IMPLEMENTATION NOTES FOR DASHBOARD:
- Do NOT use Tailwind classes for colours — use CSS variables throughout
- Do NOT use any white backgrounds anywhere on the page
- Ensure the page looks correct at 1366×768 (laptop), 1920×1080 (desktop), and 375px (mobile)
- On mobile: collapse to single column, stack KPI cards 2×2
- All fetch calls to backend: use proper error handling + loading skeleton states
  Loading skeleton: grey shimmer (--bg-elevated background, animated gradient)
- The page must render correctly even if the backend is offline (show "Offline" state gracefully)

══════════════════════════════════════════════════
TASK D: APPLY CONSISTENT DARK THEME TO ALL 6 PAGES
══════════════════════════════════════════════════

After the Dashboard is done, apply the same design language to the remaining 5 pages.
Do NOT redesign their functionality — only update their visual appearance.

For each page (Copilot, KnowledgeGraph, Documents, Maintenance, Compliance):

1. Remove any white/light backgrounds — all surfaces use CSS variables
2. Update card backgrounds to var(--bg-surface) with border var(--border-steel)
3. Update all input fields:
   background: var(--bg-elevated)
   border: 1px solid var(--border-steel)
   color: var(--text-primary)
   On focus: border-color: var(--accent-teal)
4. Update buttons:
   Primary: background var(--accent-teal), color var(--bg-void), font-weight 600
   Secondary: border 1px solid var(--border-steel), color var(--text-primary)
5. Update all headings to use Space Grotesk
6. Update the navigation sidebar to match: dark background, icon-only at < 1200px width

Specific page additions:

COPILOT PAGE:
- Chat messages from user: right-aligned, background var(--bg-elevated)
- Chat messages from AI: left-aligned, background var(--bg-surface) with 2px teal left border
- Citation chips: small pills with var(--accent-teal) border and secondary background
- Streaming text: add a blinking cursor ▌ at the end while streaming

KNOWLEDGE GRAPH PAGE:
- Full-height graph (calc(100vh - 120px))
- Left panel for filters (node type checkboxes, date range)
- Right panel slides in when node is clicked (entity details + linked documents)
- Graph background must be var(--bg-void)

DOCUMENTS PAGE:
- File upload zone: dashed border var(--accent-teal), dark background, large upload icon
- Document cards: dark cards in a responsive grid
- Status badges: "Indexed" = teal, "Processing" = amber pulse, "Failed" = red

MAINTENANCE PAGE:
- RCA output styled as a structured report with sections and severity badges
- Probable causes shown as a ranked bar chart (CSS bars, no library needed)

COMPLIANCE PAGE:
- Compliance matrix: table with RED/AMBER/GREEN status cells
- Status cells use the status color variables with 20% opacity background

══════════════════════════════════════════════════
EXECUTION ORDER:
══════════════════════════════════════════════════

1. Run Task A first (validation). Fix any bugs found before proceeding.
2. Run Task B (add 5 documents). Verify new stats.
3. Run Task C (redesign Dashboard.tsx). Get it looking correct before touching other pages.
4. Run Task D (theme remaining pages).
5. Final check: run the full validation checklist again on the completed system.
6. Take screenshots of every page and save them to ./screenshots/ for the demo video.

IMPORTANT CONSTRAINTS:
- Keep the virtual environment single: .\venv\ — do not create additional environments
- Do not change the backend logic, only fix bugs found in Task A
- The backend API contract must not change (don't rename or remove routes)
- All new frontend code must be TypeScript (not JavaScript)
- Do not add new npm packages without explicit reason — use what is installed
- After Task C, do a Lighthouse audit in Chrome DevTools: Performance must be > 80
- Test on Chrome and Edge — do not require Firefox-specific fixes

WHEN YOU ARE DONE:
Report back with:
1. List of validation checks that passed / failed and what you fixed
2. List of 5 new document files created with their final word counts
3. Screenshot of the new Dashboard
4. Any bugs or gaps you found that were outside the scope of this task
```

---

## PART 6 — PROFESSIONAL HONESTY ASSESSMENT
### What the Team Would Say in a Closed-Door Review

---

**What's genuinely strong:**
- The architecture decision to use hybrid Graph-RAG is correct and differentiating. Most teams will build pure vector RAG. The knowledge graph is the moat.
- Gemini 2.5 Flash is the right model choice — lowest latency, strong context window, good citation-following behaviour.
- 13 documents with interconnected data telling one coherent story (P-101) is exactly the right demo strategy.
- The 3-agent structure (Copilot / Maintenance / Compliance) maps cleanly to real industrial user roles.

**What's risky right now:**
- The dashboard UX will lose points with judges. First impressions matter and "looks like a template" is the death sentence in hackathon judging.
- The entity extraction quality is untested against adversarial inputs (non-standard equipment tag formats, multi-language documents, tables with merged cells). If a judge uploads something unexpected, it may fail silently.
- Session/conversation history handling in the chat: if the follow-up query test (Checklist item #19) fails, it breaks the "intelligent" narrative.
- The compliance agent's answers need to be pre-computed or very fast — a 12-second wait while it reasons about OISD-116 in a live demo is a presentation killer.

**What to do in the next 48 hours:**
1. Dashboard redesign (highest visual return on time invested)
2. Add the 5 new test documents to make the knowledge base denser
3. Pre-test the demo script at least 3 times end-to-end, noting which queries give the best answers
4. Record the demo video at 1920×1080, show both desktop and mobile views
5. Prepare 3 backup "golden" queries that you know give excellent responses, for when live demos go wrong
```
