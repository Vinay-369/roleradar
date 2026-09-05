# RoleRadar Operations & Deployment Runbook

This document provides operational guidelines for database backups, data restoration, production configuration, and Single Page Application (SPA) frontend routing.

---

## 1. Database Architecture & Backup Strategy

### What RoleRadar Stores in MongoDB
RoleRadar organizes candidate data, job market intelligence, and AI operations into collections within the `roleradar` database:

| Collection | Description | Backup Priority |
|---|---|---|
| `users` | User credentials, email, password hash (bcrypt), onboarding status | **Critical** |
| `profiles` | Candidate preferences, target roles, salary/stipend targets, locations | **Critical** |
| `master_resumes` | Versioned parsed master resume JSON, extracted sections, ATS audit findings | **Critical** |
| `resume_versions` | Job-tailored resume versions, change ledger, evidence mappings | **Critical** |
| `applications` | Application tracker records, stage progression, notes | **Critical** |
| `jobs` | Seeded and live opportunity postings, required skills, salary/stipend metadata | **High** |
| `job_matches` | Multidimensional match scores between users and jobs (cached) | Medium (recomputable) |
| `skill_gaps` | Candidate-to-opportunity skill gap evaluations (cached) | Medium (recomputable) |
| `learning_paths` | Generated learning milestones and skill roadmaps | **High** |
| `achievements` | Candidate achievements and portfolio highlights | **High** |
| `interview_sessions`| Practice interview question responses and AI feedback | **High** |
| `chat_conversations`| Career Copilot multi-session message history | **High** |
| `audit_logs` | Security and authentication event audit trail | **High** |

---

## 2. Backup & Restore Procedures

### A. Environment Configuration
The database connection is configured via the `MONGO_URI` and `MONGO_DB_NAME` environment variables.

> [!WARNING]
> Never hardcode or commit database connection strings containing credentials into Git. Pass `MONGO_URI` securely via your deployment environment or secret manager.

- **Local Development**: `mongodb://localhost:27017`
- **Production / Cloud**: `mongodb+srv://<username>:<password>@cluster.mongodb.net/roleradar?retryWrites=true&w=majority`

### B. Backup Procedure (`mongodump`)
To create an encrypted, compressed snapshot of the production database:

```bash
# Set timestamp and backup target directory
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/roleradar/${BACKUP_DATE}"

# Execute mongodump using connection URI
mongodump --uri="${MONGO_URI}" --db="${MONGO_DB_NAME:-roleradar}" --gzip --out="${BACKUP_DIR}"

# (Recommended) Encrypt backup archive with GPG/AES-256 before remote upload
tar -czf - -C "${BACKUP_DIR}" . | gpg --symmetric --cipher-algo AES256 --output "/var/backups/roleradar/roleradar_${BACKUP_DATE}.tar.gz.gpg"
```

### C. Restore Procedure (`mongorestore`)
To restore from a compressed archive:

```bash
# 1. Unpack archive (if encrypted/compressed)
gpg --decrypt "/var/backups/roleradar/roleradar_20260902_120000.tar.gz.gpg" | tar -xzf - -C "/tmp/restore_target"

# 2. Execute mongorestore (preserves existing data or specify --drop to replace)
mongorestore --uri="${MONGO_URI}" --db="${MONGO_DB_NAME:-roleradar}" --gzip "/tmp/restore_target/roleradar"

# 3. Clean up temporary decryption directory
rm -rf "/tmp/restore_target"
```

### D. Restore Verification Procedure
After performing a restore into a staging or validation instance:
1. Verify database connectivity: `python -c "import asyncio; from app.db.mongo import connect_to_mongo; asyncio.run(connect_to_mongo())"`
2. Verify collection counts: Check that `users`, `master_resumes`, and `jobs` contain expected record counts.
3. Run backend test suite: `pytest backend/tests/test_phase9_production_hardening.py`
4. Confirm user login and token decoding.

### E. Recommended Backup Frequency & Storage
- **Frequency**: Daily full snapshot with point-in-time oplog backups (e.g. MongoDB Atlas Continuous Backups or automated daily cron).
- **Storage**: Offsite encrypted object storage (e.g. AWS S3 Glacier, Google Cloud Storage, or Azure Blob with server-side encryption and 30-day retention policy).
- **Difference from Local Development**: Local environments rely on volatile ephemeral data or local Docker volumes; production requires isolated, encrypted, and append-only offsite snapshots.

---

## 3. Production Frontend SPA Deployment & Deep-Link Routing

RoleRadar's frontend is a Single Page Application built with React and React Router (`react-router-dom`).

### The Deep-Link Challenge
In standard static web hosting, requesting `/` serves `index.html`. However, when a user accesses a deep link directly (e.g., refreshing `/app/dashboard`, `/app/jobs`, `/app/resume/master`, or `/app/growth/roadmap`), the web server must rewrite the request to return `index.html` with HTTP 200 rather than returning a 404 error, allowing React Router to handle client-side rendering.

