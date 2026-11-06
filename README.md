# RoleRadar

RoleRadar is a career-support web application for managing resumes, evaluating job fit, preparing applications, and practicing interviews. It combines a React and TypeScript single-page app with a FastAPI backend and MongoDB. Optional AI providers support features such as resume tailoring and the career copilot.

## What it does

- **Resume workspace:** upload and parse resumes, review ATS-oriented feedback, and create job-specific resume versions with PDF or DOCX export.
- **Job discovery and matching:** browse job and internship listings, save opportunities, and review match information.
- **Application tracking:** organize opportunities and follow application progress.
- **Career development:** review skill gaps, follow learning roadmaps, and practice role-focused interview questions.
- **Career copilot:** get assistance with career and application tasks using a configured AI provider.

The backend is organized into feature modules for authentication, profiles, resumes, jobs, matching, tailoring, intelligence, applications, learning, interviews, and the copilot. Deterministic parsing and matching code handles structured analysis; AI services are provided through a configurable provider layer.

## Technology

- **Frontend:** React, TypeScript, Vite, React Router, TanStack Query, Tailwind CSS
- **Backend:** Python, FastAPI, Pydantic, Motor (MongoDB)
- **Resume processing and export:** PyMuPDF, spaCy, ReportLab, python-docx
- **AI providers:** Ollama, LM Studio, or a configured cloud provider
- **Tests:** pytest and pytest-asyncio (backend)

## Requirements

- Python 3.11 or 3.12
- Node.js and npm
- MongoDB 7 (local installation or Docker)
- An AI provider is optional for the application overall, but required for features that make AI requests.

## Run locally

### 1. Configure the backend

From the repository root, create the backend environment file:

```bash
cp backend/.env.example backend/.env
```

On Windows PowerShell, use:

```powershell
Copy-Item backend/.env.example backend/.env
```

Review `backend/.env` and set values for the services you intend to use. The defaults point MongoDB to `mongodb://localhost:27017`. Choose an AI provider and configure its model/service; cloud providers also need their API key. For production, set `ENV=production` and replace `JWT_SECRET` with a cryptographically random secret of at least 32 characters.

### 2. Start MongoDB

With Docker Compose:

```bash
docker compose up -d mongo
```

Alternatively, start a local MongoDB instance that listens on the URI configured in `backend/.env`.

### 3. Install and start the backend

```bash
cd backend
python -m venv .venv
```

Activate the environment, then install dependencies and start the API:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API serves interactive documentation at [http://localhost:8000/docs](http://localhost:8000/docs). Check service status at [http://localhost:8000/api/health/live](http://localhost:8000/api/health/live) and dependency readiness at [http://localhost:8000/api/health/ready](http://localhost:8000/api/health/ready).

### 4. Install and start the frontend

In a second terminal, from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies `/api` requests to the backend on port 8000.

In development mode, backend startup seeds the job data and creates a demo user if one does not already exist. Use the credentials shown in the login screen or the backend seed implementation; change demo credentials and secrets before any production deployment. Production mode does not automatically create the demo user.

## Build and checks

Run these from their respective directories:

```bash
# Backend tests
cd backend
pytest

# Frontend production build and lint
cd ../frontend
npm run build
npm run lint
```

`npm run build` runs the TypeScript project build before creating the Vite bundle. When `frontend/dist` exists, FastAPI can serve the built single-page application as well as the API.

## Configuration

Backend settings are read from environment variables and `.env`; see [`backend/.env.example`](backend/.env.example) for the full list. Common settings include:

| Variable | Purpose |
| --- | --- |
| `MONGO_URI`, `MONGO_DB_NAME` | MongoDB connection and database |
| `JWT_SECRET`, `ENV` | Authentication secret and runtime environment |
| `AI_PROVIDER` | Select `ollama`, `lmstudio`, or `cloud_fallback` |
| `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | Local Ollama endpoint and model |
| `LMSTUDIO_BASE_URL`, `LMSTUDIO_MODEL` | Local LM Studio endpoint and model |
| `CLOUD_FALLBACK_PROVIDER`, `CLOUD_FALLBACK_API_KEY`, `CLOUD_FALLBACK_MODEL` | Cloud provider configuration |
| `JOB_SOURCE_MODE` and provider settings | Job feed behavior and configured sources |
| `PUBLIC_AGGREGATORS_ENABLED` | Enables the scheduled live fallback lane for fresher/internship coverage |
| `REMOTIVE_ENABLED`, `ARBEITNOW_ENABLED` | Zero-auth public remote job sources |
| `JSEARCH_RAPIDAPI_KEY`, `JOOBLE_API_KEY`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | Optional higher-volume aggregator credentials |
| `UPLOAD_DIR`, `GENERATED_DIR`, `MAX_UPLOAD_MB` | Resume file storage and upload limit |

Keep real credentials in your local environment file or deployment secret store. Do not commit them to version control.

For fresher and internship coverage, enable `PUBLIC_AGGREGATORS_ENABLED=true`. RoleRadar refreshes these sources out of band, stores the listing timestamp and source URL, and only uses them as a clearly disclosed fallback when no verified direct employer ATS listing is available. This keeps the normal feed fast while providing additional genuine live opportunities.

## Project layout

```text
backend/
  app/              FastAPI application, shared services, and feature modules
  seeds/            Seed data used by the application
  tests/            Backend tests
  requirements.txt  Python dependencies
frontend/
  src/              React pages, components, routes, and API clients
  package.json      Frontend scripts and dependencies
docs/
  operations.md     Backup, restore, and deployment operations guide
docker-compose.yml  Local MongoDB service
```

For database backup and restore guidance and deployment notes, see the [Operations Runbook](docs/operations.md).

## Production container

Build and run the self-contained release image with Docker Compose:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Set `JWT_SECRET`, `MONGO_INITDB_ROOT_PASSWORD`, and `CORS_ORIGINS` in a deployment secret store or an untracked `.env` file first. The image serves the compiled SPA and API together; terminate TLS and configure the public hostname at the reverse proxy or managed load balancer.
