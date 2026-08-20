# RoleRadar

AI-based resume intelligence and career copilot: it doesn't just score a resume — it tells you exactly why you'd be filtered out (structural, semantic keyword gap, or unproven claim), fixes only what it can prove with your own evidence, and never lets AI invent your qualifications.

## Architecture

```
React + Vite (TS)  ──────►  FastAPI  ──────►  Modular Backend Services
                                                    │
                                    ┌───────────────┼───────────────┐
                                    ▼                                ▼
                             Business Logic                    AIService
                          (scoring, matching,                      │
                           ATS calc, Truth Guard,                  ▼
                           eligibility, CRUD)                 AI Provider (configurable)
                                    │                               │
                                    ▼                               ▼
                                MongoDB                     Local Runtime Model
                                                          (Ollama / LM Studio)
```

**Stack decisions and why:**

| Layer | Choice | Reason |
|---|---|---|
| Frontend | React + Vite + TS + Tailwind | No SSR need for a private dashboard app |
| Backend | FastAPI | Native Pydantic validation — directly needed for Truth Guard / AI-output schema enforcement |
| Database | MongoDB + Motor | Flexible document shape fits resume/JD JSON; no migration overhead mid-sprint |
| Async | Native `async def`, no Celery/Redis | LLM latency is one slow call per request, not a background-job problem |
| Runtime AI | AIService → local Ollama (default) → LM Studio / cloud fallback | Offline-safe demo, zero hard dependency on a paid API, swappable via `.env` only |
| Containers | MongoDB only in dev | Fast iteration; full Dockerfiles added near the end for packaging |

**Non-negotiable architecture rules** (see `backend/app/core/ai_service/`):
- Feature modules never call an LLM provider directly — only through `AIService`.
- Every AI structured output is validated against a Pydantic schema with a repair-retry loop (`structured_output.py`) before it's trusted.
- The master resume is never overwritten; every tailoring is a separate version.
- Every AI-proposed resume change carries `source_evidence` and must be user-approved before it's final.

## Repo layout

```
roleradar/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py            # all env-driven settings
│   │   │   └── ai_service/          # AIService abstraction (provider-agnostic)
│   │   ├── db/mongo.py              # Motor connection + collection names + indexes
│   │   └── modules/                 # auth, profile, resume, intelligence, jobs,
│   │                                 # matching, tailoring, applications, learning,
│   │                                 # interview, chatbot, notifications
│   ├── seeds/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/layout/       # Sidebar, AppShell, PagePlaceholder
│       ├── pages/                   # one folder per nav group
│       └── lib/apiClient.ts
└── docker-compose.yml                # MongoDB only
```

## Setup