### A. Nginx Reverse Proxy Configuration
Below is the standard production Nginx server block serving the compiled frontend (`dist/`) while proxying `/api/` traffic to the FastAPI/Uvicorn backend:

```nginx
server {
    listen 80;
    server_name roleradar.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name roleradar.example.com;

    ssl_certificate /etc/letsencrypt/live/roleradar.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/roleradar.example.com/privkey.pem;

    root /var/www/roleradar/frontend/dist;
    index index.html;

    # Gzip Compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml image/svg+xml;

    # Frontend Single Page Application Routing
    # Any route that is not a static asset falls back to index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend API Reverse Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        client_max_body_size 10M;
    }
}
```

### B. Modern Cloud Platforms (Rewrites)
- **Vercel**: Add `vercel.json` rewrite:
  ```json
  {
    "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
  }
  ```
- **Netlify**: Add `_redirects` file in `public/`:
  ```text
  /*    /index.html   200
  ```
- **Cloudflare Pages**: Automatically falls back to `index.html` for single-page applications.

---

## 4. Production Environment Configuration Checklist

Before launching the production stack, ensure the following environment variables are supplied:

| Variable | Description | Example / Requirement |
|---|---|---|
| `ENV` | Application environment mode | `production` |
| `DEBUG` | Debug mode flag | `false` |
| `JWT_SECRET` | 256-bit cryptographically secure signing secret | Minimum 32 random characters (enforced at startup) |
| `CORS_ORIGINS` | Allowed frontend origins (JSON array) | `["https://roleradar.example.com"]` |
| `MONGO_URI` | Production MongoDB cluster connection string | `mongodb+srv://...` |
| `MONGO_DB_NAME`| Target MongoDB database name | `roleradar_production` |
| `AI_PROVIDER` | Active AI provider runtime | `ollama` (self-hosted) or `cloud_fallback` |
| `CLOUD_FALLBACK_PROVIDER` | Cloud LLM provider | `gemini` or `openai` |
| `CLOUD_FALLBACK_API_KEY` | Production API key for cloud LLM | Secret API token |
| `CLOUD_FALLBACK_MODEL` | Target model name | `gemini-2.5-flash` |
| `RATE_LIMITING_ENABLED`| Global rate limiting switch | `true` |
| `AUTH_RATE_LIMIT_MAX_REQUESTS` | Maximum unauthenticated login/register attempts per IP window | `10` |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS`| Sliding rate limit window duration in seconds | `60` |
| `MAX_UPLOAD_MB` | Maximum allowed resume upload size | `5` |

---

## 5. Live Opportunity Provider Synchronization (Decoupled in Phase 16C)

In Phase 16C, live opportunity provider synchronization (`refresh_live_jobs()`) was permanently decoupled from synchronous user discovery requests (`GET /matching/recommended` and `GET /jobs`).

### Architectural Behavior
- **User Discovery Path**: Queries indexed MongoDB opportunity documents directly (<25ms). No synchronous HTTP calls to external ATS platforms (Greenhouse, Lever, SmartRecruiters, or Adzuna) occur during user requests.
- **Provider Synchronization Path**: Live opportunity ingestion is triggered independently out-of-band.

### Triggering Provider Synchronization
Provider synchronization can be triggered on-demand or via scheduled jobs:

1. **Authenticated API Endpoint**:
   ```bash
   POST /api/jobs/sync
   Authorization: Bearer <token>
   ```
   Returns:
   ```json
   {
     "status": "success",
     "added_count": 5
   }
   ```

2. **Automated Scheduled Ingestion (Cron / Celery / Task Scheduler)**:
   Set up a recurring worker or cron job (e.g., every 2–4 hours) to invoke the sync endpoint or directly execute the provider refresh script:
   ```bash
   # Example crontab (every 2 hours)
   0 */2 * * * curl -X POST https://api.roleradar.example.com/api/jobs/sync -H "Authorization: Bearer $SYNC_SERVICE_TOKEN"
   ```

---

## 6. Authentication Rate Limiting

Unauthenticated authentication endpoints are protected by sliding-window rate limiting to prevent brute-force attacks:
- `POST /api/auth/login`
- `POST /api/auth/register`

### Features:
- **IP-Based Keying**: Identifies unauthenticated clients via `X-Forwarded-For`, `X-Real-IP`, or direct socket client address without requiring bearer tokens.
- **Configurable Limits**: Default is 10 requests per 60 seconds (`AUTH_RATE_LIMIT_MAX_REQUESTS=10`, `AUTH_RATE_LIMIT_WINDOW_SECONDS=60`).
- **HTTP 429 Response**: Returns `429 Too Many Requests` with standard `Retry-After` header when exceeded.

