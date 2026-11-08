#!/opt/homebrew/bin/bash
# Purpose: remove only recorded Round 3 transient basetemps, 2026-11-07.
# Inputs: evidence.json, per-run inventories, completed-process witnesses.
# Output: guarded per-target cleanup.tsv; serves the U3-C Round 3 report.
# The single canary basetemp was already removed and verified separately.
set -eu
DRY=()
if [ "$#" -eq 1 ] && [ "$1" = --dry-run ]; then
  DRY=(--dry-run)
elif [ "$#" -ne 0 ]; then
  exit 2
fi
test -s /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/evidence.json
guarded() {
  test ! -e /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/plans/native_quiet_window.lock
  test -s "$1/basetemp-inventory.json"
  /opt/homebrew/bin/bash /Users/marcin/.codex/skills/safe-delete/scripts/guarded_rm.sh \
    --expect-parent "$1" \
    --log /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/cleanup.tsv \
    --note 'Round 3: completed process cleanup, complete file inventory and retained evidence verified' \
    "${DRY[@]}" "$2"
}
guarded /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/ca /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/ca/cases
guarded /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-focused /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-focused/cases
guarded /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-shared /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-shared/cases
guarded /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-bc1 /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-bc1/cases
guarded /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-api-1 /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-api-1/cases
guarded /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-api-2 /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-api-2/cases
guarded /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-api-3 /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-api-3/cases
guarded /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-api-4 /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-api-4/cases
guarded /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-schema-remaining /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-schema-remaining/cases
guarded /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/launcher-canary /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/launcher-canary/cases
guarded /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/launcher-final /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/launcher-final/cases
guarded /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-api-unfinished /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u3c-r3/b-api-unfinished/cases
