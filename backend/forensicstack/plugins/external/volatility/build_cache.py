"""
Pre-build Volatility3 identifier.cache from ISF filenames.

Run during Docker image build (after symbols are downloaded) to avoid
the ~14-minute first-run cost of decompressing all 3014 .json.xz files.

GUIDs are encoded directly in filenames:
  <pdb_name>-<GUID><AGE>.json.xz  →  identifier = "<pdb_name>!<GUID><AGE>"
"""
import sqlite3, os, re, glob, datetime

SYM_DIR = os.path.join(
    os.path.dirname(__import__("volatility3").__file__), "symbols"
)
CACHE_DIR = "/root/.cache/volatility3"
os.makedirs(CACHE_DIR, exist_ok=True)
db_path = os.path.join(CACHE_DIR, "identifier.cache")

conn = sqlite3.connect(db_path)
conn.execute("""
    CREATE TABLE IF NOT EXISTS database_info (schema_version INT DEFAULT 1)
""")
conn.execute("""
    CREATE TABLE IF NOT EXISTS cache (
        location TEXT NOT NULL, identifier TEXT, operating_system TEXT,
        hash TEXT, stats_base_types INT DEFAULT 0, stats_types INT DEFAULT 0,
        stats_enums INT DEFAULT 0, stats_symbols INT DEFAULT 0,
        local BOOL, cached DATETIME
    )
""")
conn.execute("DELETE FROM cache")
conn.execute("DELETE FROM database_info")
conn.execute("INSERT INTO database_info VALUES (1)")

now = datetime.datetime.utcnow().isoformat()
rows = []
pattern = re.compile(r"^(.+)-([0-9A-Fa-f]+)\.json\.xz$")

for xz in glob.glob(os.path.join(SYM_DIR, "**", "*.json.xz"), recursive=True):
    fname = os.path.basename(xz)
    m = pattern.match(fname)
    if not m:
        continue
    pdb_name = m.group(1)   # e.g. "ntkrnlmp"
    guid_age  = m.group(2)  # e.g. "A57C10D40BAB…1"
    identifier = f"{pdb_name}!{guid_age}"
    rows.append((xz, identifier, "windows", None, 0, 0, 0, 0, True, now))

conn.executemany(
    "INSERT INTO cache VALUES (?,?,?,?,?,?,?,?,?,?)", rows
)
conn.commit()
conn.close()
print(f"Pre-built identifier.cache: {len(rows)} entries -> {db_path}")

# Also bake a copy outside /root/.cache so it survives a named-volume mount
# shadowing that directory.  entrypoint.sh restores from this backup when
# the volume-mounted cache is empty or missing.
import shutil
backup = "/app/identifier.cache.baked"
shutil.copy2(db_path, backup)
print(f"Backup copy written to {backup}")
