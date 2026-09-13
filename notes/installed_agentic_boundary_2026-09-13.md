# Installed agentic execution boundary — 2026-09-13

Work for #1556 packages the transcript observer with a compatibility script,
uses its implementation hash in new observed extensions, makes agent discovery
resource-aware, and ships verified definition preimages so check-echo works
without Git history. Current and preimage hashes are checked before using a
packaged challenge. The source definitions and scoring rules are unchanged.

An executable playbook view substitutes the installed interpreter and schema
paths while retaining the original playbook rules. Its toolchain is recorded
for instruction replay. The CLI can run through its own Python module.
Term validation is a runtime dependency on Python 3.10 and newer, matching its
upstream Python requirement; that is the supported installed agentic runtime.
The API/evaluation modules retain their existing Python floor.

Prototype validation passes 73 observer/definition checks and all seven
fresh-wheel workflow checks. The agentic check executes emitted full/core
validation, derivation, pair checks and playbook inspection, runs the packaged
observer on a synthetic transcript, and checks installed definition discovery
and rejection of a copied preamble. The term-validator entry point is checked;
no ontology/source download or provider call is made. All 48 historical
renderer 1–4 controls still match. No real agent is spawned, no production
record is generated and no record is rescored.

Before review: integrate the corpus renderer-5 boundary from PR #1587 and
reserve renderer 6 for this portable toolchain. Refresh definition preimages
when integrating profile-definition changes. Complete broader prompt/record
compatibility and the integrated installed workflow before publication.
