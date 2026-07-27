# Ce qui a changé

75 fichiers : **39 ajoutés, 23 modifiés, 12 supprimés**. Base : `7cfe7b5` (identique à ton zip `main`).

Les tests passent : **142 verts**, 4 skippés. Les 3 rouges restants sont des manques d'environnement dans mon sandbox (`yara-python` non installé, binaire `volatility` absent), pas des régressions.

---

## 1. Sécurité — ce qui était ouvert et ne l'est plus

### L'évasion de conteneur

`docker_executor.py` faisait `--volumes-from fs_worker`. Ce flag hérite de **tous** les montages du conteneur source — bind mounts compris — et `docker-compose.yml` donnait au worker `/var/run/docker.sock` **et** `.:/app:rw`. Donc chaque conteneur Volatility, iLEAPP ou ExifTool recevait le socket Docker et ton arbre source en écriture. Les `--cap-drop=ALL`, `--read-only` et `--security-opt no-new-privileges` sur la même ligne de commande étaient décoratifs : un process qui peut appeler `POST /containers/create` avec `Privileged:true` possède la machine.

Concrètement : analyser un dump mémoire fourni par un tiers + un bug de parsing dans Volatility 3 = root sur ton hôte.

**Maintenant** (`core/runners/docker.py`) : deux montages, tous deux dérivés du workspace du job, rien d'hérité.

```
<workspace>/<job_id>/input   → /input   (ro)
<workspace>/<job_id>/output  → /output  (rw)
```

Et `docker-compose.hardened.yml` retire le socket du worker au profit d'un `docker-socket-proxy` avec allowlist (`EXEC: 0`, `VOLUMES: 0`, `NETWORKS: 0`…). Même worker entièrement compromis, il ne peut plus créer de conteneur privilégié.

Trois tests verrouillent ça définitivement :

```python
def test_runner_never_uses_volumes_from(tmp_path): ...
def test_runner_never_mounts_the_docker_socket(tmp_path): ...
def test_runner_mounts_exactly_two_paths(tmp_path): ...
```

### L'absence d'autorisation

`Case` n'avait aucune colonne propriétaire, et aucune route ne filtrait. N'importe quel compte enregistré lisait, modifiait et **supprimait** toutes les cases et tous les artefacts, et pouvait générer une URL présignée MinIO sur les preuves de n'importe qui. `require_admin()` était défini et appelé **zéro fois**.

**Maintenant** : `Case.owner_id` (FK indexée, NOT NULL), filtrage **dans la requête** (pas après le fetch), et **404 plutôt que 403** sur les objets d'autrui — un 403 confirmerait leur existence. `require_admin` est réellement utilisé. Migration Alembic fournie, avec `upgrade()` **et** `downgrade()` réels et un backfill sûr.

### Les secrets

`SECRET_KEY` retombait sur `"changeme-use-a-real-secret-in-production"`. Sans `.env`, l'API démarrait normalement et signait des JWT avec une constante publique. Même schéma pour Postgres, MinIO et Redis.

**Maintenant** : `require_env()` — aucune valeur de secret par défaut, échec au démarrage avec un message clair. Le DSN n'est plus imprimé sur stdout.

Et `Etape1.md` contenait tes **vrais** mots de passe (`Pass123456`, `Minio123456`) à HEAD : redigés. ⚠️ **Redigier ne suffit pas** — l'historique git les contient toujours. Il faut `git filter-repo` **et** rotationner ces mots de passe partout où la stack a tourné.

### Le reste

- Nom de fichier uploadé assaini (`Path(name).name`) → plus de path traversal via `../../`.
- Clé objet = `case-{id}/{sha256}/{nom}` → deux uploads de `dump.raw` n'écrasent plus le premier. C'était de la **destruction de preuve** dans un produit de chaîne de custody.
- Upload en streaming avec plafond et 413, au lieu de `await file.read()` du fichier entier en RAM.
- `content_type` forcé à `application/octet-stream` → plus de XSS stocké via URL présignée.
- CORS : `allow_origins=["*"]` + `allow_credentials=True` (combinaison invalide) → origines explicites par variable d'environnement.
- `DELETE /cases/{id}` nettoie enfin MinIO et Chroma au lieu d'orpheliner les blobs.
- Le champ `feature` est validé contre le manifeste → plus d'exécution de plugin Volatility arbitraire par tout utilisateur authentifié.

