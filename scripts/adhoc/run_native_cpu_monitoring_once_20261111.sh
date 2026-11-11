#!/usr/bin/env bash
# Purpose: run the ONE native `cpu-monitoring` diagnostic the owner approved
#   (D132, 2026-11-11T16:11:12Z; AGY4's proposal in
#   handoffs/agy4-cpu-diagnostic.md section 7) on the existing S382f contract,
#   and nothing else. Synthetic fixture, network-denied sandbox, no provider
#   or model call. It is an unqualified contended CPU diagnostic.
# Sequence:
#   1. verify identities (tool, contract, frozen source, no lock, fresh names);
#   2. wait for a low-load window (nothing is armed while waiting);
#   3. arm the private scratch config (one git config key), with a trap that
#      restores it on every exit path;
#   4. run the tool's own 20-second `canary` kind through this same shell,
#      interpreter and sandbox path (canary first; refuses to go on unless it
#      is a certified pass);
#   5. re-check the load gate from the approved proposal (1-minute load per
#      CPU below 2.5), write the once-claim, run `cpu-monitoring` once;
#   6. restore the config and print what is on disk.
#   The diagnostic is never retried: a claim file blocks a second start.
# Inputs: none on the command line. Optional environment overrides:
#   PREFER (default 1.5) and PREFER_WAIT seconds (default 1200), then
#   ACCEPT (default 2.0) and ACCEPT_WAIT seconds (default 1200); HARD is the
#   proposal's 2.5 and is not overridable.
# Outputs (all new names under scratch-native-u1u3/u3m/):
#   wp1-382f0dfd1ce8-canary-lead-rerun-20261111{,.outer.json,.outer.log,.supervisor.json}
#   wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111{,...}
#   lead-cpu-monitoring-rerun-382f0dfd1ce8.once.json
#   lead-cpu-monitoring-rerun-382f0dfd1ce8-20261111.log
#   lead-config-rearm-382f0dfd1ce8-20261111/{armed,restored}.json
# Exit: 0 diagnostic certified; 10 diagnostic ran but was not certified;
#   3 canary not certified; 75 no load window (nothing armed or run);
#   76 load rose above the hard gate after the canary (diagnostic not started);
#   2 a precondition failed.
# Serves: owner decision D132; native track, not the API route.
# Date: 2026-11-11
set -u
set -o pipefail

EXEC=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions
ROOT=$EXEC/codex-native-u1u3
SCRATCH=$EXEC/scratch-native-u1u3/u3m
VPY=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python
TOOL=$ROOT/scripts/adhoc/native_wp1_validation_20261110.py
TOOL_SHA=a995dba963a2a83d183dbb3fd523462d1fdd51b5a7132be7841c4b90557c0c6e
CONTRACT=$SCRATCH/wp1-contract-382f0dfd1ce8.json
CONTRACT_SHA=df9eb421572b3a9ca578adfe1664cd23b372c61f315d6c191d3eba4e57eeda4e
SOURCE=382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b
CFG=$EXEC/codex-development-efficiency-20261111/scripts/adhoc/native_private_config_rearm_restore_20261111.py
LABEL=lead-rerun-20261111
CANARY_OUT=$SCRATCH/wp1-382f0dfd1ce8-canary-$LABEL
RUN_OUT=$SCRATCH/wp1-382f0dfd1ce8-cpu-monitoring-$LABEL
CLAIM=$SCRATCH/lead-cpu-monitoring-rerun-382f0dfd1ce8.once.json
LOG=$SCRATCH/lead-cpu-monitoring-rerun-382f0dfd1ce8-20261111.log
QUIET_LOCK=$EXEC/plans/native_quiet_window.lock
PREFER=${PREFER:-1.5}; PREFER_WAIT=${PREFER_WAIT:-1200}
ACCEPT=${ACCEPT:-2.0}; ACCEPT_WAIT=${ACCEPT_WAIT:-1200}
HARD=2.5
NCPU=$(/usr/sbin/sysctl -n hw.logicalcpu)

stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
say() { echo "[$(stamp)] $*" | tee -a "$LOG"; }
load1() { /usr/sbin/sysctl -n vm.loadavg | /usr/bin/awk '{print $2}'; }
below() { /usr/bin/awk -v l="$(load1)" -v n="$NCPU" -v t="$1" 'BEGIN{exit !(l/n < t)}'; }
loads() { /usr/sbin/sysctl -n vm.loadavg; }

fail() { say "PRECONDITION FAILED: $*"; exit 2; }

# The tool is run with an empty environment apart from these three values, so
# no credential in the caller's shell reaches the process tree.
tool() {
  ( cd "$ROOT" && /usr/bin/env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin LANG=en_US.UTF-8 \
      U3WP1_MANIFEST="$CONTRACT" "$VPY" -S -P -B "$TOOL" "$@" )
}

certified() {  # $1 = output directory; prints a one-line summary; exit 0 only for a certified pass
  "$VPY" -I -S -c '
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
sup, outer = out.with_suffix(".supervisor.json"), out.with_suffix(".outer.json")
if not sup.is_file():
    print("no supervisor record"); raise SystemExit(1)
s = json.loads(sup.read_bytes())
o = json.loads(outer.read_bytes()) if outer.is_file() else {}
print(json.dumps(dict(kind=s.get("kind"), returncode=s.get("returncode"),
    cleanup_verified=s.get("cleanup_verified"), forced_cleanup=s.get("forced_cleanup"),
    interrupted=s.get("interrupted"), errors=s.get("errors"),
    seconds=s.get("seconds"), inner_returncode=o.get("returncode"),
    inner_seconds=o.get("seconds"), survivors=o.get("observed_surviving_pids"))))
ok = (s.get("returncode") == 0 and s.get("cleanup_verified") is True
      and s.get("forced_cleanup") is False and o.get("returncode") == 0)
raise SystemExit(0 if ok else 1)' "$1"
}

