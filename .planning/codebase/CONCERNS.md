# Codebase Concerns

**Analysis Date:** 2026-09-16

## Technical Debt

- **Git Tracking History for Database Files:**
  - `scratch/mongodb_data/` previously had binary `.wt` and journal files committed to Git. While untracked and ignored in the working tree, the commit history contains binary storage blobs that inflate repository clone size.
- **Pytest-Asyncio Fixture Scope Warning:**
  - `pytest-asyncio` displays deprecation warnings during test execution (`asyncio_default_fixture_loop_scope is unset`). Defining `asyncio_default_fixture_loop_scope = function` in `pytest.ini` or `pyproject.toml` will eliminate warning noise.
- **SPA Fallback Routing in Dev vs. Production:**
  - In development, Vite handles SPA routing fallback. In production, FastAPI static mounting must continue serving `index.html` on unknown client-side routes without capturing `/api/` endpoints.

---

## Fragile Areas

- **Windows OS File Locking on Live MongoDB Directory:**
  - If a local `mongod.exe` service runs against `scratch/mongodb_data/`, Windows holds exclusive locks on `WiredTiger.lock`. Any scripts or broad Git operations touching this directory will encounter `Permission denied`.
- **Specialized / Unclassified ATS Opportunities:**
  - 30 Indian Ashby opportunities (dubbing specialists, linguists, deployment strategists) have `canonical_role = None`. Any future feature assuming every verified active opportunity maps to a valid canonical role in `ROLE_TAXONOMY` could raise unexpected `NoneType` or mapping errors if not guarded.
- **External ATS Rate Limiting & Schema Changes:**
  - Public posting APIs (especially Lever and Ashby) are subject to undocumented throttling or payload structural shifts. Provider adapters must maintain robust defensive error handling.

---

## Performance Concerns

- **Local Development First-Request Latency:**
  - The first call to `/api/jobs` incurs a ~4s warm-up cost due to Spacy language model initialization and role taxonomy lookup table compilation. Subsequent requests execute in <150ms.
- **Batch Resume Ingestion Concurrency:**
  - PDF coordinate parsing via PyMuPDF and OCR text extraction can be CPU-intensive when multiple multi-page resumes are processed simultaneously.

---

## Security Considerations

- **Strict Evidence Guarding (Truth Guard):**
  - Continuous regression testing is required to ensure that LLM tailoring prompts never inject unverified candidate skills or alter employment dates.
- **Authentication Token Expiry:**
  - Access tokens expire after the configured window (`ACCESS_TOKEN_EXPIRE_MINUTES`). Frontend must handle 401 responses gracefully by redirecting to login.
- **Sensitive Key Exposure:**
  - Ensure all external API keys (`GREENHOUSE_API_KEY`, `LEVER_API_KEY`, `AI_API_KEY`) remain strictly confined to environment variables and `.env` files, never hardcoded in repository files.

---

## Operational Risks

- **MongoDB Service vs. Standalone Conflicts:**
  - Ensure team developers run MongoDB either exclusively as a registered Windows Service or via standard background process, preventing port 27017 bind collisions.
- **Provider API Reliability:**
  - The decoupled sync design ensures that external provider outages never impact active user browsing; however, long outages can degrade opportunity freshness if sync jobs repeatedly fail.
