# Ajouter un outil à ForensicStack

> Avant : éditer **7 fichiers** dont 3 modules core, puis redéployer l'API *et* le worker.
> Maintenant : créer **1 dossier**. Zéro fichier core touché, zéro redéploiement pour que l'outil apparaisse.

---

## 1. Le principe

Un plugin est un **dossier contenant un `plugin.yaml`**. Le registre le découvre au démarrage par `rglob`, le valide contre un modèle Pydantic, et importe son normalizer **paresseusement** (au premier usage).

```
backend/forensicstack/plugins/external/<mon_outil>/
├── plugin.yaml       ← la seule source de vérité
├── Dockerfile        ← comment construire l'image
├── entrypoint.sh     ← contrat : lit $INPUT_PATH, écrit dans $OUTPUT_PATH
├── normalizer.py     ← sortie de l'outil → Finding[]
└── tool/             ← (optionnel) le code de l'outil s'il est à toi
```

Tu peux aussi poser des plugins **hors de l'arbre** :

```bash
export FORENSICSTACK_PLUGIN_PATH=/opt/mes-plugins:/srv/plugins-equipe
```

**Conséquences directes de ce design :**

| Ce qui disparaît | Pourquoi |
|---|---|
| `core/plugin_registry.py` (dict de 231 lignes) | remplacé par la découverte |
| `core/normalization_engine.py` (2ᵉ dict, normalizers instanciés à l'import) | remplacé par le chargement paresseux |
| `plugins/external/*/config.py` (3ᵉ source, contradictoire) | remplacé par `plugin.yaml` |
| Les tableaux `IMAGES=()` dupliqués dans 4 scripts de setup | `build-tools` itère sur les manifestes |
| La whitelist manuelle du champ `feature` | `features[].id` **est** la whitelist |
| Les 407 lignes de docs outils codées en dur dans le front | `GET /api/v1/analyze/tools` |

---

## 2. Le `plugin.yaml`, champ par champ

```yaml
id: hayabusa                 # ^[a-z][a-z0-9_]{1,31}$ — unique, c'est la clé d'API
name: Hayabusa               # affiché dans l'UI
version: "2.16.0"            # version de l'OUTIL, pas du plugin
category: windows_logs
description: >-
  Analyse rapide de journaux EVTX avec règles Sigma, sortie mappée ATT&CK.
homepage: https://github.com/Yamato-Security/hayabusa
license: GPL-3.0

runtime:
  kind: docker               # docker | native
  image: forensicstack/hayabusa:2.16
  # ── Les valeurs par défaut SONT les valeurs durcies. ──────────────────
  # Tu n'as rien à écrire pour être en sécurité ; tu dois écrire quelque
  # chose pour ne PAS l'être — et le registre loggue un warning si tu le fais.
  network: none              # défaut. `bridge` = warning au chargement
  readonly: true             # défaut
  user: "1000:1000"          # défaut. root → warning
  memory: 4g
  cpus: "2"
  pids_limit: 256
  timeout: 3600              # défaut global, surchargeable par feature
  volumes:                   # volumes NOMMÉS uniquement
    - hayabusa_rules:/rules:ro
  env:
    HAYABUSA_PROFILE: super-verbose

feature_env: HAYABUSA_COMMAND     # obligatoire dès qu'il y a >1 feature
normalizer: forensicstack.plugins.external.hayabusa.normalizer:HayabusaNormalizer

accepts:
  kinds: [evtx, filesystem_archive]   # ← ce que lit le routeur automatique
  extensions: [".evtx", ".zip"]       # simple indice pour l'UI
  min_size: 1KiB
  max_size: 32GiB

features:
  - id: csv-timeline
    label: Timeline Sigma
    description: Applique les règles Sigma et produit une timeline CSV.
    timeout: 1800
    emits: [log_event, execution_evidence]   # FindingKind produits
    auto: true                                # inclus dans le plan automatique
    auto_priority: 20                         # plus bas = plus tôt
    os_hint: windows                          # n'auto-planifie que si l'OS colle
    requires: []                              # features du même plugin à faire avant
```

### Les champs qui comptent vraiment

- **`accepts.kinds`** — c'est *lui* qui branche ton outil sur l'automatisation. Les valeurs viennent de l'énumération `ArtifactKind` (`GET /api/v1/analyze/kinds` te les liste). Laisser `kinds` **vide** signifie « j'accepte tout » : ton plugin rejoint alors le chemin générique et tourne même sur un artefact non identifié.
- **`features[].auto`** — sans lui, la feature existe mais n'est jamais planifiée toute seule. C'est volontaire : « tout lancer » ne doit pas être le défaut.
- **`features[].requires`** — ordonne les étapes **à l'intérieur** d'un plugin. C'est ce qui fait passer `windows.info` avant `windows.pslist` : si la résolution du profil échoue, inutile de brûler 20 minutes sur le reste.
- **`emits`** — déclare les `FindingKind` produits. Sert au chaînage et permet à un test de vérifier la forme de sortie.

---

## 3. Le contrat du conteneur

Ton conteneur voit **exactement deux montages**, jamais hérités :

| Chemin | Mode | Contenu |
|---|---|---|
| `/input` | **ro** | l'artefact, seul |
| `/output` | rw | tout ce que tu écris |

Variables injectées : `INPUT_PATH`, `INPUT_DIR`, `INPUT_FILENAME`, `OUTPUT_PATH`, `OUTPUT_DIR`, `FEATURE`, plus ton `feature_env`.

```sh
#!/bin/sh
set -eu
: "${INPUT_PATH:?}"
: "${OUTPUT_PATH:=/output}"

[ -f "$INPUT_PATH" ] || { echo "input introuvable: $INPUT_PATH" >&2; exit 2; }

exec hayabusa csv-timeline -f "$INPUT_PATH" -o "$OUTPUT_PATH/timeline.csv"
```

> ### ⚠ Ne termine JAMAIS par `|| true`
> Les entrypoints `exiftool` et `volatility` finissaient tous les deux par `|| true`. Le conteneur sortait donc **toujours** en 0, le `check=True` de l'exécuteur ne se déclenchait jamais, et un outil planté était indistinguable d'un outil qui n'a rien trouvé. « 0 finding » devenait la façon dont les échecs se présentaient.
>
> Un code retour non nul est ton seul moyen de dire « j'ai échoué ». Utilise-le.

Côté Dockerfile : `USER` non-root, pas d'outils de build dans l'image finale, et pas de `RUN sed -i 's/\r//'` — le `.gitattributes` du repo gère déjà les fins de ligne.

---

## 4. Le normalizer

```python
from pathlib import Path
from forensicstack.core.findings.finding import Finding
from forensicstack.core.triage.kinds import FindingKind


class HayabusaNormalizer:
    tool = "hayabusa"

    def normalize(self, output_dir, *, job_id=None, artifact_sha256=None,
                  tool_version="", **_):
        out = Path(output_dir)
        csv_path = out / "timeline.csv"

        # Ne JAMAIS parser sans filet : l'ancien ExiftoolNormalizer faisait un
        # json.loads() nu, donc une sortie tronquée faisait échouer le job APRÈS
        # que l'outil ait réussi.
        if not csv_path.is_file():
            return [Finding(tool=self.tool, job_id=job_id,
                            kind=FindingKind.ERROR, severity="medium",
                            title="hayabusa n'a produit aucune timeline")]

        import csv
        findings = []
        with csv_path.open(encoding="utf-8", errors="replace") as fh:
            for row in csv.DictReader(fh):
                findings.append(Finding(
                    tool=self.tool, tool_version=tool_version, job_id=job_id,
                    artifact_sha256=artifact_sha256,
                    kind=FindingKind.LOG_EVENT,
                    ts_utc=parse_timestamp(row.get("Timestamp"))[0],   # ← JAMAIS None par défaut
                    ts_kind="logged",
                    title=row.get("RuleTitle", ""),
                    severity=_map_level(row.get("Level")),
                    data=row,
                ))
        return findings
```

### Les trois règles

1. **Le timestamp se parse, toujours.** `parse_timestamp()` (dans `core/findings/timeparse.py`) gère ISO, epoch s/ms/µs/ns, FILETIME Windows, WebKit, Cocoa, le format ExifTool et une dizaine de formats texte, et rend `None` plutôt que de deviner. Deux des cinq anciens normalizers mettaient `timestamp=None` en dur — y compris pour `windows.netscan` et pour les CSV MFT/EVTX dont c'est tout l'intérêt.
2. **`kind` vient de l'énumération fermée.** C'est la clé de jointure entre outils : sans elle, corréler « Volatility a vu ce process » avec « Prefetch a vu cette exécution » est impossible.
3. **Une erreur est un `Finding`, pas une exception.** Un normalizer qui plante ne doit pas jeter un run d'outil réussi.

Un normalizer v1 (signature `normalize(output_dir)`, dataclass historique) continue de fonctionner : le pipeline détecte la signature et convertit via `Finding.from_legacy()`. La migration se fait outil par outil.

---

## 5. Brancher et vérifier

```bash
# 1. Construire l'image
docker build -t forensicstack/hayabusa:2.16 \
  backend/forensicstack/plugins/external/hayabusa

# 2. Le manifeste est-il valide ? (échoue fort et tôt s'il ne l'est pas)
cd backend && python -c "
from forensicstack.core.plugins.registry import PluginRegistry
r = PluginRegistry().load(force=True)
print(r.ids)
m = r.get('hayabusa')
print([f.id for f in m.features], 'hardened=', m.runtime.is_hardened)
"

# 3. Que ferait le routeur d'un vrai fichier ?
curl -s -X POST localhost:8001/api/v1/analyze/identify \
  -H "Authorization: Bearer $TOKEN" -F file=@Security.evtx | jq '.plan.steps'
```

`/analyze/identify` ne met rien en file : c'est le moyen de mettre au point tes règles de routage sans dépenser de temps conteneur.

**Test doré** (le modèle à copier) : fige une vraie sortie d'outil en fixture, assert le nombre et la forme des findings.

```python
def test_hayabusa_normalizer(tmp_path):
    (tmp_path / "timeline.csv").write_text(FIXTURE_CSV)
    findings = HayabusaNormalizer().normalize(tmp_path, job_id="t")
    assert len(findings) == 42
    assert all(f.ts_utc is not None for f in findings)   # le piège n°1
    assert {f.kind for f in findings} == {FindingKind.LOG_EVENT}
```

---

## 6. Outil natif (non conteneurisable)

Pour la suite Eric Zimmerman sous Windows :

```yaml
runtime:
  kind: native
  executable: MFTECmd.exe
  tool_dir_env: EZTOOLS_DIR
  timeout: 1800
  env:
    ARGS: "-f {input} --csv {output}"     # placeholders : {input} {output} {feature}
```

Le `NativeRunner` **refuse de démarrer** sans `FORENSICSTACK_ALLOW_NATIVE_TOOLS=1` : il n'y a aucun sandbox, l'outil tourne avec les privilèges du worker. Ce n'est pas une friction gratuite — c'est la seule chose qui distingue « j'ai choisi ce risque » de « je ne savais pas ».

Le contrat d'erreur reste identique : code retour non nul → `ToolExecutionError`, stderr toujours écrit dans `logs/stderr.log`.

---

## 7. Feuille de route d'outils

Ordonnée par (impact ÷ effort). Chacun est désormais « 1 dossier ».

### Vague 1 — CTF surtout, très rentable

| Outil | `accepts.kinds` | Pourquoi |
|---|---|---|
| **binwalk / foremost** | *(vide — générique)* | Premier réflexe sur tout artefact inconnu. Sortie triviale à normaliser. |
| **zsteg / steghide** | `image_png, image_bmp, image_jpeg, audio` | Le pain quotidien du CTF forensics. |
| **tshark + Zeek** | `pcap, pcapng` | 2ᵉ catégorie CTF la plus fréquente. Zeek sort `conn/dns/http/files` déjà tabulé — cadeau pour `Finding`. |
| **YARA** | *(vide)* | **Déjà à 80 % dans ton repo** (`yara-python`, `rules_manager.py`, `scanner.py`, règles de test) mais branché sur le pipeline mort. Le rebrancher est le meilleur coup disponible. |
| **oletools / pdfid** | `office_ole, office_ooxml, pdf` | Macros et JS malveillants. CTF *et* phishing réel. |
| **bulk_extractor** | *(vide)* | Emails, URLs, CB, clés sur n'importe quel blob. |

### Vague 2 — DFIR sérieux

| Outil | Note |
|---|---|
| **Hayabusa** / **Chainsaw** | EVTX mappé ATT&CK / règles Sigma. Excellent rapport signal-bruit. |
| **The Sleuth Kit** | `plugins/disk/tsk.py` existe déjà, mort. Débloque E01/DD/RAW. |
| **RegRipper** | Le standard pour les ruches Windows, sans dépendre d'EZTools/Windows. |
| **capa** | Capacités d'un binaire mappées ATT&CK, JSON conçu pour être consommé. |
| **Plaso** | *Le* multiplicateur (super-timeline) — mais **à faire après** la montée en charge : des heures de runtime et une sortie énorme. |
| **dissect** (Fox-IT) | Alternative moderne, tout Python. Pourrait remplacer 3 outils — mérite une vraie évaluation. |

### Deux fonctionnalités transverses qui valent plus que 5 outils

**a) Le triage automatique** — déjà livré. C'est le plugin `triage` + le moteur d'identification.

**b) Le chaînage (DAG)** — la brique manquante. `emits` est déjà déclaré partout ; il reste à écrire un `pipeline.yaml` où une étape consomme les `emits` de la précédente. C'est ce qui transforme « lanceur d'outils » en « plateforme » : iLEAPP produit des fichiers → ExifTool les traite → YARA les scanne.

---

## 8. Erreurs classiques

| Symptôme | Cause |
|---|---|
| Le plugin n'apparaît pas | `enabled: false`, ou le fichier ne s'appelle pas exactement `plugin.yaml` |
| L'API refuse de démarrer | Un manifeste invalide — **c'est voulu**, le message nomme le fichier fautif |
| L'outil tourne, 0 finding | Le normalizer ne trouve pas le fichier attendu. Regarde `logs/stdout.log` dans le workspace du job |
| Jamais auto-planifié | `auto: true` oublié, ou `accepts.kinds` ne contient pas le kind détecté |
| Warning « runs unhardened » | Tu as mis `network: bridge`, `readonly: false` ou `user: root`. Justifie-le ou corrige-le |
| `ToolUnavailableError` | Le worker n'atteint pas Docker. Vérifie `DOCKER_HOST` et le socket-proxy |
