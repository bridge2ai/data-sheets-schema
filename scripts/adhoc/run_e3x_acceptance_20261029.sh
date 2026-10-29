#!/usr/bin/env bash
# Purpose: E3x review F1-F12 final acceptance, 2026-10-29.
# Inputs: Python interpreter, external pytest basetemp. Output: serial pytest log.
# Run in the selected real git checkout; no providers, fetches or rating runs.
set -euo pipefail
e3x_python=${1:?Python interpreter required}
e3x_basetemp=${2:?External pytest basetemp required}
e3x_checkout=$(git rev-parse --show-toplevel)
case "$e3x_basetemp/" in
    "$e3x_checkout/"*) echo 'pytest basetemp must be outside checkout' >&2; exit 2 ;;
esac
env -u ANTHROPIC_API_KEY -u CBORG_API_KEY -u OPENAI_API_KEY \
    PYTHONPATH="$e3x_checkout/src" PYTHONDONTWRITEBYTECODE=1 \
    "$e3x_python" -m pytest -q -o addopts='' -p no:cacheprovider \
    --basetemp="$e3x_basetemp" \
    tests/test_arm_comparison.py tests/test_blind_review_pack.py \
    tests/test_registered_eval_runner.py tests/test_audit_evaluation_comparability.py \
    tests/test_d52_scoring.py tests/test_evaluation/test_evaluate_d4d.py \
    tests/test_evaluation/test_rubric20_scoring.py tests/test_evaluation/test_general_context.py \
    tests/test_evaluation/test_explicit_dataset_scope.py tests/test_d52_publication_labels.py \
    tests/test_e3x_fixes.py tests/test_e3x_blinding_fixes.py \
    tests/test_e3x_receipt_fixes.py tests/test_e3x_guard_kills.py
