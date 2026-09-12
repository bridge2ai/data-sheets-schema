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
The remaining 55 were queued only after that evidence was published. Six jobs started before the controller stopped on a validator denial; see the execution amendment below.

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

## Validator-status execution amendment (#1347)

The stopped fill finished with five accepted ratings in this condition and
two excluded evaluator sessions. Both excluded rubric20 sessions appended
a literal exit-status echo to the exact-file validator command; the CLI
denied the compound command and neither session successfully validated.
Their original candidates (both 83/88), prompts, traces and receipts remain
unchanged and excluded. Seven evaluator sessions cost $21.24240650 in
CLI-reported usage, including $5.85996775 for these two exclusions. The
separate local pre-launch failure still has zero evaluator sessions.

The registered extension permits only the two literal status echoes and
accepts an equivalent validator command only with a matching VALID marker,
a final zero status, a successful original tool result and the frozen
Write/validation ordering checks. It changes no scoring prompt, definition,
input, candidate or original transcript. Each accepted use records its
original command and status proof in the receipt. Execution permissions
changed at this boundary; unchanged prompts alone do not establish identical
model behaviour. The registration pins the extension, all five accepted
outputs, both complete failed histories and prior controller evidence.

Offline validation passed 212 tests and six native-CLI probes against a
scripted local endpoint. Both failed original traces remain rejected; all
five accepted original traces still pass. No provider calls were made in
these checks. See validator_status_registration.json and the retained probe.

After independent review, run only AI_READI_v7_rep2_r20_rating1 as a new
batch pilot. Review its actual output before accepting this batch gate.
The primary CHORUS instrument acceptance remains unchanged; its earlier
batch review and acceptance are archived. After the new pilot passes,
50 jobs remain, including one explicitly registered retry of rep3 rubric20.
The controller still stops new launches on an observed failure, drains
active workers and refuses any unregistered further retry.

```bash
python scripts/reference_rescore_cborg_batch.py pilot
# Inspect the retry's original Write, validation proof and semantic judgments.
# Write the new batch_canary_review.json; retain the original canary acceptance.
python scripts/reference_rescore_cborg_batch.py accept-pilot
python scripts/reference_rescore_cborg_batch.py remaining
```

## Deadline boundary and retained exclusions (#1350/#1351)

At 2026-09-12T22:12:54.831584+00:00, all workers drained with17 accepted ratings and6 retained excluded evaluator sessions:4 have terminal costs,2 timed out before any Write and have unknown cost. All23 actual evaluator sessions are inventoried separately from the one zero-call local preflight. Known terminal CLI estimates total $57.13448075; a full expenditure total is unknown. The provider lookup contains only three exact message IDs from the first timeout and returned no entries.

The separately hashed execution extension increases the evaluator deadline from900 to1800seconds, preserving the $5 CLI cap and all56 full prompts, definitions, inputs, CLI, permissions and model identifiers. It retains any future timeout candidate before temporary-directory removal, without accepting it. The unchanged frozen audit remains strict by default. This dated accounting wrapper recognizes only the two reviewed byte-pinned timeout histories, reports their costs as null, and rejects every other unresolved attempt. Measurement/session completion can be reported with this explicit cost limitation.

After independent review, run only CHORUS_v8_rep1_r10_rating1 as the fresh deadline retry pilot. Inspect its original output and execution evidence, then accept the new batch gate before the remaining38 ratings. The four new failures are eligible for one fresh retry each; no original candidate is edited or promoted. Both execution boundaries must qualify comparisons and repeat panels.

## Fresh retry after validation-wrapper rejection (#1354)

At 2026-09-12T23:16:05.336973+00:00, all workers drained with 30 accepted ratings and seven excluded evaluator sessions. The CM4AI v7 rep2 rubric20 session successfully ran a validator command prefixed with a cd wrapper, which is outside the frozen accepted command grammar. Its original 75/88 candidate remains excluded, with its $3.15029550 CLI estimate retained. No command normalization, score correction or gate broadening is applied.

The scoring instrument and execution settings remain unchanged. After independent review, run one fresh CM4AI v7 rep2 rubric20 retry as the batch pilot. Inspect its original Write and validation evidence before accepting the batch gate and launching the remaining 25. The previous gates and full completed attempt/controller history are archived; the original instrument canary remains unchanged. Both older timeout costs remain unknown.
