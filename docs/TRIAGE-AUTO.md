# Triage automatique — mode autonome

> Upload un artefact → le système l'identifie par son **contenu**, planifie les
> outils qui collent, et les exécute seul. Pensé pour l'usage quotidien (réel + CTF).

## Le flux

```
POST /api/v1/analyze  (fichier)
   └─ identify()      → nature du fichier par contenu (magic, marqueurs kernel,
   │                     entropie, alignement page) — pas par extension
   └─ plan_for()      → outils applicables depuis les manifestes (plugin.yaml),
   │                     incompatibles écartés + raison
   └─ queue.submit()  → jobs sur le Redis Stream
                        stream_worker les exécute (conteneurs isolés)
```

Deux entrées, côté UI (page **Triage auto**) :

| Action | Endpoint | Coût | Ce que ça fait |
|---|---|---|---|
| Déposer un fichier | `POST /analyze/identify` | ~0 (aucun conteneur) | Identifie + planifie, **ne lance rien**. Affiche le verdict et le plan (avec les raisons + les outils écartés). |
| « Lancer l'analyse » | `POST /analyze` | conteneurs | Met tout le plan en file. Suivi en direct via `GET /analyze/plan/{plan_id}`. |

Le premier est ce qui rend l'UX **testable sans worker et sans Docker** : tu vois
l'identification et le plan immédiatement. Seule l'exécution réelle des outils a
besoin du worker.

## Faire tourner l'exécution (le worker)

Le pipeline `/analyze` dépose sur un Redis **Stream** consommé par
`forensicstack.stream_worker` — **pas** le `forensicstack.worker` historique (qui
draine l'ancienne liste et sert le chemin manuel `/jobs/direct`).

### Option 1 — worker natif sur l'hôte (recommandé en dev / Windows)

Le plus simple : il ne lui faut que **Redis** (exposé par le compose) et **Docker**.
Les résultats sont écrits dans `backend/tmp_jobs/results/<job>.json` + un résumé Redis
(ni Postgres ni MinIO requis pour le worker).

```powershell
# 1. l'infra tourne
make up                 # ou: docker compose -f backend/docker-compose.yml up -d
# 2. les images d'outils sont construites
make build-tools
# 3. le worker autonome (Windows)
./scripts/run-auto-worker.ps1 -Concurrency 2
```

```bash
# macOS / Linux / WSL
make worker-auto            # ou: ./scripts/run-auto-worker.sh 2
```

En natif, le workspace du job est un vrai chemin hôte → Docker Desktop le monte
directement, aucune traduction de chemin à configurer.

### Option 2 — worker conteneurisé + durci (cible prod)

L'overlay durci remplace le worker par `stream_worker`, ajoute le
`docker-socket-proxy` (le socket ne quitte plus le worker) et met les services
internes hors du réseau hôte :

```bash
docker compose -f backend/docker-compose.yml -f backend/docker-compose.hardened.yml up -d
```

⚠️ En conteneur, le runner monte des chemins que **le démon** voit, pas ceux du
worker. Renseigne `HOST_WORKSPACE_ROOT` avec le chemin hôte qui sauvegarde le
volume `tmp_jobs` (voir les commentaires dans `docker-compose.hardened.yml`),
sinon les conteneurs d'outils reçoivent un `/input` vide.

## Pourquoi deux workers coexistent

- `forensicstack.worker` (ancien) → chemin manuel `/jobs/direct` de l'UI, exécuteur
  `docker_executor.py`. C'est le chemin Volatility déjà testé.
- `forensicstack.stream_worker` (nouveau) → chemin autonome `/analyze`, runner durci
  `core/runners/docker.py` (sans `--volumes-from`).

État de transition volontaire : les deux tournent en parallèle. Unifier sur le
runner durci est le prochain chantier.

## Note sur les images disque (.dd/.img) et l'auto-triage

Le routeur sélectionne les outils **par kind** (pas par extension). Les manifestes
ALEAPP/iLEAPP ne déclarent pas encore les kinds `disk_image_raw`/`disk_image_ewf`,
donc une image disque brute n'est pas auto-routée vers eux (un `.dd` brut n'a pas de
marqueur d'OS → il déclencherait iLEAPP **et** ALEAPP). Le chemin manuel
`/jobs/direct` les gère déjà via les features `img` du registry. Décision produit à
trancher avant de l'ajouter à l'auto-triage.
