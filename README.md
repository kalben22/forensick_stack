# ForensicStack

> **All-in-One DFIR Investigation Platform**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
![Status](https://img.shields.io/badge/status-alpha-orange.svg)

ForensicStack is a unified digital forensics investigation platform that orchestrates popular forensic tools — **iLEAPP**, **ALEAPP**, **ExifTool**, and **Volatility3** — under a single REST API. Each tool runs in an isolated Docker container, results are normalised into a common `Finding` format, stored in MinIO, and indexed in ChromaDB for semantic search.

---

## Architecture

```text
Investigator
    │
    │  HTTP  (JWT Bearer)
    ▼
┌─────────────────────────────────┐
│         FastAPI  (port 8080)     │
│  /auth  /cases  /artifacts       │
│  /jobs  /search                  │
└────────────┬────────────────────┘
             │  lpush → job_queue
             ▼
┌─────────────────────┐       ┌──────────────────────────────┐
│    Redis  (queue)   │──────▶│        Worker process         │
└─────────────────────┘       │  DockerExecutor.run_plugin()  │
                               │  ┌──────────────────────────┐│
                               │  │  docker run              ││
                               │  │  forensicstack/exiftool  ││
                               │  │  forensicstack/ileapp    ││
                               │  │  forensicstack/aleapp    ││
                               │  │  forensicstack/volatility││
                               │  └──────────────────────────┘│
                               │  normalize() → Finding[]      │
                               │  upload results → MinIO        │
                               │  index findings → ChromaDB     │
                               └──────────────────────────────┘

Infrastructure (docker-compose):
  PostgreSQL  — cases / artifacts / analyses metadata
  Redis       — job queue + job status store
  MinIO       — raw artifact files + analysis outputs (S3-compatible)
  ChromaDB    — vector store for semantic search (all-MiniLM-L6-v2)
```

---

## Prerequisites

| Requirement    | Version |
|----------------|---------|
| Python         | 3.11+   |
| Docker         | 24+     |
| Docker Compose | v2+     |
| Git            | any     |

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/kalben22/forensick_stack.git
cd forensick_stack
```

### 2. Configure environment

```bash
cd backend
cp .env.example .env
# Edit .env — change all passwords and generate a SECRET_KEY:
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start infrastructure

```bash
cd backend
docker compose up -d postgres redis minio chromadb
docker compose ps   # all should be "healthy"
```

### 4. Build forensic tool images

This is required **once** so the worker can run tools in containers:

```bash
# Linux / macOS
chmod +x scripts/build-tools.sh
./scripts/build-tools.sh

# Windows (PowerShell)
.\scripts\build-tools.ps1
```

Expected output:

```text
[build-tools] Building forensicstack/ileapp:0.1 ...      OK
[build-tools] Building forensicstack/aleapp:0.1 ...      OK
[build-tools] Building forensicstack/exiftool:0.1 ...    OK
[build-tools] Building forensicstack/volatility:0.1 ...  OK
```

> Note: iLEAPP and ALEAPP clone their repos from GitHub — first build takes a few minutes.

### 5. Install Python dependencies

```bash
cd backend
python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 6. Run the API

```bash
cd backend
uvicorn forensicstack.api.main:app --host 0.0.0.0 --port 8080 --reload
```

Interactive docs: [http://localhost:8080/docs](http://localhost:8080/docs)

### 7. Run the worker (separate terminal)

```bash
cd backend
source venv/bin/activate   # or .\venv\Scripts\Activate.ps1
python -m forensicstack.worker
```

---

## API Overview

All protected endpoints require `Authorization: Bearer <token>`.

### Auth

| Method | Endpoint        | Description                   |
|--------|-----------------|-------------------------------|
| POST   | `/auth/register` | Create an investigator account |
| POST   | `/auth/login`    | Get a JWT access token        |
| GET    | `/auth/me`       | Current user profile          |

```bash
# Register
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"analyst1","password":"S3cur3Pass!"}'

