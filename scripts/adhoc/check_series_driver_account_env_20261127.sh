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
#     2b. built in: the caller's launch note (launch_private_note_20261127.sh). Through
#        the release-series driver's own lines: given a file and a line of the caller's,
#        one line is appended before the launch record is written and before the launch,
#        in a file of mode 600, and neither the path nor the line appears in the driver's
#        output, the launch record, the launch folder or the session; a setup the helper
#        refuses stops the driver before any launch, and a line that cannot be written
#        stops it before the launch record exists. The helper by itself: each of its
#        rules is refused with its own code (the 20 cases listed below), an existing
#        file is set to mode 600 before the append, and a new one is created 600 under
#        a loose umask. The two earlier drivers stop when either variable is given, and
#        the stream runner when the file is under its state folder. With neither given,
#        every other check here runs without the helper being present.
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
    release) FILE=scripts/adhoc/run_release_series_20261124.sh; RANGES="61,67 131,156 163,177" ;;
    *) echo "unknown driver in a case" >&2; exit 2 ;;
  esac
  [ $# -ge 2 ] || return 0
  case "$1" in
    fanout)  starts "$2" 22 '[ $# -ge 1 ] || ' && is "$2" 75 '  (' && is "$2" 82 '  )' ;;
    rubric)  starts "$2" 23 '[ $# -ge 1 ] || ' && is "$2" 58 '    (' && is "$2" 64 '    )' ;;
    release) starts "$2" 60 'RUNTIME=${D4D_SERIES_RUNTIME:-' && starts "$2" 68 'case "$SERIES$MODEL$EFFORT$REP$CONDITION$METHOD" in' \
               && starts "$2" 131 '  START=$(date -u +%Y-%m-%dT%H:%M:%SZ)' && is "$2" 132 '  {' \
               && starts "$2" 155 '  } > ".temp/launch/${P}_${LABEL}.launch.txt"' && is "$2" 156 '  say "$P LAUNCHED instruction $SHA"' \
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
    echo 'say() { echo "SAY $*"; }; SHA=sha; REP=1; SERIES=s; CONDITION=c; METHOD=m; RUNTIME=r; BUNDLE=.temp/launch/i.md'
    echo 'if [ -n "${D4D_SERIES_PRIVATE_LOG:-}${D4D_SERIES_PRIVATE_NOTE:-}" ]; then mkdir -p scripts/adhoc && cp "'"$ROOT"'/scripts/adhoc/launch_private_note_20261127.sh" scripts/adhoc/; fi'
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

# ---- 2b: the caller's launch note --------------------------------------------------------
HELPER="$ROOT/scripts/adhoc/launch_private_note_20261127.sh"
GENERIC="a precondition of the caller's launch setup failed"
TAB=$(printf '\t'); NL=$(printf '\nx'); NL=${NL%x}; CR=$(printf '\r')
mkdir -p "$T/private" "$T/open" "$T/locked" "$T/repo/sub" "$T/bare/sub" "$T/bare/objects" "$T/bare/refs" "$T/state" "$T/nogit"
chmod 700 "$T/private" "$T/locked" "$T/repo/sub" "$T/bare/sub" "$T/state"; chmod 755 "$T/open"
git -C "$T/repo" init -q 2> /dev/null; : > "$T/bare/HEAD"
for tool in dirname stat uname grep env date chmod cat; do ln -s "$(PATH=/usr/bin:/bin command -v "$tool")" "$T/nogit/$tool"; done
PLOG="$T/private/notes.tsv"; PNOTE="a line of the caller, kept private"
# -- through the driver's lines
OUT=$(run "$T/new/release.sh" "$T/run" D4D_SERIES_DEFAULT_LOGIN=1 "D4D_SERIES_PRIVATE_LOG=$PLOG" "D4D_SERIES_PRIVATE_NOTE=$PNOTE")
if [ -n "$OUT" ] && [ "$(wc -l < "$PLOG" 2> /dev/null | tr -d ' ')" = 1 ] \
   && [ "$(cut -f2-4 "$PLOG")" = "L${TAB}P${TAB}$PNOTE" ] && cut -f1 "$PLOG" | grep -q '^20[0-9-]*T[0-9:]*Z$' \
   && [ "$(stat -f '%Lp' "$PLOG" 2> /dev/null || stat -c '%a' "$PLOG")" = 600 ] && grep -q '^SAY P LAUNCHED' "$T/run/stdout"
then ok "release: the note is one line with the time, the label, the project and the caller's line, mode 600"
else bad "release: the note is not written as stated"; fi
if [ -n "$OUT" ] && [ -s "$T/run/w/.temp/launch/P_L.launch.txt" ] \
   && ! grep -r -q -F -e "$PNOTE" -e "$T/private" -e D4D_SERIES_PRIVATE "$T/run/stdout" "$T/run/stderr" "$T/run/w/out.jsonl" "$T/run/w/.temp"
