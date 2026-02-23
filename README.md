# ForensicStack 🔬

> **All-in-One DFIR Investigation Platform with AI-Powered Agents**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)]()

ForensicStack is a unified digital forensics investigation platform that orchestrates popular forensic tools (Volatility, Plaso, Eric Zimmerman Tools, RegRipper) under a single, modern interface. With AI-powered investigation agents, automated timeline correlation, and professional report generation.

---

## 🌟 Features

### Core Capabilities
- 🤖 **AI Investigation Copilot** - Conversational agents guide you through investigations
- 🔧 **20+ Integrated Tools** - Volatility, Plaso, RegRipper, Eric Zimmerman Tools, and more
- 📊 **Automated Timeline Generation** - Super-timeline creation with intelligent correlation
- 📝 **Professional Report Generation** - Executive summaries and technical reports
- 💻 **Multi-Interface** - CLI, Web UI, and Desktop application
- 🔌 **Modular Architecture** - Plugin system for easy extensibility
- 🔐 **Chain of Custody** - Automated hashing, timestamping, and audit logs
- 🌐 **Multi-User Collaboration** - Work together on complex investigations

### AI Agents
- **Investigation Copilot** - Main conversational assistant
- **Triage Agent** - Prioritization and initial analysis
- **Malware Analysis Agent** - Specialized in malware detection and analysis
- **Incident Response Agent** - Guided IR workflows
- **Timeline Analyst** - Intelligent event correlation
- **Report Writer** - Automated narrative generation
- **Threat Intelligence Agent** - IoC enrichment and attribution

---

## 🏗️ Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   CLIENT INTERFACES                      │
├───────────────┬─────────────────┬──────────────────────┤
│   CLI Tool    │   Web Browser   │   Desktop App        │
│   (Typer)     │   (React)       │   (Tauri)            │
└───────┬───────┴────────┬────────┴──────────┬───────────┘
        │                │                   │
        └────────────────┼───────────────────┘
                         │
            ┌────────────▼──────────────┐
            │      REST API              │
            │      (FastAPI)             │
            └────────────┬──────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼────┐     ┌────▼────┐     ┌────▼────┐
   │  Core   │     │   AI    │     │  Plugin │
   │ Engine  │     │ Agents  │     │ System  │
   └────┬────┘     └────┬────┘     └────┬────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
   │Database │    │  Cache  │    │ Storage │
   │(Postgres)    │ (Redis) │    │ (MinIO) │
   └─────────┘    └─────────┘    └─────────┘
                        │
        ┌───────────────┴───────────────┐
        │    External Forensic Tools     │
        │ Volatility│Plaso│RegRipper│... │
        └────────────────────────────────┘
```

### Project Structure

```
forensicstack/
├── backend/                      # Python backend
│   ├── forensicstack/            # Main package
│   │   ├── __init__.py
│   │   ├── core/                 # Core engine
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # Database models
│   │   │   ├── orchestrator.py  # Tool orchestration
│   │   │   ├── timeline.py       # Timeline generation
│   │   │   ├── reports.py        # Report engine
│   │   │   └── ioc.py            # IoC extraction
│   │   ├── api/                  # FastAPI application
│   │   │   ├── __init__.py
│   │   │   ├── main.py           # API entry point
│   │   │   ├── routes/           # API endpoints
│   │   │   ├── schemas.py        # Pydantic models
│   │   │   └── dependencies.py   # DI and auth
│   │   ├── cli/                  # CLI application
│   │   │   ├── __init__.py
│   │   │   ├── main.py           # CLI entry point
│   │   │   └── commands/         # CLI commands
│   │   ├── agents/               # AI agents
│   │   │   ├── __init__.py
│   │   │   ├── core/             # Agent framework
│   │   │   │   ├── base.py       # Base agent class
│   │   │   │   ├── orchestrator.py
│   │   │   │   └── memory.py
│   │   │   ├── specialized/      # Specialized agents
│   │   │   │   ├── copilot.py
│   │   │   │   ├── triage.py
│   │   │   │   ├── malware.py
│   │   │   │   ├── ir.py
│   │   │   │   └── timeline.py
│   │   │   ├── prompts/          # Agent prompts
│   │   │   └── tools/            # Function calling
│   │   ├── plugins/              # Plugin system
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # Plugin interface
│   │   │   ├── windows/          # Windows forensics
│   │   │   │   ├── registry.py
│   │   │   │   ├── eventlogs.py
│   │   │   │   └── prefetch.py
│   │   │   ├── memory/           # Memory analysis
│   │   │   │   └── volatility.py
│   │   │   ├── timeline/         # Timeline tools
│   │   │   │   └── plaso.py
│   │   │   ├── network/          # Network analysis
│   │   │   └── malware/          # Malware analysis
│   │   └── utils/                # Utilities
│   │       ├── __init__.py
│   │       ├── hashing.py
│   │       ├── logging.py
│   │       └── config.py
│   ├── alembic/                  # Database migrations
│   │   ├── versions/
│   │   └── env.py
│   ├── tests/                    # Tests
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   ├── requirements.txt          # Python dependencies
│   ├── requirements-dev.txt      # Dev dependencies
│   ├── alembic.ini               # Alembic config
│   ├── .env.example              # Environment template
│   └── README.md                 # Backend documentation
├── web/                          # React frontend
│   ├── src/
│   │   ├── components/           # Reusable components
│   │   ├── features/             # Feature modules
│   │   │   ├── investigation/
│   │   │   ├── timeline/
│   │   │   ├── reports/
│   │   │   └── chat/             # AI chat interface
│   │   ├── pages/                # Page components
│   │   ├── hooks/                # Custom hooks
│   │   ├── services/             # API clients
│   │   ├── stores/               # State management
│   │   ├── types/                # TypeScript types
│   │   └── utils/                # Utilities
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── desktop/                      # Tauri desktop app
│   ├── src/                      # Same as web
│   ├── src-tauri/                # Rust backend
│   │   ├── src/
│   │   └── Cargo.toml
│   └── package.json
├── docs/                         # Documentation
│   ├── getting-started.md
│   ├── architecture.md
│   ├── plugins.md
│   ├── api-reference.md
│   └── contributing.md
├── docker/                       # Docker configs
│   ├── Dockerfile.backend
│   ├── Dockerfile.web
│   └── docker-compose.prod.yml
├── scripts/                      # Utility scripts
│   ├── generate_secrets.py
│   ├── setup.sh
│   └── setup.ps1
├── .github/                      # GitHub configs
│   ├── workflows/                # CI/CD
│   │   ├── tests.yml
│   │   └── deploy.yml
│   └── ISSUE_TEMPLATE/
├── docker-compose.yml            # Development infrastructure
├── .gitignore
├── LICENSE                       # GPL-3.0
└── README.md                     # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for web/desktop)
- **Docker & Docker Compose** (recommended)
- **Git**

