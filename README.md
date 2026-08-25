# RoleRadar — AI Resume Intelligence & Career Acceleration Platform

RoleRadar is an AI career copilot and resume intelligence platform designed to eliminate rejection by ATS screening algorithms (Workday, Taleo, Greenhouse). Rather than generic scoring, RoleRadar identifies structural layout bottlenecks, semantic keyword gaps, and unquantified bullet points, tailoring 1-page format resumes grounded in verified candidate evidence without fabricating credentials.

---

## 🏛️ System Architecture

```
React 19 + Vite (TypeScript)  ──────►  FastAPI (Python 3.12)  ──────►  Modular Backend Engines
                                                                               │
                                                               ┌───────────────┼───────────────┐
                                                               ▼                               ▼
                                                        Business Logic                    AIService
                                                     (ATS Calculation,                         │
                                                      Truth Guard Tailor,                      ▼
                                                      Deterministic Matching)             AI Providers
                                                               │                           (Configurable)
                                                               ▼                               ▼
                                                           MongoDB                       Local / Cloud
                                                       (Motor Async)                  (Ollama / LM Studio)
```

### Technology Stack Decisions

| Layer | Technology | Rationale & Trade-offs |
|---|---|---|
| **Frontend** | React 19, Vite, TypeScript | Fast client-side rendering with React Query state caching and route-level code-splitting |
| **Styling** | Vanilla CSS + Tailwind CSS | Unified modern SaaS Light theme with Sora/Inter typography, card hover physics, and micro-animations |
| **Backend** | FastAPI + Pydantic v2 | High-throughput asynchronous REST API with strict runtime schema validation |
| **Database** | MongoDB + Motor | Document-oriented storage for flexible resume structures, match matrices, and application records |
| **AI Strategy** | `AIService` Provider Layer | Provider-agnostic abstraction (Ollama, LM Studio, Cloud fallback) with automated JSON repair-retry loop and deterministic fallback |
| **Bundle Optimization** | `React.lazy()` & `<Suspense>` | Route-level lazy loading reducing initial JavaScript bundle size to **266 kB** (84 kB gzipped) |

---

## 🌟 Modules & Features Actually Built

### 1. 📄 Master Resume & Strict Enterprise ATS Audit
- **Strict Screening Benchmark (0–100)**: Evaluates resumes against enterprise screening criteria (Workday, Taleo, Greenhouse).
- **4-Pillar Quality Breakdown**:
  - **ATS Parseability**: Deterministic check for single-column layout, standard section headings, and contact information integrity (Email, Phone, LinkedIn, GitHub).
  - **Recruiter Impact**: Computes the percentage of experience bullets containing quantified measurable metrics (numbers, percentages, scale).
  - **Action Verb Strength**: Identifies strong active engineering verbs vs weak/passive verbs.
  - **Domain-Separated Technical Stack**: Categorizes candidate skills into distinct groups: *Programming Languages*, *Frameworks & Web Tech*, *Databases & Storage*, *Cloud, Containers & DevOps*, and *Core CS & Tools*.

### 2. 🎯 Truth Guard Resume Tailoring & 1-Page Export
- **Truth Guard Integrity**: AI-proposed bullet rewrites are strictly constrained to candidate source evidence to prevent credential fabrication.
- **Company & Role Calibration**: Generates tailored summaries and bullet emphasis aligned with target company domains and job descriptions.
- **Strict 1-Page PDF/DOCX Exporter**:
  - Compact vertical layout (0.35–0.45 in margins, compact line heights).
  - Two-column title/company rows with right-aligned dates.
  - Formats: `harvard` (serif Times-Roman with classic rule dividers), `stanford` / `technical` (clean sans-serif), `modern`, and `classic`.

### 3. 💼 Real-Time Filterable Jobs & Internships
- **Deterministic 3-Tier Match Engine**:
  - 50% Required Skill Match (exact token + semantic alias overlap).
  - 30% Role Title Semantic Similarity (embedding vector cosine distance / lexical similarity).
  - 20% Experience Level & Location Fit.
- **WhyScoreModal**: Modal explaining the exact mathematical formula breakdown for each match.
- **Multi-Filter Bar**: Filter by Target Role, Minimum Compensation (LPA / Stipend), Workplace (`Remote Only`, `Hybrid`, `Onsite / Office`), and Experience level.
- **1-Click Quick Actions**: Direct action buttons on every job card (*Tailor Resume*, *Prep Interview*, *Ask Copilot*, and *Apply Directly*).

### 4. 🎙️ Discipline-Specific Top 20 Interview Preparation
- **Role-Specific Question Banks**: Curated Top 20 essential questions for:
  - 🌐 *Full Stack Developer*
  - ⚙️ *Backend Developer*
  - 🎨 *Frontend Developer*
  - 📊 *Data Scientist & ML Engineer*
  - 🚀 *DevOps & Cloud Engineer*
  - 💻 *Core Software Engineer*