---

## 2. L'automatisation que tu as demandée

> « quand j'upload un `dump.mem`, c'est le système qui agit dessus en tenant compte de la nature du fichier »

C'est `POST /api/v1/analyze` :

```
upload → identification par CONTENU → plan depuis les manifestes → mise en file
```

Le plan revient **immédiatement**, pendant que les jobs tournent.

### Le moteur d'identification (`core/triage/`)

- ~90 signatures binaires, sous-typage de conteneurs (un `.zip` devient APK / IPA / OOXML / backup iOS ; un `.tar` devient backup iOS ou extraction Android), détection d'ELF core vs binaire, de vrai PE vs simple « MZ ».
- **Les dumps mémoire bruts n'ont aucun magic number.** Ils sont détectés par comportement : marqueurs kernel échantillonnés dans le fichier (`KDBG`, `\SystemRoot\System32`, `PsActiveProcessHead`, `Linux version`…), alignement page, profil d'entropie, pages nulles. Ça donne aussi l'OS.
- **Coût borné, pas O(taille)** : header + footer + 24 fenêtres de 1 Mo. Un dump de 80 Go coûte la même chose qu'un de 80 Mo (hors hash).
- **Le contenu bat toujours le nom.** Un JPEG renommé `evidence.raw` est identifié JPEG, et le conflit est signalé.
- Chaque conclusion porte ses **preuves** — une identification inexplicable n'est ni défendable dans un rapport, ni débuggable.

### Le routeur (`core/triage/router.py`)

Il ne lit que les manifestes, donc un plugin déposé rejoint l'automatisation sans une ligne de code. Résultat réel pour `dump.mem` :

```
### dump.mem → memory_dump (conf 0.99, os=windows)
   0/  1  triage/scan                — accepts any input
   0/ 30  exiftool/metadata          — accepts any input
   1/  5  volatility/windows.info    — declares support for memory_dump; OS matches
   1/ 10  volatility/windows.pslist  — …
   1/ 15  volatility/windows.pstree
   1/ 20  volatility/windows.netscan
   1/ 25  volatility/windows.cmdline
   1/ 40  volatility/windows.malfind
```

`windows.info` passe **avant** les autres (`requires`) : si la résolution du profil échoue, inutile de brûler 20 minutes. `linux.pslist` a été écarté (OS incompatible) — et l'écart est **rapporté**, jamais silencieux. Un blob non identifié tombe sur le chemin générique plutôt que sur un outil deviné qui échouera 40 minutes plus tard.

`POST /api/v1/analyze/identify` fait tout ça **sans rien mettre en file** — pour mettre au point tes règles sans dépenser de temps conteneur.

---

## 3. Le système de plugins

Un plugin = **un dossier avec un `plugin.yaml`**. Découverte au runtime, validation Pydantic au démarrage, normalizer importé paresseusement.

Ça supprime `plugin_registry.py`, `normalization_engine.py`, les `plugins/external/*/config.py` (3ᵉ source de vérité, qui contredisait les deux autres), et les tableaux `IMAGES=()` dupliqués dans 4 scripts.

Deux propriétés qui changent la vie :

- **Les défauts sont les valeurs durcies.** `network: none`, `readonly: true`, `user: 1000:1000`. Tu dois écrire quelque chose pour être en danger, pas pour être en sécurité — et le registre loggue un warning si tu le fais.
- **Un manifeste invalide échoue au démarrage.** Avant, l'équivalent (entrée manquante dans `NORMALIZERS`) ne se manifestait qu'**après** que le conteneur ait tourné — jusqu'à 2 h pour Volatility.