**Operating Systems:**
- Windows 10/11 (with WSL2 for Docker)
- Linux (Ubuntu 22.04+, Debian, etc.)
- macOS (Intel or Apple Silicon)

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/forensicstack.git
cd forensicstack
```

#### 2. Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1
# Activate (Linux/Mac)
source venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# nano .env  # or use your favorite editor
```

#### 3. Setup Infrastructure (Docker)

```bash
# From project root
docker compose up -d

# Verify services are running
docker compose ps
```

**Services started:**
- PostgreSQL (port 5433)
- Redis (port 6379)
- MinIO (ports 9000, 9001)
- ChromaDB (port 8000)

#### 4. Initialize Database

```bash
cd backend

# Initialize Alembic (if not done)
alembic init alembic

# Run migrations
alembic upgrade head
```

#### 5. Setup Frontend (Optional)

```bash
cd web

# Install dependencies
npm install

# Start development server
npm run dev
```

#### 6. Run the Application

**CLI:**
```bash
cd backend
python -m forensicstack.cli.main --help
```

**API:**
```bash
cd backend
uvicorn forensicstack.api.main:app --reload
# API docs: http://localhost:8000/docs
```

**Web UI:**
```bash
cd web
npm run dev
# Open: http://localhost:5173
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
# Database
POSTGRES_USER=forensicstack
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=forensicstack
POSTGRES_HOST=localhost
POSTGRES_PORT=5433

# Redis
REDIS_PASSWORD=your-redis-password
REDIS_HOST=localhost
REDIS_PORT=6379

# MinIO (Object Storage)
MINIO_ROOT_USER=forensicadmin
MINIO_ROOT_PASSWORD=your-minio-password
MINIO_ENDPOINT=localhost:9000

# API Security
SECRET_KEY=generate-a-random-secret-key-min-32-chars
JWT_SECRET=generate-a-random-jwt-secret-min-32-chars
API_KEY=your-api-key

# AI APIs (Optional but recommended)
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-openai-key-here

# Application
DEBUG=true
LOG_LEVEL=INFO
```

### Generate Secure Secrets

```bash
cd backend
python scripts/generate_secrets.py
```

Copy the output into your `.env` file.

---

## 📖 Usage

### CLI Examples

```bash
# Create a new investigation case
forensicstack case create --title "Malware Investigation" --description "Suspected ransomware infection"

# Upload an artifact
forensicstack artifact upload --case-id 1 --file /path/to/memory.dump --type memory_dump

# Run analysis
forensicstack analyze --artifact-id 1 --module volatility --plugin pslist

# Generate timeline
forensicstack timeline generate --case-id 1

# Export report
forensicstack report generate --case-id 1 --format pdf --output report.pdf

# Chat with AI Copilot
forensicstack chat --case-id 1
```

### API Examples

