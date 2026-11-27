#!/bin/bash
# check_series_driver_account_env_20261127.sh
# Purpose: since 2026-11-27 the three launch drivers (run_agentic_fanout_20261122.sh,
#   run_rubric_eval_20261122.sh, run_release_series_20261124.sh) do not choose an account in
#   their own text. The caller's environment chooses it: D4D_SERIES_CONFIG_DIR and
#   D4D_SERIES_OAUTH_TOKEN give the configuration directory and the login token, either or
#   both, or D4D_SERIES_DEFAULT_LOGIN=1 says that the login of the default configuration
#   directory is meant. This check runs, for each driver, only the lines that test that
#   choice, build a session's environment and start it, with a stub in place of `claude`
#   that prints its environment and its arguments. It does three things:
#     1. built in, no input needed: given the directory and the token, the session gets
#        them under Claude Code's own names and no D4D_SERIES_* variable at all, another
#        one the caller exported included; given the default-login switch, it gets
#        neither, whatever the caller's shell had exported;
#     2. built in: each driver stops (exit 2) before any launch, with the message that
#        belongs to the case, when no choice is made, when the switch has another value
#        than 1, when the switch comes with a directory or a token, when
#        D4D_SERIES_CONFIG_DIR is relative (also where that relative directory exists) or
#        not an existing directory, and when the retired D4D_SERIES_ACCOUNT is set;
#     3. with a reference and a cases file: the lines as they were at that reference,
#        given a caller's setup, and the lines of this checkout, given the same account
#        through the new variables, give the stub the same environment and arguments.
#        This shows that every earlier setup can be stated in the new variables. It does
#        not show that an earlier setup still works unchanged: it does not, by design
#        (the drivers stop, see 2).
# Inputs:  [<git ref of the drivers before the edit> <cases file>]
#   The cases file has one case per line, tab-separated:
#     <fanout|rubric|release> <caller's variables for the old lines> <the same for the new lines> <folders to create under the stub home, or ->
#   Variables are space-separated NAME=VALUE, or - for none; @HOME@ in a value is the stub
#   home. Values are split on spaces and are not quoted, so a value holds no space and no
#   glob character. A case in which both sides are expected to stop cannot be stated. A case
#   names variables of the caller's own shell, so the file is kept outside the repository,
#   and this script prints the number and the driver of a case, never its text.
# Outputs: one line per check on stdout, ending "ALL SAME" or "FAILED"; exit 1 on a failure,
#   2 when the drivers do not have the expected lines at the expected places.
#   Everything is written under a temporary directory, which is removed. No model call.
# What it does not show: that a real session logs in with what it is given. A canary does.
# Serves: issue 6433 (review 1 of PR 6431, findings F1 and F2) and review 2 of that PR.
# Date: 2026-11-27.
set -u
HERE=$(cd "$(dirname "$0")" && pwd -P)
ROOT=$(cd "$HERE/../.." && pwd -P)
REF=${1:-}; CASES=${2:-}
T=$(mktemp -d) || exit 2
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin" "$T/home/given" "$T/tmp" "$T/old" "$T/new"
printf '%s\n' '#!/bin/bash' 'env | LC_ALL=C sort | grep -v "^_="' 'printf "ARG %s\n" "$@"' > "$T/bin/claude"
chmod +x "$T/bin/claude"
FAILED=0

