#!/usr/bin/env bash
# Purpose: serial offline #5212 authentic controls after the verified c3 canary.
# Inputs: dependency Python, repository, scratch/pre-d41; output: retained logs.
# Ref #5212; 2026-10-29. Uses the same driver/process mode as the one-case canary.
set -euo pipefail
legacy_python=$1
legacy_repo=$2
legacy_scratch=$3
legacy_evidence=${4:-$legacy_scratch}
legacy_mode=${5:-rest}
legacy_script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
legacy_driver="$legacy_script_dir/d41_legacy_controls_20261029.py"
legacy_command=(/usr/bin/sandbox-exec -D "LOCAL_ROOT=$legacy_scratch" -f "$legacy_script_dir/d41_loopback_only_20261029.sb" "$legacy_python" -S -P -B "$legacy_driver")
legacy_cases=(c1 c2 c4 c5 c6 c7 c8)
if [[ "$legacy_mode" == canary ]]; then legacy_cases=(c3); fi
for legacy_case in "${legacy_cases[@]}"; do
    "${legacy_command[@]}" --mode generate --case "$legacy_case" \
        --tree "$legacy_scratch/pre-d41" --scratch "$legacy_scratch" --evidence "$legacy_evidence" \
        > "$legacy_evidence/$legacy_case-generate.log" 2>&1
    legacy_calls=2
    case "$legacy_case" in
        c4) legacy_calls='2 3' ;;
        c5) legacy_calls=1 ;;
        c6) legacy_calls='1 2' ;;
    esac
    for legacy_call in $legacy_calls; do
        "${legacy_command[@]}" --mode replay --case "$legacy_case" \
            --call "$legacy_call" --tree "$legacy_repo" --scratch "$legacy_scratch" --evidence "$legacy_evidence" \
            > "$legacy_evidence/$legacy_case-replay-$legacy_call.log" 2>&1
    done
    echo "$legacy_case complete"
done
if [[ "$legacy_mode" == canary ]]; then exit 0; fi
for legacy_case in c5 c6; do
    "${legacy_command[@]}" --mode generate --derived --case "$legacy_case" \
        --tree "$legacy_scratch/pre-d41" --scratch "$legacy_scratch" --evidence "$legacy_evidence" \
        > "$legacy_evidence/$legacy_case-derived-generate.log" 2>&1
    for legacy_call in 2 3; do
        "${legacy_command[@]}" --mode replay --derived --case "$legacy_case" \
            --call "$legacy_call" --tree "$legacy_repo" --scratch "$legacy_scratch" --evidence "$legacy_evidence" \
            > "$legacy_evidence/$legacy_case-derived-replay-$legacy_call.log" 2>&1
    done
    echo "$legacy_case emitted-artifact supplement complete"
done