```bash
# Create a case
curl -X POST "http://localhost:8000/api/v1/cases" \
  -H "Content-Type: application/json" \
  -d '{"title": "Investigation #001", "description": "Malware analysis"}'

# Upload artifact
curl -X POST "http://localhost:8000/api/v1/artifacts" \
  -F "file=@memory.dump" \
  -F "case_id=1" \
  -F "artifact_type=memory_dump"

# Run analysis
curl -X POST "http://localhost:8000/api/v1/analyses" \
  -H "Content-Type: application/json" \
  -d '{"artifact_id": 1, "module": "volatility", "plugin": "pslist"}'
```

### Web UI

1. Open http://localhost:5173
2. Create a new investigation case
3. Upload artifacts (disk images, memory dumps, PCAPs, logs)
4. Chat with AI Copilot: "Analyze this memory dump for suspicious processes"
5. View results in the timeline
6. Generate and download reports

---

## 🧪 Development

### Running Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=forensicstack --cov-report=html

# Run specific test
pytest tests/unit/test_models.py
```

### Code Quality

```bash
# Format code
black forensicstack/

# Lint
ruff check forensicstack/

# Type checking
mypy forensicstack/
```

### Database Migrations

```bash
# Create a new migration (auto-detect changes)
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

---

## 🗺️ Roadmap

### Phase 1: Foundation ✅ (Current)
- [x] Project structure
- [x] Core engine architecture
- [x] Database models
- [x] CLI interface (basic)
- [x] Docker infrastructure

### Phase 2: Core Modules (Q2 2026)
- [ ] Windows forensics modules (Registry, Event Logs, Prefetch)
- [ ] Memory analysis (Volatility integration)
- [ ] Timeline generation (Plaso integration)
- [ ] Basic report generation
- [ ] Web API (FastAPI)

### Phase 3: AI Agents (Q3 2026)
- [ ] Investigation Copilot
- [ ] Triage Agent
- [ ] Malware Analysis Agent
- [ ] IoC Intelligence Hub
- [ ] Conversational interface

### Phase 4: UI & Collaboration (Q4 2026)
- [ ] Web UI (React)
- [ ] Desktop app (Tauri)
- [ ] Multi-user support
- [ ] Real-time collaboration
- [ ] Advanced visualizations

### Phase 5: Advanced Features (2027)
- [ ] Mobile forensics (iOS, Android)
- [ ] Network forensics (Zeek, Wireshark)
- [ ] Cloud forensics (AWS, Azure, GCP)
- [ ] Automated playbooks
- [ ] Machine learning triage
- [ ] Enterprise features (SSO, RBAC, audit)

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](docs/contributing.md) for guidelines.

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/forensicstack.git
cd forensicstack

# Add upstream remote
git remote add upstream https://github.com/originalauthor/forensicstack.git

# Create branch
git checkout -b feature/my-feature

# Make changes, commit, push
git add .
git commit -m "feat: add new feature"
git push origin feature/my-feature
```

---

## 📚 Documentation

- [Getting Started Guide](docs/getting-started.md)
- [Architecture Overview](docs/architecture.md)
- [Plugin Development](docs/plugins.md)
- [API Reference](docs/api-reference.md)
- [Contributing Guide](docs/contributing.md)

---

## 🔐 Security

ForensicStack handles sensitive forensic data. Security best practices:

- ✅ Never commit `.env` files
- ✅ Use strong, randomly generated secrets
- ✅ Rotate credentials regularly (every 3-6 months)
- ✅ Enable authentication in production
- ✅ Use HTTPS for web access
- ✅ Isolate forensic environments (air-gapped if possible)
- ✅ Maintain chain of custody logs
- ✅ Encrypt artifact storage

To report security vulnerabilities, please email: security@forensicstack.io

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0** - see the [LICENSE](LICENSE) file for details.

### Third-Party Tools

ForensicStack integrates with external forensic tools, each with their own licenses:
- Volatility 3 (Volatility Software License)
- Plaso (Apache 2.0)
- Eric Zimmerman Tools (various)
- RegRipper (GPL)

---

## 🙏 Acknowledgments

- **Volatility Foundation** - Memory forensics framework
- **Log2Timeline/Plaso** - Timeline generation
- **Eric Zimmerman** - Windows forensics tools
- **The DFIR Community** - Continuous inspiration and knowledge sharing

---

## 📧 Contact

- **Project Lead:** Your Name
- **Email:** contact@forensicstack.io
- **Discord:** [Join our community](https://discord.gg/forensicstack)
- **Twitter:** [@ForensicStack](https://twitter.com/forensicstack)

---

## ⭐ Star History

If you find ForensicStack useful, please consider giving it a star! ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/forensicstack&type=Date)](https://star-history.com/#yourusername/forensicstack&Date)

---

<div align="center">

**Built with ❤️ by the DFIR community, for the DFIR community**

[Documentation](https://docs.forensicstack.io) • [Report Bug](https://github.com/yourusername/forensicstack/issues) • [Request Feature](https://github.com/yourusername/forensicstack/issues)

</div>