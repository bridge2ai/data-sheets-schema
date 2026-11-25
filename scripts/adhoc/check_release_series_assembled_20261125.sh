#!/bin/bash
# check_release_series_assembled_20261125.sh
# Purpose: after the records of a release series are copied by label from their launch
#   worktrees into one tree (the data branch), rerun there the record gates of
#   run_release_series_20261124.sh that do not need the transcript: schema validation of the
#   full and core record, receipts check --strict, scope check, runs check --strict and the
#   render gate. A record that passed in its launch worktree and fails here was changed by
#   the copy or depends on something the launch worktree had and the branch does not.
#   No model call; nothing under data/ is written.
# Inputs:  <assembled worktree> <python of an environment with the project's dependencies>
#          <series> <model> <replicate count> <project> ...
#          Environment: D4D_SERIES_CONDITION (default generic_v9), D4D_SERIES_METHOD (default
#          claudecode_release).
# Outputs: one line per record and check on stdout, then a total; exit 0 when all pass.
# Serves:  the release-series rerun 2026-11-25c (PR 6325, issues 6324, 6312). Date: 2026-11-25.
set -u
W=${1:?assembled worktree}; PY=${2:?python}; SERIES=${3:?series}; MODEL=${4:?model}; REPS=${5:?replicates}; shift 5
[ $# -ge 1 ] || { echo "no projects given" >&2; exit 2; }
CONDITION=${D4D_SERIES_CONDITION:-generic_v9}
METHOD=${D4D_SERIES_METHOD:-claudecode_release}
cd "$W" || exit 2
export PYTHONPATH="$W/src"
SRC=$("$PY" -c "import data_sheets_schema.api_runner as m; print(m.__file__)")
case "$SRC" in "$(pwd -P)"/*) ;; *) echo "STOP: the interpreter imports '$SRC', not this worktree"; exit 2;; esac
D4D=("$PY" -m data_sheets_schema.cli)
BAD=0; N=0
for REP in $(seq 1 "$REPS"); do
  LABEL="${SERIES}_${MODEL}-claudecode-${CONDITION//_/-}_rep${REP}"
  for P in "$@"; do
    N=$((N + 1))
    FULL="data/d4d_concatenated/$METHOD/$LABEL/${P}_d4d.yaml"
    CORE="data/d4d_concatenated/${METHOD}_core/$LABEL/${P}_d4d_core.yaml"
    BUNDLE="data/preprocessed/concatenated/${P}_preprocessed.txt"
    CHUNKS="data/preprocessed/chunks/${P}_chunks.yaml"
    R=""
    "$PY" -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset "$FULL" > /dev/null 2>&1; R="$R full=$?"
    "$PY" -c 'from linkml.validator.cli import cli; cli()' -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset "$CORE" > /dev/null 2>&1; R="$R core=$?"
    RECEIPTS=$("${D4D[@]}" --manifest data/preprocessed/source_manifest.yaml receipts check --method "$METHOD" --label "$LABEL" \
      --project "$P" --bundle "$BUNDLE" --chunk-manifest "$CHUNKS" --strict 2>&1); R="$R receipts=$?"
    "${D4D[@]}" download scope --manifest data/preprocessed/source_manifest.yaml --project "$P" --check \
      --record "$FULL" --record "$CORE" --strict > /dev/null 2>&1; R="$R scope=$?"
    # `runs check` exits 0 when no run matches its filters (review 1 of PR 6349, F1), so the
    # exit code alone would pass a record it never selected: require that it checked one.
    RUNS=$("${D4D[@]}" runs check --method "$METHOD" --label "$LABEL" --project "$P" --strict 2>&1); RUNS_RC=$?
    if [ $RUNS_RC -eq 0 ] && ! printf '%s\n' "$RUNS" | grep -q "^1 run(s) checked, 1 subject to the requirement, 0 failing"; then RUNS_RC=9; fi
    R="$R runs_check=$RUNS_RC"
    RENDER=$("$PY" -c "import sys; from data_sheets_schema import runs; s = runs.verify_request(sys.argv[1], sys.argv[2], sys.argv[3]); print(s[0]); sys.exit(0 if s[0] == 'match' else 1)" "$METHOD" "$LABEL" "$P" 2>&1 | tail -1); R="$R render=$RENDER"
    COUNTS=$(printf '%s\n' "$RECEIPTS" | grep -o 'chunks [0-9/]* reviewed.*slots [0-9/]* with a receipt' | head -1)
    case "$R" in " full=0 core=0 receipts=0 scope=0 runs_check=0 render=match") VERDICT=ok;; *) VERDICT=FAIL; BAD=$((BAD + 1));; esac
    echo "$VERDICT $P rep$REP:$R | $COUNTS"
  done
done
echo "records checked: $N; failing: $BAD"
[ "$BAD" -eq 0 ]
