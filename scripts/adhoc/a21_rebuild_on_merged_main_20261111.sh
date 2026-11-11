#!/usr/bin/env bash
# Purpose: rebuild the A21 CHORUS generic_v10 (BC1) registration, sizing record
#   and batch roster on main after PR 5808 merged, following steps 1.1 to 1.4 of
#   notes/development_efficiency_20261111/handoffs/agy3-a21-rebuild-runbook.md.
#   No provider call is possible: the builder and check steps run with the
#   provider keys removed, and the launcher step is --dry-run only.
# Inputs: the launch-base worktree d4d-executions/launch-a21 (moved to the
#   merge commit by the `move` step), its own .venv and tracked inputs.
# Outputs: d4d-executions/plans/a21_registration_<label>/ (three JSON files)
#   and the sibling logs a21_registration_<label>.{preflight,builder,check,
#   dryrun}.log and .sha256.
# Serves: owner decision D131 (2026-11-11), PR 5808, the A21 re-canary.
# Date: 2026-11-11
#
# Usage: a21_rebuild_on_merged_main_20261111.sh <step> [args]
#   preflight            read-only checks before the move
#   move                 switch launch-a21 (detached) to the merge commit, then verify
#   build                step 1.2: write registration, sizing record and roster
#   check                step 1.3: offline --check, and re-hash the three files
#   dryrun <sha> <usd>   step 1.4: launcher --dry-run with the roster sha256 and slice
#   poststate            read-only: HEAD, status, sweep status, label directories
# This script never passes --launch or --yes and never runs `d4d api batch`
# without --dry-run.
set -u
set -o pipefail

EXEC=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions
LB=$EXEC/launch-a21
PY=$LB/.venv/bin/python
D4D=$LB/.venv/bin/d4d
M4=673838c51547278cfd79254670ec95421c7bcaf7
PRE=925d726d67cdd03fe28fdeafdde60fa27df57205
MERGE=7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1
P=2026-11-11a_claude-opus-5-api-bc1-a21
L=${P}_rep1
OUT=$EXEC/plans/a21_registration_${L}
SIZING="CHORUS=$LB/data/ATTIC/d4d_concatenated_archived/claudecode_api_core/2026-10-22a_claude-opus-5-api-generic-v10_rep1/intermediate"

stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
noenv() { env -u D4D_MANIFEST -u CBORG_API_KEY -u ANTHROPIC_API_KEY "$@"; }

builder() {
  # The builder is run from the launch base so that the working directory is
  # the checkout whose files the registration pins.
  ( cd "$LB" && noenv "$PY" "$LB/scripts/build_api_registrations.py" \
      -p CHORUS -l "$L" --partition chorus \
      --bounded-carry-version 1 --bc1-fan-in 2 --aggregate-input-tokens 4500000 \
      --source-manifest "$LB/data/preprocessed/source_manifest.yaml" \
      --sizing-record "$SIZING" \
      -o "$OUT" "$@" )
}

hash_three() {
  shasum -a 256 "$OUT/roster_${L}.json" "$OUT/registration_chorus_${L}.json" \
    "$OUT/registration_chorus_${L}.sizing.json"
}

state() {
  echo "HEAD $(git -C "$LB" rev-parse HEAD)"
  echo "status:"; git -C "$LB" status --porcelain | sed 's/^/  /'
  echo "sweeps:"; ( cd "$LB" && noenv "$D4D" api status 2>&1 | sed 's/^/  /' )
  echo "locks:"; ls -la "$LB/data/.run_locks" 2>/dev/null | sed 's/^/  /' || echo "  (no lock directory)"
  echo "label directories:"
  for d in "$LB/data/d4d_concatenated/claudecode_api/$L" "$LB/data/d4d_concatenated/claudecode_api_core/$L"; do
    if [ -e "$d" ]; then echo "  PRESENT $d"; else echo "  absent  $d"; fi
  done
}

