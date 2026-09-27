# External Integrations

**Analysis Date:** 2026-09-16

## APIs & External Services

**Live Employer ATS Integrations:**
RoleRadar connects directly to official public endpoints of modern Applicant Tracking Systems to discover authentic live job and internship opportunities in India:
- **Ashby Job Board API**
  - **Endpoint:** `GET https://api.ashbyhq.com/posting-api/job-board/{board_token}?includeCompensation=true`
  - **Adapter:** `AshbyJobProvider` in `backend/app/modules/jobs/ashby_provider.py`
  - **Authentication:** Unauthenticated public job board API with User-Agent header
  - **Boards Configured:** `ramp`, `retool`, `linear`, `deel`, `quora`, `kong`, `elevenlabs`
  - **Capabilities:** Direct JSON requisitions, structured compensation, location arrays, direct apply links (`jobs.ashbyhq.com/{org}/{job_id}/application`)
- **Greenhouse Job Board API**
  - **Endpoint:** `GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`
  - **Adapter:** `GreenhouseJobProvider` in `backend/app/modules/jobs/greenhouse_provider.py`
  - **Authentication:** Public board token
  - **Capabilities:** Requisition descriptions, department hierarchies, direct apply URLs
- **Lever Postings API**
  - **Endpoint:** `GET https://api.lever.co/v0/postings/{company}`
  - **Adapter:** `LeverJobProvider` in `backend/app/modules/jobs/lever_provider.py`
  - **Authentication:** Public company slug
  - **Capabilities:** Structured workplace categories (remote/hybrid/onsite), team tags, Lever direct apply URLs
- **SmartRecruiters Postings API**
  - **Endpoint:** `GET https://api.smartrecruiters.com/v1/companies/{company}/postings`
  - **Adapter:** `SmartRecruitersJobProvider` in `backend/app/modules/jobs/smartrecruiters_provider.py`
  - **Authentication:** Public company identifier / optional client ID
  - **Capabilities:** Multilingual postings, city/country location filters, SmartRecruiters apply portal

**Secondary Aggregators:**
- **Adzuna API**
  - **Adapter:** `backend/app/modules/jobs/adzuna_provider.py`
  - **Usage:** Secondary aggregated index. Strictly excluded from the primary live employer ATS public feed (`source != 'adzuna'`).

**AI & LLM Services:**
- **Local AI Engines:**
  - **Ollama:** `http://localhost:11434/api/generate` (e.g., `llama3.1`, `mistral`)
  - **LM Studio:** `http://localhost:1234/v1/chat/completions` (OpenAI-compatible local server)
- **Cloud Fallback:**
  - Configurable cloud endpoints (OpenAI / DeepSeek / Gemini compatible) controlled via `AI_PROVIDER`, `AI_API_KEY`, `AI_BASE_URL` in `backend/app/core/config.py`.
  - Used for resume tailoring bullet rephrasing and Career Copilot chat guidance, safeguarded by Truth Guard deterministic validation.

---

## Data Storage

**Databases:**
- **MongoDB (WiredTiger Storage Engine):**
  - **Connection:** Managed asynchronously via Motor in `backend/app/db/mongo.py`.
  - **Default Database:** `roleradar` (configurable via `MONGO_DB_NAME`).
  - **Collections:**
    - `users` — User credentials, bcrypt hashes, roles, created timestamps.
    - `profiles` — Candidate career profiles, targets, preferences.
    - `resumes` — Document metadata, extracted raw text, `NormalizedDocument` layout structures, extracted entities, and atomic `EvidenceLedger`.
    - `jobs` — Active opportunities normalized from ATS providers and custom user JDs.
    - `matches` — Cached match calculations between candidates and opportunities.
    - `tailored_resumes` — Grounded tailored resume versions, template selections, and PDF/DOCX artifacts.
    - `applications` — User job application CRM stages (`SAVED` to `OFFER`).
    - `chat_history` — Conversational copilot session messages.
  - **Index Management:** Automated on application startup via `ensure_indexes()` in `backend/app/db/mongo.py` (unique email, source requisition IDs, TTL indexes, location text indexes).

**File Storage:**
- **Local Filesystem Storage:**
  - Uploaded raw resume files (`PDF`, `DOCX`) stored in `backend/storage/uploads/`.
  - Rendered tailored resumes (`PDF`, `DOCX`) generated on demand in `backend/storage/generated/`.
  - Isolated temporary scratch directory in `scratch/`.

---

## Authentication & Identity

**Authentication Architecture:**
- **Custom Stateless JWT:**
  - Implemented in `backend/app/core/security.py` using `python-jose` and `bcrypt`.
  - Token payload encodes subject user ID (`sub`) and expiration timestamp (`exp`).
  - Signed using HS256 algorithm with secret `JWT_SECRET`.
  - Injected as HTTP Authorization header: `Bearer <token>`.
- **FastAPI Dependencies:**
  - `get_current_user` in `backend/app/modules/auth/dependencies.py` decodes the bearer token and resolves the user document from MongoDB.
  - Ownership checks enforced across profile, resume, tailoring, and application routes.
  - Demo user support for non-production environments (`ensure_demo_user` in `backend/app/modules/auth/services.py`).
