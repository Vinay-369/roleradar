# Testing Strategy

**Analysis Date:** 2026-09-16

## Overview

RoleRadar employs an automated test suite comprising **110 test files** located in `backend/tests/`. The suite enforces strict regression guarantees across geometric parsing, semantic entity structuring, taxonomy resolution, ATS provider adapters, matching algorithms, tailoring truth guards, security matrices, and end-to-end user workflows.

---

## Test Organization

- **Unit Tests:**
  - `test_role_intelligence.py` — Authoritative semantic role resolver tests, token discrimination, and synonym matching.
  - `test_role_taxonomy_coverage.py` — Verifies all 61 canonical role profiles resolve with HIGH/MEDIUM confidence.
  - `test_compensation_audit.py` — LPA and stipend extraction from raw text and structured payloads.
  - `test_opportunity_completeness.py` — Completeness scoring and rejection reason classification.
- **Provider Tests:**
  - `test_ashby_provider.py` (20 tests) — Ashby board crawling, URL classification, compensation parsing, and error recovery.
  - `test_greenhouse_provider.py` (17 tests) — Greenhouse board ingestion, requisition extraction, and deduplication.
  - `test_lever_provider.py` (24 tests) — Lever team mapping, workplace category parsing, and active filtering.
  - `test_smartrecruiters_provider.py` (18 tests) — SmartRecruiters multi-region filtering and payload normalization.
- **Pipeline & Integration Tests:**
  - `test_verified_opportunity_pipeline.py` — Validates opportunity ingestion, active verification, and feed isolation.
  - `test_live_jobs.py` — Ensures public job feeds correctly filter by region, job type, and exclude non-live benchmarks.
  - `test_complete_pipeline_phase11.py` — Validates full candidate onboarding, match calculation, and application submission.
  - `test_india_opportunity_intelligence_phase12.py` — Verifies Indian opportunity discovery across all active providers.
  - `test_phase7_end_to_end_lifecycle.py` — Tests resume upload $\rightarrow$ tailoring $\rightarrow$ export $\rightarrow$ application tracking.
- **Security & Hardening:**
  - `test_phase9_comprehensive_security_matrix.py` (20 tests) — Tests expired/malformed JWTs, SQL/NoSQL injection prevention, payload limits, rate limiting, and CORS headers.

---

## Test Commands

- **Run All Tests:**
  ```powershell
  cd backend
  .\.venv\Scripts\pytest
  ```
- **Run Provider Suite:**
  ```powershell
  cd backend
  .\.venv\Scripts\pytest tests/test_ashby_provider.py tests/test_greenhouse_provider.py tests/test_lever_provider.py tests/test_smartrecruiters_provider.py
  ```
- **Run Role Intelligence Suite:**
  ```powershell
  cd backend
  .\.venv\Scripts\pytest tests/test_role_intelligence.py tests/test_role_taxonomy_coverage.py
  ```

---

## Fixtures & Mocking

- **Database Mocking:** Tests utilize `mongomock-motor` or dedicated mock database clients to ensure tests run in-memory without polluting local development data.
- **External Network Mocking:** HTTP calls to ATS APIs (Ashby, Lever, Greenhouse) are mocked using `unittest.mock.patch` on `httpx.AsyncClient` or `respx`, simulating timeouts, HTTP 500s, malformed responses, and successful payloads.
- **Test Fixtures:** Sample PDF layouts and resume texts reside in `backend/tests/fixtures/`.

---

## Coverage & Scope

- **Automated Test Count:** **495+ tests across 110 test files**.
- **Pass Rate:** **100%** (verified 362/362 passing in recent Phase 13B regression run).
- **Core Guarantees Tested:**
  - Zero date fabrication.
  - Zero hallucinated technologies in tailored resumes.
  - Strict 1-page vertical budget enforcement in PDF exports.
  - Constant-time password hashing and unguessable token security.
  - Complete isolation of read endpoints from external ATS network latency.
