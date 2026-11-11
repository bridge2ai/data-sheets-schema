#!/usr/bin/env bash
# Purpose: monitor the A21 CHORUS re-canary once the OWNER has launched it, and
#   say when the stop rule is met. It never launches anything.
#   The stop rule (owner decisions D58, D64 items 6 and 7, D88's figures): stop
#   when settled cost plus the pending call's worst case reaches the trigger,
#   or 3 hours after launch.
# Modes:
#   once             one reading, then exit (read-only)
#   watch            (default) read-only; exits when the run ends or the stop
#                    rule is met, so that whoever started it is told
#   watch-and-stop   as watch, and at the stop rule runs exactly
#                    `d4d api stop --label-prefix <prefix>` through the launcher.
#                    Use only if the owner's launch word names this script as
#                    the stop operator (D64 item 7 names agy).
# Inputs (environment, with defaults): CAP=60.00 TRIGGER=51 MAX_SECONDS=10800
#   INTERVAL=30 WAIT_START=7200. METADATA_DIR overrides the run's core
#   directory (used to test `once` against an archived run).
# Outputs: lines on stdout, also appended to
#   plans/codex_logs/chorus_a21_<label>.watch.log. Reads the launch log, the
#   usage ledger, the latch journal and `d4d api status`. Writes nothing else.
# Exit: 0 run ended (no sweep running, ledger present); 11 trigger or cap
#   reached; 12 the 3-hour clock; 13 the launch never appeared;
#   21/22 as 11/12 after the stop command was run (watch-and-stop).
# Serves: owner decision D131 (2026-11-11); the A21 launch packet.
# Date: 2026-11-11
set -u
set -o pipefail

EXEC=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions
LB=$EXEC/launch-a21
PY=$LB/.venv/bin/python
P=2026-11-11a_claude-opus-5-api-bc1-a21
L=${P}_rep1
CORE=${METADATA_DIR:-$LB/data/d4d_concatenated/claudecode_api_core/$L}
LAUNCH_LOG=$EXEC/plans/codex_logs/chorus_a21_${L}.log
WATCH_LOG=$EXEC/plans/codex_logs/chorus_a21_${L}.watch.log
CAP=${CAP:-60.00}; TRIGGER=${TRIGGER:-51}; MAX_SECONDS=${MAX_SECONDS:-10800}
INTERVAL=${INTERVAL:-30}; WAIT_START=${WAIT_START:-7200}
MODE=${1:-watch}
case "$MODE" in once|watch|watch-and-stop) ;; *) echo "usage: $0 [once|watch|watch-and-stop]" >&2; exit 2;; esac

stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
say() { if [ "$MODE" = once ]; then echo "[$(stamp)] $*"; else echo "[$(stamp)] $*" | tee -a "$WATCH_LOG"; fi; }
noenv() { env -u CBORG_API_KEY -u ANTHROPIC_API_KEY -u D4D_MANIFEST "$@"; }

sweep_running() {  # read-only; true when `d4d api status` reports a sweep
  local out; out=$( cd "$LB" && noenv "$LB/.venv/bin/d4d" api status 2>&1 )
  ! printf '%s' "$out" | /usr/bin/grep -q "No sweep is running"
}

READING=""; RC=0
reading() {  # sets READING (one line) and RC (0 ok, 1 trigger, 2 cap, 9 no ledger yet)
  if [ ! -d "$CORE" ] || ! /bin/ls "$CORE"/CHORUS_api_usage_*.json >/dev/null 2>&1; then
    READING="no usage ledger yet under $CORE"; RC=9; return
  fi
  local json
  json=$( cd "$LB" && noenv "$PY" "$LB/scripts/api_dollar_readout.py" --metadata-dir "$CORE" \
            --project CHORUS --cap "$CAP" --trigger "$TRIGGER" --json 2>&1 ); RC=$?
  READING=$( printf '%s' "$json" | "$PY" -I -S -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception as exc:
    print("readout not parsed: " + type(exc).__name__); raise SystemExit
p = d.get("pending_call") or {}
print("settled calls %s $%.2f | pending %s | settled plus pending worst case $%.2f | trigger %s cap %s | label %s" % (
    d.get("settled_calls"), d.get("settled_dollars") or 0.0, p.get("phase") or "none",
    d.get("total_projected_dollars") or 0.0, d.get("trigger_reached"), d.get("cap_reached"),
    (d.get("identity") or {}).get("label")))' )
}

journal_head() {
  local j="$CORE/CHORUS_latch_journal.jsonl"
  if [ -f "$j" ]; then echo "journal $(/usr/bin/shasum -a 256 "$j" | /usr/bin/cut -d" " -f1) lines $(/usr/bin/wc -l < "$j" | /usr/bin/tr -d " ")"; else echo "journal not present"; fi
}

if [ "$MODE" = once ]; then
  reading; say "$READING (readout exit $RC); $(journal_head)"
  if sweep_running; then say "a sweep is running"; else say "no sweep is running"; fi
  exit 0
fi

say "watching label $L; cap $CAP, trigger $TRIGGER, clock ${MAX_SECONDS}s, mode $MODE"
waited=0
while [ ! -f "$LAUNCH_LOG" ]; do
  [ "$waited" -lt "$WAIT_START" ] || { say "launch log never appeared: $LAUNCH_LOG"; exit 13; }
  sleep 10; waited=$((waited + 10))
done
START=$(/usr/bin/stat -f %B "$LAUNCH_LOG")
say "launch log present (created $(date -u -r "$START" +%Y-%m-%dT%H:%M:%SZ)); first lines:"
/usr/bin/head -5 "$LAUNCH_LOG" | /usr/bin/cut -c1-400 | tee -a "$WATCH_LOG"

stop_now() {  # $1 reason code (11 or 12), $2 text
  say "STOP RULE MET: $2; $(journal_head)"
  if [ "$MODE" = watch-and-stop ]; then
    say "running the stop command"
    ( cd "$LB" && "$PY" "$LB/scripts/api_launcher.py" --worktree "$LB" -- d4d api stop --label-prefix "$P" ) 2>&1 | tee -a "$WATCH_LOG"
    sleep 5
    if sweep_running; then say "A SWEEP IS STILL RUNNING AFTER THE STOP COMMAND"; else say "no sweep is running after the stop command"; fi
    say "$(journal_head)"
    exit $(( $1 + 10 ))
  fi
  say "read-only mode: the stop command was NOT run. It is: $PY $LB/scripts/api_launcher.py --worktree $LB -- d4d api stop --label-prefix $P"
  exit "$1"
}

seen_running=0
while :; do
  elapsed=$(( $(date +%s) - START ))
  reading
  if sweep_running; then running=1; seen_running=1; else running=0; fi
  say "elapsed ${elapsed}s | sweep running: $running | $READING"
  if [ "$RC" = 1 ] || [ "$RC" = 2 ]; then stop_now 11 "settled plus pending worst case reached the trigger or cap (readout exit $RC)"; fi
  if [ "$running" = 1 ] && [ "$elapsed" -ge "$MAX_SECONDS" ]; then stop_now 12 "the ${MAX_SECONDS}s clock"; fi
  if [ "$running" = 0 ] && { [ "$seen_running" = 1 ] || [ "$elapsed" -ge 120 ]; }; then
    say "run ended: no sweep is running; $(journal_head)"; /usr/bin/tail -5 "$LAUNCH_LOG" | /usr/bin/cut -c1-400 | tee -a "$WATCH_LOG"; exit 0
  fi
  sleep "$INTERVAL"
done
