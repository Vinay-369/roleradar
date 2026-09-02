# RoleRadar — AI Resume Intelligence & Career Acceleration Platform

RoleRadar is an enterprise-grade AI career copilot and resume intelligence platform designed to eliminate rejection by ATS screening algorithms (Workday, Taleo, Greenhouse). Rather than generic scoring, RoleRadar utilizes multi-phase semantic document reconstruction, strict 8-tier evidence-ledger verification, and candidate-grounded tailoring to produce high-impact, 1-page resumes without fabricating credentials.

---

## 🏛️ System Architecture

```
React 19 + Vite (TypeScript)  ──────►  FastAPI (Python 3.12)  ──────►  Modular Processing Pipeline
                                                                               │
                                  ┌────────────────────────────────────────────┴────────────────────────────────────────────┐
                                  ▼                                                                                         ▼
               Document & Semantic Intelligence Layer                                                    AI & Tailoring Orchestrator
           ┌─────────────────────────────────────────────────────────┐                              ┌─────────────────────────────────────────┐
           │ Phase 1: 5-Gate Geometric Reading-Order Engine         │                              │ Truth Guard Grounded Tailoring Engine   │
           │ Phase 2: Canonical Resume Semantic Entity Structurer    │                              │ Deterministic Fallback & JSON Repair    │
           │ Phase 3: Generalized JD Reconstruction & Taxonomy       │                              │ 8-Tier Evidence Ledger Matcher          │
           │ Phase 4: Deterministic ATS & RRI Scoring Engine         │                              │ 1-Page ReportLab / DOCX Renderer        │
           └─────────────────────────────────────────────────────────┘                              └─────────────────────────────────────────┘
                                  │                                                                                         │
                                  ▼                                                                                         ▼
                              MongoDB                                                                               AI Providers Layer
                          (Motor Async)                                                                        (Ollama / LM Studio / Cloud)
```

### Technology Stack Decisions

| Layer | Technology | Rationale & Capabilities |
|---|---|---|
| **Frontend** | React 19, Vite, TypeScript | Fast client-side rendering with React Query state caching, typed API integrations, and route-level code-splitting |
| **Styling** | Vanilla CSS + Tailwind CSS | SaaS Light design system with Sora/Inter typography, card hover physics, and micro-animations |
| **Backend** | FastAPI + Pydantic v2 | High-throughput asynchronous REST API with strict runtime schema validation and modular routing |
| **Document Geometry** | PyMuPDF (fitz) + PDFMiner | Coordinate-aware block extraction, 5-gate column detection, gutter analysis, and reading-order normalization |
| **Document Export** | ReportLab + python-docx | Pixel-precise 1-page vertical budget PDF and DOCX generation (`harvard`, `stanford`, `modern`, `classic`) |
| **Database** | MongoDB + Motor | Document storage for canonical profiles, structured JD requirements, evidence ledger mappings, and applications |
| **AI Strategy** | `AIService` Provider Layer | Provider-agnostic abstraction (Ollama, LM Studio, Cloud fallback) with automated JSON repair-retry loop and deterministic fallback |
| **Test Suite** | Pytest + pytest-asyncio | **495+ automated tests (100% pass rate)** covering geometry, semantic parsing, taxonomy, and end-to-end tailoring |

---

## 🌟 Core Pipeline & Engineering Innovations

### 1. 📐 Phase 1 — Generalized Document Geometry & Reading Order Engine
- **5-Gate Column Detection**: Replaces fragile midpoint assumptions with continuous vertical-overlap tracking, gutter width thresholds, column height ratios, and bounding-box geometry.
- **Hanging Header & Multi-Column Support**: Accurately handles asymmetric two-column resumes, single-column indented headers, and complex PDF stream orderings.
- **Coordinate-Preserving Normalization**: Maps raw PDF text blocks into normalized page models (`NormalizedDocument`, `LayoutBlock`) with absolute bounding coordinates and reading indices.

### 2. 🧬 Phase 2 — Canonical Semantic Resume Reconstruction
- **Canonical Entity Models**: Eliminates lossy string-flattening by structuring resumes directly into typed entities: `WorkExperienceEntity`, `ProjectEntity`, `EducationCredentialEntity`, and `SkillCategoryEntity`.
- **Atomic Evidence Ledger (`EvidenceLedger`)**: Extracts verifiable, immutable candidate claims (`EvidenceUnit`) tagged with source section, entity ID, normalized text, and detected technologies.
- **Implicit Skill Extraction**: Discovers candidate technologies embedded inside bullet point narratives and projects even when omitted from explicit skills lists.

