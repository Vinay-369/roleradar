# Project Roadmap: RoleRadar

## Overview

RoleRadar has evolved through 13 major development, validation, and expansion phases. The project has progressed from foundational coordinate document geometry to an authoritative 660-opportunity live Indian ATS ecosystem. Current work focuses on production release hardening, automated sync orchestration, and deployment acceptance.

---

## Phases

### Completed Historical Phases

- [x] **Phase 1: Generalized Document Geometry & Reading Order** — 5-gate continuous vertical-overlap tracking, gutter width thresholds, and coordinate block normalization (`PyMuPDF`).
- [x] **Phase 2: Canonical Semantic Resume Reconstruction** — Typed entity extraction (`WorkExperience`, `Projects`, `Education`, `Skills`) and atomic `EvidenceLedger` generation.
- [x] **Phase 3: Generalized JD Reconstruction & Role Taxonomy** — Semantic zone zoning, tenure extraction, and 61 canonical role competency profiles.
- [x] **Phase 4: Deterministic 8-Tier Evidence Ledger Matching** — Objective candidate-to-JD alignment with explainable scoring breakdown (`WhyScoreModal`).
- [x] **Phase 5: Candidate/Opportunity Evidence Alignment** — Bi-directional skill validation and transferable technology clustering.
- [x] **Phase 6: Resume Tailoring & Truth Guard** — Grounded LLM bullet rephrasing strictly bound to verified candidate claims.
- [x] **Phase 7: End-to-End Integration & 1-Page Export** — Vertical line budgeting and pixel-precise ReportLab PDF / DOCX generation across enterprise templates.
- [x] **Phase 8: UX Audit & Student Workflows** — Top 20 interview banks across 6 technical tracks, fresher/student suitability signals, and interactive practice tools.
- [x] **Phase 9: Production Hardening & Security Matrix** — Constant-time auth checks, regex attack shields, rate limiting, and HTTP security headers.
- [x] **Phase 10: Release Preparation & Deployability Audit** — Production asset serving and SPA fallback routing.
- [x] **Phase 11: Real Browser Validation & Opportunity Reconciliation** — Reconciled 588 baseline live employer ATS opportunities in India; excluded Adzuna from public live feeds.
- [x] **Phase 12: Provider Coverage & Opportunity Expansion** — Expanded live Indian ATS inventory to 611 verified opportunities (SmartRecruiters, Lever, Greenhouse).
- [x] **Phase 13: Ashby Provider Integration** — Implemented Ashby provider adapter for 7 company boards (`ramp`, `retool`, `linear`, `deel`, `quora`, `kong`, `elevenlabs`).
- [x] **Phase 13B: Ashby Verification & Inventory Reconciliation** — Verified 49 active Indian opportunities (100% reachable direct URLs), fixed role taxonomy discriminative category matching defect, and reconciled total live Indian ATS inventory to 660.
- [x] **Phase 14: Release Packaging & Operational Hardening** — Verified production frontend build (`npm run build`), resolved `pytest-asyncio` loop scope deprecation warning via `backend/pytest.ini`, synchronized `backend/.env.example`, created `.dockerignore` to isolate development artifacts, and standardized production runbooks.

---

### Active & Upcoming Phases

- [ ] **Phase 15: Background Sync Daemon & Health Monitoring**
  - **Goal**: Implement scheduled ATS opportunity synchronization with automated dead-link pruning, provider rate limit backoff, and inventory alerting.
  - **Depends on**: Phase 14
  - **Requirements**: REQ-MON-01
  - **Success Criteria**:
    1. Scheduled background job syncs active boards at configured intervals without user request latency.
    2. Stale or closed requisitions automatically transition to `CLOSED` without manual intervention.
    3. Ingestion telemetry logs processed records, duplicates, and errors per board.
  - **Plans**: 2 plans (TBD)
