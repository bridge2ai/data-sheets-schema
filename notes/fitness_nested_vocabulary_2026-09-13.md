# Nested vocabulary guidance for fitness judgments — 2026-09-13

Issue #1469: a fitness judgment of `resources` received the immediate Dataset
specification but omitted the term sources for its nested `instances` values.
The same omission affected the form-subtype classifier, which uses that field
specification. A neutral-profile judgment could not see that `data_topic`
accepts GO, MeSH, EFO and NCIT terms; study judgments also lacked the nested
profile vocabulary.

## Resolution and instrument boundary

Judges now receive vocabulary constraints from every inline object class
reachable through the selected field. Each rule identifies its owning class.
Classes are visited once, so recursive and repeated object types terminate
without repeating their rules. LinkML determines whether an attribute holds
objects: implicit inline ranges are included, references are not followed,
and unrelated top-level fields cannot introduce constraints. Direct vocabulary
fields receive the same term-source and selected-profile rendering.

The evaluation inventory follows all inline depths, including attributes
beyond the generation digest's two-level limit. Its schema and import bytes
are captured together with the generation inventory. Each uses a separate
cache, and returned inventories are copies. This preserves the bounded
generation instructions while letting a deep vocabulary edit change the
evaluation specification and its cache identity.

This is the new `fitness_nested_vocabulary_2026-09-13` evaluation condition.
The companion JSON records the base commit, before/after implementation hashes,
and before/after specification SHA256 values for Dataset and CoreDataset under
both neutral and study profiles. All four generation MD5 and SHA256 values
are unchanged. The fitness and form-subtype system rubrics are unchanged;
the supplied field specifications change. New fitness cache lookups reject
entries carrying an earlier specification identity, and old entries remain
on disk. Frozen form-subtype instruments retain their existing offline replay
rules and cannot be filled from a different live specification.

Historical D4Ds, evaluations, caches and registration notes are preserved.
No generation, rescore, evaluator spawn or source download occurs here; all
test model replies are local fakes. No evaluator quoted a new definition.
The API and agentic generation canaries and all evaluation styles remain in
the [completion plan](d4d_generation_evaluation_completion_plan_2026-09-12.md).
Any new fitness or subtype measurements must register this specification
identity separately from earlier results.

## Validation

- Seven behavior regressions fail against main at `3fdd2bce8`, reproducing
  missing nested scope and unchanged cache identities after deep edits.
- All ten expanded regressions pass, including actual fake-client fitness
  and form-subtype requests, neutral/study profiles, deep implicit objects,
  cycles, references, unrelated fields, direct vocabulary fields, persistent
  and in-memory caches, immutable inventory copies, and edits during capture.
- The initial focused fitness/profile/digest suite passes 110 checks.
- The integration suite passes 155 checks covering form classification,
  evidence scoring, schema imports/caches, snapshots and synchronization.
- All four full/core, neutral/study generation prompt hashes match the
  pre-change baseline byte for byte.

Independent review and exact-head CI follow before merge. No canary or new
measurement is included in this change.
