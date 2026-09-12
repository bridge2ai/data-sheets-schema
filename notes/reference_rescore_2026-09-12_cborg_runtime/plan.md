# CBORG reference rescore with execution metadata — 2026-09-12

This supersedes the preliminary CBORG condition before any cohort fill.
That condition retains one accepted canary, three excluded attempts and
$10.26736050 of CLI-reported usage across four sessions. No prior rating
is edited or promoted into this new condition.

The requested cohort stays at 24 existing v7/v8 full D4Ds: both semantic
rubrics, 48 primary ratings and eight rubric10 repeats. The two agent
definitions, rubric texts, schemas and record bytes are unchanged. All
259 prior evaluations remain pinned. The complete previous prompt is an
exact prefix of each new prompt, followed by identical execution metadata
outside the record. The manifest and metadata boundary record both hashes.

Two preliminary sessions asserted Opus 4.5 even though the CLI request,
its supplied model context, CBORG route metadata and returned trace all
name Opus 5. The new provenance instruction defines model.name and
evaluator_model as API/runtime identifiers supplied by the launcher and
independently checked against the trace. It does not ask the evaluator to
identify underlying weights. The frozen model-identity gate stays strict.

Run one CHORUS v7 rep1 rubric10 primary rating through the same four-worker
controller used by the fill, with only this job queued. It is both the
instrument and scheduler canary, so no second pilot is needed. Inspect
source-aligned headings, input/instrument hashes, the definition echo,
actual runtime identifiers, exact original Write, scores and controller
result. Write both canary reviews before accepting both gates. Only then
run remaining jobs. Every attempt retains its own evidence; an observed
failure stops new launches and active workers finish. No automatic retry.

Use the project environment in the same foreground shell for both phases:

```bash
export PATH="/private/tmp/d4d-cborg-pinned-bin:$PATH"
export DISABLE_AUTOUPDATER=1
python scripts/reference_rescore_cborg_batch.py pilot
# Inspect the original output; write canary_review.md and batch_canary_review.json.
python scripts/reference_rescore_cborg.py accept-canary
python scripts/reference_rescore_cborg_batch.py accept-pilot
python scripts/reference_rescore_cborg_batch.py remaining
```

Opus 5 is requested as claude-opus-5[1m] through the explicit CBORG
endpoint, with high effort, temperature unspecified and the existing
$5 CLI maximum per attempt. Estimates and all excluded attempts remain
in the accounting; this is not a reconciled invoice. One canary cannot
measure load behavior or repeatability.

Completion requires all 56 original ratings, a complete attempt/cost
inventory, original successful-Write binding and preserved prior bytes.
Inspect all 24 new rubric20 Q19 rationales under the frozen text-or-graph
rule before generating qualified manuscript tables. The earlier Q19
erratum remains separate and does not predetermine these results.

The separate CHORUS v9 generation canary already passed its registered
gates. No new v9 cohort, additional v9 generation or downloads are part
of this rescore condition.

## Registered CLI preflight repair (#1345)

The first fresh-condition launch stopped locally because the default CLI
symlink had advanced to 2.1.270. The frozen adapter rejected it before
evaluator exec; its four original attempt files and controller result remain
unchanged. A reviewed, exact-hash classification keeps this local failure
separate from model-session accounting. It does not fabricate a terminal
cost record or permit uncertain attempts to be ignored.

The retained 2.1.269 binary is copied to the dedicated path above and pinned
by SHA256 in the batch registration. The scheduler checks that hash before
creating an attempt. The scoring manifest, all 56 prompts and both agent
definitions are unchanged. One separately reviewed retry of the primary
canary must pass and receive both acceptances before the remaining jobs run.

## Accepted canary and completion checks

The canary was accepted on 2026-09-12 after its original final Write scored
34/50 (68%), with the recorded definition digest and check-echo verified.
See [the inspected result](canary_review.md) and both acceptance records.
The remaining 55 were launched only after that evidence was published.

For this condition's complete audit, use the dated helper below. It applies
the reviewed local pre-launch classification, preserves uncertain attempts
as blockers, and checks scheduler snapshots from both CBORG conditions.
Then inspect all 24 new rubric20 Q19 objects and write `semantic_review.json`
with the original evidence and dispositions before rendering the tables.
The reporter verifies the inspection and every audited measurement hash.

```bash
python notes/reference_rescore_2026-09-12_cborg_runtime/execution_tools/audit_completion.py
# Complete the evidence-backed 24-rating Q19 inspection in semantic_review.json.
python notes/reference_rescore_2026-09-12_cborg_runtime/execution_tools/write_completion_summary.py
python scripts/instrument_provenance.py --write
```