step=${1:-}
case "$step" in
  preflight)
    {
      echo "# preflight $(stamp)"
      echo "origin/main $(git -C "$LB" rev-parse origin/main)"
      git -C "$LB" merge-base --is-ancestor "$M4" "$MERGE" && echo "ancestor M4 -> merge: yes"
      git -C "$LB" merge-base --is-ancestor "$PRE" "$MERGE" && echo "ancestor 925d -> merge: yes"
      state
      if [ -e "$OUT" ]; then echo "REFUSE: $OUT already exists"; exit 3; fi
      echo "output directory absent: $OUT"
    } 2>&1 | tee -a "$OUT.preflight.log"
    ;;
  move)
    {
      echo "# move $(stamp)"
      echo "before: $(git -C "$LB" rev-parse HEAD)"
      # stderr is kept: a refused switch must be visible.
      git -C "$LB" switch --detach "$MERGE" || { echo "REFUSED: switch failed"; exit 4; }
      echo "after:  $(git -C "$LB" rev-parse HEAD)"
      [ "$(git -C "$LB" rev-parse HEAD)" = "$MERGE" ] || { echo "REFUSE: HEAD is not the merge commit"; exit 4; }
      echo "status:"; git -C "$LB" status --porcelain | sed 's/^/  /'
      echo "imports:"
      ( cd "$LB" && noenv "$PY" -c 'import data_sheets_schema, download; print(" ", data_sheets_schema.__file__); print(" ", download.__file__)' )
      echo "prompts check --strict:"
      ( cd "$LB" && noenv "$D4D" api prompts check --strict 2>&1 | tail -15 | sed 's/^/  /' ); echo "  exit=$?"
      echo "schema check-digest --strict:"
      ( cd "$LB" && noenv "$D4D" schema check-digest --strict 2>&1 | tail -15 | sed 's/^/  /' ); echo "  exit=$?"
      echo "sweeps:"; ( cd "$LB" && noenv "$D4D" api status 2>&1 | sed 's/^/  /' )
    } 2>&1 | tee -a "$OUT.preflight.log"
    ;;
  build)
    [ "$(git -C "$LB" rev-parse HEAD)" = "$MERGE" ] || { echo "REFUSE: launch base is not at the merge commit"; exit 4; }
    [ -e "$OUT" ] && { echo "REFUSE: $OUT already exists"; exit 3; }
    { echo "# build $(stamp)"; builder; echo "builder exit=$?"; } 2>&1 | tee "$OUT.builder.log"
    hash_three | tee "$OUT.sha256"
    ls -la "$OUT"
    ;;
  check)
    { echo "# check $(stamp)"; builder --check; echo "check exit=$?"; } 2>&1 | tee "$OUT.check.log"
    echo "re-hash against $OUT.sha256:"
    shasum -a 256 -c "$OUT.sha256"
    ;;
  dryrun)
    SHA=${2:?roster sha256 required}
    USD=${3:?slice in dollars required}
    {
      echo "# dryrun $(stamp) expect-sha256=$SHA max-cost-dollars=$USD"
      echo "## state before"; state
      echo "## launcher --dry-run"
      ( cd "$LB" && "$PY" "$LB/scripts/api_launcher.py" --worktree "$LB" -- d4d api batch \
          --projects CHORUS --arm baseline --condition generic_v10 \
          --shared-generation-version 1 --shared-generation-registration "$OUT/roster_${L}.json" \
          --expect-sha256 "$SHA" \
          --api-playbook-version 2 --receipt-completion-version 2 \
          --replicates 1 --label-prefix "$P" \
          --max-cost-dollars "$USD" --dry-run )
      echo "dry-run exit=$?"
      echo "## state after"; state
      echo "## re-hash"; shasum -a 256 -c "$OUT.sha256"
    } 2>&1 | tee "$OUT.dryrun.log"
    ;;
  poststate)
    state
    ;;
  *)
    echo "usage: $0 preflight|move|build|check|dryrun <sha256> <usd>|poststate" >&2
    exit 2
    ;;
esac
