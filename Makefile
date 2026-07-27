# =============================================================================
# ForensicStack — developer task runner
# =============================================================================
# Thin wrappers around the scripts in scripts/ and the compose stack in
# backend/docker-compose.yml. Nothing here reimplements logic: if a target
# feels wrong, fix the underlying script, not the Makefile.
#
# POSIX sh is used deliberately (no bashisms) so this works on macOS, Linux
# and Git-Bash/WSL on Windows.
#
# Usage: make <target>   —   run `make` or `make help` for the list.
# =============================================================================

SHELL := /bin/sh

# Single source of truth for the compose invocation. Override the project name
# with `make up COMPOSE_PROJECT=foo` to run a second isolated stack.
COMPOSE_FILE    ?= backend/docker-compose.yml
COMPOSE_PROJECT ?= forensicstack
COMPOSE         := docker compose -p $(COMPOSE_PROJECT) -f $(COMPOSE_FILE)

# Prefer the venv's tools so `make lint` matches CI even when the venv is not
# activated in the current shell; fall back to whatever is on PATH.
# Absolute paths, so targets that `cd` into a subdirectory still resolve them.
VENV_BIN := $(CURDIR)/backend/venv/bin
PYTHON   := $(shell [ -x $(CURDIR)/backend/venv/bin/python ] && echo $(CURDIR)/backend/venv/bin/python || echo python3)
PYTEST   := $(shell [ -x $(CURDIR)/backend/venv/bin/pytest ] && echo $(CURDIR)/backend/venv/bin/pytest || echo pytest)
RUFF     := $(shell [ -x $(CURDIR)/backend/venv/bin/ruff   ] && echo $(CURDIR)/backend/venv/bin/ruff   || echo ruff)
BLACK    := $(shell [ -x $(CURDIR)/backend/venv/bin/black  ] && echo $(CURDIR)/backend/venv/bin/black  || echo black)

# Every target is a task name, not a file to be built.
.PHONY: help setup up down logs test lint fmt build-tools clean

# `make` with no arguments prints the menu rather than running something.
.DEFAULT_GOAL := help

## help: show this list of targets
help:
	@echo 'ForensicStack — available targets:'
	@echo ''
	@grep -E '^## [a-z-]+:' $(MAKEFILE_LIST) \
		| sed 's/^## //' \
		| awk -F': ' '{ printf "  \033[36m%-14s\033[0m %s\n", $$1, substr($$0, index($$0, ": ") + 2) }'
	@echo ''
	@echo 'Compose file: $(COMPOSE_FILE)   project: $(COMPOSE_PROJECT)'

## setup: full one-time install (prereqs, stack, images, venv, symbols)
setup:
	@chmod +x scripts/setup.sh
	@./scripts/setup.sh

## up: start the infrastructure + application containers in the background
up:
	$(COMPOSE) up -d
	@echo 'Stack starting. Follow progress with: make logs'

## down: stop and remove the containers (named volumes are preserved)
down:
	$(COMPOSE) down

## logs: tail the logs of every service (Ctrl-C to detach)
logs:
	$(COMPOSE) logs -f --tail=100

## test: run the backend pytest suite
test:
	cd backend && $(PYTEST) tests -v

## lint: check formatting and run the ruff linter (read-only, CI-safe)
lint:
	$(RUFF) check backend
	$(BLACK) --check backend

## fmt: auto-format the code and apply ruff's safe fixes
fmt:
	$(RUFF) check --fix backend
	$(BLACK) backend

## build-tools: build the per-tool forensic Docker images (iLEAPP, Vol3, ...)
build-tools:
	@chmod +x scripts/build-tools.sh
	@./scripts/build-tools.sh

## clean: remove caches and build artifacts (does NOT touch Docker volumes)
clean:
	@# -prune on .git/node_modules/venv keeps this fast and avoids nuking
	@# caches that belong to third-party dependencies.
	find . \( -name .git -o -name node_modules -o -name venv \) -prune -o \
		\( -type d \( -name '__pycache__' -o -name '.pytest_cache' \
		   -o -name '.ruff_cache' -o -name '.mypy_cache' \) \) \
		-exec rm -rf {} +
	find . \( -name .git -o -name node_modules -o -name venv \) -prune -o \
		-type f -name '*.py[co]' -exec rm -f {} +
	rm -rf web/.next web/tsconfig.tsbuildinfo backend/htmlcov backend/.coverage
	@echo 'Caches cleared. Docker volumes and node_modules were left alone;'
	@echo 'remove volumes explicitly with: $(COMPOSE) down -v'