then ok "release: neither the path nor the line, nor either variable, is in the driver's output, the launch record or the session"
else bad "release: the note leaks into an output"; fi
OUT=$(run "$T/new/release.sh" "$T/run" D4D_SERIES_DEFAULT_LOGIN=1 "D4D_SERIES_PRIVATE_LOG=$PLOG" "D4D_SERIES_PRIVATE_NOTE=$PNOTE")
if [ -n "$OUT" ] && [ "$(wc -l < "$PLOG" | tr -d ' ')" = 2 ]
then ok "release: a second launch appends a second line to the same file"
else bad "release: a second launch does not append"; fi
refusal release "a note file is given without a line" "$GENERIC" D4D_SERIES_DEFAULT_LOGIN=1 "D4D_SERIES_PRIVATE_LOG=$PLOG"
refusal release "a note line is given without a file" "$GENERIC" D4D_SERIES_DEFAULT_LOGIN=1 "D4D_SERIES_PRIVATE_NOTE=$PNOTE"
refusal release "the note file is one the helper refuses" "$GENERIC" D4D_SERIES_DEFAULT_LOGIN=1 "D4D_SERIES_PRIVATE_LOG=$T/open/notes.tsv" "D4D_SERIES_PRIVATE_NOTE=$PNOTE"
chmod 500 "$T/locked"
run "$T/new/release.sh" "$T/run" D4D_SERIES_DEFAULT_LOGIN=1 "D4D_SERIES_PRIVATE_LOG=$T/locked/notes.tsv" "D4D_SERIES_PRIVATE_NOTE=$PNOTE" > /dev/null; RC=$?
if [ $RC -eq 3 ] && grep -q -F "SAY P STOP: $GENERIC" "$T/run/stdout" && ! grep -q 'LAUNCHED' "$T/run/stdout" \
   && [ ! -e "$T/run/w/out.jsonl" ] && [ ! -e "$T/run/w/.temp/launch/P_L.launch.txt" ] \
   && ! grep -q -F -e "$PNOTE" -e "$T/locked" "$T/run/stdout" "$T/run/stderr"
then ok "release: a line that cannot be written stops before the launch record and before the launch"
else bad "release: does not stop cleanly when the line cannot be written (exit $RC)"; fi
chmod 700 "$T/locked"
for D in fanout rubric; do
  refusal "$D" "a launch note is asked for" "(code 20)" D4D_SERIES_DEFAULT_LOGIN=1 "D4D_SERIES_PRIVATE_LOG=$PLOG" "D4D_SERIES_PRIVATE_NOTE=$PNOTE"
done
( cd "$T" && /usr/bin/env -i "HOME=$T/home" "PATH=$T/bin:/usr/bin:/bin" "D4D_SERIES_PRIVATE_LOG=$T/state/notes.tsv" "D4D_SERIES_PRIVATE_NOTE=$PNOTE" \
    /bin/bash "$ROOT/scripts/adhoc/run_release_series_stream_20261125.sh" "$ROOT" 2099-01-01z model high 1 "$T/state" P > "$T/runner.out" 2> "$T/runner.err" ); RC=$?
if [ $RC -eq 2 ] && grep -q -F "(code 29)" "$T/runner.err" && [ ! -e "$T/state/stream_rep1.state" ] && [ ! -e "$T/state/notes.tsv" ]
then ok "stream runner: stops before anything when the note file is under its state folder"
else bad "stream runner: does not stop when the note file is under its state folder (exit $RC)"; fi
mkdir -p "$T/oldwt/scripts/adhoc" "$T/state2"; chmod 700 "$T/state2"
sed 's/launch_private_note_20261127\.sh" write/launch_private_note_20261127.sh" absent/' "$ROOT/scripts/adhoc/run_release_series_20261124.sh" > "$T/oldwt/scripts/adhoc/run_release_series_20261124.sh"
( cd "$T" && /usr/bin/env -i "HOME=$T/home" "PATH=$T/bin:/usr/bin:/bin" "D4D_SERIES_PRIVATE_LOG=$T/private/runner.tsv" "D4D_SERIES_PRIVATE_NOTE=$PNOTE" \
    /bin/bash "$ROOT/scripts/adhoc/run_release_series_stream_20261125.sh" "$T/oldwt" 2099-01-01z model high 1 "$T/state2" P > "$T/runner.out" 2> "$T/runner.err" ); RC=$?
