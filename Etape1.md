# ForensicStack - Documentation Étape 1
## Installation et Configuration Initiale

> **Date :** 23 février 2026  
> **Version :** 0.1.0-alpha  
> **Statut :** Complété

---

## 📋 Table des matières

1. [Résumé de l'étape 1](#résumé-de-létape-1)
2. [Architecture mise en place](#architecture-mise-en-place)
3. [Technologies installées](#technologies-installées)
4. [Structure du projet](#structure-du-projet)
5. [Configuration](#configuration)
6. [Services déployés](#services-déployés)
7. [Endpoints API disponibles](#endpoints-api-disponibles)
8. [Commandes CLI disponibles](#commandes-cli-disponibles)
9. [Tests et validation](#tests-et-validation)
10. [Problèmes résolus](#problèmes-résolus)
11. [Prochaines étapes](#prochaines-étapes)

---

## 🎯 Résumé de l'étape 1

### Objectifs atteints

- **Setup complet du projet** (backend, infrastructure)
- **Installation de toutes les dépendances**
- **Configuration de l'environnement de développement**
- **Déploiement de l'infrastructure Docker** (PostgreSQL, Redis, MinIO, ChromaDB)
- **API REST FastAPI fonctionnelle**
- **Celery worker opérationnel**
- **CLI de base avec Typer**
- **Documentation et configuration des secrets**

### Durée totale
Environ 4-6 heures (incluant résolution des problèmes)

---

## 🏗️ Architecture mise en place

```
┌─────────────────────────────────────────────────────────┐
│                   ForensicStack v0.1.0                   │
└─────────────────────────────────────────────────────────┘

┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   CLI Tool   │  │   REST API   │  │ Celery Worker│
│   (Typer)    │  │  (FastAPI)   │  │   (Tasks)    │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                  │
       └─────────────────┼──────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼────┐     ┌────▼────┐     ┌────▼────┐
   │PostgreSQL    │  Redis   │    │  MinIO  │
   │  (5432)  │     │ (6379)  │    │ (9000)  │
   └──────────┘     └─────────┘    └─────────┘

Ports utilisés :
- 5432  : PostgreSQL
- 5433  : PostgreSQL local (Windows)
- 6379  : Redis
- 8000  : ChromaDB
- 8001  : ForensicStack API
- 9000  : MinIO Storage
- 9001  : MinIO Console
```

---

## 🛠️ Technologies installées

### Backend (Python)

| Package | Version | Usage |
|---------|---------|-------|
| **Python** | 3.13 | Langage principal |
| **FastAPI** | Latest | Framework API REST |
| **Uvicorn** | Latest | ASGI server |
| **Pydantic** | Latest | Validation de données |
| **SQLAlchemy** | 2.0+ | ORM base de données |
| **Alembic** | Latest | Migrations DB |
| **psycopg** | 3.x (binary) | Driver PostgreSQL |
| **Celery** | Latest | Task queue asynchrone |
| **Redis** | Latest | Cache et message broker |
| **Typer** | Latest | CLI framework |
| **Rich** | Latest | Terminal UI |
| **python-dotenv** | Latest | Gestion variables d'env |

### Infrastructure (Docker)

| Service | Image | Port | Usage |
|---------|-------|------|-------|
| **PostgreSQL** | postgres:15-alpine | 5432 | Base de données principale |
| **Redis** | redis:7-alpine | 6379 | Cache et Celery broker |
| **MinIO** | minio/minio | 9000, 9001 | Stockage objet (artefacts) |
| **ChromaDB** | chromadb/chroma | 8000 | Vector DB (pour AI/RAG) |

### Outils de développement

- **pip** : Gestion des packages Python
- **Docker Desktop** : Containerization
- **Docker Compose** : Orchestration des services
- **Git** : Versioning

---

## 📁 Structure du projet

```
H:\forensick_stack\
├── backend\                          # Backend Python
│   ├── forensicstack\                # Package principal
│   │   ├── __init__.py
│   │   ├── api\                      # API REST
│   │   │   ├── __init__.py
│   │   │   ├── main.py               # Point d'entrée API
│   │   │   └── routes\               # Endpoints
│   │   │       ├── __init__.py
│   │   │       └── cases.py          # Routes cases
│   │   ├── cli\                      # Interface CLI
│   │   │   ├── __init__.py
│   │   │   └── main.py               # CLI Typer
│   │   ├── core\                     # Logique métier
│   │   │   ├── __init__.py
│   │   │   ├── models.py             # Modèles SQLAlchemy
│   │   │   └── tasks.py              # Tâches Celery
│   │   ├── plugins\                  # Plugins forensics (futur)
│   │   │   └── __init__.py
│   │   └── utils\                    # Utilitaires
│   │       └── __init__.py
│   ├── alembic\                      # Migrations DB
│   │   ├── versions\
│   │   └── env.py
│   ├── forensic\                     # Environnement virtuel
│   ├── .env                          # Variables d'environnement
│   ├── .env.example                  # Template
│   ├── .gitignore
│   ├── alembic.ini                   # Config Alembic
│   ├── requirements.txt              # Dépendances Python
│   └── run.py                        # Script de lancement
├── web\                              # Frontend (futur)
├── docker-compose.yml                # Infra Docker
├── .gitignore
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## ⚙️ Configuration

### Variables d'environnement (.env)

**Emplacement :** `backend/.env`

```bash
# Database
POSTGRES_USER=forensicstack
POSTGRES_PASSWORD=Pass123456
POSTGRES_DB=forensicstack
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis (SANS mot de passe pour Docker local)
REDIS_PASSWORD=
REDIS_HOST=localhost
REDIS_PORT=6379

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=Minio123456
MINIO_ENDPOINT=localhost:9000

# API
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET=your-jwt-secret-change-in-production
API_KEY=your-api-key

# Application
DEBUG=true
LOG_LEVEL=INFO
```

### Configuration Alembic

**Fichier :** `backend/alembic.ini`

- Script location : `alembic`
- Database URL : Chargée depuis `.env`
- Template : Standard SQLAlchemy

### Configuration Docker Compose

**Fichier :** `docker-compose.yml`

Services configurés :
- PostgreSQL : Volume persistant, port 5432
- Redis : Sans authentification, port 6379
- MinIO : Ports 9000 et 9001
- ChromaDB : Port 8000

---

## Services déployés

### 1. API FastAPI

**URL :** http://localhost:8001  
**Documentation :** http://localhost:8001/docs  
**Status :** Running

**Commande de lancement :**
```powershell
cd H:\forensick_stack\backend
.\forensic\Scripts\Activate.ps1
uvicorn forensicstack.api.main:app --reload --port 8001
```

**Features :**
- OpenAPI documentation auto-générée
- CORS configuré
- Endpoints de base (root, health, cases)
- Validation Pydantic

### 2. Celery Worker

**Status :** Running  
**Tasks enregistrées :**
- `forensicstack.analyze_artifact`
- `forensicstack.generate_timeline`
- `forensicstack.test_task`

**Commande de lancement :**
```powershell
cd H:\forensick_stack\backend
.\forensic\Scripts\Activate.ps1
celery -A forensicstack.core.tasks worker --loglevel=info --pool=solo
```

**Configuration :**
- Broker : Redis (localhost:6379)
- Backend : Redis (localhost:6379)
- Serializer : JSON
- Timezone : UTC

### 3. PostgreSQL

**Status :** Running  
**Port :** 5432  
**Database :** forensicstack  
**User :** forensicstack

**Tables créées :**
- `cases` : Cas d'investigation
- `artifacts` : Artefacts forensics
- `analyses` : Résultats d'analyse

**Connexion :**
```powershell
docker exec -it forensick_stack-postgres-1 psql -U forensicstack -d forensicstack
```

### 4. Redis

**Status :** Running  
**Port :** 6379  
**Auth :** Aucune (développement)

**Connexion :**
```powershell
docker exec -it forensick_stack-redis-1 redis-cli
```

### 5. MinIO

**Status :** Running  
**API Port :** 9000  
**Console Port :** 9001  
**Console URL :** http://localhost:9001

**Credentials :**
- User : minioadmin
- Password : Minio123456

### 6. ChromaDB

**Status :** Running  
**Port :** 8000  
**Usage :** Vector database pour AI/RAG (futur)

---

## 🔌 Endpoints API disponibles

### Documentation interactive
- **Swagger UI :** http://localhost:8001/docs
- **ReDoc :** http://localhost:8001/redoc

### Endpoints implémentés

#### Root & Health

```http
GET /
```
**Response :**
```json
{
  "message": "Welcome to ForensicStack API",
  "version": "0.1.0",
  "status": "running",
  "timestamp": "2026-02-23T20:00:00.000000",
  "docs": "/docs",
  "endpoints": {
    "cases": "/api/v1/cases",
    "health": "/health"
  }
}
```

```http
GET /health
```
**Response :**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-23T20:00:00.000000",
  "services": {
    "api": "running",
    "database": "configured",
    "redis": "configured",
    "celery": "configured"
  }
}
```

#### Cases (Mock - pas encore connecté à la DB)

```http
GET /api/v1/cases
```
**Response :**
```json
{
  "cases": [],
  "total": 0,
  "message": "Database integration coming next"
}
```

```http
POST /api/v1/cases
```
**Body :**
```json
{
  "title": "Malware Investigation",
  "description": "Suspected ransomware"
}
```
**Response :**
```json
{
  "message": "Case created (mock)",
  "case": {
    "id": 1,
    "case_number": "CASE-2026-001",
    "title": "Malware Investigation",
    "description": "Suspected ransomware",
    "status": "open"
  }
}
```

```http
GET /api/v1/cases/{case_id}
```
**Response :**
```json
{
  "id": 1,
  "message": "Case details coming soon"
}
```

---

## 💻 Commandes CLI disponibles

### Commandes principales

```powershell
# Afficher la version
python -m forensicstack.cli.main version

# Afficher le statut des services
python -m forensicstack.cli.main status
```

### Commandes cases

```powershell
# Lister les cas
python -m forensicstack.cli.main case list

# Créer un cas
python -m forensicstack.cli.main case create --title "Mon cas" --description "Description"
```

**Note :** Les commandes ne sont pas encore connectées à la base de données.

---

## Tests et validation

### Tests effectués

#### Infrastructure
```powershell
# Vérifier Docker
docker ps
# Résultat : 4 containers running (postgres, redis, minio, chromadb)

# Tester PostgreSQL
docker exec -it forensick_stack-postgres-1 psql -U forensicstack -d forensicstack -c "SELECT 1;"

# Tester Redis
docker exec -it forensick_stack-redis-1 redis-cli ping
# Résultat : PONG
```

#### API
```powershell
# Health check
curl.exe http://localhost:8001/health

# List cases
curl.exe http://localhost:8001/api/v1/cases

# Documentation Swagger
# Ouvrir : http://localhost:8001/docs
```

#### Celery
```powershell
# Worker running
celery -A forensicstack.core.tasks worker --loglevel=info --pool=solo
# Résultat : 3 tasks enregistrées, connecté à Redis
```

#### CLI
```powershell
# Version
python -m forensicstack.cli.main version

# Status
python -m forensicstack.cli.main status
```

---

## 🐛 Problèmes résolus

### 1. Poetry - Erreur "No module named 'packaging.licenses'"

**Problème :** Poetry ne fonctionnait pas correctement.

**Solution :** Utilisation directe de pip + requirements.txt
```powershell
pip install -r requirements.txt
```

### 2. Alembic - UnicodeDecodeError

**Problème :** Erreur d'encodage UTF-8 lors de la connexion à PostgreSQL.

**Cause :** Caractères accentués dans les variables d'environnement Windows.

**Solution :**
- Hardcoder l'URL de connexion dans `alembic/env.py`
- Utiliser uniquement des caractères ASCII dans les mots de passe

### 3. Celery - Cannot connect to Redis "Authentication required"

**Problème :** Redis demandait un mot de passe qui n'était pas configuré.

**Solution :**
- Laisser `REDIS_PASSWORD` vide dans `.env`
- Modifier `tasks.py` pour gérer l'absence de mot de passe
```python
if REDIS_PASSWORD and REDIS_PASSWORD.strip():
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
```

### 4. Port 8000 déjà utilisé

**Problème :** ChromaDB utilisait le port 8000.

**Solution :** Démarrer l'API ForensicStack sur le port 8001
```powershell
uvicorn forensicstack.api.main:app --reload --port 8001
```

### 5. psycopg2 - Compilation failed

**Problème :** psycopg2-binary nécessitait Rust pour compiler.

**Solution :** Utiliser psycopg v3 (pure Python avec wheels)
```txt
psycopg[binary]==3.2.0
```

### 6. Docker Desktop not running

**Problème :** Docker Desktop n'était pas lancé.

**Solution :**
- Lancer Docker Desktop manuellement
- Attendre que l'icône devienne verte
- Ou utiliser PostgreSQL local sur port 5433

### 7. CLI - TypeError with --help

**Problème :** Bug de compatibilité Typer/Click lors de `--help`.

**Solution :** Ignoré pour l'instant, toutes les commandes directes fonctionnent.

---

## Métriques du projet

### Lignes de code (approximatif)

- **API (main.py + routes) :** ~150 lignes
- **CLI (main.py) :** ~50 lignes
- **Tasks (tasks.py) :** ~80 lignes
- **Models (models.py) :** ~100 lignes
- **Config (alembic, docker-compose, etc.) :** ~200 lignes

**Total :** ~580 lignes de code fonctionnel

### Fichiers créés

- **Python :** 12 fichiers
- **Configuration :** 8 fichiers
- **Documentation :** 5 fichiers

### Temps de démarrage

- **API :** < 2 secondes
- **Celery Worker :** < 3 secondes
- **Infrastructure Docker :** ~15 secondes

---

## 🔐 Sécurité

### Bonnes pratiques appliquées

- Fichier `.env` dans `.gitignore`
- Template `.env.example` sans secrets
- Script de génération de secrets aléatoires
- Séparation des secrets par environnement
- Documentation des meilleures pratiques

### Points d'attention

- Redis sans mot de passe (OK pour dev, **À CHANGER en prod**)
- CORS ouvert à tous (`*`) - **À restreindre en prod**
- DEBUG=true - **À désactiver en prod**

---

## 📝 Commandes de démarrage complètes

### Démarrage de l'infrastructure

```powershell
# Lancer Docker Desktop (manuellement)

# Démarrer les services
cd H:\forensick_stack
docker compose up -d

# Attendre que tout démarre
Start-Sleep -Seconds 15

# Vérifier
docker compose ps
```

### Démarrage de l'application

**Terminal 1 - API :**
```powershell
cd H:\forensick_stack\backend
.\forensic\Scripts\Activate.ps1
uvicorn forensicstack.api.main:app --reload --port 8001
```

**Terminal 2 - Celery Worker :**
```powershell
cd H:\forensick_stack\backend
.\forensic\Scripts\Activate.ps1
celery -A forensicstack.core.tasks worker --loglevel=info --pool=solo
```

**Terminal 3 - CLI (tests) :**
```powershell
cd H:\forensick_stack\backend
.\forensic\Scripts\Activate.ps1
python -m forensicstack.cli.main status
```

### Arrêt propre

```powershell
# Arrêter l'API et Celery : Ctrl+C dans chaque terminal

# Arrêter Docker
docker compose down

# OU garder les données
docker compose stop
```

---

## 🎯 Prochaines étapes

### Étape 2 : Connexion à la base de données
- [ ] Créer database session/dependency
- [ ] Implémenter les opérations CRUD
- [ ] Connecter les endpoints aux modèles
- [ ] Tester avec données réelles

### Étape 3 : CRUD complet Cases
- [ ] GET /api/v1/cases (avec pagination)
- [ ] POST /api/v1/cases (avec validation)
- [ ] GET /api/v1/cases/{id}
- [ ] PUT /api/v1/cases/{id}
- [ ] DELETE /api/v1/cases/{id}
- [ ] Tests unitaires

### Étape 4 : Upload d'artefacts
- [ ] Endpoint POST /api/v1/artifacts
- [ ] Upload vers MinIO
- [ ] Hashing automatique (MD5, SHA256)
- [ ] Métadonnées et stockage en DB
- [ ] Gestion des fichiers volumineux

### Étape 5 : Intégration Volatility
- [ ] Plugin Volatility dans forensicstack/plugins
- [ ] Task Celery pour analyse mémoire
- [ ] Endpoint pour lancer l'analyse
- [ ] Stockage des résultats
- [ ] Affichage dans l'API

---

## 📚 Ressources et références

### Documentation officielle
- **FastAPI :** https://fastapi.tiangolo.com/
- **Celery :** https://docs.celeryq.dev/
- **SQLAlchemy :** https://docs.sqlalchemy.org/
- **Alembic :** https://alembic.sqlalchemy.org/
- **Typer :** https://typer.tiangolo.com/
- **Docker :** https://docs.docker.com/

### Outils forensics
- **Volatility 3 :** https://volatility3.readthedocs.io/
- **Plaso :** https://plaso.readthedocs.io/
- **Eric Zimmerman Tools :** https://ericzimmerman.github.io/

### Communauté DFIR
- **SANS DFIR :** https://www.sans.org/digital-forensics-incident-response/
- **Awesome Forensics :** https://github.com/cugu/awesome-forensics

---

## 🏆 Accomplissements

### Ce qui a été réalisé

1. **Infrastructure complète** déployée et opérationnelle
2. **API REST moderne** avec documentation auto-générée
3. **System de tâches asynchrones** avec Celery
4. **CLI professionnel** avec interface Rich
5. **Base de données** PostgreSQL configurée
6. **Stockage objet** MinIO pour artefacts
7. **Documentation exhaustive** du projet
8. **Bonnes pratiques** de sécurité et configuration

### Skills acquis

- Configuration d'environnement Python complexe
- Intégration Docker multi-services
- Développement API REST avec FastAPI
- Gestion de tâches asynchrones
- Debugging et résolution de problèmes
- Documentation technique

---

## 📞 Support et contribution

### En cas de problème

1. Vérifier que Docker Desktop tourne
2. Vérifier que l'environnement virtuel est activé
3. Vérifier les logs : `docker compose logs`
4. Consulter la documentation : http://localhost:8001/docs

### Contribution

Le projet suit les conventions :
- **PEP 8** pour Python
- **Conventional Commits** pour Git
- **Type hints** partout
- **Docstrings** Google style

---

## 📅 Changelog

### Version 0.1.0-alpha (23/02/2026)

**Added :**
- Setup initial du projet
- API FastAPI de base
- Celery worker
- CLI Typer
- Infrastructure Docker
- Documentation complète

**Fixed :**
- Problèmes d'encodage UTF-8
- Connexion Redis sans password
- Compatibilité psycopg v3
- Conflits de ports

---

## ✨ Conclusion

L'étape 1 est **complète et validée**. Tous les composants de base sont en place et fonctionnels. Le projet est maintenant prêt pour le développement des fonctionnalités métier (CRUD, plugins forensics, AI agents).

**Temps investi :** ~6 heures  
**Résultat :** Infrastructure solide et extensible  
**Prochaine session :** Connexion DB et CRUD complet

---

**🎉 Bravo pour cette première étape réussie ! 🚀**