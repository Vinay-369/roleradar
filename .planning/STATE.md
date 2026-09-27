# Project State

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-09-16)

**Core value:** Zero-hallucination, evidence-grounded resume tailoring and high-trust Indian job discovery that mathematically aligns candidate credentials with authentic employer requisitions.  
**Current focus:** Phase 14 — Release Packaging & Operational Hardening

---

## Current Position

Phase: 14 of 15 (Release Packaging & Operational Hardening)  
Plan: Completed  
Status: Phase 14 Verified & Complete; Ready for Phase 15  
Last activity: 2026-09-16 — Completed Phase 14 Release Packaging & Operational Hardening (resolved pytest-asyncio deprecation warnings, synchronized .env.example, created .dockerignore, updated production runbooks).

Progress: [█████████▉] 93%

---

## Performance Metrics

**Historical Phase Completion:**
- Phase 1–8: Verified & Shipped
- Phase 9 (Security Hardening): PASS WITH CONDITIONS (Verified)
- Phase 10 (Release Prep): PASS WITH CONDITIONS (Verified)
- Phase 11 (Browser & Inventory Audit): PASS WITH CONDITIONS (Verified)
- Phase 12 (Opportunity Coverage Expansion): PASS WITH CONDITIONS (Verified)
- Phase 13 (Ashby Integration): PASS (Verified)
- Phase 13B (Ashby Verification & Taxonomy Fix): PASS WITH CONDITIONS (Verified)
- Phase 14 (Release Packaging & Operational Hardening): PASS (Verified)

**Test Suite Health:**
- Total Test Files: 110
- Total Automated Tests: 495+
- Active Regression Suite (Phase 13B): 362 passed, 0 failed (100% pass rate)

---

## Accumulated Context

### Decisions
- **Phase 1**: 5-gate geometric PDF coordinate extraction chosen over fixed-midpoint column parsing.
- **Phase 4–5**: 8-tier deterministic evidence ledger chosen over black-box prompt matching to guarantee reproducible ATS score provenance.
- **Phase 7**: Truth Guard rule engine enforced to constrain LLM tailoring strictly to candidate source evidence units.
- **Phase 11**: Adzuna aggregated data strictly excluded from the live public feed; live feed reserved exclusively for direct employer ATS.
- **Phase 13**: Ashby direct job board API integrated across 7 boards, adding 49 active Indian requisitions with direct apply URLs.
- **Phase 13B**: Discriminative category token matching bug in `role_taxonomy.py` fixed; specialized unclassified roles isolated from false canonical recommendations; active Indian ATS inventory reconciled to 660.
- **Phase 14**: Configured `backend/pytest.ini` with `asyncio_default_fixture_loop_scope = function` eliminating test deprecation warnings; enforced container packaging boundaries with `.dockerignore`.

### Pending Technical Debt
- Untrack live MongoDB binary storage files (`scratch/mongodb_data/`) from future commits.
