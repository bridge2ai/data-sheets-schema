#!/usr/bin/env bash
# Purpose: carry out the A21 CHORUS re-canary launch that the owner delegated
#   to the lead (owner decision D133, 2026-11-12T03:30:53Z: "you should do
#   1-6", answering the lead's six numbered steps whose step 1 names roster
#   d49cc352..., a $60 slice, a $51 stop trigger, no canary baseline and the
#   watcher script as the stop operator).
# Steps:
#   preflight   free checks only: the launch base, the three registration
#               hashes, no sweep or lock, the label unused, free disk, the
#               provider key (presence, validity and remaining budget through
#               the repository's scripts/check_budget.py), the launcher's own
#               dry-run of the exact launch command, and the batch dry-run.
#               Writes <plans>/a21_registration_<label>.prelaunch.log and, on
#               success, .prelaunch.ok.
#   launch      refuses unless preflight passed within the last 15 minutes and
#               the quiet-state checks still hold; then runs EXACTLY the
#               command of the launch packet, section 4 step 2.
#   watcher     starts a21_launch_watch_20261111.sh watch-and-stop in its own
#               session, so that it outlives the lead's shell.
#   state       read-only: process, lock, sweep status, log head and tail.
# Inputs: none besides the step. The slice, trigger and hash are the word's.
# Outputs: the logs named above; the launch log and the run's own files are
#   written by the launcher and the run.
# Serves: the A21 launch packet d4d-executions/plans/a21_launch_packet_2026-11-11.md.
# Date: 2026-11-11 (local), 2026-11-12 UTC
set -u
set -o pipefail

E=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions
LB=$E/launch-a21
PY=$LB/.venv/bin/python
P=2026-11-11a_claude-opus-5-api-bc1-a21
L=${P}_rep1
REG=$E/plans/a21_registration_$L
LOGS=$E/plans/codex_logs
OUT=$E/plans/a21_registration_$L
STATUS_FILE=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md
WATCH=$E/codex-development-efficiency-20261111/scripts/adhoc/a21_launch_watch_20261111.sh
MERGE=7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1
ROSTER_SHA=d49cc3529a11e60716cde4affc6f5deec521b861576fcae6b961e2f74060dd63
REG_SHA=55691023e1d75c3bf5f9df09dcb524b4536870b93a4a3dde67306276f082aa1a
SIZ_SHA=0ae32356404e52d28acf0ff9ae8e39707947664df7506104a52fbab438465c87
SLICE=60.00
AT_CAPS=44.31   # the launch packet's "at caps, ordinary input as cache writes" figure for the nominal plan
KEYINFO=$E/codex-development-efficiency-20261111/scripts/adhoc/a21_prelaunch_key_info_fields_20261111.py
MIN_FREE_KB=$((2 * 1024 * 1024))
LAUNCH_LOG=$LOGS/chorus_a21_${L}.log
FULL_DIR=$LB/data/d4d_concatenated/claudecode_api/$L
CORE_DIR=$LB/data/d4d_concatenated/claudecode_api_core/$L

stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
noenv() { env -u CBORG_API_KEY -u ANTHROPIC_API_KEY -u D4D_MANIFEST PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$LB/src" "$@"; }
sha() { /usr/bin/shasum -a 256 "$1" | /usr/bin/cut -d" " -f1; }

FAILS=0
ok() { echo "  ok    $*"; }
bad() { echo "  FAIL  $*"; FAILS=$((FAILS + 1)); }

quiet_state() {  # everything that must hold immediately before the launch
  local head st status
  head=$(git -C "$LB" rev-parse HEAD)
  [ "$head" = "$MERGE" ] && ok "launch base at $MERGE" || bad "launch base at $head"
  st=$(git -C "$LB" status --porcelain)
  [ "$st" = "?? poetry.toml" ] && ok "launch base status: ?? poetry.toml only" || bad "launch base status: $st"
  [ "$(sha "$REG/roster_${L}.json")" = "$ROSTER_SHA" ] && ok "roster sha256 $ROSTER_SHA" || bad "roster sha256 differs"
  [ "$(sha "$REG/registration_chorus_${L}.json")" = "$REG_SHA" ] && ok "registration sha256 $REG_SHA" || bad "registration sha256 differs"
  [ "$(sha "$REG/registration_chorus_${L}.sizing.json")" = "$SIZ_SHA" ] && ok "sizing sha256 $SIZ_SHA" || bad "sizing sha256 differs"
  status=$( cd "$LB" && noenv "$LB/.venv/bin/d4d" api status 2>&1 )
  printf '%s\n' "$status" | /usr/bin/grep -q "^No sweep is running" && ok "d4d api status: no sweep" || bad "d4d api status: $(printf '%s' "$status" | /usr/bin/head -3 | /usr/bin/tr '\n' ' ')"
  if [ -d "$LB/data/.run_locks" ] && [ -n "$(/bin/ls -A "$LB/data/.run_locks" 2>/dev/null)" ]; then bad "lock directory not empty: $(/bin/ls -A "$LB/data/.run_locks" | /usr/bin/tr '\n' ' ')"; else ok "no run lock"; fi
  [ ! -e "$FULL_DIR" ] && [ ! -e "$CORE_DIR" ] && ok "label unused (no run directories)" || bad "a run directory for the label exists"
  [ ! -e "$LAUNCH_LOG" ] && ok "no launch log yet" || bad "launch log already exists: $LAUNCH_LOG"
  local free
  free=$(/bin/df -k /System/Volumes/Data | /usr/bin/awk 'NR==2{print $4}')
  [ "$free" -ge "$MIN_FREE_KB" ] && ok "free disk $((free / 1024)) MiB (lead's floor 2048 MiB)" || bad "free disk $((free / 1024)) MiB is below the lead's floor of 2048 MiB"
  [ "${#CBORG_API_KEY}" -gt 0 ] 2>/dev/null && ok "CBORG_API_KEY present (length ${#CBORG_API_KEY})" || bad "CBORG_API_KEY is not set in this shell"
  [ -z "${ANTHROPIC_API_KEY:-}" ] && ok "ANTHROPIC_API_KEY not set (the launcher would remove it anyway)" || ok "ANTHROPIC_API_KEY is set; the launcher removes it"
  /usr/bin/grep -q "D133. Launch A21 on the rebuilt registration" "$STATUS_FILE" && ok "the owner's word (D133) is recorded in STATUS" || bad "D133 is not recorded in STATUS"
}

batch_args() {  # the launch packet's arguments after `d4d api batch`, without the final --yes or --dry-run
  printf '%s\n' --projects CHORUS --arm baseline --condition generic_v10 \
    --shared-generation-version 1 --shared-generation-registration "$REG/roster_${L}.json" \
    --expect-sha256 "$ROSTER_SHA" \
    --api-playbook-version 2 --receipt-completion-version 2 \
    --replicates 1 --label-prefix "$P" \
    --max-cost-dollars "$SLICE"
}

case "${1:-}" in
  preflight)
    /bin/rm -f "$OUT.prelaunch.ok"
    {
      echo "# prelaunch $(stamp) roster=$ROSTER_SHA slice=$SLICE"
      echo "## quiet state"; quiet_state
      echo "## provider key: accepted, not blocked, parallel limit, and the budget that applies (read-only)"
      # scripts/check_budget.py divides by the key's max_budget, which is empty
      # for this key (first preflight, 2026-11-12T03:35Z), so the lead's reader
      # is used. The key is charged to no team; the account figures apply.
      kinfo=$( env -u ANTHROPIC_API_KEY PYTHONDONTWRITEBYTECODE=1 "$PY" -I "$KEYINFO" /key/info 2>&1 )
      uinfo=$( env -u ANTHROPIC_API_KEY PYTHONDONTWRITEBYTECODE=1 "$PY" -I "$KEYINFO" /user/info 2>&1 )
      field() { printf '%s\n' "$1" | /usr/bin/awk -v n="  $2:" '$0 ~ "^" n {sub("^" n " *", ""); gsub(/\x27/, ""); print; exit}'; }
      printf '%s\n' "$kinfo" | /usr/bin/grep -q "^HTTP 200 from /key/info" && ok "the provider accepts the key" || bad "the provider did not accept the key: $(printf '%s' "$kinfo" | /usr/bin/head -2 | /usr/bin/tr '\n' ' ')"
      [ "$(field "$kinfo" blocked)" = None ] && ok "key not blocked; expires $(field "$kinfo" expires)" || bad "key blocked field: $(field "$kinfo" blocked)"
      [ "$(field "$kinfo" max_budget)" = None ] && ok "no per-key budget cap" || echo "  note  per-key cap $(field "$kinfo" max_budget), key spend $(field "$kinfo" spend)"
      par=$(field "$kinfo" max_parallel_requests)
      case "$par" in ''|None) ok "no parallel-request limit reported";; *) [ "$par" -ge 4 ] && ok "parallel-request limit $par covers the registered 4 workers" || bad "parallel-request limit $par is below the registered 4 workers";; esac
      umax=$(field "$uinfo" max_budget); uspend=$(field "$uinfo" spend)
      if [ -n "$umax" ] && [ "$umax" != None ] && [ -n "$uspend" ]; then
        rem=$(/usr/bin/awk -v m="$umax" -v s="$uspend" 'BEGIN{printf "%.2f", m - s}')
        echo "  account budget \$$umax per $(field "$uinfo" budget_duration), spent \$$(/usr/bin/awk -v s="$uspend" 'BEGIN{printf "%.2f", s}'), remaining \$$rem, resets $(field "$uinfo" budget_reset_at)"
        /usr/bin/awk -v r="$rem" -v c="$AT_CAPS" 'BEGIN{exit !(r + 0 >= c + 0)}' && ok "remaining account budget covers the plan at its caps (\$$AT_CAPS)" || bad "remaining account budget \$$rem is below the plan at its caps (\$$AT_CAPS)"
        /usr/bin/awk -v r="$rem" -v s="$SLICE" 'BEGIN{exit !(r + 0 >= s + 0)}' || echo "  NOTE  remaining account budget \$$rem is below the \$$SLICE slice: the provider would refuse calls before the slice is reached"
      elif [ "$umax" = None ]; then
        ok "no account-level budget cap reported"
      else
        bad "no account-level budget reading: $(printf '%s' "$uinfo" | /usr/bin/head -2 | /usr/bin/tr '\n' ' ')"
      fi
      echo "## launcher dry-run of the exact launch command (prints the configuration, starts nothing)"
      mapfile_args=(); while IFS= read -r a; do mapfile_args+=("$a"); done < <(batch_args)
      ( cd "$E" && "$PY" "$LB/scripts/api_launcher.py" --worktree "$LB" --dry-run --launch --log "$LAUNCH_LOG" -- d4d api batch "${mapfile_args[@]}" --yes ); rc=$?
      [ "$rc" = 0 ] && ok "launcher dry-run exit 0" || bad "launcher dry-run exit $rc"
      echo "## batch dry-run (--dry-run in place of --yes, foreground; returns before confirm, lock and spend)"
      ( cd "$LB" && "$PY" "$LB/scripts/api_launcher.py" --worktree "$LB" -- d4d api batch "${mapfile_args[@]}" --dry-run ); rc=$?
      [ "$rc" = 0 ] && ok "batch dry-run exit 0" || bad "batch dry-run exit $rc"
      echo "## quiet state again (the dry-runs must have written nothing)"; quiet_state
      echo "# prelaunch finished $(stamp) with $FAILS failure(s)"
      [ "$FAILS" = 0 ] && date +%s > "$OUT.prelaunch.ok"
    } 2>&1 | /usr/bin/tee "$OUT.prelaunch.log"
    [ -f "$OUT.prelaunch.ok" ] || exit 1
    ;;
  launch)
    [ -f "$OUT.prelaunch.ok" ] || { echo "no passed preflight on record"; exit 2; }
    age=$(( $(date +%s) - $(/bin/cat "$OUT.prelaunch.ok") ))
    [ "$age" -le 900 ] || { echo "the passed preflight is ${age}s old (limit 900s); run preflight again"; exit 2; }
    echo "# launch step $(stamp); preflight passed ${age}s ago"
    echo "## quiet state"; quiet_state
    [ "$FAILS" = 0 ] || { echo "quiet state does not hold; nothing launched"; exit 2; }
    mapfile_args=(); while IFS= read -r a; do mapfile_args+=("$a"); done < <(batch_args)
    echo "## launching at $(stamp)"
    "$PY" "$LB/scripts/api_launcher.py" --worktree "$LB" --launch --log "$LAUNCH_LOG" -- d4d api batch "${mapfile_args[@]}" --yes 2>&1 | /usr/bin/tee "$OUT.launch.stdout"
    rc=${PIPESTATUS[0]}
    echo "launcher exit=$rc at $(stamp)" | /usr/bin/tee -a "$OUT.launch.stdout"
    /bin/rm -f "$OUT.prelaunch.ok"   # one launch per passed preflight
    exit "$rc"
    ;;
  watcher)
    [ -f "$LAUNCH_LOG" ] || { echo "no launch log; the watcher is started only after the launch"; exit 2; }
    if [ -f "$LOGS/chorus_a21_${L}.watch.pid" ] && kill -0 "$(/bin/cat "$LOGS/chorus_a21_${L}.watch.pid")" 2>/dev/null; then
      echo "a watcher is already running: pid $(/bin/cat "$LOGS/chorus_a21_${L}.watch.pid")"; exit 0
    fi
    # Its own session, so that the end of the lead's shell does not end it.
    CAP=$SLICE TRIGGER=51 MAX_SECONDS=10800 INTERVAL=30 \
      nohup /usr/bin/perl -MPOSIX=setsid -e 'setsid(); exec @ARGV or die "exec failed: $!"' \
      "$WATCH" watch-and-stop >> "$LOGS/chorus_a21_${L}.watch.stdout" 2>&1 < /dev/null &
    echo $! > "$LOGS/chorus_a21_${L}.watch.pid"
    sleep 3
    wp=$(/bin/cat "$LOGS/chorus_a21_${L}.watch.pid")
    if kill -0 "$wp" 2>/dev/null; then echo "watcher started at $(stamp): pid $wp, session $(/bin/ps -o sess= -p "$wp" | /usr/bin/tr -d ' ')"; else echo "THE WATCHER DID NOT STAY UP"; /usr/bin/tail -5 "$LOGS/chorus_a21_${L}.watch.stdout"; exit 1; fi
    ;;
  state)
    echo "# state $(stamp)"
    ( cd "$LB" && noenv "$LB/.venv/bin/d4d" api status 2>&1 | /usr/bin/cut -c1-300 )
    for f in "$LB"/data/.run_locks/*.json; do [ -f "$f" ] && { echo "lock $f:"; /usr/bin/tr -d '\n' < "$f" | /usr/bin/cut -c1-400; echo; }; done
    [ -f "$LOGS/chorus_a21_${L}.watch.pid" ] && { wp=$(/bin/cat "$LOGS/chorus_a21_${L}.watch.pid"); kill -0 "$wp" 2>/dev/null && echo "watcher pid $wp alive" || echo "watcher pid $wp not running"; }
    [ -f "$LAUNCH_LOG" ] && { echo "launch log: $(/usr/bin/wc -l < "$LAUNCH_LOG" | /usr/bin/tr -d ' ') lines, $(/usr/bin/stat -f %z "$LAUNCH_LOG") bytes"; }
    [ -d "$CORE_DIR" ] && { echo "core directory:"; /bin/ls -la "$CORE_DIR" | /usr/bin/tail -n +2; }
    [ -d "$FULL_DIR" ] && { echo "full directory:"; /bin/ls -la "$FULL_DIR" | /usr/bin/tail -n +2; }
    /bin/df -h /System/Volumes/Data | /usr/bin/awk 'NR==2{print "free disk " $4}'
    ;;
  wait)
    # Read-only: returns when the watcher has exited or after <seconds>, so
    # that the lead's session is woken. It does not stop or restart anything.
    MAXW=${2:-1500}
    wp=$(/bin/cat "$LOGS/chorus_a21_${L}.watch.pid" 2>/dev/null || echo 0)
    t0=$(date +%s)
    while kill -0 "$wp" 2>/dev/null && [ $(( $(date +%s) - t0 )) -lt "$MAXW" ]; do sleep 15; done
    if kill -0 "$wp" 2>/dev/null; then echo "# $(stamp): the watcher (pid $wp) is still running after ${MAXW}s"; else echo "# $(stamp): THE WATCHER (pid $wp) HAS EXITED"; fi
    echo "## watch log, last lines"; /usr/bin/tail -6 "$LOGS/chorus_a21_${L}.watch.log" 2>/dev/null | /usr/bin/cut -c1-330
    echo "## launch log, last lines"; /usr/bin/tail -8 "$LAUNCH_LOG" | /usr/bin/cut -c1-330
    "$0" state
    ;;
  *)
    echo "usage: $0 preflight|launch|watcher|state|wait [seconds]" >&2; exit 2
    ;;
esac
