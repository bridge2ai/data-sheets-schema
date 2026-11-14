#!/usr/bin/env bash
# 6233, 2026-11-14: one offline public case; inputs case/output names; outputs logs in assigned scratch.
set -eu
task_root=$(cd "$(dirname "$0")/../.." && pwd)
scratch_root=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-bash-timeout-20261114
python_bin=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python
case_name=${1:?case required}
output_name=${2:?fresh output basename required}
case "$output_name" in *[!a-zA-Z0-9_-]*|'') exit 2;; esac
case "$case_name" in
 correction) node=tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion;;
 omissions) node=tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses;;
 pending) node=tests/test_native_pending_public_completion.py::test_pending_floor_public_completion_retains_diagnostic_reading;;
 *) exit 2;;
esac
output_dir="$scratch_root/$output_name"
mkdir "$output_dir"
mkdir -p "$scratch_root/tmp"
export TMPDIR="$scratch_root/tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$task_root/src"
cd "$task_root"
command=("$python_bin" -m pytest "$node" --basetemp="$output_dir/cases" -p no:cacheprovider --junitxml="$output_dir/junit.xml")
printf '%q ' "${command[@]}" > "$output_dir/command.txt"
date -u > "$output_dir/start.txt"
set +e
"${command[@]}" > "$output_dir/pytest.log" 2>&1
status=$?
set -e
printf '%s\n' "$status" > "$output_dir/exit-status.txt"
date -u > "$output_dir/end.txt"
exit "$status"
