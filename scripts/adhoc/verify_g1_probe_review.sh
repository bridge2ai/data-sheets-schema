#!/bin/bash
# Purpose: offline G1 regression checks for issues 6204, 6209, 6210, 6219, 6226, 6228.
# Inputs: committed worktree; outputs: retained .temp/g1/final-suite artifacts and log.
# Date: 2026-11-14. No native/provider execution is authorized by this script.
set -u
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/src"
mkdir -p .temp/g1
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -m pytest \
  tests/test_native_permission_probe.py tests/test_native_u4b_probe_sequence.py \
  tests/test_native_model_aliases.py tests/test_native_shared_gates.py \
  tests/test_native_execution_gates.py tests/test_native_synthetic_profiles.py \
  -n 4 --dist=loadscope -q --basetemp=.temp/g1/final-suite "$@" \
  > .temp/g1/final-suite.log 2>&1
result=$?
printf '%s\n' "$result" > .temp/g1/final-suite.exit
cat .temp/g1/final-suite.log
exit "$result"
