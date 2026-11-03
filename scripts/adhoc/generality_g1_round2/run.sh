#!/bin/bash
# Purpose: serial offline P4a findings 1/4/5 validation, 2026-10-30.
# Inputs: offline_pytest.py arguments. Outputs: caller-selected logs/artifacts.
set -eu
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
PYTHON=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python
LAUNCHER="$ROOT/scripts/adhoc/generality_g1_round2/offline_pytest.py"
FLAGS=(-B)
if [[ "$1" == pytest ]]; then
  # Existing G1 harness also isolates .pth startup and routes Poetry/LinkML
  # children into this installed environment without bootstrapping a venv.
  LAUNCHER="$ROOT/scripts/adhoc/generality_g1_offline_20261029.py"
  FLAGS=(-S -B)
fi
cd "$ROOT"
exec env -u ANTHROPIC_API_KEY -u CBORG_API_KEY -u OPENAI_API_KEY -u GEMINI_API_KEY -u GOOGLE_API_KEY \
  HTTP_PROXY=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 ALL_PROXY=http://127.0.0.1:9 \
  http_proxy=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9 all_proxy=http://127.0.0.1:9 NO_PROXY= no_proxy= \
  GIT_NO_LAZY_FETCH=1 PYTHONPATH="$ROOT/src:$ROOT" PYTHONDONTWRITEBYTECODE=1 \
  G1_CHECKOUT_ROOT="$ROOT" \
  VIRTUAL_ENV="$(dirname "$(dirname "$PYTHON")")" PATH="$(dirname "$PYTHON"):$PATH" \
  PIP_NO_INDEX=1 UV_OFFLINE=1 \
  PYTHONPYCACHEPREFIX="$ROOT/.g1-round2-evidence/pycache" \
  "$PYTHON" "${FLAGS[@]}" "$LAUNCHER" "$@"
