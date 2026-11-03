#!/usr/bin/env bash
# Purpose: retain bounded, serial offline pytest evidence for G1V-1/G1V-2.
# Inputs: tree, evidence directory, explicit pytest arguments; outputs: log, XML, status, identity.
# Uses the existing G1 offline launcher; no providers/network. Date: 2026-11-03.
set -eu
check_tree=$(cd -- "$1" && pwd)
check_output=$2
shift 2
check_helpers=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
check_repo=$(cd -- "$check_helpers/../../.." && pwd)
check_python=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python
mkdir -p "$check_output/tmp" "$check_output/cache"
export TMPDIR="$check_output/tmp" PYTHONPYCACHEPREFIX="$check_output/cache"
export PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 UV_OFFLINE=1 GIT_NO_LAZY_FETCH=1
export G1_CHECKOUT_ROOT="$check_tree" G1_TEST_FAILURES_PATH="$check_output/failures.jsonl"
export PYTHONPATH="$check_tree/src:$check_tree/fairscape_models:$check_tree"
cd -- "$check_tree"
{
    "$check_python" -S -B --version
    printf 'tree=%s\n' "$check_tree"
    git rev-parse HEAD || true
    shasum -a 256 pyproject.toml poetry.lock
    printf 'argv:'
    printf ' %q' "$@"
    printf '\n'
} > "$check_output/identity.txt" 2>&1
set +e
"$check_helpers/timeout" 3600 "$check_python" -S -B \
    "$check_repo/scripts/adhoc/generality_g1_offline_20261029.py" pytest \
    -p no:cacheprovider --basetemp="$check_output/cases" \
    --junitxml="$check_output/pytest.xml" "$@" > "$check_output/pytest.log" 2>&1
check_status=$?
set -e
printf '%s\n' "$check_status" > "$check_output/exit-status.txt"
tail -n 24 "$check_output/pytest.log"
exit "$check_status"
