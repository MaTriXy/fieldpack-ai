#!/usr/bin/env bash
# Drive the E2E harness against a running FieldPack stack.
# Override the target with FIELDPACK_E2E_URL (default http://localhost:8000).
set -e
export FIELDPACK_E2E_URL="${FIELDPACK_E2E_URL:-http://localhost:8000}"
cd "$(dirname "$0")/../backend"
PYTHONPATH=. ../venv/Scripts/python.exe -m pytest tests/e2e/ -m e2e -v