starts() { case "$(sed -n "${2}p" "$1")" in "$3"*) return 0 ;; esac; return 1; }
is()     { [ "$(sed -n "${2}p" "$1")" = "$3" ]; }
# spec <driver> <source file>: the file, the lines that are run, and a test that those
# lines are where they are expected (the same places before and after the edit)
spec() {
  case "$1" in
    fanout)  FILE=scripts/adhoc/run_agentic_fanout_20261122.sh; RANGES="22,22 75,82" ;;
    rubric)  FILE=scripts/adhoc/run_rubric_eval_20261122.sh;    RANGES="23,23 58,64" ;;
    release) FILE=scripts/adhoc/run_release_series_20261124.sh; RANGES="61,67 163,177" ;;
    *) echo "unknown driver in a case" >&2; exit 2 ;;
  esac
  [ $# -ge 2 ] || return 0
  case "$1" in
    fanout)  starts "$2" 22 '[ $# -ge 1 ] || ' && is "$2" 75 '  (' && is "$2" 82 '  )' ;;
    rubric)  starts "$2" 23 '[ $# -ge 1 ] || ' && is "$2" 58 '    (' && is "$2" 64 '    )' ;;
    release) starts "$2" 60 'RUNTIME=${D4D_SERIES_RUNTIME:-' && starts "$2" 68 'case "$SERIES$MODEL$EFFORT$REP$CONDITION$METHOD" in' \
               && starts "$2" 163 '  LAUNCH_ENV=(' && starts "$2" 174 '  /usr/bin/env -i "${LAUNCH_ENV[@]}" "$CLAUDE_BIN" -p' \
               && sed -n '177p' "$2" | grep -q '< /dev/null$' ;;
  esac || { echo "$FILE: the launch lines are not at $RANGES" >&2; exit 2; }
}
# block <driver> <source file> <out file>: a prelude and the driver's lines
block() {
  spec "$1" "$2"
  {
    echo 'set -u'
    echo 'mkdir -p w/.temp/launch/transcripts/L w/relative && cd w || exit 9'
    echo 'set -- P'
    echo 'P=P; LABEL=L; MODEL=m; EFFORT=e; AGENT=a; EVALMODEL=m; PROMPT=prompt; W=$(pwd -P)'
    echo 'INSTR=.temp/launch/i.md; SPEC=.temp/launch/s.json; STREAM=out.jsonl; CLAUDE_BIN=$(type -P claude)'
    echo 'echo instruction > "$INSTR"; echo "{}" > "$SPEC"'
    for r in $RANGES; do sed -n "${r}p" "$2"; done
    echo 'echo REACHED >&2'
  } > "$3"
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
has() { grep -q -F -x -- "$1" <<<"$2"; }
ok()  { echo "ok    $*"; }
bad() { echo "WRONG $*"; FAILED=1; }
refusal() { # <driver> <what> <words the STOP line must hold> <NAME=VALUE ...>
  local driver=$1 what=$2 words=$3; shift 3
  run "$T/new/$driver.sh" "$T/run" "$@" > /dev/null; local rc=$?
  if [ $rc -eq 2 ] && grep '^STOP: ' "$T/run/stderr" | grep -q -F -- "$words" && ! grep -q REACHED "$T/run/stderr" && [ ! -e "$T/run/w/out.jsonl" ]
  then ok "$driver: stops before launch when $what"
  else bad "$driver: does not stop, or not for that reason, when $what (exit $rc)"; fi
}

# ---- 1 and 2: built in --------------------------------------------------------------
for D in fanout rubric release; do
  spec "$D"; block "$D" "$ROOT/$FILE" "$T/new/$D.sh"
  OUT=$(run "$T/new/$D.sh" "$T/run" CLAUDE_CONFIG_DIR=/stale CLAUDE_CODE_OAUTH_TOKEN=stale OTHER_TOKEN=kept \
        "D4D_SERIES_CONFIG_DIR=$T/home/given" D4D_SERIES_OAUTH_TOKEN=given D4D_SERIES_OTHER=exported)
  if has "CLAUDE_CONFIG_DIR=$T/home/given" "$OUT" && has "CLAUDE_CODE_OAUTH_TOKEN=given" "$OUT" && ! grep -q '^D4D_SERIES_' <<<"$OUT"
  then ok "$D: directory and token given: the session gets them under Claude Code's names only"
  else bad "$D: directory and token given"; fi
  OUT=$(run "$T/new/$D.sh" "$T/run" CLAUDE_CONFIG_DIR=/stale CLAUDE_CODE_OAUTH_TOKEN=stale OTHER_TOKEN=kept D4D_SERIES_DEFAULT_LOGIN=1)
  if [ -n "$OUT" ] && ! grep -q '^CLAUDE_CONFIG_DIR=\|^CLAUDE_CODE_OAUTH_TOKEN=\|^D4D_SERIES_' <<<"$OUT"
  then ok "$D: default login chosen: the session gets neither, whatever the caller exported"
  else bad "$D: default login chosen"; fi
  refusal "$D" "no account is chosen" "no account chosen" CLAUDE_CONFIG_DIR=/stale CLAUDE_CODE_OAUTH_TOKEN=stale OTHER_TOKEN=kept
  refusal "$D" "the default-login switch is not 1" "no account chosen" D4D_SERIES_DEFAULT_LOGIN=true
  refusal "$D" "the switch comes with a directory" "contradicts" D4D_SERIES_DEFAULT_LOGIN=1 "D4D_SERIES_CONFIG_DIR=$T/home/given"
  refusal "$D" "the switch comes with a token" "contradicts" D4D_SERIES_DEFAULT_LOGIN=1 D4D_SERIES_OAUTH_TOKEN=given
  refusal "$D" "D4D_SERIES_CONFIG_DIR is relative and exists" "must be an absolute path" D4D_SERIES_CONFIG_DIR=relative
  refusal "$D" "D4D_SERIES_CONFIG_DIR is not an existing directory" "is not a directory" "D4D_SERIES_CONFIG_DIR=$T/home/absent"
  refusal "$D" "D4D_SERIES_ACCOUNT is set" "D4D_SERIES_ACCOUNT" D4D_SERIES_ACCOUNT=anything D4D_SERIES_DEFAULT_LOGIN=1
done

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
    # No session may see a D4D_SERIES variable after the edit; the old lines never read one,
    # so one a case gave them is taken out of their side only.
    if [ -n "$OLD" ] && [ "$ORC" -eq "$NRC" ] && [ "$(grep -v '^D4D_SERIES_' <<<"$OLD")" = "$NEW" ]
    then ok "case $N ($D): the session's environment and arguments are the same before and after"
    else bad "case $N ($D): before and after differ (exit $ORC and $NRC)"; fi
  done < "$CASES"
  [ "$N" -gt 0 ] || { echo "the cases file holds no case" >&2; exit 2; }
fi
[ "$FAILED" -eq 0 ] && echo "ALL SAME" || echo "FAILED"
exit "$FAILED"
