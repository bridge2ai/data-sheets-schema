#!/bin/bash
# run_release_series_stream_20261125.sh
# Purpose: run one replicate stream of a release series, one project at a time, through the
#   reviewed driver (scripts/adhoc/run_release_series_20261124.sh in the launch worktree),
#   with three rules the driver does not have because they span streams:
#     - a stop file, checked before every project, ends the stream cleanly;
#     - a budget check before every project (release_series_budget_20261125.py) creates
#       that stop file when the series' estimated share of the account's weekly Fable
#       allowance would pass the limit, so no stream starts another project;
#     - a run that never got a model turn because the provider was overloaded (HTTP 529,
#       nothing written) is retried under the same label after its attempt files are moved
#       out as evidence, at most MAX_OVERLOAD_TRIES times, ten minutes apart. Any other
#       failure stops the stream; the driver already stops on a gate failure.
#   No model call of its own. The series, model, effort and account are arguments or
#   environment, as for the driver.
# Inputs:  <launch worktree> <series> <model> <effort> <replicate number> <state dir> <project> ...
#   Environment: D4D_SERIES_CONFIG_DIR, D4D_SERIES_OAUTH_TOKEN and D4D_SERIES_DEFAULT_LOGIN (read by the driver), D4D_SERIES_TREES (the
#   launch worktrees of all streams, colon-separated, for the budget check), and the budget
#   check's calibration: D4D_BUDGET_BASE_PERCENT and D4D_BUDGET_POINTS_PER_USD (both
#   required) and D4D_BUDGET_ALREADY_COUNTED (optional); see release_series_budget_20261125.py.
#   Without the two required values, or with a value that is not valid, the first budget
#   check answers stop: this script then
#   writes the stop file, every stream ends at its next check, and the exit status is 0.
#   Series 2026-11-25c ran before the calibration moved out of the budget script.
# Outputs: the driver's outputs in the worktree; <state dir>/stream_rep<N>.state and .log;
#   overload evidence under <state dir>/overload-attempts/.
# Serves:  the release-series rerun 2026-11-25c (PR 6325, issues 6324, 6312). Date: 2026-11-25.
set -u
W=${1:?launch worktree}; SERIES=${2:?series}; MODEL=${3:?model}; EFFORT=${4:?effort}; REP=${5:?replicate}; STATE=${6:?state dir}; shift 6
[ $# -ge 1 ] || { echo "no projects given" >&2; exit 2; }
HERE=$(cd "$(dirname "$0")" && pwd -P); [ -f "$W/scripts/adhoc/run_release_series_20261124.sh" ] || { echo "STOP: the launch worktree holds no driver (scripts/adhoc/run_release_series_20261124.sh)" >&2; exit 2; }; grep -q '^\[ -n "$ACCOUNT_DIR$ACCOUNT_TOKEN" \] || \[ "${D4D_SERIES_DEFAULT_LOGIN:-}" = 1 \] || ' "$W/scripts/adhoc/run_release_series_20261124.sh" || { echo "STOP: the driver in the launch worktree does not have the account check this runner relies on (it predates 2026-11-27)" >&2; exit 2; }
CONDITION=${D4D_SERIES_CONDITION:-generic_v9}
METHOD=${D4D_SERIES_METHOD:-claudecode_release}
LABEL="${SERIES}_${MODEL}-claudecode-${CONDITION//_/-}_rep${REP}"
MAX_OVERLOAD_TRIES=4
mkdir -p "$STATE" || exit 2
STOP="$STATE/STOP"
MINE="$STATE/stream_rep$REP.state"
say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) stream rep$REP $*"; }
# True when the transcript ends in a 529 result and holds no message from the model itself.
overloaded_before_any_turn() {
  /usr/bin/python3 - "$1" "$MODEL" <<'PYCHECK'
import json, sys
status, turns = None, 0
for line in open(sys.argv[1], encoding="utf-8"):
    try:
        event = json.loads(line)
    except ValueError:
        continue
    if not isinstance(event, dict):
        continue
    if event.get("type") == "assistant" and (event.get("message") or {}).get("model") == sys.argv[2]:
        turns += 1
    if event.get("type") == "result":
        status = event.get("api_error_status")
sys.exit(0 if status == 529 and turns == 0 else 1)
PYCHECK
}
IFS=: read -r -a TREES <<< "${D4D_SERIES_TREES:-$W}"
echo idle > "$MINE"

for P in "$@"; do
  if [ -e "$STOP" ]; then say "STOP file present ($(head -c 200 "$STOP")); not starting $P"; echo idle > "$MINE"; exit 0; fi
  FULL="$W/data/d4d_concatenated/$METHOD/$LABEL/${P}_d4d.yaml"
  GATE="$W/.temp/launch/gates/${P}_${LABEL}.txt"
  if [ -s "$FULL" ] && [ -e "$GATE" ] && grep -q "^GATES: PASS" "$GATE"; then say "$P already passed; skipping"; continue; fi
  BUDGET=$(/usr/bin/python3 "$HERE/release_series_budget_20261125.py" --series "$SERIES" --model "$MODEL" \
             --condition "$CONDITION" --state-dir "$STATE" --next "$P" --rep "$REP" "${TREES[@]}"); BRC=$?
  say "budget: $BUDGET"
  if [ $BRC -ne 0 ]; then
    echo "budget check before $P of rep$REP: $BUDGET" > "$STOP"
    say "budget stop written; not starting $P"; echo idle > "$MINE"; exit 0
  fi
  TRY=1
  while :; do
    echo "running $P" > "$MINE"
    say "$P attempt $TRY"
    bash "$W/scripts/adhoc/run_release_series_20261124.sh" "$W" "$SERIES" "$MODEL" "$EFFORT" "$REP" "$P"; RC=$?
    echo idle > "$MINE"
    [ $RC -eq 0 ] && break
    STREAM="$W/.temp/launch/transcripts/$LABEL/${P}.stream.jsonl"
    # Overloaded before any model turn: a 529 result, no message from the model, nothing written.
    if [ -e "$STREAM" ] && overloaded_before_any_turn "$STREAM" \
       && [ ! -e "$FULL" ] && [ ! -e "$W/data/d4d_concatenated/${METHOD}_core/$LABEL/${P}_d4d_core.yaml" ] \
       && [ $TRY -lt $MAX_OVERLOAD_TRIES ]; then
      KEEP="$STATE/overload-attempts/rep$REP/${P}-attempt$TRY"
      mkdir -p "$KEEP"
      mv "$W/.temp/launch/${P}_${LABEL}".* "$GATE" "$W/.temp/launch/transcripts/$LABEL/${P}".* "$KEEP"/ 2>/dev/null
      if [ -e "$STREAM" ] || [ -e "$GATE" ]; then say "$P: could not move the overloaded attempt's files; stopping"; exit 3; fi
      say "$P: provider overloaded (529) before any model turn; attempt files kept in $KEEP; retrying in 10 minutes"
      TRY=$((TRY + 1)); sleep 600
      if [ -e "$STOP" ]; then say "STOP file present; not retrying $P"; exit 0; fi
      continue
    fi
    say "$P: driver exit $RC; stream stops here (see $GATE)"
    exit 3
  done
done
say "ALL PROJECTS OF THIS STREAM FINISHED"
