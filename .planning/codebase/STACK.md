# Technology Stack

**Analysis Date:** 2026-09-16

## Languages

**Primary:**
- **Python 3.12** — All backend application services, document geometry algorithms, AST parsing, REST API routes, deterministic scoring models, and PDF/DOCX generation in `backend/app/`.
- **TypeScript 5.x / 6.0** — All frontend UI components, state stores, router setups, typed API clients, and React 19 pages in `frontend/src/`.

**Secondary:**
- **CSS / Vanilla CSS** — Custom styling, design tokens, card physics, and micro-animations.
- **PowerShell / Bash** — Local development scripts, background service management, and test runners.

---

## Runtime

**Environment:**
- **Python Runtime:** CPython 3.12 (Virtualenv at `backend/.venv`)
- **Frontend Runtime:** Node.js 20+ (ES Modules, `type: module`)
- **Local Database:** MongoDB Community Server 8.3 (WiredTiger Storage Engine)

**Package Managers:**
- **Backend:** `pip` / virtualenv with pinned `backend/requirements.txt`
- **Frontend:** `npm` with `frontend/package.json` and `frontend/package-lock.json`

---

## Frameworks

**Core:**
- **FastAPI 0.115.0** (`backend/requirements.txt`) — High-throughput asynchronous REST API web framework with Pydantic v2 data models and OpenAPI documentation.
- **Uvicorn 0.30.6** (`backend/requirements.txt`) — ASGI server implementation for FastAPI with standard event loop and reload support.
- **React 19.2.8** (`frontend/package.json`) — Frontend view library with component architecture, hooks, and Concurrent Mode rendering.
- **React Router DOM 7.18.2** (`frontend/package.json`) — Client-side SPA routing, dynamic route parameters, and protected layout wrappers.

**Testing:**
- **Pytest 8.3.3** (`backend/requirements.txt`) — Test runner for unit, integration, security, and lifecycle test suites.
- **pytest-asyncio 0.24.0** (`backend/requirements.txt`) — Asynchronous fixture and coroutine test execution.
- **mongomock-motor 0.0.34** (`backend/requirements.txt`) — In-memory async MongoDB mock for isolated provider and route unit tests.

**Build / Dev Tools:**
- **Vite 8.2.0** (`frontend/package.json`) — Next-generation frontend build tool, HMR dev server, and Rollup bundler.
- **Tailwind CSS 4.3.3 & @tailwindcss/vite 4.3.3** (`frontend/package.json`) — Utility-first styling framework with Vite compiler integration.
- **Oxlint 1.75.0** (`frontend/package.json`) — High-performance JavaScript/TypeScript linter.
- **Pyright** (`pyrightconfig.json`) — Static type checking configuration for backend Python source.

---

## Key Dependencies

**Critical Application Dependencies:**
- **Pydantic 2.9.2 & pydantic-settings 2.5.2** — Runtime data validation, strict schema serialization, and type-safe environment configuration (`app.core.config.Settings`).
- **Motor 3.6.0** — Official async Python driver for MongoDB built on PyMongo and Tornado/asyncio event loop.
- **PyMuPDF (fitz) 1.24.10** — Low-level PDF geometry extraction, coordinate-preserving text blocks, bounding box calculations, and font size metadata.
- **python-docx 1.1.2** — Word DOCX document generation and manipulation.
- **ReportLab 4.2.2** — Low-level PDF generation canvas, Flowable layout engine, and vertical line-budget enforcement for 1-page resumes.
- **spacy 3.7.5 & sentence-transformers 3.1.1** — Natural language entity recognition, linguistic tokenization, and semantic embeddings for role similarity.
- **HTTPX 0.27.2** — Asynchronous HTTP client for live ATS job provider integrations (`SmartRecruiters`, `Lever`, `Greenhouse`, `Ashby`).
- **python-jose[cryptography] 3.3.0 & bcrypt 4.2.0** — JWT token issuance, verification, and cryptographic password hashing.

**Frontend UI Dependencies:**
- **@tanstack/react-query 5.101.4** — Asynchronous server-state management, cache invalidation, and data fetching hooks.
- **Axios 1.19.0** — HTTP client with centralized interceptors for Bearer token injection and error handling (`frontend/src/lib/api.ts`).
- **Lucide React 1.32.0** — SVG icon library.
- **Recharts 3.10.1** — Responsive SVG charting for candidate dashboard and match score analytics.

---

## Configuration

**Backend Configuration:**
- **File:** `backend/.env` (Loaded via `pydantic-settings` in `app/core/config.py`)
- **Key Parameters:**
  - `MONGO_URI` / `MONGO_DB_NAME` — MongoDB connection string and database selector (`roleradar`).
  - `JWT_SECRET` / `JWT_ALGORITHM` / `ACCESS_TOKEN_EXPIRE_MINUTES` — Auth credentials and session durations.
  - `CORS_ORIGINS` — Allowed frontend origins (e.g., `http://localhost:5173`, `http://127.0.0.1:5173`).
  - `AI_PROVIDER` / `AI_MODEL` — Configured AI provider strategy (Ollama / LM Studio / Cloud fallback).
  - Provider configs: `GREENHOUSE_API_KEY`, `LEVER_API_KEY`, `SMARTRECRUITERS_CLIENT_ID`, `ASHBY_COMPANY_BOARDS`.

**Frontend Configuration:**
- **Vite Config:** `frontend/vite.config.ts` — React plugin, Tailwind integration, dev server port (5173), and proxy settings.
- **TypeScript Config:** `frontend/tsconfig.json` & `frontend/tsconfig.app.json`.
