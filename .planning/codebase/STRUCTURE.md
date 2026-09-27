# Directory Structure

**Analysis Date:** 2026-09-16

## Overview

RoleRadar is organized as a monorepo containing a FastAPI backend, a React Vite frontend, automated test suites, architectural documentation, and temporary development scratch tools.

---

## Root Layout

```
c:\VINAY\roleradar\
├── .agent/              # GSD skills, workflows, references, and tool manifests
├── .planning/           # GSD project state, codebase maps, roadmaps, and requirements
│   └── codebase/        # Mapped codebase documentation (STACK, ARCHITECTURE, etc.)
├── backend/             # FastAPI backend application, tests, and storage
│   ├── app/             # Application source code
│   ├── tests/           # Comprehensive Pytest test suite (110 test files)
│   ├── storage/         # Local file storage (uploads, generated resumes)
│   └── requirements.txt # Pinned Python dependencies
├── frontend/            # React 19 + TypeScript + Vite frontend
│   ├── src/             # Frontend source code (pages, components, context, lib)
│   ├── public/          # Static assets and favicon
│   └── package.json     # Node.js dependencies and scripts
├── docs/                # Architectural reports and operational documentation
├── scratch/             # Scratch benchmarking scripts, audits, and local MongoDB data
├── README.md            # Comprehensive project introduction and technical decisions
├── ats_audit_report.md  # ATS algorithm verification report
└── docker-compose.yml   # Multi-service container orchestration config
```

---

## Key Locations

### Backend Architecture (`backend/app/`)
- `app/main.py` — Application factory (`create_app`), security middleware, route registration, and SPA serving.
- `app/core/` — Infrastructure configurations:
  - `config.py` — Pydantic Settings model, environment variables, provider keys.
  - `security.py` — Cryptographic helpers (BCrypt hashing, JWT token generation/decoding).
  - `rate_limit.py` — In-memory rate limiting dependency for sensitive routes.
- `app/db/` — Database layer:
  - `mongo.py` — Motor client lifecycle, connection pooling, and collection index creation.
- `app/modules/` — Domain-driven feature modules:
  - `auth/` — User authentication, registration, token verification, dependencies.
  - `profile/` — Candidate profile management, targets, preferences.
  - `resume/` — PDF reading order geometry (`geometry/`), section parsing, and `EvidenceLedger`.
  - `jobs/` — Job discovery, ATS provider adapters (`ashby`, `lever`, `greenhouse`, `smartrecruiters`), URL classifier, and compensation extractor.
  - `matching/` — Deterministic 3-tier matching engine and WhyScore breakdown.
  - `tailoring/` — Evidence ledger mapping, Truth Guard grounded bullet rewrites, 1-page budget calculation, PDF/DOCX generators.
  - `learning/` — 61 canonical role profiles, aliases, and skills roadmap generation.
  - `applications/` — Job application lifecycle and Kanban status CRM.
  - `interview/` — Discipline-specific top 20 interview banks, STAR coaching, interactive timer.
  - `chatbot/` — Career Copilot conversation engine.
- `backend/tests/` — Automated test suite with 110 test modules covering all phases.

### Frontend Architecture (`frontend/src/`)
- `src/App.tsx` — Main application component, layout wrapper, router configuration.
- `src/main.tsx` — React 19 root DOM render entry point.
- `src/pages/` — Route-level views:
  - `Dashboard.tsx` — Candidate overview, metrics, resume score, application stats.
  - `Copilot.tsx` — Interactive Career Copilot assistant.
  - `opportunities/` — Job/internship search, filters, and detailed score breakdown.
  - `resume/` — Resume upload, entity review, and JD-targeted tailoring studio.
  - `growth/` — Interview preparation, roadmap, and learning tools.
  - `auth/` — Login, registration, and demo access.
- `src/components/` — Reusable UI building blocks (Navbar, Sidebar, Modals, Cards, WhyScoreModal).
- `src/context/` — React Context providers (AuthContext).
- `src/lib/` — Shared utilities and Axios API client (`api.ts`).
- `src/types/` — TypeScript interface and type declarations.

---

## Naming Conventions

- **Python Backend Files:** Snake case (`ashby_provider.py`, `role_taxonomy.py`, `compensation_extractor.py`).
- **Python Classes:** PascalCase (`AshbyJobProvider`, `EvidenceLedger`, `RoleCompetencyProfile`).
- **Python Variables/Functions:** Snake case (`resolve_role`, `fetch_company_openings`, `is_india_opportunity`).
- **Frontend Components & Pages:** PascalCase (`Dashboard.tsx`, `WhyScoreModal.tsx`, `TailorResume.tsx`).
- **Frontend Utilities & Hooks:** Camel case (`api.ts`, `useAuth.ts`).
- **API Endpoints:** Pluralized lowercase kebab/snake nouns under `/api/` (`/api/jobs`, `/api/resumes`, `/api/matches`, `/api/applications`).
