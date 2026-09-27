# System Architecture

**Analysis Date:** 2026-09-16

## Overview

RoleRadar is an enterprise AI resume intelligence and career copilot platform. It bridges the gap between candidate resumes and Applicant Tracking Systems (Workday, Taleo, Greenhouse) using geometric document extraction, semantic entity structuring, strict 8-tier evidence ledger verification, and candidate-grounded tailoring.

---

## Pattern & Style

- **Modular Domain Architecture:** The backend (`backend/app/modules/`) is cleanly segmented into self-contained domain modules (`resume`, `jobs`, `matching`, `tailoring`, `learning`, `applications`, `interview`, `chatbot`, `auth`, `profile`). Each module encapsulates its own routes, business services, database repositories, and Pydantic schemas.
- **Asynchronous Non-Blocking I/O:** The entire backend runs asynchronously on Python 3.12 with FastAPI and Motor (async MongoDB), ensuring high concurrency without thread pool starvation.
- **Deterministic Truth Guarding:** Rather than delegating critical matching and tailoring decisions entirely to an LLM, RoleRadar uses deterministic rule engines (5-gate geometry, 8-tier evidence matcher, vertical line budgeting) to ensure 0% hallucination and verifiable provenance.
- **Decoupled Synchronization:** Read-heavy user traffic (`GET /api/jobs`, `GET /api/matches`) reads indexed MongoDB data directly. ATS external crawling and synchronization (`POST /api/jobs/sync`) is isolated and throttled.

---

## Layers & Boundaries

```
┌────────────────────────────────────────────────────────┐
│               Frontend Presentation Layer              │
│       React 19 Components • Pages • React Query Hooks  │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP JSON / Bearer Auth
                            ▼
┌────────────────────────────────────────────────────────┐
│                   API Routing Layer                    │
│      FastAPI APIRouter • Security & Rate Limiting      │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                 Domain Services Layer                  │
│  • Resume Service: 5-Gate Geometry & Entity Structuring│
│  • Jobs Service: ATS Crawlers, URL Validation, Dedupe │
│  • Matching Service: 3-Tier Scoring & WhyScore Modal   │
│  • Tailoring Service: 8-Tier Evidence Ledger & Budget  │
│  • Learning Service: 61 Canonical Profiles & Taxonomy  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                Data Repositories Layer                 │
│      Async MongoDB Queries • Projections • Aggregates  │
└────────────────────────────────────────────────────────┘
```

### Module Boundaries:
- `app/modules/resume/`:
  - `geometry/`: Low-level PDF block analysis, column detection, and bounding boxes.
  - `semantic_parser.py`: Section recognition, WorkExperience, Projects, Education, Skills extraction, and `EvidenceLedger` creation.
- `app/modules/jobs/`:
  - `ashby_provider.py`, `lever_provider.py`, `greenhouse_provider.py`, `smartrecruiters_provider.py`: ATS scrapers/adapters.
  - `url_classifier.py`: Validates direct application links and rejects non-direct portals.
  - `jd_parser.py`: Semantic JD section zoning, must-have skills, preferred skills, tenure extraction.
- `app/modules/matching/`:
  - Evaluates candidate `EvidenceLedger` against target opportunity requirements using deterministic weightings (50% skills, 30% title, 20% experience).
- `app/modules/tailoring/`:
  - `evidence_matcher.py`: 8-tier evidence ledger matching.
  - `truth_guard.py`: Constrains LLM tailoring to candidate source evidence units.
  - `budget_engine.py`: Computes character/line density for 1-page vertical fit.
  - `pdf_generator.py` & `docx_generator.py`: Pixel-precise document export (`harvard`, `stanford`, `modern`, `classic`).
- `app/modules/learning/`:
  - `role_taxonomy.py`: Authoritative 61 canonical role profiles, aliases, competencies, and discriminative role resolution.

---

## Data Flow

### 1. Resume Ingestion Flow
```
PDF/DOCX Upload 
  ──► PyMuPDF Geometry Engine (Column Detection & Coordinate Bounding)
  ──► NormalizedDocument (Ordered Layout Blocks)
  ──► Semantic Entity Parser (Experience, Projects, Education, Skills)
  ──► Atomic Evidence Ledger (Tagged verifiable units)
  ──► Stored in MongoDB `resumes` Collection
```

### 2. Opportunity Ingestion Flow
```
ATS External Provider (Ashby, Lever, Greenhouse, SmartRecruiters)
  ──► Provider Normalizer (Opportunity model)
  ──► Location Normalizer (Country, State, City verification)
  ──► Compensation Extractor (LPA, Stipend, Disclosed)
  ──► URL Classifier (Direct Requisition HTTPS check)
  ──► Role Taxonomy Resolver (Canonical Role mapping)
  ──► Deduplication Engine (Multi-board requisition matching)
  ──► Upserted to MongoDB `jobs` Collection
```

### 3. Resume Tailoring Flow
```
Candidate Resume + Target Job 
  ──► JD Parser (Extract must-have/preferred requirements & tenure)
  ──► 8-Tier Evidence Matcher (Map candidate units to requirements)
  ──► Truth Guard (LLM rephrasing grounded strictly in evidence units)
  ──► 1-Page Vertical Budget Engine (Compute line count & font scale)
  ──► ReportLab / DOCX Renderer (Generate final document)
  ──► Stored in MongoDB `tailored_resumes` Collection
```

---

## Key Abstractions

- `NormalizedDocument` (`app/modules/resume/geometry/models.py`) — Canonical geometric representation of a document containing ordered `LayoutBlock` items with absolute bounding box coordinates.
- `EvidenceLedger` & `EvidenceUnit` (`app/modules/resume/models.py`) — Fine-grained candidate claims with source section, entity ID, normalized text, and extracted tech tokens.
- `RoleCompetencyProfile` (`app/modules/learning/role_taxonomy.py`) — Authoritative career identity containing canonical title, domain, aliases, core competencies, tools, and typical responsibilities.
- `Opportunity` (`app/modules/jobs/schemas.py`) — Normalized job/internship model across all providers with verification status and direct apply metadata.
- `TailoringPlan` & `TailoredResume` (`app/modules/tailoring/schemas.py`) — Grounded bullet point rewrites, skill adjustments, and template configuration.

---

## Entry Points

- **Backend Entry Point:** `backend/app/main.py`
  - Function: `create_app() -> FastAPI`
  - Lifespan context initializes Mongo connection, ensures indexes, and verifies demo user.
  - Route mounting: prefixes all modular routers under `/api`.
- **Frontend Entry Point:** `frontend/src/main.tsx` & `frontend/src/App.tsx`
  - Boots React 19 app, sets up React Query provider, AuthContext, and React Router routes.
