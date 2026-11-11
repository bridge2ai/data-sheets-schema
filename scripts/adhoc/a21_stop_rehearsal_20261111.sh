#!/usr/bin/env bash
# Purpose: rehearse, offline and away from the launch base, the two ways the
#   A21 stop rule can fire, using the launch packet's own stop command:
#     A. the dollar trigger (readout exit 1), and
#     B. the wall clock,
#   and C. the packet's stop command through the launcher in the real launch
#   base while nothing is running (a no-op that proves the launcher admits it),
#   each against a stand-in process that holds a real sweep lock
#   (a21_stop_rehearsal_fake_sweep_20261111.py). No provider call is made and
#   nothing is written in launch-a21.
# What is the same as launch day: the watcher script, the readout script, the
#   launcher and its `-- d4d api stop --label-prefix <prefix>` command line,
#   the run-lock code, the interpreter and packages (launch-a21's .venv), and
#   the source commit (a sparse checkout of the same commit).
# What differs: the checkout path (so the launcher is given --venv), the
#   label prefix, the ledger (a copy of the archived 10-22a run's, with the
#   trigger lowered so that it fires), and the process being stopped (it
#   sleeps; it is not a generation run in the middle of a provider call).
# Inputs: none. Outputs: the rehearsal checkout
#   d4d-executions/claude-a21-stop-rehearsal-20261111 (src and scripts only)
#   and, inside it, rehearsal-logs/ with the watcher logs and result.txt.
# Serves: the A21 launch packet of 2026-11-11 (owner decision D131).
# Date: 2026-11-11
set -u
set -o pipefail

EXEC=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions
PRIMARY=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema
REAL_LB=$EXEC/launch-a21
VENV=$REAL_LB/.venv
MERGE=7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1
WT=$EXEC/claude-a21-stop-rehearsal-20261111
ADHOC=$EXEC/codex-development-efficiency-20261111/scripts/adhoc
WATCH=$ADHOC/a21_launch_watch_20261111.sh
FAKE=$ADHOC/a21_stop_rehearsal_fake_sweep_20261111.py
ARCHIVED=$REAL_LB/data/ATTIC/d4d_concatenated_archived/claudecode_api_core/2026-10-22a_claude-opus-5-api-generic-v10_rep1
LOGS=$WT/rehearsal-logs
RESULT=$LOGS/result.txt

stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
say() { echo "[$(stamp)] $*" | tee -a "$RESULT"; }

[ "$(git -C "$REAL_LB" rev-parse HEAD)" = "$MERGE" ] || { echo "launch base is not at the merge commit"; exit 2; }
before_lb=$(git -C "$REAL_LB" status --porcelain; ls -la "$REAL_LB/data/.run_locks" 2>&1 | tail -1)

if [ ! -d "$WT" ]; then
  git -C "$PRIMARY" worktree add --detach --no-checkout "$WT" "$MERGE" || exit 2
  git -C "$WT" sparse-checkout set --cone src scripts || exit 2
  git -C "$WT" checkout --detach "$MERGE" || exit 2
fi
[ "$(git -C "$WT" rev-parse HEAD)" = "$MERGE" ] || { echo "rehearsal checkout is not at the merge commit"; exit 2; }
mkdir -p "$LOGS"
say "rehearsal checkout $WT at $(git -C "$WT" rev-parse HEAD | cut -c1-12); interpreter $VENV/bin/python"

FAKE_PID=
fake_sweep() {  # $1 prefix; sets FAKE_PID. Not run in a command substitution:
  # a backgrounded child would hold the substitution's pipe open until it exits.
  cd "$WT" || return 1
  env -u CBORG_API_KEY -u ANTHROPIC_API_KEY PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$WT/src" \
    nohup "$VENV/bin/python" -B "$FAKE" "$1" 300 >> "$LOGS/fake-sweep-$1.log" 2>&1 < /dev/null &
  FAKE_PID=$!
  cd "$EXEC" || return 1
}