### 3. 🎯 Phase 3 — Generalized JD Reconstruction & Analysis
- **Semantic Section Zoning**: Partitions arbitrary JDs into semantic zones (`COMPANY_OVERVIEW`, `ROLE_OVERVIEW`, `RESPONSIBILITIES`, `REQUIREMENTS_MUST_HAVE`, `REQUIREMENTS_PREFERRED`, `QUALIFICATIONS`, `BENEFITS`, `EEO_LEGAL`).
- **Compound Heading Toleration**: Seamlessly resolves slashed, hyphenated, and ampersand-delimited headings (e.g. *"Nice-to-Have / Preferred"*, *"What You Bring / Minimum Qualifications"*).
- **Multi-Word Experience Extractor**: Accurately parses tenure with intervening qualifiers (e.g. *"3+ years of professional software development experience"* $\rightarrow$ `min_years = 3.0`) while shielding against company marketing claims (e.g. *"25 years in business"*).
- **Anchored Seniority & Weighted Domain Inference**: Anchors seniority strictly to target titles and quantitative requirements (ignoring incidental mentions like *"collaborating with architects"*), and computes multi-zone weighted domain scoring (Title $3\times$, Responsibilities $2\times$, Skills $1.5\times$).
- **Context & Boilerplate Quarantine**: Guarantees that company overviews, benefits, and EEO statements never become phantom candidate requirements.

### 4. ⚖️ 8-Tier Deterministic Evidence-to-JD Mapping
- Maps candidate evidence units against structured JD requirements without semantic inflation:
  - `EXACT_MATCH` (1.00) — Direct verbatim technology/credential match in candidate experience.
  - `STRONG_MATCH` (0.90) — Exact synonym match supported by high-impact delivery evidence.
  - `SUPPORTED` (0.85) — Verified evidence unit demonstrating equivalent core competency.
  - `RELATED` (0.70) — Adjacent transferable technology cluster (e.g., FastAPI for Django requirement).
  - `PARTIAL` (0.50) — High semantic narrative overlap across candidate projects.
  - `WEAK` (0.30) — Minimal keyword overlap.
  - `MISSING` (0.00) — Qualification absent from candidate history (isolated into gap roadmap).
  - `CONFLICTING` (0.00) — Contradictory requirement (e.g., active Top Secret clearance absent).

### 5. 🛡️ Truth Guard Resume Tailoring & 1-Page Export
- **Grounded Bullet Generation**: Constrains LLM tailoring to candidate source evidence units; prevents hallucination of unworked technologies.
- **Deterministic 1-Page Budget Engine**: Dynamically calculates content density and enforces line-budget constraints per experience item.
- **Enterprise PDF/DOCX Templates**:
  - `harvard` — Classic serif with horizontal rule dividers and right-aligned dates.
  - `stanford` / `technical` — Modern high-density sans-serif with bold tech keywords.
  - `modern` / `classic` — Balanced spacing with prominent headers and section accents.

### 6. 💼 Real-Time Filterable Jobs & Internships
- **Deterministic 3-Tier Match Engine**:
  - 50% Required Skill Match (exact token + semantic alias overlap).
  - 30% Role Title Semantic Similarity.
  - 20% Experience Level & Location Fit.
- **WhyScoreModal**: Complete mathematical formula breakdown explaining score calculations.
- **Multi-Filter Search**: Target Role, LPA/Stipend, Workplace (`Remote Only`, `Hybrid`, `Onsite`), and Freshness.

### 7. 🎙️ Top 20 Discipline-Specific Interview Preparation
- Curated Top 20 question banks across 6 technical tracks (*Full Stack*, *Backend*, *Frontend*, *Data Science/ML*, *DevOps/Cloud*, *Core Software Engineering*).
- 3 structured interview rounds (Technical, Managerial, HR) with STAR hints, strategy breakdowns, sample answers, and pitfalls.
- Interactive 2-minute mock answer practice timer with a scratchpad and browser-persisted bookmarking.

