# RoleRadar — AI Resume Intelligence & Career Acceleration Platform

## What This Is

RoleRadar is an enterprise-grade AI career copilot and resume intelligence platform engineered to eliminate rejection by Applicant Tracking Systems (Workday, Taleo, Greenhouse). Rather than relying on generic keyword stuffing or hallucinated LLM text, RoleRadar utilizes multi-phase geometric document parsing, an immutable 8-tier evidence ledger, candidate-grounded resume tailoring (Truth Guard), and verified live employer ATS opportunity feeds.

## Core Value

Zero-hallucination, evidence-grounded resume tailoring and high-trust Indian job discovery that mathematically aligns candidate credentials with authentic employer requisitions.

## Requirements

### Validated (Phases 1–13B Completed & Verified)

- [x] **REQ-GEO-01**: 5-gate geometric reading order engine with continuous vertical-overlap tracking, gutter width thresholds, and coordinate-aware block normalization (`PyMuPDF`).
- [x] **REQ-SEM-01**: Canonical semantic entity reconstruction (`WorkExperienceEntity`, `ProjectEntity`, `EducationCredentialEntity`, `SkillCategoryEntity`).
- [x] **REQ-LED-01**: Atomic, immutable candidate `EvidenceLedger` extracting verified claims (`EvidenceUnit`) tagged with source section, entity ID, and technologies.
- [x] **REQ-JD-01**: Generalized JD reconstruction with semantic zone partitioning, compound heading toleration, and tenure extraction.
- [x] **REQ-TAX-01**: Authoritative 61-profile `ROLE_TAXONOMY` with discriminative modifier matching, category token validation, and zero false collapse.
- [x] **REQ-ATS-01**: Deterministic 8-tier evidence-to-JD alignment (`EXACT_MATCH` to `CONFLICTING`) with mathematically explainable scoring (`WhyScoreModal`).
- [x] **REQ-TG-01**: Truth Guard grounded tailoring preventing hallucination of unworked technologies or fabricated dates.
- [x] **REQ-BUD-01**: Deterministic 1-page vertical density budget engine enforcing line-budget constraints per experience item.
- [x] **REQ-EXP-01**: Pixel-precise ReportLab PDF and python-docx export across enterprise templates (`harvard`, `stanford`, `modern`, `classic`).
- [x] **REQ-JOB-01**: Unified live employer ATS ingestion across SmartRecruiters (319), Lever (228), Greenhouse (64), and Ashby (49) delivering 660 verified active Indian opportunities.
- [x] **REQ-URL-01**: Strict direct requisition URL validation (`UrlType.DIRECT_REQUISITION`) with HTTPS enforcement and 100% reachability.
- [x] **REQ-SEC-01**: Comprehensive security hardening with constant-time password verification, regex attack shields, rate limiting, and HTTP security headers.

### Active (Current Milestone: Release Preparation & Production Hardening)

- [ ] **REQ-PROD-01**: Clean build and containerized production packaging for frontend (Vite static bundle) and backend (Uvicorn ASGI).
- [ ] **REQ-OPS-01**: Resolution of test runner deprecation warnings (`pytest-asyncio` loop scope configuration).
- [ ] **REQ-MON-01**: Automated background synchronization daemon with failure alerting and dead-link pruning.

### Out of Scope

- **Aggregated Non-ATS Scraping**: Indiscriminate job scraping from unauthenticated job boards or secondary portals (e.g., generic Indeed/LinkedIn scraping) — violates direct ATS trust guarantee.
- **Credential Fabrication**: LLM-driven generation of synthetic projects, phantom skills, or altered employment dates — strictly blocked by Truth Guard.
- **Unconstrained Multi-Page Resumes**: Allowing uncontrolled vertical expansion beyond standard 1-page ATS specifications — strictly regulated by budget engine.

---

## Context

- **Brownfield Evolution**: RoleRadar has completed 13 major development and audit phases, expanding from core PDF reading order geometry to a multi-provider live opportunity ecosystem.
- **Opportunity Model**:
  - *Primary Live Employer ATS*: SmartRecruiters, Lever, Greenhouse, Ashby (660 active Indian listings).
  - *Secondary Index*: Adzuna (151 indexed opportunities, isolated from public live feed).
  - *Catalog & Private Data*: Curated benchmarks (55) and custom user JDs (17).
- **Test Integrity**: Automated test suite of 110 test files with 362+ passing regression tests and zero failures.

---

## Constraints

- **Language & Frameworks**: Python 3.12 (FastAPI, Pydantic v2, Motor) and TypeScript (React 19, Vite, Tailwind CSS).
- **Storage**: MongoDB with WiredTiger engine. Active database storage paths (`scratch/mongodb_data/`) must remain untracked by Git to avoid Windows OS file locks.
- **Trust Standard**: Every public job opportunity must have a verified direct application link (`jobs.*` or employer ATS domain) with direct candidate apply destination.
- **Tailoring Grounding**: Tailored resume bullets must reference verified candidate `EvidenceUnit` claims.

---

## Key Decisions

| Decision | Context & Rationale | Status |
|---|---|---|
| **5-Gate Geometry over Fixed Midpoint** | Replaced fragile 50% width midpoint column splits with continuous vertical overlap and gutter threshold analysis to support asymmetric multi-column resumes. | Locked (Phase 1) |
| **8-Tier Evidence Ledger over LLM Matching** | Replaced black-box prompt matching with an immutable evidence ledger and deterministic tier weights to guarantee reproducible ATS scoring. | Locked (Phases 4–5) |
| **Truth Guard Constrained Tailoring** | Restricts LLM tailoring to rephrasing existing candidate claims. Disallows introducing skills not present in `EvidenceLedger`. | Locked (Phase 7) |
| **Exclusion of Adzuna from Live Feed** | Relegated Adzuna secondary indexed jobs to non-live catalog storage, ensuring public feeds contain only direct employer ATS requisitions. | Locked (Phase 11) |
| **Ashby Direct Provider Integration** | Integrated official Ashby public JSON board API (`/posting-api/job-board/{board}`) to add 49 verified high-quality Indian opportunities. | Locked (Phase 13) |
| **Specialized Role Isolation** | 30 specialized Ashby roles (e.g. Dubbing Specialists, Deployment Strategists) remain unclassified (`canonical_role = None`) to prevent false mapping to unrelated roles. | Locked (Phase 13B) |
| **Discriminative Category Token Matching** | Fixed role resolution to require generic category overlap (e.g. *"engineer"*) before matching specialized aliases, preventing leadership/location collusions. | Locked (Phase 13B) |