case_run() {  # $1 name, $2 prefix, $3 trigger, $4 clock seconds, $5 expected watcher exit
  local name=$1 prefix=$2 trigger=$3 clock=$4 expected=$5
  local label=${prefix}_rep1
  local core=$WT/data/d4d_concatenated/claudecode_api_core/$label
  say "== case $name: prefix $prefix, trigger $trigger, clock ${clock}s, expected watcher exit $expected"
  mkdir -p "$core"
  cp "$ARCHIVED"/CHORUS_api_usage_*.json "$core/" || return 1
  fake_sweep "$prefix" || return 1
  local pid=$FAKE_PID
  local lock=$WT/data/.run_locks/$prefix.json n=0
  until [ -s "$lock" ] || [ $n -ge 40 ]; do sleep 0.5; n=$((n+1)); done
  [ -s "$lock" ] || { say "FAIL: the stand-in never wrote its lock"; return 1; }
  say "stand-in pid $pid; lock: $(tr -d '\n' < "$lock" | cut -c1-200)"
  : > "$LOGS/chorus_a21_${label}.log"; echo "# rehearsal launch log $(stamp)" >> "$LOGS/chorus_a21_${label}.log"
  A21_LB=$WT A21_VENV=$VENV A21_PREFIX=$prefix A21_LOGS=$LOGS A21_STOP_DIRECT=1 \
    CAP=60.00 TRIGGER=$trigger MAX_SECONDS=$clock INTERVAL=5 WAIT_START=30 \
    "$WATCH" watch-and-stop > "$LOGS/watch-$name.stdout" 2>&1
  local rc=$?
  sed 's/^/    /' "$LOGS/watch-$name.stdout" | cut -c1-260 | tee -a "$RESULT"
  sleep 1
  local alive=no; kill -0 "$pid" 2>/dev/null && alive=yes
  say "watcher exit $rc (expected $expected); stand-in still alive: $alive; lock file present: $([ -e "$lock" ] && echo yes || echo no)"
  if [ "$alive" = yes ]; then kill "$pid" 2>/dev/null; say "FAIL: the stand-in survived the stop command (killed now)"; return 1; fi
  [ "$rc" = "$expected" ] || { say "FAIL: unexpected watcher exit"; return 1; }
  say "PASS: case $name"
}

fails=0
# Suffix r2: the first attempt's locks and logs are kept as they are.
case_run trigger rehearsal-20261111-trigger-r2 10 600 21 || fails=$((fails+1))
case_run clock rehearsal-20261111-clock-r2 51 12 22 || fails=$((fails+1))

# The launch packet's exact stop command, through the launcher, in the real
# launch base, while no sweep is running: it sends no signal and writes
# nothing, and shows that the launcher admits the command there.
say "== case launcher: the packet's stop command in the launch base with no sweep running"
out=$( cd "$REAL_LB" && "$VENV/bin/python" "$REAL_LB/scripts/api_launcher.py" --worktree "$REAL_LB" -- d4d api stop --label-prefix 2026-11-11a_claude-opus-5-api-bc1-a21 2>&1 ); rc=$?
printf '%s\n' "$out" | sed 's/^/    /' | cut -c1-220 | tee -a "$RESULT"
if [ "$rc" = 0 ] && printf '%s' "$out" | grep -q "No running sweep holds"; then say "PASS: case launcher (exit 0, no signal sent)"; else say "FAIL: case launcher (exit $rc)"; fails=$((fails+1)); fi

after_lb=$(git -C "$REAL_LB" status --porcelain; ls -la "$REAL_LB/data/.run_locks" 2>&1 | tail -1)
[ "$before_lb" = "$after_lb" ] && say "launch base status and lock directory unchanged" || { say "FAIL: launch base changed: $after_lb"; fails=$((fails+1)); }
say "rehearsal finished with $fails failure(s)"
exit "$fails"
