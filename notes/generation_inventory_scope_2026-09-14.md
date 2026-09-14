# Inventory scope and repair propagation — 2026-09-14

The approved v10f CHORUS API replacement completed for $3.487946 and failed
independent review of its unchanged originals. Its description and EEG
instance received the source's in-progress qualifier, while an inventory in
the sensitivity field still asserted EEG content without that qualifier.
The record also inferred the absence of comparable datasets from a project
goal. The [rejection record](matched_cborg_2026-09-14_v10f_cap20/rejected_canaries/CHORUS_api_rep1/README.md)
preserves all 38 originals, exact review identities and five settled requests.
[#1782](https://github.com/bridge2ai/data-sheets-schema/issues/1782) remains
open for empirical acceptance; static instruction checks cannot establish
model compliance.

The generic instruction correction applies to API generation, audit and
reconciliation and to the native playbooks through the shared rules:

1. Treat each member of an inventory as a separate claim. An unqualified
   assertion that data include several items assigns presence to every item,
   even inside a sensitivity, governance or other contextual field.
2. Audit negative current-state assertions explicitly. A development goal
   does not establish the absence of comparable resources.
3. Before repairing a finding, locate every occurrence of its fact, including
   synonyms and members of prose lists in fields the auditor did not name.
   After editing named locations, revisit occurrences left unchanged. The
   auditor's findings are not an exhaustive occurrence inventory.
4. Qualify or omit unsupported members without removing supported members or
   converting a supported presence boolean to false. Preserve supported plans
   where the field permits them, with their status stated locally.

This changes the assembled generation instructions. A fresh source-instrument
condition is required; preserve v10f and all earlier conditions. The raw
historical prompt files, schemas, profiles, vocabularies, source bundles,
phase count, model and effort policy remain unchanged. Source-specific
examples occur only in the experiment/review notes, not in the generic
generation instructions. The exact system-prompt snapshot is updated along
with this deliberate instrument change.

All new spending remains in the additional $200 allocation: 22 settled
requests total $16.163918, leaving $183.836082. The rejected v10e and v10f
attempts together cost $7.235012 against the approved $63.75 combined ceiling.
The three unrun canaries retain caps of $10/$15/$15. A proposed next CHORUS
API cap of **$16.51**, below the approved $20 maximum, keeps maximum exposure
including both rejected attempts at **$63.745012**, within that same ceiling.
Preparing and reviewing this new condition does not authorize an additional
whole attempt. No automatic retry is permitted.

Prepare the [v10g candidate](matched_cborg_2026-09-14_v10g/README.md), independently
review it and pass its exact-commit CI before requesting approval for one more
attempt. Any approved launch still requires fresh pin, pricing, accounting
and original-artifact checks. Both generation arms, all five Bridge2AI datasets
including VOICE_PEDIATRIC, Kids First and every applicable evaluation style
remain in the [dated plan](matched_cborg_source_scope_continuation_2026-09-14.md).
No later generation, evaluator or production job follows the rejected canary.
