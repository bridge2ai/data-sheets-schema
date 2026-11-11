#!/usr/bin/env bash
# Purpose: check PR 5808's head merged onto the main it would land on, since the
#   PR's green CI ran against an older base (7233f193) and main has since gained
#   PR 5814 and PR 5835. Builds a LOCAL merge preview (never pushed, no branch),
#   checks it out sparsely (no data/ or notes/: the disk has ~12 GB free), and
#   runs only the test files either side touched, plus a collect-only pass.
# Inputs: none; identities are fixed below. Uses the primary checkout's .venv.
# Outputs: logs and JUnit XML under $WT/tmp/combined-head-20261111/.
# Usage: pr5808_combined_head_check_20261111.sh setup|canary|focused|collect|rerun|rerun2|widen|widen2|collect2
# History: canary, focused and collect ran 2026-11-11T07:35Z with
#   `-o tmp_path_retention_policy=none`. That option makes pytest leave its base
#   temp unlocked (keep=0), and the nested pytest sessions test_ci_sharding
#   spawns then rotated the parent's directory away: 76 setup errors and one
#   failure, all FileNotFoundError on pytest-of-<user>/pytest-N. Those logs are
#   kept as focused.log / focused.junit.xml. `rerun` repeats the two affected
#   files without the option and with a base temp of its own. `widen` adds the
#   few data/ and notes/ directories the 16 sparse collection errors named,
#   and `collect2` repeats the collect-only pass.
# Serves: the merge decision on PR 5808 (lead transfer 2026-11-11).
# Date: 2026-11-11.
set -euo pipefail

REPO=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema
EXEC=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions
WT=$EXEC/claude-pr5808-combined-20261111
MAIN=925d726d67cdd03fe28fdeafdde60fa27df57205
HEAD_PR=6792947ea6558d10c85106065b023cb57838835a
OUT=$WT/tmp/combined-head-20261111
PYTEST=$REPO/.venv/bin/pytest
FOCUSED=(
  tests/test_schema_release_identity.py
  tests/test_final_generation_acceptance.py
  tests/test_final_record_component_limits.py
  tests/test_ci_timing_update.py
  tests/test_ci_sharding.py
  tests/test_schema_snapshot_cache.py
)

run_pytest() {  # name, then pytest arguments
  local name=$1; shift
  mkdir -p "$OUT"
  local start end rc=0
  start=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  ( cd "$WT" && PYTHONPATH="$WT/src" GIT_CONFIG_GLOBAL=/dev/null \
      "$PYTEST" -p no:cacheprovider ${RETENTION_OPT:+-o "$RETENTION_OPT"} "$@" \
      > "$OUT/$name.log" 2>&1 ) || rc=$?
  end=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  printf '%s rc=%s start=%s end=%s\n' "$name" "$rc" "$start" "$end" | tee -a "$OUT/runs.txt"
  tail -n 4 "$OUT/$name.log"
  return 0
}

case "${1:-}" in
  setup)
    [ -e "$WT" ] && { echo "refusing: $WT exists"; exit 2; }
    tree=$(git -C "$REPO" merge-tree --write-tree "$MAIN" "$HEAD_PR")
    commit=$(git -C "$REPO" commit-tree "$tree" -p "$MAIN" -p "$HEAD_PR" \
      -m "Local merge preview: PR 5808 head onto main 925d726d (not pushed)")
    git -C "$REPO" worktree add --no-checkout --detach "$WT" "$commit"
    git -C "$WT" sparse-checkout set --cone src tests utils project docs scripts .github .claude
    git -C "$WT" checkout --detach "$commit"
    mkdir -p "$OUT"
    {
      echo "tree=$tree"; echo "commit=$commit"; echo "main=$MAIN"; echo "pr_head=$HEAD_PR"
      echo "created=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      echo "parents=$(git -C "$WT" rev-list --parents -n 1 HEAD)"
    } | tee "$OUT/identity.txt"
    ;;
  canary)
    RETENTION_OPT=tmp_path_retention_policy=none
    run_pytest canary -q "${FOCUSED[0]}" --junitxml="$OUT/canary.junit.xml"
    ;;
  focused)
    RETENTION_OPT=tmp_path_retention_policy=none
    run_pytest focused -q "${FOCUSED[@]}" --junitxml="$OUT/focused.junit.xml"
    ;;
  collect)
    RETENTION_OPT=tmp_path_retention_policy=none
    run_pytest collect --collect-only -q tests
    ;;
  rerun)
    run_pytest rerun -q tests/test_ci_sharding.py tests/test_schema_snapshot_cache.py \
      --basetemp="$OUT/basetemp-rerun" --junitxml="$OUT/rerun.junit.xml"
    ;;
  rerun2)
    # `rerun` put --basetemp inside the worktree, so the nested pytest sessions
    # took the worktree as rootdir and printed node ids relative to it; the one
    # test that compares bare node ids failed on that alone. Repeat it with a
    # base temp outside any repository.
    mkdir -p "$EXEC/scratch-claude-pr5808-basetemp-20261111"
    run_pytest rerun2 -q \
      "tests/test_ci_sharding.py::test_one_long_case_starts_before_a_file_with_many_short_cases" \
      --basetemp="$EXEC/scratch-claude-pr5808-basetemp-20261111/rerun2" \
      --junitxml="$OUT/rerun2.junit.xml"
    ;;
  widen)
    git -C "$WT" sparse-checkout add data/rubric data/preprocessed \
      notes/matched_cborg_2026-09-13 notes/native_trace_comparison_2026-10-08 \
      notes/claudecode_direct notes/reference_rescore_2026-09-12_cborg_runtime/execution_tools
    du -sh "$WT"
    ;;
  widen2)
    # config/ holds audit_partitions.yaml, which the registration builder reads
    # for --partition; added for AGY3's no-write builder rehearsal.
    git -C "$WT" sparse-checkout add config
    ls "$WT/config"
    ;;
  collect2)
    run_pytest collect2 --collect-only -q tests --basetemp="$OUT/basetemp-collect2"
    ;;
  *)
    echo "usage: $0 setup|canary|focused|collect|rerun|rerun2|widen|widen2|collect2"; exit 64 ;;
esac