**Prerequisites:** Python 3.12+, Node 20+, Docker (for MongoDB), and either [Ollama](https://ollama.com) or [LM Studio](https://lmstudio.ai) running locally with a model pulled.

```bash
# 1. Start MongoDB
docker compose up -d

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev
```

- Backend health check: `http://localhost:8000/api/health`
- API docs (auto-generated from Pydantic schemas): `http://localhost:8000/docs`
- Frontend: `http://localhost:5173`

### Live job listings (optional)

By default, RoleRadar uses only the curated demo dataset — zero setup required. To also pull in **real listings with real apply links**, sign up free at [developer.adzuna.com/signup](https://developer.adzuna.com/signup), then in `backend/.env`:

```env
JOB_SOURCE_MODE=hybrid
ADZUNA_APP_ID=your_app_id
ADZUNA_APP_KEY=your_app_key
```

**Important:** the Adzuna integration (`app/modules/jobs/live_provider.py`) was built and unit-tested against a fixture matching Adzuna's documented response shape, but could not be tested against the *live* API — this sandbox has no general internet access. Verify it actually works on your machine: visit the Jobs page after setting the above, and check real company names/real "View listing" links appear (tagged "Live" vs "Demo" in the UI). If something's off, `backend/app/modules/jobs/live_provider.py`'s `_transform()` method is the single place to fix field mapping.

### Local runtime model

```bash
# Ollama (default)
ollama pull qwen2.5:7b-instruct
# then in backend/.env: AI_PROVIDER=ollama, OLLAMA_MODEL=qwen2.5:7b-instruct

# or LM Studio: start its local server, then set AI_PROVIDER=lmstudio in .env
```

The exact model is intentionally not locked in yet — it's selected after testing for JSON reliability, resume/JD understanding, and response speed on demo hardware (see Development Context in the original project brief).

## Phase roadmap

- [x] **Phase 0 — Foundation**: monorepo scaffold, AIService abstraction with local-first provider + JSON repair-retry loop, Mongo connection + indexes, frontend shell wired to full navigation.
- [x] **Phase 1 — Authentication + onboarding**: JWT auth, bcrypt hashing, candidate profile + consent capture, route guards.
- [x] **Phase 2 — Resume Intelligence**: PDF/DOCX parsing, deterministic Parseability Engine (multi-column/table/scanned-PDF detection), deterministic Recruiter Impact analyzer (weak verbs, quantification).
- [x] **Phase 3 — Jobs + Matching**: curated 45-job seed dataset, `JobProvider`/`EmbeddingProvider` abstractions, weighted matching engine with per-category weights and apply-readiness bands.
- [x] **Phase 4 — Tailoring (Truth Guard)**: `AIService.generate_resume_rewrite()`, per-change approval workflow, finalize step that only ever applies explicitly-approved changes.
- [x] **Phase 5 — ATS Compatibility + export**: RoleRadar ATS Compatibility Score (combining existing engines), real PDF/DOCX generation gated to finalized content only.
- [x] **Phase 6 — Applications + Smart Apply**: kanban tracker, duplicate-application detection, package-prep-only Smart Apply (no automation, no scraping).
- [x] **Phase 7 — Skill gaps, learning, interview, Career Copilot**: deterministic skill-gap/roadmap engine, AI-generated interview questions, Career Copilot grounded in real per-user data with cross-user isolation verified.
- [x] **Phase 8 — UI polish**: real Dashboard (RRI, top matches, next action), real Settings page, visual consistency pass.

Every phase has passing tests exercising real logic (70 backend tests total) — see `backend/tests/`.

## Known simplifications (read before your viva/report)

Built honestly within a single extended session and this sandbox's constraints. Worth knowing before you demo or write these up as limitations:

- **Semantic matching uses TF-IDF, not sentence-transformers** by default (config: `EMBEDDING_PROVIDER=tfidf`). This sandbox couldn't reliably install PyTorch. Catches lexical overlap well ("React.js" ≈ "React") but not deeper synonym gaps. Swap to `EMBEDDING_PROVIDER=sentence_transformer` after `pip install sentence-transformers` on your own machine — zero other code changes needed, same `EmbeddingProvider` interface.
- **No live LLM was available in this sandbox** (no Ollama/LM Studio installed here). Every AI-dependent path (tailoring, interview questions, Career Copilot) is fully built and tested with fake providers proving the *pipeline and Truth Guard logic* are correct — but real generation quality on your chosen model is untested by me. Test this first on your machine.
- **JD analysis is currently reused from curated job seed data**, not a separate "paste any JD" flow with `AIService.analyze_job_description()`. The AI method and prompt pattern exist; wiring a free-text JD paste UI is a natural next increment if you want it.
- **Cover letter generation** (`AIService.generate_cover_letter`) and **interview answer evaluation** (`evaluate_interview_answer`) are declared in `AIService` but not implemented — natural "future work" items for your report.
- **Achievement Journal and Saved jobs/internships** pages remain UI placeholders (each clearly phase-tagged in the code) — lower-priority per your own SHOULD-WORK/NICE-TO-HAVE tiers, not core to the demo flow.
- **Job dataset is 45 curated entries**, not 500 — a deliberate scope trim for build time; the generator script (`seeds/generate_jobs_seed.py`) can be re-run with larger `n_full_time`/`n_internships` values.
- **RRI (Role Readiness Index)** is computed from 3 components that exist (Parseability, Recruiter Impact, best-match Skill Coverage) rather than the original 5-component formula — Evidence Score and Integrity Score weren't built as separate engines in this pass. Documented directly in `dashboard.py`.

None of these are hidden — each is called out in the relevant module's docstring, not just here.

## Testing

```bash
cd backend
pytest
```

Phase 0 ships `tests/test_structured_output.py`, proving the AI-output validation + repair-retry loop works correctly using fake providers — no live model required to verify the foundation.

## Ethics statement

RoleRadar never fabricates skills, metrics, experience, or credentials. Every AI-proposed resume change must trace to real evidence in the candidate's own resume, profile, or achievement journal, and requires explicit human approval before becoming part of a final resume. Application "automation" is limited to preparing a tailored package (resume, cover letter, checklist) — the candidate always submits manually on the real site.
