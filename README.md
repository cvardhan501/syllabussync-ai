# SyllabusSync AI 🎓⚡

> **Personalized Course Roadmap & Adaptive Video Study Assistant**  
> Turn university course syllabi into an actionable, daily study schedule powered by real educational YouTube video lectures, AI topic hierarchy extraction, and exam deadline awareness.

---

## 1. Project Overview & Progress

SyllabusSync AI is an AI-guided student study roadmap platform built with **React 19 + TypeScript + Vite**, **Tailwind CSS v4**, **FastAPI**, and the **Strands Agents SDK**.

- **Phase 1: Project Foundation (Completed)**
  - Full-stack repository scaffolding and Dark navy/indigo learning dashboard.
  - In-memory PDF (`pypdf`) and Word DOCX (`python-docx`) parsing and validation engine.
  - Scanned PDF detection (explicitly noting OCR is not performed), 10 MB size limits, clean service layer.
  - Initial SQLite database schema and health monitoring.
- **Phase 2: Strands-Powered Syllabus Analyzer (Completed)**
  - Integrated the official **Strands Agents SDK** (`strands-agents`) with multi-provider model routing (Amazon Bedrock by default, OpenAI, Anthropic).
  - Implemented `SyllabusAnalyzerAgent` in `backend/app/agents/syllabus_analyzer.py` returning structured JSON schemas for courses, modules, discrete topics, study minutes, difficulty levels, prerequisites, and ambiguous sections.
  - Strict security guardrails: document contents wrapped in `<UNTRUSTED_SYLLABUS_DOCUMENT>` tags to prevent prompt injection.
  - Transparent development fallback mode: deterministic rule-based analysis for local offline testing when live API keys are not configured.
  - Relational persistence in SQLite (`syllabi`, `modules`, `topics`) with transactional atomic updates.
  - Interactive Topic Hierarchy Editor in the UI: inline editing of course & topic titles, reordering, adding/deleting modules and topics with confirmation, and saving changes to the backend.
- **Phase 3: YouTube Resource Discovery & Topic Matching (Next)**
  - YouTube Data API v3 search with channel consistency (1 primary channel first, max 2 complementary channels).
- **Phase 4: Adaptive Daily Planner & Exam Readiness (Planned)**
  - Dynamic rescheduling after missed study sessions, exam deadline feasibility warnings, and topic mastery tracking.

---

## 2. Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, TypeScript, Vite 8, Tailwind CSS v4, Lucide React |
| **Backend** | Python 3.13, FastAPI, Uvicorn, Pydantic v2, Pydantic-Settings |
| **AI Agent Framework** | **Strands Agents SDK** (`strands-agents>=1.62.0`) |
| **Document Parsing** | `pypdf` (digital text extraction), `python-docx` (Word paragraph & table extraction) |
| **Database** | SQLite (persistent local storage for syllabi, modules, and topics) |
| **Testing** | `pytest`, `httpx`, `fastapi.testclient` (19 automated tests) |

---

## 3. Strands Model Configuration & Environment Variables

Strands is provider-agnostic. Configure your provider and credentials in `backend/.env` (see `backend/.env.example`):

### Option A: Amazon Bedrock (Strands Default)
```env
STRANDS_PROVIDER=bedrock
STRANDS_MODEL=bedrock/us.anthropic.claude-3-5-sonnet-20241022-v2:0
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=us-east-1
# AWS_SESSION_TOKEN=your_token_if_using_temporary_credentials
```

### Option B: OpenAI Direct
```env
STRANDS_PROVIDER=openai
STRANDS_MODEL=openai/gpt-4o-mini
OPENAI_API_KEY=your_openai_api_key
```