: >> "$LOG" || { echo "cannot write $LOG"; exit 2; }
say "start; logical CPUs $NCPU; load $(loads); thresholds prefer<$PREFER accept<$ACCEPT hard<$HARD"

# 1. identities and fresh names
[ "$(/usr/bin/shasum -a 256 "$TOOL" | /usr/bin/cut -d' ' -f1)" = "$TOOL_SHA" ] || fail "tool bytes differ"
[ "$(/usr/bin/shasum -a 256 "$CONTRACT" | /usr/bin/cut -d' ' -f1)" = "$CONTRACT_SHA" ] || fail "contract bytes differ"
[ "$(/usr/bin/git -C "$ROOT" rev-parse HEAD)" = "$SOURCE" ] || fail "frozen source is not at $SOURCE"
[ -z "$(/usr/bin/git -C "$ROOT" status --porcelain --untracked-files=normal)" ] || fail "frozen source is not clean"
[ ! -e "$QUIET_LOCK" ] || fail "quiet-window lock exists"
[ ! -e "$CLAIM" ] || fail "the diagnostic was already started once ($CLAIM); it is not retried"
for p in "$RUN_OUT" "$RUN_OUT.outer.json" "$RUN_OUT.outer.log" "$RUN_OUT.supervisor.json" "$RUN_OUT.qualification"; do
  [ ! -e "$p" ] || fail "output name is taken: $p"
done
"$VPY" -I "$CFG" status | tee -a "$LOG"
[ "$("$VPY" -I "$CFG" status | "$VPY" -I -S -c 'import json,sys; print(json.load(sys.stdin)["state"])')" = "original" ] \
  || fail "private config is not in its original state"

# 2. wait for a window; two consecutive samples 20 s apart must be below the threshold
wait_window() {  # $1 threshold, $2 seconds
  local deadline=$(( $(date +%s) + $2 ))
  while [ "$(date +%s)" -lt "$deadline" ]; do
    if below "$1"; then sleep 20; if below "$1"; then return 0; fi; fi
    sleep 20
  done
  return 1
}
if wait_window "$PREFER" "$PREFER_WAIT"; then
  say "window: 1-minute load per CPU below $PREFER; load $(loads)"
elif wait_window "$ACCEPT" "$ACCEPT_WAIT"; then
  say "window: 1-minute load per CPU below $ACCEPT (preferred $PREFER not reached); load $(loads)"
else
  say "NO WINDOW within $((PREFER_WAIT + ACCEPT_WAIT)) s; load $(loads); nothing armed, nothing run"
  exit 75
fi

# 3. arm, with restoration on every exit path
restore() { say "restoring private config"; "$VPY" -I "$CFG" restore 2>&1 | tee -a "$LOG"; }
trap restore EXIT
trap 'say "signal received"; exit 130' INT TERM
"$VPY" -I "$CFG" arm 2>&1 | tee -a "$LOG"
[ "$("$VPY" -I "$CFG" status | "$VPY" -I -S -c 'import json,sys; print(json.load(sys.stdin)["state"])')" = "armed" ] \
  || { say "arming failed"; exit 2; }

# 4. canary through this same path (reused if this script's canary already passed)
if [ -e "$CANARY_OUT" ] || [ -e "$CANARY_OUT.supervisor.json" ]; then
  say "canary evidence already present; checking it"
else
  say "canary start; load $(loads)"
  tool canary --label "$LABEL" 2>&1 | tee -a "$LOG"
  say "canary tool exit ${PIPESTATUS[0]}"
fi
if certified "$CANARY_OUT" | tee -a "$LOG"; then say "canary certified"; else say "CANARY NOT CERTIFIED; diagnostic not started"; exit 3; fi

# 5. hard gate, once-claim, the one diagnostic
if ! below "$HARD"; then
  say "load per CPU is at or above $HARD after the canary; waiting up to 300 s; load $(loads)"
  wait_window "$HARD" 300 || { say "HARD GATE NOT MET; diagnostic not started; load $(loads)"; exit 76; }
fi
( set -o noclobber; printf '{"started_utc": "%s", "output": "%s", "contract_sha256": "%s", "source_commit": "%s", "authority": "owner decision D132"}\n' \
    "$(stamp)" "$RUN_OUT" "$CONTRACT_SHA" "$SOURCE" > "$CLAIM" ) || { say "could not write the once-claim"; exit 2; }
say "diagnostic start; load $(loads); top CPU:"
/bin/ps -Ao pcpu,pid,comm -r | /usr/bin/head -8 | tee -a "$LOG"
tool cpu-monitoring --label "$LABEL" --canary-out "$CANARY_OUT" 2>&1 | tee -a "$LOG"
RC=${PIPESTATUS[0]}
say "diagnostic tool exit $RC; load $(loads)"

# 6. restore now (the trap then finds it already original), and report
trap - EXIT
restore
say "evidence on disk:"
/bin/ls -la "$RUN_OUT" "$RUN_OUT/phase-metrics" 2>&1 | tee -a "$LOG"
if certified "$RUN_OUT" | tee -a "$LOG"; then say "DIAGNOSTIC CERTIFIED"; exit 0; fi
say "DIAGNOSTIC NOT CERTIFIED (see records); not retried"
exit 10
