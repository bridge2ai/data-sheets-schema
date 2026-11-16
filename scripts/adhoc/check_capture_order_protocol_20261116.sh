#!/bin/bash
# Purpose: preserve ratified capture-order evidence for issues 6191 and 6207.
# Inputs: ratified Git blobs, primary coordination notes, external runbook.
# Outputs: protocol snapshots and ignore-independent search evidence. 2026-11-16.
set -eu
P=$(cd -- "$(dirname -- "$0")/../.." && pwd)
E=${1:?Usage: check_capture_order_protocol_20261116.sh EXECUTION_ROOT}
S="$E/scratch-capture-order-20261116"
mkdir -p "$S"
cd "$P"
for spec in 'c289eed19e37e227e04dd5e0c4fc077da54184aa n1 2026-11-08' 'dcbbdc417dfd6c0f92712bcb38f565742cd794ef np1 2026-11-12'; do
  read -r commit kind day <<< "$spec"
  git show "$commit:notes/generic_v10_analysis_plan_amendment_${kind}_${day}.md" > "$S/$kind.raw"
  if grep -q "$(printf '\100')" "$S/$kind.raw"; then
    echo 'Unexpected prohibited character in source snapshot'; exit 1
  fi
  mv "$S/$kind.raw" "$S/$kind.md"
done
grep -rn -E 'capture|prewarm|admission|verification|NP1.5' "$S/n1.md" "$S/np1.md" > "$S/ratified-search.txt"
grep -rn -E 'D153|D07|D22|D36|capture.*verification|verification.*capture|capture.*prewarm|prewarm.*capture|later.capture|capture, guard and launch' "$P/notes/coordination" "$E/plans/native_post_merge_runbook_DRAFT_20261114.md" | grep -v "$(printf '\100')" > "$S/coordination-search.txt"
shasum -a 256 "$S/n1.md" "$S/np1.md"
grep -n -E 'alternative not taken|Steps 5 and 6|\*\*\(z\)\*\*|sequence script' "$S/n1.md"
grep -n -E 'N1.5|launch terms|D07|D22|D36' "$S/np1.md" | tail -15
