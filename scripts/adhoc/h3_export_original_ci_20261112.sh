#!/usr/bin/env bash
# Export the exact scanner input tree from CI for H3 profiling, 2026-11-12.
# Input: local Git commit. Output: new immutable archive outside executions.
# Uses the lead simulation script's archive path, omitting unrelated collection.
set -euo pipefail
primary=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema
commit=1a137b58860416a31618de44173180d021dfcc61
dest=/Users/marcin/agent-work/data-sheets-schema/ci-sim-1a137b588604
test ! -e "$dest"
mkdir "$dest"
git -C "$primary" archive "$commit" | tar -x -C "$dest"
git -C "$primary" rev-parse "$commit"
shasum -a 256 "$dest/.claude/skills/d4d-generation-specificity-audit/scan.py" "$dest/tests/test_generation_specificity_skill.py"
