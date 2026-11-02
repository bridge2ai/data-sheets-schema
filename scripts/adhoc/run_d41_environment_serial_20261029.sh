#!/usr/bin/env bash
# Purpose: isolate #5212 validation-environment failures, 2026-10-29.
# Inputs: Python, unchanged base, TMPDIR scratch/evidence, suite and stage.
# Outputs: external JSON/JUnit/log evidence. Canary before each full group.
set -eu
control_python=$1
control_tree=$2
control_scratch=$3
control_evidence=$4
control_suite=$5
control_stage=$6
control_scripts=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
control_name="$control_suite-environment-$control_stage"
mkdir -p "$control_scratch" "$control_evidence"
control_command=(/usr/bin/sandbox-exec -D "LOCAL_ROOT=$control_scratch" -D "EVIDENCE_ROOT=$control_evidence" \
    -f "$control_scripts/d41_validation_offline_20261029.sb" \
    "$control_python" -S -P -B "$control_scripts/d41_environment_controls_20261029.py" \
    --tree "$control_tree" --scratch "$control_scratch" --evidence "$control_evidence" \
    --suite "$control_suite")
if [[ "$control_stage" == canary ]]; then control_command+=(--canary); fi
exec "${control_command[@]}" > "$control_evidence/$control_name.log" 2>&1