# Login and capture token
TOKEN=$(curl -s -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"analyst1","password":"S3cur3Pass!"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### Cases

| Method | Endpoint              | Description      |
|--------|-----------------------|------------------|
| POST   | `/api/v1/cases/`      | Create a case    |
| GET    | `/api/v1/cases/`      | List all cases   |
| GET    | `/api/v1/cases/{id}`  | Get case detail  |
| PATCH  | `/api/v1/cases/{id}`  | Update case      |
| DELETE | `/api/v1/cases/{id}`  | Delete case      |

```bash
CASE=$(curl -s -X POST http://localhost:8080/api/v1/cases/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Malware Investigation #001","description":"Suspected ransomware"}')
CASE_ID=$(echo $CASE | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
```

### Artifacts

| Method | Endpoint                              | Description                     |
|--------|---------------------------------------|---------------------------------|
| POST   | `/api/v1/cases/{id}/artifacts/`       | Upload a file to MinIO          |
| GET    | `/api/v1/cases/{id}/artifacts/`       | List artifacts                  |
| GET    | `/api/v1/cases/{id}/artifacts/{aid}`  | Detail + presigned download URL |
| DELETE | `/api/v1/cases/{id}/artifacts/{aid}`  | Delete artifact                 |

```bash
# Upload a memory dump
curl -X POST http://localhost:8080/api/v1/cases/$CASE_ID/artifacts/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/memory.dmp" \
  -F "artifact_type=memory_dump"
```

Supported `artifact_type` values: `memory_dump`, `disk_image`, `mobile_backup`, `pcap`, `logs`, `malware_sample`, `document`, `other`.

### Jobs (analysis)

| Method | Endpoint                   | Description              |
|--------|----------------------------|--------------------------|
| GET    | `/api/v1/jobs/tools`       | List available tools     |
| POST   | `/api/v1/jobs/submit`      | Submit an analysis job   |
| GET    | `/api/v1/jobs/{job_id}`    | Poll job status          |

```bash
# Submit a job
JOB=$(curl -s -X POST http://localhost:8080/api/v1/jobs/submit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool":"exiftool","artifact_id":1}')
JOB_ID=$(echo $JOB | python -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

# Poll until completed
curl http://localhost:8080/api/v1/jobs/$JOB_ID -H "Authorization: Bearer $TOKEN"
```

Available tools: `exiftool`, `ileapp`, `aleapp`, `volatility`.

### Semantic Search

| Method | Endpoint                     | Description               |
|--------|------------------------------|---------------------------|
| POST   | `/api/v1/search/semantic`    | Natural language search   |
| GET    | `/api/v1/search/stats`       | ChromaDB collection stats |

```bash
curl -X POST http://localhost:8080/api/v1/search/semantic \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"suspicious process injection into lsass","top_k":10}'
```

---

## Running Tests

```bash
cd backend
pip install pytest httpx

# All tests
pytest tests/ -v

# API tests only (mocked services — no Docker needed)
pytest tests/test_api.py -v

# Tool-level tests (checks local binaries + YARA)
pytest tests/test_tools.py -v

# With coverage
pytest tests/ --cov=forensicstack --cov-report=html
```

---

## Project Structure

```text
forensick_stack/
├── backend/
│   ├── Dockerfile                         # Backend + worker image
│   ├── docker-compose.yml                 # Full infrastructure stack
│   ├── .env.example                       # Environment template
│   ├── requirements.txt
│   └── forensicstack/
│       ├── api/
│       │   ├── main.py                    # FastAPI app (29 routes)
│       │   ├── schemas.py                 # Pydantic request/response models
│       │   ├── jobs.py                    # Redis queue helpers
│       │   └── routes/
│       │       ├── auth.py                # /auth/*
│       │       ├── cases.py               # /api/v1/cases/*
│       │       ├── artifacts.py           # /api/v1/cases/{id}/artifacts/*
│       │       ├── analysis.py            # /api/v1/analysis/*
│       │       ├── jobs.py                # /api/v1/jobs/*
│       │       └── search.py              # /api/v1/search/*
│       ├── core/
│       │   ├── auth.py                    # JWT helpers + FastAPI dependency
│       │   ├── database.py                # SQLAlchemy engine + session
│       │   ├── crud.py                    # DB operations
│       │   ├── minio_service.py           # MinIO client (singleton)
│       │   ├── chroma_service.py          # ChromaDB client (singleton)
│       │   ├── plugin_registry.py         # Tool → Docker image mapping
│       │   ├── normalization_engine.py    # Routes output_dir → normalizer
│       │   ├── models/
│       │   │   ├── orm_models.py          # Case, Artifact, Analysis
│       │   │   ├── user_model.py          # User (auth)
│       │   │   └── finding_models.py      # Finding dataclass
│       │   ├── normalizers/               # Per-tool output parsers
│       │   └── executor/
│       │       └── docker_executor.py     # docker run wrapper
│       ├── plugins/
│       │   └── external/                  # Dockerised forensic tools
│       │       ├── ileapp/                # Dockerfile + entrypoint.sh
│       │       ├── aleapp/                # Dockerfile + entrypoint.sh
│       │       ├── exiftool/              # Dockerfile + entrypoint.sh
│       │       └── volatility/            # Dockerfile + entrypoint.sh
│       └── worker.py                      # Redis queue consumer
├── scripts/
│   ├── build-tools.sh                     # Build tool images (Linux/macOS)
│   └── build-tools.ps1                    # Build tool images (Windows)
└── README.md
```

---

## Tools

| Tool         | Category         | Mechanism        | Docker Image                   |
|--------------|------------------|------------------|--------------------------------|
| ExifTool     | Metadata         | Docker container | `forensicstack/exiftool:0.1`   |
| iLEAPP       | iOS forensics    | Docker container | `forensicstack/ileapp:0.1`     |
| ALEAPP       | Android forensics | Docker container | `forensicstack/aleapp:0.1`    |
| Volatility3  | Memory forensics | Docker container | `forensicstack/volatility:0.1` |

All containers run with:

- `--network none` (no internet access during analysis)
- `--cap-drop=ALL` (minimum privileges)
- `--read-only` filesystem + tmpfs for /tmp
- Resource limits (`--memory`, `--cpus`, `--pids-limit`)

---

## Roadmap

### Phase 1 — Backend Foundation (current)

- [x] FastAPI with JWT authentication
- [x] Case and artifact management
- [x] MinIO artifact storage with MD5/SHA256 hashing
- [x] Redis job queue + worker
- [x] Docker-isolated forensic tool execution (ExifTool, iLEAPP, ALEAPP, Volatility3)
- [x] Normalised `Finding` output format
- [x] ChromaDB semantic search over findings
- [x] REST API (29 endpoints, Swagger docs)

### Phase 2 — Additional Tools (Q3 2026)

- [ ] Plaso / log2timeline integration via Docker
- [ ] YARA scanning pipeline
- [ ] Network forensics (Zeek, Wireshark via Docker)
- [ ] Windows artefact plugins (Registry, Event Logs, Prefetch)

### Phase 3 — Frontend (Q4 2026)

- [ ] React web interface
- [ ] Case timeline visualisation
- [ ] Investigation dashboard

### Phase 4 — AI Agents (2027)

- [ ] Investigation Copilot (Claude API)
- [ ] Automated triage and classification
- [ ] Report generation

---

## Security

ForensicStack handles sensitive forensic data. Follow these practices:

- Never commit `.env` to version control — it contains secrets
- Use strong randomly generated passwords for all services
- Each forensic tool runs in an isolated container with no network access
- All artifacts are hashed (MD5 + SHA256) on upload
- JWT tokens expire after 24 hours by default

---

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE).

### Third-Party Tools

- [iLEAPP](https://github.com/abrignoni/iLEAPP) — iOS Logs, Events, And Plists Parser (MIT)
- [ALEAPP](https://github.com/abrignoni/ALEAPP) — Android Logs, Events, And Plists Parser (MIT)
- [ExifTool](https://exiftool.org/) — libimage-exiftool-perl (Artistic / GPL)
- [Volatility3](https://github.com/volatilityfoundation/volatility3) — Volatility Software License

---

**Built for the DFIR community.**