if [ $RC -eq 2 ] && grep -q -F "STOP: $GENERIC" "$T/runner.err" && [ ! -e "$T/state2/stream_rep1.state" ] && [ ! -e "$T/private/runner.tsv" ]
then ok "stream runner: stops when a note is asked for and the launch worktree's driver would not write one"
else bad "stream runner: does not stop when the launch worktree's driver would not write the note (exit $RC)"; fi
# -- the helper by itself: one rule, one code
rule() { # <code> <what> <path or - for the default PATH> <mode> [args ...] -- NAME=VALUE ...
  local code=$1 what=$2 path=$3 mode=$4; shift 4
  local args=()
  while [ $# -gt 0 ] && [ "$1" != -- ]; do args+=("$1"); shift; done
  shift
  [ "$path" = - ] && path="/usr/bin:/bin"
  ( cd "$T" && /usr/bin/env -i "HOME=$T/home" "PATH=$path" "$@" /bin/bash "$HELPER" "$mode" ${args[@]+"${args[@]}"} > "$T/rule.out" 2> "$T/rule.err" ); local rc=$?
  if [ $rc -eq "$code" ] && { [ "$code" -eq 0 ] || grep -q -F "$GENERIC (code $code)" "$T/rule.err"; } \
     && ! grep -q -F -e "$PNOTE" -e "$T/" "$T/rule.out" "$T/rule.err"
  then ok "helper: code $code when $what"
  else bad "helper: exit $rc, not code $code, when $what"; fi
}
L="D4D_SERIES_PRIVATE_LOG"; M="D4D_SERIES_PRIVATE_NOTE"
rule 21 "the line is missing" - check -- "$L=$PLOG"
rule 22 "the file is named relatively" - check -- "$L=notes.tsv" "$M=$PNOTE"
rule 23 "the line holds a newline" - check -- "$L=$PLOG" "$M=two${NL}lines"
rule 23 "the line holds a carriage return" - check -- "$L=$PLOG" "$M=two${CR}lines"
rule 23 "the line holds a tab" - check -- "$L=$PLOG" "$M=two${TAB}columns"
rule 23 "the line is blank" - check -- "$L=$PLOG" "$M=   "
rule 24 "the folder does not exist" - check -- "$L=$T/absent/notes.tsv" "$M=$PNOTE"
rule 25 "the file is a descriptor under /dev" - check -- "$L=/dev/fd/1" "$M=$PNOTE"
rule 26 "the folder is open to others" - check -- "$L=$T/open/notes.tsv" "$M=$PNOTE"
rule 27 "the folder is inside a git repository" - check -- "$L=$T/repo/sub/notes.tsv" "$M=$PNOTE"
rule 27 "it is inside a repository and git is not on PATH" "$T/nogit" check -- "$L=$T/repo/sub/notes.tsv" "$M=$PNOTE"
rule 27 "it is inside a repository and GIT_DIR points elsewhere" - check -- "$L=$T/repo/sub/notes.tsv" "$M=$PNOTE" GIT_DIR=/nonexistent
rule 27 "the folder is inside a bare repository" - check -- "$L=$T/bare/sub/notes.tsv" "$M=$PNOTE"
rule 28 "git is not there to confirm" "$T/nogit" check -- "$L=$PLOG" "$M=$PNOTE"
rule 29 "the folder is under a folder given as published" - check "$T/private" -- "$L=$PLOG" "$M=$PNOTE"
ln -s "$T/private/elsewhere.tsv" "$T/private/link.tsv"; mkdir "$T/private/folder.tsv"; mkfifo "$T/private/fifo.tsv"
ln "$PLOG" "$T/private/second-name.tsv"; : > "$T/private/empty.tsv"; echo "some other log" > "$T/private/other.tsv"
rule 30 "the file is a symbolic link" - check -- "$L=$T/private/link.tsv" "$M=$PNOTE"
rule 30 "the file is a folder" - check -- "$L=$T/private/folder.tsv" "$M=$PNOTE"
rule 30 "the file is a pipe" - check -- "$L=$T/private/fifo.tsv" "$M=$PNOTE"
rule 30 "the file has a second name (a hard link)" - check -- "$L=$PLOG" "$M=$PNOTE"
rule 30 "the file exists and is empty" - check -- "$L=$T/private/empty.tsv" "$M=$PNOTE"
rule 30 "the file holds something else" - check -- "$L=$T/private/other.tsv" "$M=$PNOTE"
rm -f "$T/private/second-name.tsv"
( cd "$T" && /usr/bin/env -i "HOME=$T/home" PATH=/usr/bin:/bin "$L=$T/private/own-output.tsv" "$M=$PNOTE" /bin/bash "$HELPER" write L P > "$T/private/own-output.tsv" 2> /dev/null ); RC=$?
if [ $RC -eq 30 ] && [ ! -s "$T/private/own-output.tsv" ]
then ok "helper: code 30 when the file is the file its own output goes to"
else bad "helper: exit $RC when the file is the file its own output goes to"; fi
chmod 644 "$PLOG"
rule 0 "an existing note file is appended to" - write L P -- "$L=$PLOG" "$M=$PNOTE"
if [ "$(stat -f '%Lp' "$PLOG" 2> /dev/null || stat -c '%a' "$PLOG")" = 600 ] && [ "$(wc -l < "$PLOG" | tr -d ' ')" = 3 ]
then ok "helper: an existing file readable by others is set to mode 600 and gains one line"
else bad "helper: an existing file is not set to mode 600 or does not gain one line"; fi
( cd "$T" && umask 022 && /usr/bin/env -i "HOME=$T/home" PATH=/usr/bin:/bin "$L=$T/private/new.tsv" "$M=$PNOTE" /bin/bash "$HELPER" write L P > /dev/null 2>&1 ); RC=$?
if [ $RC -eq 0 ] && [ "$(stat -f '%Lp' "$T/private/new.tsv" 2> /dev/null || stat -c '%a' "$T/private/new.tsv")" = 600 ]
then ok "helper: a new file is created with mode 600 under a loose umask"
else bad "helper: a new file is not created with mode 600 (exit $RC)"; fi

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
