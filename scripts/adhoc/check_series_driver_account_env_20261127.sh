#!/bin/bash
# check_series_driver_account_env_20261127.sh
# Purpose: since 2026-11-27 the three launch drivers (run_agentic_fanout_20261122.sh,
#   run_rubric_eval_20261122.sh, run_release_series_20261124.sh) take the configuration
#   directory and the login token of the account from the caller's environment
#   (D4D_SERIES_CONFIG_DIR, D4D_SERIES_OAUTH_TOKEN) and no longer choose an account in their
#   own text. This check runs, for each driver, only the lines that build a session's
#   environment and start it, with a stub in place of `claude` that prints its environment
#   and its arguments. It does three things:
#     1. built in, no input needed: given the two variables, the session gets them under
#        Claude Code's own names and nothing named D4D_SERIES_*; given neither, it gets
#        neither, whatever the caller's shell had exported;
#     2. built in: the release-series driver stops (exit 2) when the retired variable
#        D4D_SERIES_ACCOUNT is set, and when D4D_SERIES_CONFIG_DIR is relative or not a
#        directory;
#     3. with a reference and a cases file: the lines as they were at that reference and
#        the lines of this checkout give the stub the same environment and arguments.
# Inputs:  [<git ref of the drivers before the edit> <cases file>]
#   The cases file has one case per line, tab-separated:
#     <fanout|rubric|release> <caller's variables for the old lines> <the same for the new lines> <folders to create under the stub home, or ->
#   Variables are space-separated NAME=VALUE, or - for none; @HOME@ in a value is the stub
#   home. A case
#   names variables of the caller's own shell, so the file is kept outside the repository,
#   and this script prints the number and the driver of a case, never its text.
# Outputs: one line per check on stdout, ending "ALL SAME" or "FAILED"; exit 1 on a failure,
#   2 when the drivers do not have the expected lines at the expected places.
#   Everything is written under a temporary directory, which is removed. No model call.
# What it does not show: that a real session logs in with what it is given. A canary does.
# Serves: issue 6433 (review 1 of PR 6431, findings F1 and F2). Date: 2026-11-27.
set -u
HERE=$(cd "$(dirname "$0")" && pwd -P)
ROOT=$(cd "$HERE/../.." && pwd -P)
REF=${1:-}; CASES=${2:-}
T=$(mktemp -d) || exit 2
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin" "$T/home" "$T/tmp" "$T/old" "$T/new"
printf '%s\n' '#!/bin/bash' 'env | LC_ALL=C sort | grep -v "^_="' 'printf "ARG %s\n" "$@"' > "$T/bin/claude"
chmod +x "$T/bin/claude"
FAILED=0

