# SyllabusSync AI 🎓⚡

> **Personalized Course Roadmap & Adaptive Video Study Assistant**  
> Turn university course syllabi into an actionable, daily study schedule powered by real educational YouTube video lectures, AI topic hierarchy extraction, and exam deadline awareness.

---

## 1. Phase 1 Overview: Project Foundation

This repository contains **Phase 1** of **SyllabusSync AI**, built for the Strands hackathon. Phase 1 establishes the production-grade foundation:

- **Full-Stack Architecture**: React 19 + TypeScript + Vite frontend with Tailwind CSS styling, coupled with a Python + FastAPI backend service.
- **Syllabus Parsing Engine**: In-memory parsing for both digital **PDF** and **DOCX** files with file extension/MIME verification, 10 MB size limits, and scanned/image-only document detection (explicitly noting that OCR is not performed).
- **Modern Student Learning Dashboard**: Dark navy / indigo theme, responsive sidebar navigation (laptop & mobile drawer), health monitoring badge, empty states with clear labeling (no fake statistics or fabricated data), and preview inspection of extracted syllabus text.
- **Database Schema Ready**: SQLite database models configured for syllabus metadata, topics, and study plan sessions.
- **Strands Agents Extension Points**: Cleanly isolated agent module ready for Phase 2 Strands Agents SDK integration.

---

## 2. Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, TypeScript, Vite 8, Tailwind CSS v4, Lucide React |
| **Backend** | Python 3.13, FastAPI, Uvicorn, Pydantic v2, Pydantic-Settings |
| **Parsing** | `pypdf` (digital text extraction), `python-docx` (Word paragraph & table extraction) |
| **Database** | SQLite (MVP local persistence) |
| **Testing** | `pytest`, `httpx`, `fastapi.testclient` |
| **AI Agents** | Extension point for Strands Agents SDK (Phase 2) |
| **Video Discovery** | Extension point for YouTube Data API v3 (Phase 3) |

---

## 3. Project Structure

```text
SyllabusSync-AI/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.tsx           # Page header, mobile toggle, status indicator
│   │   │   └── Sidebar.tsx          # Responsive navigation & API connectivity badge
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx    # Welcome banner, action CTA, overview cards
│   │   │   ├── SyllabusPage.tsx     # Drag-and-drop upload, validation, text preview
│   │   │   ├── StudyPlanPage.tsx    # Empty state & roadmap blueprint
│   │   │   ├── ProgressPage.tsx     # Zero-state mastery & streak tracking
│   │   │   └── SettingsPage.tsx     # Configuration & Phase roadmap tracker
│   │   ├── services/
│   │   │   └── api.ts               # REST client for /api/health and /api/syllabus/upload
│   │   ├── types/
│   │   │   └── index.ts             # Shared TypeScript models
│   │   ├── App.tsx                  # Main application shell & tab routing
│   │   ├── index.css                # Tailwind CSS styling & custom scrollbars
│   │   └── main.tsx                 # React entry point
│   ├── vite.config.ts               # Vite configuration with Tailwind & /api proxy
│   ├── package.json
│   └── tsconfig.json
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py          # API router aggregation
│   │   │   ├── health.py            # GET /api/health endpoint
│   │   │   └── syllabus.py          # POST /api/syllabus/upload endpoint
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py            # Pydantic Settings & environment variables
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── syllabus_parser.py   # PDF & DOCX text extraction & validation service
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── database.py          # SQLite schema initialization & connection context
│   │   │   └── syllabus.py          # Data classes for persistent records
│   │   ├── schemas/
│   │   │   ├── health.py            # Health check Pydantic schemas
│   │   │   └── syllabus.py          # Upload response schemas
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   └── syllabus_analyzer.py # Phase 2 Strands Agents SDK extension stub
│   │   └── main.py                  # FastAPI app factory, CORS, and error handlers
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_health.py           # Health check and root endpoint tests
│   │   └── test_syllabus_upload.py  # 7 validation & extraction test scenarios
│   ├── requirements.txt             # Pinned backend dependencies
│   ├── .env.example                 # Configuration template
│   └── syllabus_sync.db             # Local SQLite database (gitignored)
├── .gitignore
└── README.md
```

---

## 4. Setup & Running Instructions

### Prerequisites
- **Node.js**: v18+ (tested on Node v24)
- **Python**: 3.10+ (tested on Python 3.13)

### 4.1 Backend Setup

