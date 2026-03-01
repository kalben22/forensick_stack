# ForensicStack

> **All-in-One DFIR Investigation Platform**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
![Status](https://img.shields.io/badge/status-alpha-orange.svg)

ForensicStack orchestrates **iLEAPP**, **ALEAPP**, **ExifTool**, and **Volatility 3** under a single web interface. Each tool runs in an isolated Docker container. Results are normalised into a common `Finding` format, stored in MinIO, and indexed in ChromaDB for semantic search.

---

## Prerequisites

| Requirement      | Version  | Install |
|------------------|----------|---------|
| Python           | 3.11+    | [python.org](https://www.python.org/downloads/) |
| Node.js          | 18+      | [nodejs.org](https://nodejs.org/) |
| Docker           | 24+      | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Docker Compose   | v2+      | bundled with Docker Desktop |
| Git              | any      | [git-scm.com](https://git-scm.com/) |

---

## Quick Setup

### Automated (recommended)

```bash
# Linux / macOS
git clone https://github.com/kalben22/forensick_stack.git
cd forensick_stack
chmod +x scripts/setup.sh
./scripts/setup.sh
```

```powershell
# Windows (PowerShell — run as Administrator)
git clone https://github.com/kalben22/forensick_stack.git
cd forensick_stack
.\scripts\setup.ps1
```

The script handles everything: `.env` files, `SECRET_KEY` generation, Docker infrastructure, forensic tool images, Python venv, and frontend dependencies.

---

### Manual Setup (step by step)

#### 1. Clone

```bash
git clone https://github.com/kalben22/forensick_stack.git
cd forensick_stack
```

#### 2. Backend — environment file

```bash
cd backend
cp .env.example .env
```

Open `.env` and:
- Change all `change_me_*` passwords to strong random values
- Generate a `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

#### 3. Start infrastructure (Docker)

```bash
cd backend
docker compose up -d postgres redis minio chromadb
docker compose ps   # all services should show "healthy"
```

> ChromaDB takes ~30 s to become ready on first start.

#### 4. Build forensic tool images

Required **once** before running any analysis:

```bash
# Linux / macOS
chmod +x ../scripts/build-tools.sh
../scripts/build-tools.sh

# Windows (PowerShell)
..\scripts\build-tools.ps1
```

Expected output:
```
[build-tools] Building forensicstack/ileapp:0.1 ...      OK
[build-tools] Building forensicstack/aleapp:0.1 ...      OK
[build-tools] Building forensicstack/exiftool:0.1 ...    OK
[build-tools] Building forensicstack/volatility:0.1 ...  OK
```

#### 5. Backend — Python environment

```bash
cd backend

python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

#### 6. Run the API

```bash
# Inside backend/ with venv active
uvicorn forensicstack.api.main:app --host 0.0.0.0 --port 8001 --reload
```

Swagger docs: [http://localhost:8001/docs](http://localhost:8001/docs)

#### 7. Run the worker (separate terminal)

```bash
cd backend
source venv/bin/activate   # or .\venv\Scripts\Activate.ps1
python -m forensicstack.worker
```

#### 8. Frontend — environment file

```bash
cd web
cp .env.local.example .env.local
```

> `.env.local` is already configured to connect to `http://127.0.0.1:8001`. Change the URL only if your backend runs on a different host or port.

#### 9. Frontend — install and run

```bash
cd web

# ✅ Use npm ci for reproducible installs (reads package-lock.json exactly)
npm ci

# Development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) — log in with the account you created via the API.

#### 10. Create your first user

```bash
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"analyst","password":"YourStrongPassword!"}'
```

---

## ⚠ npm — Critical Rules

```bash
# ✅ CORRECT — for fresh installs and deployments
npm ci

# ✅ CORRECT — for local development only
npm install

# ❌ NEVER RUN THIS — upgrades packages across major versions and breaks the build
npm audit fix --force
```

`npm audit fix --force` has been known to upgrade Next.js from v14 → v16 (incompatible with Tailwind v4) and break the entire frontend. **Never use it.** To address audit warnings, upgrade packages manually and test the build.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│           Next.js Frontend  (port 3000)              │
│   Dashboard · Tools · Jobs · Findings · Timeline     │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP / JWT Bearer
                       ▼
┌─────────────────────────────────────────────────────┐
│           FastAPI Backend  (port 8001)               │
│   /auth  /api/v1/jobs  /api/v1/cases                 │
│   /api/v1/artifacts  /api/v1/search                  │
└──────┬──────────────────────────────────────────────┘
       │ lpush → job_queue
       ▼
┌──────────────┐     ┌──────────────────────────────────┐
│  Redis queue │────▶│  Worker process                   │
└──────────────┘     │  DockerExecutor.run_plugin()      │
                     │  ┌────────────────────────────┐   │
                     │  │  docker run                │   │
                     │  │  forensicstack/exiftool    │   │
                     │  │  forensicstack/ileapp      │   │
                     │  │  forensicstack/aleapp      │   │
                     │  │  forensicstack/volatility  │   │
                     │  └────────────────────────────┘   │
                     │  normalize() → Finding[]           │
                     │  store results → Redis + MinIO     │
                     └──────────────────────────────────┘

Infrastructure (docker compose):
  PostgreSQL  :5433  — metadata (cases, artifacts, analyses)
  Redis       :6379  — job queue + job status
  MinIO       :9000  — artifact files + analysis outputs
  ChromaDB    :8000  — vector store for semantic search
```

---

## Ports Reference

| Service     | Host Port | Notes |
|-------------|-----------|-------|
| **Frontend** | 3000 | `npm run dev` or `npm start` |
| **Backend API** | 8001 | uvicorn, local dev |
| PostgreSQL  | 5433 | configured in `.env` |
| Redis       | 6379 | configured in `.env` |
| MinIO API   | 9000 | S3-compatible endpoint |
| MinIO Console | 9001 | web UI at [localhost:9001](http://localhost:9001) |
| ChromaDB    | 8000 | vector search |

---

## Project Structure

```
forensick_stack/
├── backend/
│   ├── Dockerfile
│   ├── docker-compose.yml          # PostgreSQL, Redis, MinIO, ChromaDB
│   ├── .env.example                # Environment template — copy to .env
│   ├── requirements.txt
│   └── forensicstack/
│       ├── api/
│       │   ├── main.py             # FastAPI app entry point
│       │   ├── jobs.py             # Redis queue helpers
│       │   └── routes/
│       │       ├── auth.py         # POST /auth/register, /auth/login
│       │       ├── cases.py        # /api/v1/cases/*
│       │       ├── artifacts.py    # /api/v1/cases/{id}/artifacts/*
│       │       ├── jobs.py         # /api/v1/jobs/* (tools + submit + direct)
│       │       └── search.py       # /api/v1/search/*
│       ├── core/
│       │   ├── auth.py             # JWT + bcrypt
│       │   ├── database.py         # SQLAlchemy (postgresql://:8001 → psycopg2)
│       │   ├── plugin_registry.py  # tool → Docker image + features mapping
│       │   ├── normalization_engine.py
│       │   ├── normalizers/        # per-tool output parsers
│       │   └── executor/
│       │       └── docker_executor.py
│       ├── plugins/
│       │   └── external/           # Dockerised forensic tools
│       │       ├── ileapp/         # Dockerfile + entrypoint.sh
│       │       ├── aleapp/
│       │       ├── exiftool/
│       │       └── volatility/     # VOLATILITY_PLUGIN env var → single plugin
│       └── worker.py               # Redis queue consumer
│
├── web/                            # Next.js 14 frontend
│   ├── .env.local.example          # copy to .env.local
│   ├── package.json                # pinned versions — do NOT npm audit fix --force
│   ├── app/
│   │   ├── (auth)/login/           # login page
│   │   └── (dashboard)/
│   │       ├── page.tsx            # home — platform intro + tools grid
│   │       ├── tools/[slug]/       # tool detail — features + upload + results
│   │       ├── jobs/               # job history
│   │       ├── findings/
│   │       ├── timeline/
│   │       ├── storage/
│   │       └── reports/
│   ├── components/
│   │   ├── tools/
│   │   │   ├── tool-detail-page.tsx   # feature list + upload + live results
│   │   │   └── tools-catalog-content.tsx
│   │   └── dashboard/
│   └── lib/
│       ├── api/                    # axios API client
│       └── hooks/                  # React Query hooks
│
└── scripts/
    ├── setup.sh                    # automated setup (Linux/macOS)
    ├── setup.ps1                   # automated setup (Windows)
    ├── build-tools.sh              # build forensic Docker images (Linux/macOS)
    └── build-tools.ps1             # build forensic Docker images (Windows)
```

---

## API Overview

All protected endpoints require `Authorization: Bearer <token>`.

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create an account |
| POST | `/auth/login` | Get a JWT token |
| GET  | `/auth/me` | Current user profile |

### Jobs (analysis)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/v1/jobs/tools` | List tools + features |
| POST | `/api/v1/jobs/direct` | Upload file + run analysis (multipart) |
| GET  | `/api/v1/jobs/{job_id}` | Poll job status + results |

### Direct Analysis (used by the UI)

```bash
curl -X POST http://localhost:8001/api/v1/jobs/direct \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@memory.raw" \
  -F "tool=volatility" \
  -F "feature=windows.pslist"
```

Available tools and features: `GET /api/v1/jobs/tools`

---

## Running Tests

```bash
cd backend
source venv/bin/activate

# All tests (no Docker needed — services are mocked)
pytest tests/ -v

# With coverage
pytest tests/ --cov=forensicstack --cov-report=html
```

---

## Tools

| Tool | Category | Docker Image | Accepted Input |
|------|----------|--------------|----------------|
| Volatility 3 | Memory | `forensicstack/volatility:0.1` | `.raw` `.dmp` `.vmem` `.mem` `.lime` |
| ExifTool | Metadata | `forensicstack/exiftool:0.1` | any file |
| iLEAPP | iOS | `forensicstack/ileapp:0.1` | `.tar` `.zip` `.tar.gz` |
| ALEAPP | Android | `forensicstack/aleapp:0.1` | `.tar` `.zip` `.ab` |

All containers run with `--network none`, `--cap-drop=ALL`, read-only filesystem, and resource limits.

---

## Roadmap

### Phase 1 — Backend (complete)
- [x] FastAPI + JWT authentication
- [x] Case and artifact management
- [x] Redis job queue + worker
- [x] Docker-isolated forensic tool execution
- [x] Normalised `Finding` output
- [x] ChromaDB semantic search

### Phase 2 — Frontend (complete)
- [x] Next.js 14 web interface
- [x] Tool-centric UI (features + upload + live results)
- [x] Job polling with live status updates
- [x] Direct analysis endpoint (no case required)

### Phase 3 — Additional Tools (Q3 2026)
- [ ] Plaso / log2timeline
- [ ] YARA scanning pipeline
- [ ] Network forensics (Zeek)
- [ ] Windows artefacts (Registry, Event Logs, Prefetch)

### Phase 4 — AI Copilot (2027)
- [ ] Investigation assistant (Claude API)
- [ ] Automated triage and report generation

---

## Security

- Never commit `.env` or `.env.local` — both are gitignored
- Generate a strong `SECRET_KEY` (64-char hex) for each deployment
- JWT tokens expire after 24 hours
- Each forensic tool runs in an isolated container with no network access

---

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE).

**Built for the DFIR community.**