# driver -> file, the line ranges that are run, and what the first and last line must hold
spec() {
  case "$1" in
    fanout)  FILE=scripts/adhoc/run_agentic_fanout_20261122.sh;  RANGES="75,82";         FIRST='  (';             LAST='  )' ;;
    rubric)  FILE=scripts/adhoc/run_rubric_eval_20261122.sh;     RANGES="58,64";         FIRST='    (';           LAST='    )' ;;
    release) FILE=scripts/adhoc/run_release_series_20261124.sh;  RANGES="61,67 163,177"; FIRST='';                LAST='' ;;
    *) echo "unknown driver in a case" >&2; exit 2 ;;
  esac
}
# block <driver> <source file> <out file>: the prelude and the driver's lines
block() {
  spec "$1"
  {
    echo 'set -u'
    echo 'mkdir -p w/.temp/launch/transcripts/L && cd w || exit 9'
    echo 'P=P; LABEL=L; MODEL=m; EFFORT=e; AGENT=a; EVALMODEL=m; PROMPT=prompt; W=$(pwd -P)'
    echo 'INSTR=.temp/launch/i.md; SPEC=.temp/launch/s.json; STREAM=out.jsonl; CLAUDE_BIN=$(type -P claude)'
    echo 'echo instruction > "$INSTR"; echo "{}" > "$SPEC"'
    for r in $RANGES; do sed -n "${r}p" "$2"; done
    echo 'echo REACHED >&2'
  } > "$3"
  if [ -n "$FIRST" ]; then
    [ "$(sed -n "${RANGES%,*}p" "$2")" = "$FIRST" ] && [ "$(sed -n "${RANGES#*,}p" "$2")" = "$LAST" ] \
      || { echo "$FILE: the launch lines are not at $RANGES" >&2; exit 2; }
  else
    sed -n '163p' "$2" | grep -q '^  LAUNCH_ENV=(' && sed -n '177p' "$2" | grep -q '< /dev/null$' \
      && sed -n '174p' "$2" | grep -q '/usr/bin/env -i "${LAUNCH_ENV\[@\]}" "$CLAUDE_BIN" -p' \
      || { echo "$FILE: the launch lines are not at $RANGES" >&2; exit 2; }
  fi
}
# run <block file> <work dir> <NAME=VALUE ...>: the stub's output, or nothing; status of the block
run() {
  local file=$1 dir=$2; shift 2
  rm -rf "$dir"; mkdir -p "$dir"
  ( cd "$dir" && /usr/bin/env -i "HOME=$T/home" "PATH=$T/bin:/usr/bin:/bin" USER=u LOGNAME=u LANG=C "TMPDIR=$T/tmp" "$@" \
      /bin/bash "$file" > "$dir/stdout" 2> "$dir/stderr" )
  local rc=$?
  cat "$dir/w/out.jsonl" 2>/dev/null
  return $rc
}
has() { grep -q -x -- "$1" <<<"$2"; }
ok()  { echo "ok    $*"; }
bad() { echo "WRONG $*"; FAILED=1; }

# ---- 1 and 2: built in --------------------------------------------------------------
mkdir -p "$T/home/given"
for D in fanout rubric release; do
  spec "$D"; block "$D" "$ROOT/$FILE" "$T/new/$D.sh"
  OUT=$(run "$T/new/$D.sh" "$T/run" CLAUDE_CONFIG_DIR=/stale CLAUDE_CODE_OAUTH_TOKEN=stale OTHER_TOKEN=kept \
        "D4D_SERIES_CONFIG_DIR=$T/home/given" D4D_SERIES_OAUTH_TOKEN=given)
  if has "CLAUDE_CONFIG_DIR=$T/home/given" "$OUT" && has "CLAUDE_CODE_OAUTH_TOKEN=given" "$OUT" && ! grep -q '^D4D_SERIES_' <<<"$OUT"
  then ok "$D: both variables given: the session gets them under Claude Code's names only"
  else bad "$D: both variables given"; fi
  OUT=$(run "$T/new/$D.sh" "$T/run" CLAUDE_CONFIG_DIR=/stale CLAUDE_CODE_OAUTH_TOKEN=stale OTHER_TOKEN=kept)
  if [ -n "$OUT" ] && ! grep -q '^CLAUDE_CONFIG_DIR=\|^CLAUDE_CODE_OAUTH_TOKEN=\|^D4D_SERIES_' <<<"$OUT"
  then ok "$D: neither variable given: the session gets neither, whatever the caller exported"
  else bad "$D: neither variable given"; fi
done
refusal() { # <what> <NAME=VALUE ...>
  local what=$1; shift
  run "$T/new/release.sh" "$T/run" "$@" > /dev/null; local rc=$?
  if [ $rc -eq 2 ] && grep -q '^STOP: ' "$T/run/stderr" && ! grep -q REACHED "$T/run/stderr" && [ ! -e "$T/run/w/out.jsonl" ]
  then ok "release: stops before launch when $what"
  else bad "release: does not stop when $what (exit $rc)"; fi
}
refusal "D4D_SERIES_ACCOUNT is set" D4D_SERIES_ACCOUNT=anything
refusal "D4D_SERIES_CONFIG_DIR is relative" D4D_SERIES_CONFIG_DIR=given
refusal "D4D_SERIES_CONFIG_DIR is not a directory" "D4D_SERIES_CONFIG_DIR=$T/home/absent"

# ---- 3: before and after, from the cases file ----------------------------------------
if [ -n "$REF" ]; then
  [ -r "$CASES" ] || { echo "no readable cases file" >&2; exit 2; }
  N=0
  while IFS=$'\t' read -r D OLDVARS NEWVARS DIRS; do
    [ -n "$D" ] || continue
    N=$((N + 1))
    spec "$D"
    git -C "$ROOT" show "$REF:$FILE" > "$T/old/$D.src" 2>/dev/null || { echo "$REF has no $FILE" >&2; exit 2; }
    block "$D" "$T/old/$D.src" "$T/old/$D.sh"
    [ "$DIRS" = "-" ] || for d in $DIRS; do mkdir -p "$T/home/$d"; done
    [ "$OLDVARS" = "-" ] && OLDVARS=""; [ "$NEWVARS" = "-" ] && NEWVARS=""
    # shellcheck disable=SC2086
    OLD=$(run "$T/old/$D.sh" "$T/run" ${OLDVARS//@HOME@/$T/home}); ORC=$?
    # shellcheck disable=SC2086
    NEW=$(run "$T/new/$D.sh" "$T/run" ${NEWVARS//@HOME@/$T/home}); NRC=$?
    # The caller's own variables differ by construction (the new lines are given the two
    # D4D_SERIES variables, the old ones were not); what the session receives is compared.
    if [ -n "$OLD" ] && [ "$ORC" -eq "$NRC" ] && [ "$(grep -v '^D4D_SERIES_' <<<"$OLD")" = "$NEW" ]
    then ok "case $N ($D): the session's environment and arguments are the same before and after"
    else bad "case $N ($D): before and after differ (exit $ORC and $NRC)"; fi
  done < "$CASES"
  [ "$N" -gt 0 ] || { echo "the cases file holds no case" >&2; exit 2; }
fi
[ "$FAILED" -eq 0 ] && echo "ALL SAME" || echo "FAILED"
exit "$FAILED"