1. Open a terminal in the project directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```powershell
   # Windows PowerShell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   ```bash
   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

4. Create your `.env` file (optional for Phase 1 development, defaults work out-of-the-box):
   ```bash
   cp .env.example .env
   ```

5. Start the backend development server:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

The backend is accessible at:
- **API Base**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
- **Health Check**: `http://127.0.0.1:8000/api/health`

### 4.2 Frontend Setup

1. Open a second terminal window in the project root:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```

4. Open your browser at **`http://localhost:5173`**. The Vite dev server proxies all `/api/*` calls automatically to the backend on port 8000.

---

## 5. Running Tests & Verifications

### 5.1 Backend Pytest Suite
Run the comprehensive test suite covering health checks, valid PDF parsing, valid DOCX parsing, empty files, scanned PDFs, unsupported formats, and oversized uploads:

```bash
cd backend
.\.venv\Scripts\pytest -v
```

**Results:**
```text
tests/test_health.py::test_health_check_endpoint PASSED           [ 11%]
tests/test_health.py::test_root_endpoint PASSED                   [ 22%]
tests/test_syllabus_upload.py::test_upload_valid_docx PASSED      [ 33%]
tests/test_syllabus_upload.py::test_upload_valid_pdf PASSED       [ 44%]
tests/test_syllabus_upload.py::test_upload_unsupported_file_extension PASSED [ 55%]
tests/test_syllabus_upload.py::test_upload_empty_file PASSED      [ 66%]
tests/test_syllabus_upload.py::test_upload_blank_scanned_pdf PASSED [ 77%]
tests/test_syllabus_upload.py::test_upload_empty_docx PASSED      [ 88%]
tests/test_syllabus_upload.py::test_upload_oversized_file PASSED  [100%]
======================== 9 passed in 1.01s ========================
```

### 5.2 Frontend Production Build Check
Verify TypeScript compilation and Vite bundling:

```bash
cd frontend
npm run build
```

**Results:**
```text
✓ 2037 modules transformed.
✓ built in 595ms with 0 errors.
```

---

## 6. API Reference

### `GET /api/health`
Returns system health, version, and deployment environment.
```json
{
  "status": "healthy",
  "app_name": "SyllabusSync AI API",
  "version": "0.1.0",
  "timestamp": "2026-10-29T18:41:49.634910Z",
  "environment": "development"
}
```

### `POST /api/syllabus/upload`
Accepts `multipart/form-data` with key `file` (`.pdf` or `.docx`).
- **Enforced Constraints**:
  - Maximum size: 10 MB.
  - Allowed extensions: `.pdf`, `.docx`.
  - Scanned PDF detection: Returns HTTP 400 with actionable feedback if no digital text is found.
- **Successful Response (200 OK)**:
```json
{
  "status": "success",
  "filename": "cs301_syllabus.docx",
  "file_type": "docx",
  "file_size_bytes": 36711,
  "char_count": 145,
  "word_count": 22,
  "unit_count": 3,
  "unit_label": "paragraphs & table rows",
  "preview_text": "CS 301: Database Systems\n\nInstructor: Dr. Connor...\n\nWeek 1: Relational Algebra...",
  "full_text_length": 145,
  "extraction_notes": "Extracted 3 text paragraph(s)",
  "message": "Syllabus 'cs301_syllabus.docx' parsed successfully (22 words)."
}
```

---

## 7. Security & Configuration Guardrails

- **Zero Client-Side Secrets**: No API keys or tokens are present in frontend code.
- **In-Memory Document Handling**: Uploaded syllabus documents are parsed in-memory using byte buffers and discarded; no sensitive student files remain on disk.
- **Path Protection**: Server exceptions sanitize filesystem paths and internal tracebacks from API error responses.
- **Clean Configuration**: Environment variables loaded strictly through `pydantic-settings` via `backend/.env`.

---

## 8. Next Step: Phase 2 Roadmap

The exact next step for **Phase 2** is:
> **Extracting syllabus text into an editable, structured topic list using the Strands Agents SDK.**

This includes:
1. Connecting the `SyllabusAnalyzerAgentStub` (`backend/app/agents/syllabus_analyzer.py`) to the Strands Agents SDK.
2. Prompting/orchestrating the agent to break down extracted syllabus text into course metadata, modules, and discrete testable topics with estimated study hours.
3. Implementing the UI topic review interface where students can inspect, reorder, delete, or add topics before initiating video discovery.