- **3 Comprehensive Interview Rounds**: Structured into Technical, Managerial, and HR/Culture rounds with STAR hints, strategy breakdowns, sample answers, and pitfalls to avoid.
- **⏱️ 2-Minute Mock Answer Practice Timer**: Interactive countdown timer with a live talking-points scratchpad for practicing concise STAR responses.
- **Mastery Tracker & Bookmarks**: Progress bar tracking mastered questions (`Mastered: X/20`) and revision bookmarks persisted in browser storage.
- **Free Mock Platform Directory**: Curated links to free peer practice platforms (Pramp, interviewing.io, LeetCode Discuss).

### 5. 🤖 Career Copilot (Grounded AI Strategist)
- **Grounded Career Guidance**: Personalized AI assistant answering queries on resume bullet metrics, missing skill roadmaps, STAR frameworks, and cold outreach.
- **Interactive UI**: 1-click starter suggestion chips, animated 3-dot typing indicator (`animate-bounce`), structured Markdown formatting, and 1-click Markdown export.

### 6. 📊 Application Pipeline CRM Tracker
- **Kanban Pipeline**: Tracks job applications through authentic workflow stages:
  `SAVED` $\rightarrow$ `TAILORED` $\rightarrow$ `QUEUED` $\rightarrow$ `APPLIED` $\rightarrow$ `VIEWED` $\rightarrow$ `INTERVIEW` $\rightarrow$ `OFFER` (with `REJECTED` and `WITHDRAWN` options).
- **Duplicate Detection**: Prevents duplicate applications to the same role and company.

### 7. 🗺️ 4-Sprint Skill Gap Bridge & Learning Roadmap
- **Deterministic Gap Detection**: Compares candidate master resume skills against target role requirements.
- **Structured 4-Sprint Plan**: Breaks missing competencies into weekly milestones with curated learning topics and project implementation goals.

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

# Start FastAPI development server
uvicorn app.main:app --reload --port 8000
```

- **API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

> [!NOTE]
> On startup, the backend automatically seeds `demo@example.com` / `Password123!` with a complete Full Stack profile and Master Resume.

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
3. The dashboard will load with pre-computed ATS scores, top job matches, and interview preparation data.

---

## 📁 Repository Structure

```
roleradar/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py             # Environment configurations
│   │   │   ├── security.py           # JWT generation & bcrypt password hashing
│   │   │   └── ai_service/           # Provider-agnostic AI service & fallback engine
│   │   ├── db/
│   │   │   └── mongo.py              # Motor MongoDB async client & index definitions
│   │   ├── modules/
│   │   │   ├── auth/                 # Authentication, JWT tokens & demo user auto-seed
│   │   │   ├── profile/              # Candidate profile, preferences & target roles
│   │   │   ├── resume/               # Master resume parser, ATS auditor & skill categorizer
│   │   │   ├── jobs/                 # Curated dataset & Adzuna live job provider
│   │   │   ├── matching/             # Deterministic 3-tier ATS compatibility match engine
│   │   │   ├── tailoring/            # Truth Guard resume tailoring & 1-page PDF/DOCX exporter
│   │   │   ├── applications/         # Kanban application tracker CRM
│   │   │   ├── learning/             # 4-sprint skill gap bridge & learning roadmaps
│   │   │   ├── interview/            # Role-specific question banks & mock platform links
│   │   │   ├── chatbot/              # Career Copilot conversational AI strategist
│   │   │   └── intelligence/         # Role Readiness Index (RRI) & Dashboard KPI metrics
│   │   └── main.py                   # FastAPI application & startup lifecycle
│   ├── seeds/                        # Curated seed datasets
│   ├── tests/                        # Pytest automated test suite (70 tests)
│   └── requirements.txt              # Backend Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/               # AppShell, Sidebar, AuthBrandPanel
│   │   │   ├── jobs/                 # JobMatchCard & WhyScoreModal
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

## 🔬 Technical Implementation Notes (For Viva / Submission Defense)

1. **Deterministic Scoring Over LLM Guesswork**:
   - RoleRadar uses deterministic algorithms for ATS scoring, parseability, impact metrics, and job matching. AI (LLM) is reserved strictly for natural language tasks (tailoring bullet wording, formulating interview feedback, and Copilot Q&A).
2. **Local-First & Offline-Safe**:
   - The platform includes comprehensive fallback engines across all AI operations, ensuring the entire demonstration and testing pipeline works even without an active LLM endpoint or internet connection.
3. **Truth Guard Guarantee**:
   - The master resume is immutable. Every tailoring operation creates an isolated child version requiring candidate verification before export.
4. **Single-Page Optimization**:
   - PDF/DOCX templates are engineered with compact vertical budgets and right-aligned headers to prevent overflow past 1 page for early-career candidates.
