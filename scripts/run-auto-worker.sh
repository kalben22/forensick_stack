#!/usr/bin/env bash
# =============================================================================
# run-auto-worker.sh — start the autonomous triage worker on the host
# =============================================================================
# The /api/v1/analyze pipeline queues jobs on a Redis Stream consumed by
# forensicstack.stream_worker (NOT the legacy forensicstack.worker). This runs
# that consumer natively against the compose stack's exposed Redis.
#
# Prereqs: the compose stack is up, tool images are built (make build-tools),
# and the host Docker socket is reachable.
#
# Usage:  ./scripts/run-auto-worker.sh [concurrency]
# =============================================================================
set -euo pipefail

CONCURRENCY="${1:-2}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
ENV_FILE="$BACKEND/.env"

[ -f "$ENV_FILE" ] || { echo "backend/.env not found — run scripts/setup first." >&2; exit 1; }

# Load only the keys we need (KEY=VALUE lines, ignore comments/blank).
get_env() { grep -E "^\s*$1\s*=" "$ENV_FILE" | tail -1 | cut -d= -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'; }

# Redis is published to the host by compose — reach it on localhost, not the
# compose-internal "redis" hostname.
export REDIS_HOST="127.0.0.1"
export REDIS_PORT="$(get_env REDIS_PORT)"; REDIS_PORT="${REDIS_PORT:-6379}"
export REDIS_PASSWORD="$(get_env REDIS_PASSWORD)"

# Native run: the worker's workspace path IS the daemon's path, so no
# HOST_WORKSPACE_ROOT translation is needed.
export FORENSICSTACK_WORKSPACE="$BACKEND/tmp_jobs/work"
mkdir -p "$FORENSICSTACK_WORKSPACE"

# Prefer the project venv interpreter.
PY="$BACKEND/forensic/bin/python"
[ -x "$PY" ] || PY="$BACKEND/venv/bin/python"
[ -x "$PY" ] || PY="python3"

echo "[auto-worker] Redis  : $REDIS_HOST:$REDIS_PORT"
echo "[auto-worker] Workdir: $FORENSICSTACK_WORKSPACE"
echo "[auto-worker] Consuming /analyze jobs (concurrency=$CONCURRENCY). Ctrl-C to stop."

cd "$BACKEND"
exec "$PY" -u -m forensicstack.stream_worker --concurrency "$CONCURRENCY"