### 8. 🤖 Career Copilot & CRM Application Pipeline
- **Conversational Career Strategist**: Grounded assistant for STAR formatting, cold outreach scripts, and resume bullet metric quantification.
- **Kanban Pipeline CRM**: Tracks applications through authentic workflow states (`SAVED` $\rightarrow$ `TAILORED` $\rightarrow$ `APPLIED` $\rightarrow$ `INTERVIEW` $\rightarrow$ `OFFER`).

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.12+**
- **Node.js 20+** & **npm**
- **MongoDB** (Local instance or Docker container)
- *(Optional)* [Ollama](https://ollama.com) or [LM Studio](https://lmstudio.ai) for local LLM inference

---

### 1. Database (MongoDB)

```bash
# Start MongoDB via Docker Compose
docker compose up -d
```

---

### 2. Backend (FastAPI)

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
# source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Run full automated test suite (495+ tests)
pytest

# Start FastAPI development server
uvicorn app.main:app --reload --port 8000
```

- **API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### 3. Frontend (React + Vite)

```bash
# Navigate to frontend directory in a new terminal
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server
npm run dev
```

- **Frontend Application**: [http://localhost:5173](http://localhost:5173)

---

### 4. ⚡ 1-Click Quick Demo Sign-In

1. Open [http://localhost:5173/login](http://localhost:5173/login).
2. Click **"⚡ 1-Click Sign In as Demo Candidate"** (or enter `demo@example.com` / `Password123!`).
3. The dashboard loads instantly with pre-computed ATS scores, tailored resumes, top job matches, and interview preparation tracks.

---

## 📁 Repository Structure

```
roleradar/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py             # Environment configurations
│   │   │   ├── security.py           # JWT generation & bcrypt password hashing
│   │   │   └── ai_service/           # Provider-agnostic AI service, prompts & repair engine
│   │   ├── db/
│   │   │   └── mongo.py              # Motor MongoDB async client & index definitions
│   │   ├── modules/
│   │   │   ├── auth/                 # Authentication, JWT tokens & demo user auto-seed
│   │   │   ├── profile/              # Candidate profile, preferences & target roles
│   │   │   ├── resume/               # Phase 1 Geometry & Phase 2 Semantic Structurer
│   │   │   │   ├── models.py         # Canonical CandidateProfile & EvidenceUnit models
│   │   │   │   ├── ledger.py         # Atomic Evidence Ledger & provenance tracking
│   │   │   │   ├── parsing/          # 5-gate column detector & reading-order normalizer
│   │   │   │   └── export/           # ReportLab PDF & python-docx 1-page renderers
│   │   │   ├── jobs/                 # Phase 3 JD Reconstruction, Taxonomy & Skill Vocabulary
│   │   │   │   ├── taxonomy.py       # Generalized section reconstructor & JD analyzer
│   │   │   │   └── skill_vocabulary.py # Multi-domain technology taxonomy graph
│   │   │   ├── matching/             # Phase 4 Deterministic 8-Tier Evidence-to-JD Matcher
│   │   │   ├── tailoring/            # Truth Guard tailoring & validation engine
│   │   │   ├── applications/         # Kanban application tracker CRM
│   │   │   ├── learning/             # 4-sprint skill gap bridge & learning roadmaps
│   │   │   ├── interview/            # Role-specific question banks & practice timer
│   │   │   ├── chatbot/              # Career Copilot conversational AI strategist
│   │   │   └── intelligence/         # Role Readiness Index (RRI) & ATS scoring metrics
│   │   └── main.py                   # FastAPI application & startup lifecycle
│   ├── seeds/                        # Curated seed datasets
│   ├── tests/                        # Pytest automated test suite (495+ tests)
│   └── requirements.txt              # Backend Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/               # AppShell, Sidebar, AuthBrandPanel
│   │   │   ├── jobs/                 # JobMatchCard & WhyScoreModal
│   │   │   ├── resume/               # ResumePreviewModal, ATSScoreRadar, SkillBadgeGrid
│   │   │   └── ui/                   # ScoreRing, modals, buttons
│   │   ├── context/                  # AuthContext state management
│   │   ├── lib/                      # Axios API clients & typed service methods
│   │   ├── pages/                    # Lazy-loaded page components (Dashboard, Resume, Jobs, etc.)
│   │   ├── App.tsx                   # Route definitions & React.lazy code-splitting
│   │   ├── index.css                 # Clean SaaS light design system & micro-animations
│   │   └── main.tsx                  # Application bootstrap entry point
│   ├── package.json                  # Frontend dependencies
│   └── vite.config.ts                # Vite build & proxy configuration
└── docker-compose.yml                # MongoDB container orchestration
```

---

## 🔬 Technical Implementation Principles

1. **Deterministic Foundations Over LLM Guesswork**:
   - Parsing, layout geometry, section zoning, ATS scoring, and evidence mapping are strictly deterministic. LLMs are reserved solely for creative phrasing and natural language feedback.
2. **Provenance & Traceability**:
   - Every candidate evidence unit and JD requirement traces directly back to its originating document position, section heading, and raw text.
3. **Truth Guard Integrity**:
   - Master resumes remain immutable. Tailoring operations create isolated versions with strict hallucination checks against the candidate's verified evidence ledger.
4. **Offline-Safe Architecture**:
   - Deterministic rule engines ensure that all parsing, matching, ATS auditing, and template rendering functions operate fully offline without external cloud dependencies.
