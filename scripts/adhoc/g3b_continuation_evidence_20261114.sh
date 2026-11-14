#!/usr/bin/env bash
# Purpose: retain local continuation evidence for issue 6214, 2026-11-14.
# Inputs: this checkout, the original candidate, and existing scratch test logs.
# Outputs: commit, diff, pin and blocker summaries in the supplied scratch directory.
set -euo pipefail
g3b_scratch=${1:?Supply the existing G3b scratch directory}
test -d "$g3b_scratch"
git log -4 --format='%H %s' > "$g3b_scratch/continuation-commits.txt"
git diff 6ed891e84 --stat > "$g3b_scratch/continuation-diff-stat.txt"
git diff --check > "$g3b_scratch/continuation-diff-check.txt"
git status --short > "$g3b_scratch/continuation-status.txt"
shasum -a 256 tests/fixtures/native_shared_execution/fake_cli.py \
    src/data_sheets_schema/native_runtime_profiles.py > "$g3b_scratch/continuation-pin-hashes.txt"
git diff 6ed891e84 -- src/data_sheets_schema/shared_generation.py \
    src/data_sheets_schema/api_runner.py src/download/prompts/canonical_hashes.yaml \
    tests/utils/run_spec_boundary_contracts.json \
    src/data_sheets_schema/native_controller_sources_v1.json \
    src/data_sheets_schema/native_controller_sources_v2.json \
    > "$g3b_scratch/continuation-protected-diff.txt"
jq '{first_stop,state,runtime_gates_passed}' \
    "$g3b_scratch/continuation-canary-2/test_denial_live_and_saved_Bas0/not_prescribed/actual-result.json" \
    > "$g3b_scratch/continuation-blocker.json"
test -s "$g3b_scratch/continuation-blocker.json"
test -s "$g3b_scratch/continuation-commits.txt"
