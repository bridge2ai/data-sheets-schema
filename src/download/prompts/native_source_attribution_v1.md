# Native source-attribution draft preflight v1

This is an explicitly selected native request supplement for renderers 16–23.
Offline registration and verification do not authorize executing a condition.

## Prompt body

Before the final terminal evidence check, check the saved final report draft
with the exact source-attribution preflight command supplied below. This draft
check does not replace any terminal evidence, removal, schema, receipt or
source-review inventory check.

In source_review claims, attributed_to lists distinct named source **filenames**
from chunk_manifest.chunks[].source, or is empty. A source_manifest source_id
belongs in a source-manifest provenance assertion; it is not a filename.
Provenance-only assertions require empty attributed_to. A valid filename can
happen to have the same spelling as a source ID: do not reinterpret it.

If the draft check reports findings, reread the selected source and correct
only the unaccepted report draft within the registered finite draft-check
limit. Do not automatically translate IDs, invent evidence, change a verdict
to supported, or use correct spelling as proof of semantic support. Preserve
every failed result and correction in the transcript. Exit 2, unusable inputs,
an interrupted check, or an absent result cannot establish a passing check.

A passing draft check binds the saved report, final full record and selected
input bytes. Editing any of them invalidates that observation; check the
current draft again. These draft permissions never permit changing frozen
originals, the audit, source inputs or the final full/core records. They do not
increase any registered turn, time or cost budget.

Any failed terminal evidence_assertions check or uncheckable source_review
inventory remains terminal. Stop that attempt; a later draft pass cannot erase
the failure or authorize another paid request. Run the unchanged final terminal
evidence check only after a current passing draft check. Its complete evidence
and declared-removal obligations remain mandatory.
