#!/bin/bash
# launch_private_note_20261127.sh
# Purpose: lets a caller of the release-series driver keep a note of their own about each
#   launch, in a file of their own. The caller gives a file and one line of text; before
#   each launch this helper appends one line to that file:
#     <UTC time> TAB <label> TAB <project> TAB <the caller's line>
#   It is off unless the caller sets both variables; the driver does not call it then.
# What it accepts, and nothing else:
#   - both variables, or neither (code 21);
#   - a file named by an absolute path (22);
#   - a line that is one line, holds no tab and has a visible character (23);
#   - a folder that exists (24), is not /dev or /proc or under them (25), belongs to the
#     caller and gives no permission to group or others (26);
#   - a folder with no git repository at or above it: no `.git` entry and no bare
#     repository in any ancestor, looked for without git (27), and git itself, asked with
#     its discovery variables removed, must answer "not a git repository" (27 if it finds
#     one, 28 if it is missing or answers anything else);
#   - a folder that is not under any folder given as an argument (29; the stream runner
#     gives its state folder, whose logs have been published before);
#   - a file that is absent, or is a regular file of the caller's with one name (no other
#     hard link), not empty, and holding only lines of the shape above (30). A terminal, a
#     pipe, a log of something else and an empty file are all refused by that rule.
# What it guarantees when it writes (31 if it cannot):
#   - a new file is created with mode 600, and only if no file of that name exists;
#   - an existing file is set to mode 600 before the line is appended;
#   - nothing of the path or of the line is printed. A refusal prints one fixed sentence
#     with the code above, and the exit status is that code.
# Do not run it, or the driver, with shell tracing (`set -x`, SHELLOPTS=xtrace) when a
# note is asked for: a trace prints what the variables hold.
# Inputs:  check [<folder the file may not be under> ...]
#          write <label> <project> [<folder the file may not be under> ...]
#   Environment: D4D_SERIES_PRIVATE_LOG (the file) and D4D_SERIES_PRIVATE_NOTE (the line).
# Outputs: with `write`, one line appended to the file.
# Serves: issue 6433 (finding F5), owner's decision of 2026-11-27. Date: 2026-11-27.
{ set +x; } 2> /dev/null
set -u
MODE=${1:-}
[ $# -ge 1 ] && shift
LOG=${D4D_SERIES_PRIVATE_LOG:-}
NOTE=${D4D_SERIES_PRIVATE_NOTE:-}
TAB=$(printf '\t')
SHAPE="^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z${TAB}[^${TAB}]+${TAB}[^${TAB}]+${TAB}[^${TAB}]+\$"
stop() { echo "STOP: a precondition of the caller's launch setup failed (code $1)" >&2; exit "$1"; }
case "$(uname -s)" in
  Darwin|*BSD) mode_of() { stat -f '%Lp' "$1" 2> /dev/null; }; links_of() { stat -f '%l' "$1" 2> /dev/null; } ;;
  *)           mode_of() { stat -c '%a' "$1" 2> /dev/null; };  links_of() { stat -c '%h' "$1" 2> /dev/null; } ;;
esac
DIR=""
check() {
  [ -n "$LOG" ] && [ -n "$NOTE" ] || stop 21
  case "$LOG" in /*) ;; *) stop 22 ;; esac
  case "$LOG" in *$'\n'*|*$'\r'*) stop 22 ;; esac
  case "$NOTE" in *$'\n'*|*$'\r'*|*"$TAB"*) stop 23 ;; esac
  case "$NOTE" in *[![:space:]]*) ;; *) stop 23 ;; esac
  DIR=$(cd "$(dirname "$LOG")" 2> /dev/null && pwd -P) || stop 24
  case "$DIR/" in /dev/*|/proc/*) stop 25 ;; esac
  [ -O "$DIR" ] || stop 26
  case "$(mode_of "$DIR")" in *00) ;; *) stop 26 ;; esac
  local d=$DIR out rc other
  while :; do
    [ ! -e "$d/.git" ] || stop 27
    if [ -f "$d/HEAD" ] && [ -d "$d/objects" ] && [ -d "$d/refs" ]; then stop 27; fi
    [ "$d" != / ] || break
    d=$(dirname "$d")
  done
  command -v git > /dev/null 2>&1 || stop 28
  out=$(LC_ALL=C env -u GIT_DIR -u GIT_WORK_TREE -u GIT_COMMON_DIR -u GIT_INDEX_FILE -u GIT_CEILING_DIRECTORIES \
        -u GIT_DISCOVERY_ACROSS_FILESYSTEM git -C "$DIR" rev-parse --git-dir 2>&1); rc=$?
  [ $rc -ne 0 ] || stop 27
  case "$out" in *"not a git repository"*) ;; *) stop 28 ;; esac
  for other in "$@"; do
    other=$(cd "$other" 2> /dev/null && pwd -P) || continue
    case "$DIR/" in "$other"/*) stop 29 ;; esac
  done
  if [ -e "$LOG" ] || [ -L "$LOG" ]; then
    [ ! -L "$LOG" ] && [ -f "$LOG" ] && [ -O "$LOG" ] && [ "$(links_of "$LOG")" = 1 ] && [ -s "$LOG" ] || stop 30
    if grep -q -v -E "$SHAPE" "$LOG" 2> /dev/null; then stop 30; fi
  fi
}
case "$MODE" in
  check)
    check "$@" ;;
  write)
    [ $# -ge 2 ] || stop 21
    LABEL=$1; PROJECT=$2; shift 2
    check "$@"
    LINE=$(printf '%s\t%s\t%s\t%s' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$LABEL" "$PROJECT" "$NOTE")
    printf '%s\n' "$LINE" | grep -q -E "$SHAPE" || stop 31
    if [ -e "$LOG" ]; then
      chmod 600 "$LOG" 2> /dev/null || stop 31
      chmod -N "$LOG" 2> /dev/null || true
      ( printf '%s\n' "$LINE" >> "$LOG" ) 2> /dev/null || stop 31
    else
      ( umask 077; set -o noclobber; printf '%s\n' "$LINE" > "$LOG" ) 2> /dev/null || stop 31
      chmod -N "$LOG" 2> /dev/null || true
    fi ;;
  *)
    stop 21 ;;
esac
