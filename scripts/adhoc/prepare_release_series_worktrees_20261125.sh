#!/bin/bash
# prepare_release_series_worktrees_20261125.sh
# Purpose: build the launch worktrees for a release series, one per replicate stream, each
#   with its own in-project .venv that imports that worktree's source, as
#   run_release_series_20261124.sh requires. No model call, no push, nothing generated.
#   The previous series (2026-11-22b) ran three replicate streams side by side, one worktree
#   each; this builds the same layout ahead of the canary so the environment is not on the
#   critical path. The worktrees are detached; move each to the launch commit with
#   `git -C <worktree> checkout --detach <commit>` before a run (dependencies unchanged, so
#   the editable install follows the files).
# Inputs:  <repository checkout to add worktrees from> <commit> <parent directory> <name prefix> <count>
# Outputs: <parent>/<prefix>-rep1 .. -rep<count>, each with .venv; one status line per worktree.
# Serves:  the release-series rerun (issues #6312, #6324; PR #6325). Date: 2026-11-25.
set -u
REPO=${1:?repository checkout}; COMMIT=${2:?commit}; PARENT=${3:?parent directory}; PREFIX=${4:?name prefix}; COUNT=${5:?count}
case "$PREFIX$COUNT" in *[!A-Za-z0-9._-]*) echo "prefix and count take plain tokens" >&2; exit 2;; esac
case "$COUNT" in ''|*[!0-9]*|0) echo "count must be a positive whole number" >&2; exit 2;; esac
git -C "$REPO" cat-file -e "$COMMIT^{commit}" || { echo "unknown commit $COMMIT" >&2; exit 2; }
for n in $(seq 1 "$COUNT"); do
  W="$PARENT/$PREFIX-rep$n"
  if [ ! -e "$W" ]; then
    git -C "$REPO" worktree add --detach "$W" "$COMMIT" >/dev/null 2>&1 || { echo "rep$n STOP: worktree add failed"; exit 3; }
  fi
  [ "$(git -C "$W" rev-parse HEAD)" = "$(git -C "$REPO" rev-parse "$COMMIT^{commit}")" ] \
    || { echo "rep$n STOP: $W is not at $COMMIT"; exit 3; }
  if [ ! -x "$W/.venv/bin/python" ]; then
    # The host has returned EINTR and EPERM on large copies under load; retry the install.
    for try in 1 2 3; do
      ( cd "$W" && POETRY_VIRTUALENVS_IN_PROJECT=true poetry install --no-interaction > "$W/.poetry-install.log" 2>&1 ) && break
      echo "rep$n install attempt $try failed (see $W/.poetry-install.log)"; sleep 5
    done
  fi
  [ -x "$W/.venv/bin/python" ] || { echo "rep$n STOP: no .venv"; exit 4; }
  SRC=$("$W/.venv/bin/python" -c "import data_sheets_schema.api_runner as m; print(m.__file__)" 2>/dev/null)
  case "$SRC" in "$(cd "$W" && pwd -P)"/*) echo "rep$n READY $W (HEAD $(git -C "$W" rev-parse --short HEAD); imports its own source)";;
    *) echo "rep$n STOP: .venv imports '$SRC', not this worktree"; exit 5;; esac
done
