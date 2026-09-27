# Requirements Specification

**Project:** RoleRadar — AI Resume Intelligence & Career Acceleration Platform  
**Status:** Living Specification  
**Baseline Date:** 2026-09-16

---

## 1. Document Geometry & Reading Order (Phase 1)

- [x] **REQ-GEO-01**: Parse arbitrary multi-column PDF resumes into coordinate-preserving `NormalizedDocument` models containing ordered `LayoutBlock` items.
- [x] **REQ-GEO-02**: Implement continuous vertical-overlap tracking to distinguish adjacent columns from spanning section headers without static midpoint assumptions.
- [x] **REQ-GEO-03**: Handle hanging section headers, asymmetric two-column splits, and gutter boundary variations.

---

## 2. Semantic Entity Structuring & Evidence Ledger (Phase 2)

- [x] **REQ-SEM-01**: Extract and structure raw document blocks into typed canonical entities: `WorkExperienceEntity`, `ProjectEntity`, `EducationCredentialEntity`, and `SkillCategoryEntity`.
- [x] **REQ-SEM-02**: Generate an atomic, verifiable `EvidenceLedger` where each candidate claim is tagged with source section, entity ID, normalized text, and extracted tech tokens.
- [x] **REQ-SEM-03**: Discover implicit candidate technologies from descriptive project and experience narrative bullets.

---

## 3. Generalized JD Reconstruction & Role Taxonomy (Phase 3)

- [x] **REQ-JD-01**: Partition arbitrary job descriptions into semantic zones (`COMPANY_OVERVIEW`, `ROLE_OVERVIEW`, `RESPONSIBILITIES`, `REQUIREMENTS_MUST_HAVE`, `REQUIREMENTS_PREFERRED`, `QUALIFICATIONS`, `BENEFITS`, `EEO_LEGAL`).
- [x] **REQ-JD-02**: Extract tenure requirements with intervening qualifiers (e.g. *"3+ years of professional software development experience"* $\rightarrow$ `3.0`) while shielding against company marketing claims.
- [x] **REQ-TAX-01**: Maintain an authoritative 61-profile `ROLE_TAXONOMY` with explicit domains, subdomains, competencies, and tools.
- [x] **REQ-TAX-02**: Implement discriminative semantic role resolution (`resolve_role`) that enforces category token overlap and prevents false collapse of specialized titles into generic profiles.

---

## 4. Deterministic Matching & Explainable Scoring (Phases 4–6)

- [x] **REQ-ATS-01**: Align candidate evidence units against JD requirements using an 8-tier matching rubric (`EXACT_MATCH`, `STRONG_MATCH`, `SUPPORTED`, `RELATED`, `PARTIAL`, `WEAK`, `MISSING`, `CONFLICTING`).
- [x] **REQ-ATS-02**: Calculate overall match scores via a deterministic formula (50% required skills, 30% role title similarity, 20% experience & location fit).
- [x] **REQ-ATS-03**: Expose mathematical score breakdowns and evidence provenance through `WhyScoreModal`.

---

## 5. Truth Guard Tailoring & Document Export (Phase 7)

- [x] **REQ-TG-01**: Constrain LLM tailoring strictly to candidate source evidence units; strictly forbid fabrication of unworked skills, synthetic metrics, or modified employment dates.
- [x] **REQ-BUD-01**: Implement a deterministic 1-page vertical density budget engine that dynamically calculates line counts and enforces page-budget limits per experience item.
- [x] **REQ-EXP-01**: Generate pixel-precise PDF (ReportLab) and DOCX (python-docx) files across enterprise ATS templates (`harvard`, `stanford`, `modern`, `classic`).

---

## 6. Live Opportunity Ecosystem & Verification (Phases 8–13B)

- [x] **REQ-JOB-01**: Integrate direct employer ATS adapters:
  - SmartRecruiters (319 active Indian opportunities)
  - Lever (228 active Indian opportunities)
  - Greenhouse (64 active Indian opportunities)
  - Ashby (49 active Indian opportunities)
  - Total Verified Live ATS Indian Inventory: **660 opportunities**.
- [x] **REQ-URL-01**: Enforce direct requisition URL validation (`DIRECT_REQUISITION` on HTTPS scheme); reject generic company homepages or authentication walls.
- [x] **REQ-DEC-01**: Decouple public read endpoints (`GET /api/jobs`) completely from external ATS network requests. Trigger synchronization solely via `POST /api/jobs/sync`.
- [x] **REQ-DED-01**: Enforce intra- and cross-provider deduplication using normalized company, title, location, and application destination signatures.

---

## 7. Security Hardening & Production Operations (Current Active)

- [x] **REQ-SEC-01**: Enforce constant-time password verification via `bcrypt` and stateless JWT verification via `python-jose`.
- [x] **REQ-SEC-02**: Shield endpoints with in-memory rate limiting and HTTP security headers (`nosniff`, `DENY`, `strict-origin-when-cross-origin`).
- [x] **REQ-PROD-01**: Implement production frontend build validation (`npm run build`) and backend production containerization/packaging exclusions (`.dockerignore`).
- [x] **REQ-OPS-01**: Eliminate `pytest-asyncio` loop scope deprecation warnings via `backend/pytest.ini` configuration.
- [ ] **REQ-MON-01**: Establish automated background synchronization health monitoring with dead-link detection.
