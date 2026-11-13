#!/usr/bin/env bash
# Purpose: reproduce on this host what GitHub's runner sees when it collects
#   the test suite of a commit: the tree exported to a directory that is NOT
#   below `d4d-executions`, then `pytest --collect-only`. On 2026-11-12 the
#   first full CI run of the native stack top (run 42976790438, head
#   1a137b588604) failed every job at collection because
#   tests/test_native_u3c_test_driver.py imports a script that refuses to load
#   unless the source sits below the canonical d4d-executions root. Local runs
#   in worktrees under d4d-executions cannot see that class of fault.
# Inputs: argument 1, a commit present in the primary repository's object
#   store. Reads the primary repository; uses its virtual environment's Python.
# Outputs: the exported tree under ~/agent-work/data-sheets-schema/ci-sim-<12>/
#   and the collection log beside it (ci-sim-<12>.collect.log). Prints the
#   collection summary and every collection error. Collects only; runs no test.
# Serves: owner direction D134 (native arm first), gate G12 of the native
#   critical path. Date: 2026-11-12.
set -euo pipefail
PRIMARY=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema
COMMIT=${1:?commit}
git -C "$PRIMARY" cat-file -e "$COMMIT^{commit}"
FULL=$(git -C "$PRIMARY" rev-parse "$COMMIT^{commit}")
SHORT=${FULL:0:12}
BASE="$HOME/agent-work/data-sheets-schema"
DEST="$BASE/ci-sim-$SHORT"
LOG="$BASE/ci-sim-$SHORT.collect.log"
case "$DEST" in *d4d-executions*) echo "destination must not be below d4d-executions" >&2; exit 2;; esac
mkdir -p "$BASE"
if [ ! -f "$DEST/pyproject.toml" ]; then
  mkdir -p "$DEST"
  git -C "$PRIMARY" archive "$FULL" | tar -x -C "$DEST"
fi
echo "exported $FULL to $DEST ($(find "$DEST" -type f | wc -l | tr -d ' ') files)"
cd "$DEST"
set +e
env -u CBORG_API_KEY -u ANTHROPIC_API_KEY -u D4D_MANIFEST -u D4D_PROFILE \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$DEST/src" \
  "$PRIMARY/.venv/bin/python" -m pytest --collect-only -q tests \
  -p no:cacheprovider > "$LOG" 2>&1
RC=$?
set -e
echo "pytest --collect-only exit code: $RC"
echo "--- collection errors"
grep -E '^ERROR |^E  ' "$LOG" | cut -c1-220 || true
echo "--- summary"
tail -3 "$LOG" | cut -c1-220
echo "log: $LOG"