### Option C: Anthropic Direct
```env
STRANDS_PROVIDER=anthropic
STRANDS_MODEL=anthropic/claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### Development Fallback Mode (No Paid API Keys Required)
```env
ALLOW_DEV_FALLBACK_ANALYSIS=true
```
When live model credentials are not configured, SyllabusSync AI runs a deterministic, rule-based extraction analyzer that accurately structures headings, modules, and topics from the uploaded document. The UI displays an explicit `Dev Fallback Mode` indicator for full transparency.

---

## 4. API Reference

### Core Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Uptime check, version (`0.2.0`), and environment status. |
| `POST` | `/api/syllabus/upload` | Upload and validate PDF or DOCX file (up to 10 MB). Extracts digital text and returns metrics. |
| `POST` | `/api/syllabus/analyze` | Accepts uploaded PDF/DOCX or an existing `syllabus_id`. Strands Agent extracts modules, topics, study times, difficulty, and prerequisites. Persists hierarchy in SQLite. |
| `GET` | `/api/syllabus/{id}` | Retrieves saved syllabus record and normalized module/topic hierarchy. |
| `PUT` | `/api/syllabus/{id}/topics` | Atomically updates student-edited modules, topics, and titles. |

---

## 5. Running the Application

### 5.1 Backend
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Base: `http://127.0.0.1:8000`
- Swagger Docs: `http://127.0.0.1:8000/docs`

### 5.2 Frontend
```powershell
cd frontend
npm run dev
```
- Available at `http://localhost:5173` (with automatic `/api` proxying to FastAPI).

---

## 6. Verification & Test Suite

### 6.1 Backend Tests
Run the 19 automated tests covering health checks, parsing validation, empty documents, scanned PDFs, oversized uploads, Strands mock calls, malformed model output handling, missing credential handling, and database updates:

```powershell
cd backend
.\.venv\Scripts\pytest -v
```

**Results:**
```text
tests/test_health.py::test_health_check_endpoint PASSED           [  5%]
tests/test_health.py::test_root_endpoint PASSED                   [ 10%]
tests/test_syllabus_analysis.py::test_analyze_syllabus_with_file_dev_fallback PASSED [ 15%]
tests/test_syllabus_analysis.py::test_analyze_empty_syllabus_rejects PASSED [ 21%]
tests/test_syllabus_analysis.py::test_analyze_missing_input_rejects PASSED [ 26%]
tests/test_syllabus_analysis.py::test_analyze_nonexistent_syllabus_id_returns_404 PASSED [ 31%]
tests/test_syllabus_analysis.py::test_credentials_missing_and_fallback_disabled_returns_503 PASSED [ 36%]
tests/test_syllabus_analysis.py::test_mocked_strands_agent_call PASSED   [ 42%]
tests/test_syllabus_analysis.py::test_malformed_model_output_handling PASSED [ 47%]
tests/test_syllabus_analysis.py::test_get_and_put_syllabus_topics PASSED [ 52%]
tests/test_syllabus_analysis.py::test_put_empty_modules_fails PASSED     [ 57%]
tests/test_syllabus_analysis.py::test_put_nonexistent_syllabus_returns_404 PASSED [ 63%]
tests/test_syllabus_upload.py::test_upload_valid_docx PASSED             [ 68%]
tests/test_syllabus_upload.py::test_upload_valid_pdf PASSED              [ 73%]
tests/test_syllabus_upload.py::test_upload_unsupported_file_extension PASSED [ 78%]
tests/test_syllabus_upload.py::test_upload_empty_file PASSED             [ 84%]
tests/test_syllabus_upload.py::test_upload_blank_scanned_pdf PASSED      [ 89%]
tests/test_syllabus_upload.py::test_upload_empty_docx PASSED             [ 94%]
tests/test_syllabus_upload.py::test_upload_oversized_file PASSED         [100%]
============================= 19 passed in 2.39s ==============================
```

### 6.2 Frontend Production Build
```powershell
cd frontend
npm run build
```
**Results:**
```text
✓ 2038 modules transformed.
✓ built in 654ms with 0 errors.
```

---

## 7. Next Step: Phase 3

> **Phase 3: Real YouTube Resource Discovery and Topic Matching.**
- Implement YouTube Data API v3 search agent for each topic.
- Channel selection policy: try 1 primary channel first, then up to 2 complementary channels, asking the student before selecting a 3rd.
- Topic-to-video coverage verification and playlist preview.
