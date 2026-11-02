#!/usr/bin/env bash
# Purpose: serial offline collection, D41 and full CI-shard-union validation.
# Inputs: Python, tested worktree, TMPDIR scratch, durable evidence; outputs logs.
# Ref #5212 legacy design; 2026-10-29. Run canary separately and inspect it first.
set -u
validation_python=$1
validation_tree=$2
validation_scratch=$3
validation_evidence=$4
validation_mode=$5
validation_scripts=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
validation_command=(/usr/bin/sandbox-exec -D "LOCAL_ROOT=$validation_scratch" -D "EVIDENCE_ROOT=$validation_evidence" -f "$validation_scripts/d41_validation_offline_20261029.sb" "$validation_python" -S -P -B "$validation_scripts/d41_legacy_controls_20261029.py")
validation_steps=(collect suites ci)
if [[ "$validation_mode" == canary ]]; then validation_steps=(ci-canary); fi
if [[ "$validation_mode" == observer-canary ]]; then validation_steps=(ci-observer-canary); fi
if [[ "$validation_mode" == ci-only ]]; then validation_steps=(ci); fi
for validation_step in "${validation_steps[@]}"; do
    "${validation_command[@]}" --mode "$validation_step" --tree "$validation_tree" \
        --scratch "$validation_scratch" --evidence "$validation_evidence" \
        > "$validation_evidence/$validation_step.log" 2>&1
    validation_code=$?
    echo "$validation_step exit=$validation_code"
    # A failing collected test is evidence, not permission to omit later gates.
    # A missing result means the harness itself failed; stop for investigation.
    if [[ ! -s "$validation_evidence/$validation_step/result.json" ]]; then exit 2; fi
done
