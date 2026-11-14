#!/usr/bin/env bash
# Issue 6233, 2026-11-14: isolated offline public test and persisted CPU evidence.
# Inputs: case and fresh directory name. Outputs: assigned scratch logs and JSONL.
set -eu
task_root=$(cd "$(dirname "$0")/../.." && pwd)
scratch_root=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-callback-growth-20261114
python_bin=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python
case_name=${1:?case required}
output_name=${2:?fresh output basename required}
case "$output_name" in *[!a-zA-Z0-9_-]*|'') exit 2;; esac
case "$case_name" in
 correction) node=tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion;;
 omissions) node=tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses;;
 pending) node=tests/test_native_pending_public_completion.py::test_pending_floor_public_completion_retains_diagnostic_reading;;
 omissions-profile) node=--standalone-omissions;;
 correction-profile) node=--standalone-correction;;
 *) exit 2;;
esac
mkdir -p "$scratch_root/tmp"
output_dir="$scratch_root/$output_name"
mkdir "$output_dir"
export TMPDIR="$scratch_root/tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$task_root/src"
export CALLBACK_METRICS="$output_dir/callback-cpu.jsonl"
cd "$task_root"
printf '%s\n' "$python_bin scripts/adhoc/measure_callback_growth_20261114.py $node --basetemp=$output_dir/cases -p no:cacheprovider --junitxml=$output_dir/junit.xml" > "$output_dir/command.txt"
shasum -a 256 scripts/adhoc/measure_callback_growth_20261114.py > "$output_dir/diagnostic-source.sha256"
uptime > "$output_dir/host-load-start.txt"
date -u > "$output_dir/start.txt"
set +e
"$python_bin" scripts/adhoc/measure_callback_growth_20261114.py "$node" --basetemp="$output_dir/cases" -p no:cacheprovider --junitxml="$output_dir/junit.xml" > "$output_dir/pytest.log" 2>&1
status=$?
set -e
printf '%s\n' "$status" > "$output_dir/exit-status.txt"
date -u > "$output_dir/end.txt"
uptime > "$output_dir/host-load-end.txt"
exit "$status"