Les 4 outils existants sont migrés. Au passage : Volatility repasse en `network: none` (les symboles sont déjà dans l'image + le volume de cache), et gagne un `windows.info` par défaut — l'ancien code émettait `VOLATILITY_PLUGIN=fs` faute de `default_type`, produisant `vol -f dump --renderer json fs`, un échec garanti.

Guide complet : **`docs/AJOUTER-UN-OUTIL.md`**.

---

## 4. Le nouvel outil de référence : `triage`

Conteneur Python stdlib-only, non-root, qui répond à « qu'est-ce qui mérite un regard dans ce fichier ? » pour un artefact de **n'importe quel type** :

- **strings classifiées** (pas un dump brut) : URL, IP, email, chemins Windows/UNC/Unix, clés de registre, clé privée, clé AWS, JWT, adresse Bitcoin, base64, user-agent, PowerShell encodé/caché ;
- **carving** de signatures embarquées à offset non nul — la question binwalk ;
- **profil d'entropie par blocs** qui *localise* les zones chiffrées au lieu d'un chiffre global ;
- **candidats flag CTF** (regex configurable).

Sur un JPEG piégé de test : 8 classes de strings, 2 fichiers embarqués (ZIP + PNG), 1 flag, et 12 `Finding` v2 dont 3 en `high` (clé AWS, clé privée, flag).

C'est aussi le modèle à copier : dossier autonome, manifeste, entrypoint sans `|| true`, normalizer défensif.

---

## 5. Fiabilité

### La file

`LPUSH` + `BRPOP` était un pop **destructif** sans acquittement : worker tué en cours de job = job disparu, statut bloqué sur `running` pour toujours. Ni retry, ni DLQ, ni visibility timeout.

**Maintenant** (`core/queue.py`) : Redis Streams + consumer groups. `XREADGROUP` enregistre le message comme pending, `XAUTOCLAIM` permet à un worker sain de reprendre ceux d'un worker mort, `XACK` est explicite, les redéliveries sont comptées et un message empoisonné part en dead-letter. TTL sur l'état des jobs.

### La concurrence

L'ancien worker : une boucle `while True` sur un `brpop` bloquant, **un job à la fois**. Un job Volatility de 7200 s bloquait toute la file pendant 2 heures.

**Maintenant** (`stream_worker.py`) : pool de threads, `--concurrency N`, lease par job, arrêt propre sur SIGTERM, et balayage des workspaces orphelins **sur timer** — l'ancien nettoyage ne tournait que sur le chemin idle, donc un worker chargé ne collectait jamais rien.

### Le contrat d'erreur

Un seul `except` fourre-tout transformait « MinIO était down » et « ce fichier est invalide » en le même `status=failed`. Et `NativeExecutor` ignorait `returncode` : outil planté → dossier vide → normalizer `[]` → job **`completed` avec 0 finding**.

**Maintenant** : `ToolUnavailableError` (retryable, message laissé non-acké donc redélivré) ≠ `ToolExecutionError` (terminal) ≠ `ToolTimeoutError` ≠ `InputRejectedError`. Codes retour vérifiés dans les deux runners.

### Les findings

Ils étaient `json.dumps` dans **un champ de hash Redis, sans TTL**, avec Redis sans `appendonly`. Un `$MFT` produit des millions de lignes ; tout partait dans une seule réponse HTTP. Maintenant : plafond explicite (et signalé, jamais silencieux), écriture dans un fichier de résultat, résumé seul dans Redis.

---

## 6. `Finding` v2

v1 était une enveloppe, pas un schéma. Le plus grave : **deux des cinq normalizers mettaient `timestamp=None` en dur** — y compris pour `windows.netscan` (qui porte `Created`) et pour les CSV MFT/EVTX dont c'est tout l'intérêt. Un produit de timeline forensique détruisait chaque timestamp à la frontière de normalisation. Et `source` voulait dire quatre choses différentes selon le normalizer, donc corréler entre outils était impossible.

v2 : vocabulaire **fermé** (`FindingKind`), `ts_utc` en `datetime` UTC réel + `ts_kind` (created/modified/accessed/logged…), provenance obligatoire (version d'outil, hash de l'artefact, chemin **dans** l'artefact, offset), `severity` à la place d'un `confidence` magique.

`core/findings/timeparse.py` centralise le parsing : ISO, epoch s/ms/µs/ns, FILETIME Windows, WebKit, Cocoa, format ExifTool, ~15 formats texte, offsets — et rend `None` plutôt que de deviner. Fenêtre de plausibilité 1980-2100, parce qu'un 1970 ou un 4000 empoisonne une timeline.

Les normalizers v1 continuent de marcher (`Finding.from_legacy`), donc la migration se fait outil par outil.

---

## 7. Frontend

- **Tous les toasts étaient perdus.** `hooks/use-toast.ts` et `components/ui/use-toast.ts` étaient byte-identiques avec chacun son état module-level : le `<Toaster/>` monté écoutait le store A, les composants dispatchaient dans le store B. Zéro feedback sur création de case et upload. Corrigé.
- **Les erreurs de login étaient inaffichables** : l'intercepteur 401 se déclenchait sur le 401 que renvoie `/auth/login` lui-même, et la page naviguait avant l'affichage. Corrigé.
- **Timeout axios de 30 s** sur des uploads annoncés jusqu'à 5 Go → `timeout: 0` sur les requêtes multipart.
- **`.tar.gz` toujours rejeté** (`'.' + name.split('.').pop()` = `.gz`) → helper conscient des doubles extensions. Débloque l'input phare d'iLEAPP.
- **Upload inaccessible au clavier** → `role`, `tabIndex`, `aria-label`, Entrée **et** Espace.
- Tailles en « 0.00 GB » pour 4 Mo → `formatBytes()`.
- Le toast mentait (« queued for analysis » alors qu'aucun `jobsApi.submit` n'existe) → texte honnête.

---

## 8. Hygiène

`LICENSE` GPL-3.0 ajouté (le badge du README pointait dans le vide, le projet était donc *tous droits réservés*). `Makefile`. `pyproject.toml` (ruff/black — installés depuis toujours **sans aucun fichier de config**). `.dockerignore` pour backend et web (sans eux, `COPY . .` embarquait `.env` dans les couches d'image). `backend/.gitignore` réparé — un `>>` PowerShell y avait écrit de l'UTF-16LE, cassant ses deux dernières règles.

Supprimés : les `setup.sh`/`setup.ps1` racine (leur `REPO_ROOT` sortait du dépôt, ils ne pouvaient **jamais** fonctionner — leur bloc de seed vol3 a été porté dans `scripts/` avant suppression), `Untitled.txt` et `pb_deploiement.txt` (dumps de terminal exposant tes chemins Windows), `tasks.py.backup`, `docker_runner.py` (zéro appelant), `core/models.py`, `test_output/`, `tsconfig.tsbuildinfo`.

`/api/v1/analysis/*` est **débranché** : il dispatche via Celery alors qu'aucun worker Celery n'existe, ses dépendances ne sont pas dans `requirements.txt`, et il passe une clé objet MinIO à du code qui attend un chemin filesystem. Il faisait aussi échouer l'import de toute l'API. Les fichiers restent, avec une note — à toi de décider de les supprimer.

---

## Ce qu'il reste — dans l'ordre

1. **`git filter-repo` + rotation des mots de passe.** Le seul point que je ne peux pas faire à ta place. Au passage, `.git` fait 94 Mo parce qu'il contient `node_modules/` et des caches webpack.
2. **Pinner `requirements.txt`.** 25 des 27 deps sont non contraintes. C'est déjà visible : deux tests d'auth ont changé de comportement (403 → 401) juste parce que mon sandbox a résolu une version de FastAPI plus récente que la tienne.
3. **Basculer le worker** sur `python -m forensicstack.stream_worker` (l'ancien `worker.py` reste fonctionnel en parallèle le temps de la transition).
4. **Le front sur `/api/v1/analyze`** — et supprimer `mock-data.ts` page par page : `/jobs` → `/findings` → `/timeline` → `/cases/[id]`. Attention, `/cases/[id]` affiche aujourd'hui **systématiquement la mauvaise case** (`mockCases.find(...) || mockCases[0]` avec des ids string vs numériques) : en forensique, montrer les preuves de A sous l'URL de B est le pire mode de défaillance possible.
5. **CI GitHub Actions** — tu as des tests que rien n'exécute jamais.
6. **Les findings en Postgres** (JSONB + index GIN sur `data`, B-tree sur `ts_utc`) plutôt qu'en fichiers.
7. **Le chaînage DAG** — `emits` est déjà déclaré partout, c'est la brique qui reste.
