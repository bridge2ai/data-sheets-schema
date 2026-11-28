# Repeated root-scope scoring, 2026-11-26

This convention adds two independent scorings of each existing record/rubric
pair. Generation replicate and scoring replicate are separate indices. The
first campaign contains 15 records, each assessed with two rubrics. Scoring
replicates 2 and 3 add 60 measurements, giving 90 measurements in total.

The measured scorer remains at commit
`9452a5c49a0533d86c5e08c1093021036ef98830`, the source used for scoring
replicate 1. It is not edited to support repeats. Two fresh detached checkouts,
one for each added scoring replicate, provide unused canonical output paths.
Each job retains its original publication and private runtime evidence in
that checkout and its external run directory.

The orchestration helper is
`scripts/adhoc/repeat_root_scope_scoring_20261126.py`. Its implementation
commit is recorded separately from the measured source commit. Before each
new measurement it checks the source head, tracked cleanliness and scorer
hash, then compares the complete scorer-supplied prompt, input hashes,
definition provenance, deterministic fields, executable hashes and validator
bindings with the retained successful scoring-replicate-1 plan. The original
record, scope declaration, rubric, schema and evidence authority are preserved.
The original scorer's main entry point retains its interruption and credential
cleanup handling. A repeat index is not added to the prompt or evaluation JSON.

Validated repeat outputs are copied exclusively, without rewriting their
bytes, to:

```text
data/evaluation_repeats/INSTRUMENT/scoring_rep2/FAMILY_semantic/PROJECT_LABEL_evaluation.json
data/evaluation_repeats/INSTRUMENT/scoring_rep3/FAMILY_semantic/PROJECT_LABEL_evaluation.json
```

`LABEL` remains the original generation label, including its generation
replicate suffix. The parent directory identifies the scoring replicate.
The instrument is
`2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6`.
No scoring-replicate-1 output is moved, copied over, renamed or modified.
An existing repeat destination also refuses; it never authorizes a new call.
The source publication is retained so its original receipt path remains true.

A private export manifest binds scoring and generation replicate identities,
the measured source head, baseline and repeat plans/receipts, the source and
destination byte hashes, prompt equality and the runtime-evidence location.
The copied file passes the same strict exact-file validator with the same
record, captured composed definition, independent scope and version 6.0.
Failed or interrupted exports are retained for review and stop that stream.
They must not silently become another scoring attempt.

Default reader selection remains unchanged:

| Reader | Current selection |
| --- | --- |
| Whole-corpus evaluation validator | Recursively discovers evaluation files below `data/evaluation_llm` |
| Exact-file evaluation validator | Accepts explicitly named files with their independently supplied input and instrument bindings |
| `arm_comparison.rubric_scores` | Nonrecursive project glob directly below each rubric's `label_aware` directory |
| `evaluation_manifest.live_and_archived` | Direct `label_aware` files and named `superseded_*` children |
| `audit_evaluation_comparability.evaluations` | Direct JSON files in the named `label_aware` stores |
| Review CLI prior-evaluation search | Direct files matched by its fixed `data/evaluation_llm/*/label_aware` glob |

The new repeat tree is outside all default selections. The existing v6
instrument subdirectory is already outside the legacy nonrecursive score
globs; this convention does not change that behavior. Analysis of all 90
measurements must explicitly select scoring replicate 1 once, then the two
repeat directories. Preserve both replicate indices and compare scoring
variation within each record/rubric before aggregating generation replicates.
Repeated measurements are not superseded versions of the first measurement.

Plan mode checks all 60 jobs without a scoring process or run-directory
creation. The schedule has three streams, one per generation replicate, with
20 roster entries each: five projects, two rubrics and two added scoring
replicates. One live repeat canary must be run and accepted before the batch.
The batch may skip that one canary only through its verified export manifest;
it still counts as one of the 20 stream entries. Thus the first stream has
19 remaining calls after its canary, and the other streams have 20 each.
No general resume, automatic retry or overwrite is implied.

The repeat-scoring build assignment authorizes offline preparation and tests.
The handoff records exact proposed live commands and their reviewed helper
head; it does not execute them or replace the required live authorization.
