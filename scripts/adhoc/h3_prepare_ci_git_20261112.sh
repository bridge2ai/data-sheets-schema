#!/usr/bin/env bash
# Purpose: give the lead's archive export real Git metadata for offline tests.
# Inputs: exported CI tree and matching commit. Outputs: metadata only, no source edits.
# Serves helper3 CI origin proof, 2026-11-12. No fetch or remote is configured.
set -euo pipefail
tree=${1:?tree}
commit=${2:?commit}
primary=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema
case "$tree" in /Users/marcin/agent-work/data-sheets-schema/ci-sim-*) ;; *) exit 2;; esac
test ! -e "$tree/.git"
git -C "$tree" init -b ci-simulation
objects=$(git -C "$primary" rev-parse --path-format=absolute --git-path objects)
printf '%s\n' "$objects" > "$tree/.git/objects/info/alternates"
git -C "$tree" update-ref refs/heads/ci-simulation "$commit"
git -C "$tree" read-tree "$commit"
git -C "$tree" diff --exit-code
git -C "$tree" rev-parse HEAD
