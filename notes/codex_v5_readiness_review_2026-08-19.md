<!-- Saved verbatim. The review body is evidence of what was found on this
     date; corrections belong in the issues filed from it. -->

# Codex review: is the repository ready to run the v5 arm?

- **Run:** 2026-08-19, Codex session `01a01ba9-79ca-76a1-af0b-1b282c4a8094`
- **Verdict: NO-GO.**
- Third readiness review, after `codex_v5_readiness_review_2026-08-15.md` and
  `..._2026-08-17.md`. This one was also asked to check whether what those two
  found was *fixed* or merely *filed*.

**2026-08-15: 11 of 14 fixed**, not 14 of 14 as the first version of this
header said. Counting the review's own words, 285 lines below: item 6 (report
before/after) *partially fixed*, item 11 (v4/v5 comparability) *reframed, not
fully cleaned up*, item 12 (agentic phase names) **not fixed**. The wrong
figure was also self-contradicting — "14 of 14 fixed, with one partially fixed"
cannot both hold — and it erased an open defect, so item 12 is now #642.

**2026-08-17: 12 of 14 fixed**, with item 3 (four-vs-five rules) not fixed and
item 13 (report before/after) partially fixed. That figure was right.

## The blocking reason, and a correction to how the review states it

The 2026-08-16 canary cannot authorise this sweep. It ran a different prompt
(`bc239c3a`, 12,167 bytes) and a different assembly (`9c2ad4a7`, a layout with
no source-ranking block) from what the arm would run today (`389f7bfe`, 13,237
bytes; assembly `d59f8532`).

The review reports that canary as `regressed` today. **Read from its own
recorded blocks it reports `ok`** — verified:

```
status of the 2026-08-16 canary under today's gate: OK
```

Both are true and the difference is the point. Its recorded `grounding` block
carries **no findings of any kind**, because the resolver-URL finding did not
exist when it was written. Recomputing the same checks from the artifacts on
disk gives:

```
RECOMPUTED status: REGRESSED
  resolver URLs in identifier slots: 22 against a baseline worst of 0
```

So the canary's stored verdict is not a pass; it is an absence of measurement
that reads like one — the failure this corpus keeps naming (#447, #599, #613).

The v4 bar it is measured against **is** a real measurement, not the same
absence — and the asymmetry is sharper than the first version of this header
claimed. All **12** v4 records recompute cleanly (no drifted bundle, so no
record's zero is an unmeasurable) and all 12 give `resolver_distinct = 0`.
Their *recorded* blocks are themselves post-check measurements: every one
carries `recorded_by: backfill_checks` written 2026-08-18, after both the
resolver metric and the form metrics existed, and two carry real findings of
other kinds — direct evidence the findings list was live rather than empty by
default.

So the gate compares a **stale run-time block against freshly backfilled
baselines**. v4 genuinely had none and the canary genuinely had 22 — which is
#591, the regression subsequently fixed by restoring the CURIE rule and
re-pinning.

That is the whole case in one line: **the canary exhibited a regression, the
regression was fixed, and nothing has been canaried since.** Exactly the
situation the canary rule addresses — re-canary after a fix; do not fix and fan
out in the same step.

## One correction to earlier statements of mine

I have described the gate as having "eight gated metrics". It has **seven
gated** plus one reported-only (`minted fragments`, deliberately ungated because
prediction 2 expects it to rise). Verified: `len(METRICS) == 7`,
`len(REPORTED_ONLY) == 1`.

And one caution about the review's section 6, which a reader skimming for a
green light will misread: **credentials are not verified reachable.** What was
established is that `CBORG_API_KEY` is present in the launch shell and that
`_client()` constructs; the endpoint was deliberately not called, and the
section's own verdict is UNVERIFIED. Given that the canary rule names missing
credentials in a child process as a recurring failure, this is the last thing to
round up — the re-canary is what tests it.

---

# v5 production readiness: NO-GO

The generation and canary code is substantially improved, but the arm should not fan out yet. The existing canary is obsolete and fails today’s gate; the analysis plan describes an older prompt/assembly and contains an unmeasurable agentic prediction; and the report phase still cannot observe the before-state it is asked to describe.

## Summary

| # | Verdict | Reason |
|---|---|---|
| 1 | **BLOCKER** | The August 16 canary used an obsolete prompt and assembly. It passes structural gates but is `regressed` under today’s canary metrics. |
| 2 | **OK** | A record constructed with every field `execute()` writes conforms, including the repair branch; agentic records without `validation` also conform. |
| 3 | **OK** | A failing first run stops after one execution under `--continue-on-error`; every project has all seven gated v4 baselines. |
| 4 | **BLOCKER** | All five metrics exist and v4 numbers reproduce, but prediction 5’s “unchanged on the agentic arm” clause cannot be measured by an API-only arm. |
| 5 | **UNVERIFIED** | Status, signalling, duplicate refusal, and resume dependency logic worked, but actual lock writing and end-to-end progress resume could not run in this read-only sandbox. |
| 6 | **UNVERIFIED** | Bundles, disk, prompt pin, client construction, sizing, and a fresh label are good. Schema-sync rebuilding and authenticated endpoint reachability remain unverified. |

## 1. Canary freshness

The existing canary is not evidence for the current v5 generation path.

Its provenance records:

- prompt SHA `bc239c3a…`, 12,167 bytes
- request SHA `74ee6e5f…`
- assembly SHA `9c2ad4a7…`
- layout without source ranking

See [AI_READI_provenance.yaml](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/data/d4d_concatenated/claudecode_agent_core/2026-08-16_claude-opus-5-api-generic-v5_rep1/AI_READI_provenance.yaml:37>).

Current code produces:

```text
current prompt:   389f7bfe… 13,237 bytes
current request:  dee6e3ab…
current assembly: d59f8532…
layout: schema digest, input bundle, source ranking, arm prompt,
        carried artifacts, phase instruction
```

The assembly definition is at [api_runner.py:341](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/api_runner.py:341>). Since the canary, the generation path gained:

- a stronger CURIE rule and resolver-URL metric (`f23c7af1`);
- source priority and supersession information (`c62e60f3`, `9aa32357`);
- a fifth prompt rule and multiple subsequent re-pins (`c62e60f3`, `437f6af3`);
- `companions` in every newly built record (`e6b99727`), at [provenance.py:1329](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/provenance.py:1329>);
- the `form` block and three new canary metrics (`864fe33a`), written at [api_runner.py:2497](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/api_runner.py:2497>);
- transitive/hash-bound resume invalidation (`9aa32357`);
- stricter audit shape, report regeneration after repair, and corrected flat-output provenance (`62c7b01c`);
- fresh- and resume-exit record conformance gates (`68006080`), at [api_runner.py:2170](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/api_runner.py:2170>) and [api_runner.py:2522](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/api_runner.py:2522>).

Today’s local gates gave:

```text
check_record = ([], None)
check_provenance = ok
validate_outputs_count = 0
d4d provenance validate-records: 1 checked, 0 failing
```

Thus the obsolete record still passes `execute()`’s structural resume gates. `d4d runs check --strict` also exited successfully, but warned that its prompt is superseded and its request cannot be re-rendered.

The actual canary verdict is different:

```text
old_canary_today_status = regressed
regression = resolver URLs in identifier slots: 22
             against baseline worst 0
```

The existing canary therefore proves only that the older route completed once. It cannot authorize the current sweep.

## 2. Conformance gate

No spurious failure was reproduced.

I constructed the record exactly as [execute()](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/api_runner.py:2381>) does: `build_record`, current prompt resolution and assembly, model/context, validation, pair/report/grounding/form blocks, and intermediates.

Results:

```text
execute_record_conformance = ([], None)
repair_branch_conformance = ([], None)
```

The repair probe included `report_regenerated_after_repair`, declared at [d4d_generation_record.yaml:181](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/schema/d4d_generation_record.yaml:181>).

The writer-field AST checks also passed:

```text
test_no_writer_sets_a_field_the_schema_forbids ... OK
test_the_scan_sees_both_builders_and_not_just_one_idiom ... OK
```

A live record made through the same `build_record()` path used by `d4d provenance record` had no `validation`, but still conformed:

```text
agentic_has_validation = False
agentic_has_companions = True
agentic_record_conformance = ([], None)
```

That matches the schema’s deliberate live requirements—`inputs`, `model`, and `system`, not `validation`—at [d4d_generation_record.yaml:323](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/schema/d4d_generation_record.yaml:323>).

## 3. Canary control flow and baselines

I invoked the real `batch_cmd.callback` with local stub execution, no provider, under both failure modes.

With `--continue-on-error`:

```text
raising canary:    execute calls = [rep1]
validation failure: execute calls = [rep1]
```

Both raised `ClickException: canary did not pass` before rep2. The relevant control flow is [cli/api.py:342](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/api.py:342>) through [cli/api.py:444](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/api.py:444>).

There are seven lower-is-better gated metrics plus one reported-only metric, not eight gated metrics. Minted fragments are intentionally reported-only because an increase is the predicted outcome; see [canary.py:75](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/canary.py:75>).

All seven gated bars resolve for all four projects:

| Project | Pair | Report | Ungrounded | Resolver URL | Org fragment | Prefix | British |
|---|---:|---:|---:|---:|---:|---:|---:|
| AI_READI | 10 | 2 | 0 | 0 | 0 | 15 | 146 |
| CHORUS | 6 | 0 | 0 | 0 | 0 | 228 | 28 |
| CM4AI | 9 | 4 | 10 | 0 | 0 | 86 | 55 |
| VOICE | 9 | 2 | 19 | 0 | 7 | 0 | 49 |

Each project matched exactly three v4 records, and no value was `None`. `verdict()` correctly makes a missing or partially missing requested baseline `UNMEASURABLE` at [canary.py:181](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/canary.py:181>).

## 4. Predictions and analysis plan

The metric wiring itself is correct:

| Prediction | Metric | Block | v4 computable |
|---|---|---|---|
| 1 | ungrounded identifiers | `grounding` | Yes |
| 2 | minted fragments | `grounding`, reported-only | Yes |
| 3 | organisational fragments | `form` | Yes |
| 4 | undeclared prefixes | `form` | Yes |
| 5 | British spellings | `form` | Yes |

The mapping is at [canary.py:98](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/canary.py:98>).

`scripts/v5_baselines.py` ran successfully and reproduced the plan exactly:

```text
undeclared prefixes: 370
URL-valued identifier slots: 397
British generated-prose spellings: 613
AI_READI minted: 17, 14, 13
CM4AI rep3 absent: 10
VOICE rep1 absent/org-frag: 19 / 7
```

However, the analysis plan is not current:

- It still says “Four rules” at [generic_v5_analysis_plan.md:18](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/generic_v5_analysis_plan.md:18>), although the executable block has five rules.
- It records assembly `2c1442fc` at [generic_v5_analysis_plan.md:39](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/generic_v5_analysis_plan.md:39>); current assembly is `d59f8532`.
- It says `comparable_conditions('generic_v4', 'generic_v5')` returns `False` at line 47. The direct result is `True`; that function now deliberately assesses prompt adjacency only, while `runs.arm_confounds` handles procedure differences.
- Prediction 5 requires British spelling to be unchanged “on the agentic arm” at [generic_v5_analysis_plan.md:91](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/generic_v5_analysis_plan.md:91>). The planned production arm contains only API runs, and there are no current agentic-v5 records. That clause is unmeasurable without adding an agentic arm or narrowing the prediction before generation.

## Additional confirmed blocker: report before/after dataflow

The second review’s report finding was only partially fixed.

The report is asked “what was changed in each record” at [api_runner.py:544](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/api_runner.py:544>), but its declared inputs are only audit plus final full/core at [api_runner.py:578](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/api_runner.py:578>).

A constructed request confirmed:

```text
AUDIT_MARKER          sent=True
ORIGINAL_FULL_MARKER  sent=False
FINAL_FULL_MARKER     sent=True
FINAL_CORE_MARKER     sent=True
```

Commit `62c7b01c` fixed reports becoming stale after validator repair, but did not supply the original records. The phase still cannot independently determine what changed, and the report checker covers only narrow claim forms. This remains a production-quality blocker from the second review.

## 5. Lock, stop, and resume

Verified:

- `d4d api status` works and reported one stale v4 lock.
- `d4d api stop --label-prefix <nonexistent>` returned cleanly.
- A real child process was found through a constructed lock and stopped with SIGTERM:

```text
child_live_before=True
stop_signal_sent=True
child_live_after=False
returncode=-15
```

- The duplicate refusal branch raised `AlreadyRunning` with the correct stop instruction.
- Thirty dependency/resume/canary tests passed, including transitive invalidation and completed-run re-gating.

Not fully verified:

- Actual lock-file creation and duplicate acquisition on a real filesystem.
- A complete resume-from-progress execution after the new conformance gate.

The sandbox has no writable temporary directory, so write-dependent tests fail before reaching repository code. Also, acquisition is a read-then-write sequence at [run_lock.py:130](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/run_lock.py:130>), not an atomic exclusive create; simultaneous launches retain a theoretical race.

## 6. Other preflight results

Good:

- All four bundles exist and their MD5s match every v4 replicate.
- Prompt registry: `11 prompt file(s), 0 not at their pin`.
- The launch shell exposes `CBORG_API_KEY`; `_client()` constructed an `anthropic.Anthropic` client targeting `https://api.cborg.lbl.gov`.
- Current estimated phase peaks are 193,044 AI_READI, 45,731 CHORUS, 133,750 CM4AI, and 157,263 VOICE input tokens.
- The recorded corpus peak is 363,261, and the largest observed output is 81,129. The selected route declares 1M input/128k output in code, with 96k full/reconcile output budgets.
- Disk: 174 GiB available; existing generated data is about 52 MiB.
- `2026-08-19_claude-opus-5-api-generic-v5_*` is collision-free.
- The August 16 label already exists and must not be reused.

Unverified:

- `d4d schema check-digest --strict` requires rebuilding into a temporary directory at [schema_sync.py:100](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/schema_sync.py:100>) and could not run in this read-only environment.
- Actual authenticated endpoint reachability was not tested because that would cross the no-live-provider boundary.
- The worktree records `dirty: true` because the `aurelian` submodule contains untracked data. It appears unrelated to generation, but a production record would still attest a dirty checkout.

## Prior-review disposition

### Review dated 2026-08-15

1. CURIE/URL conflict — **fixed** by `f23c7af1`/`437f6af3`.
2. Weak parity probe — **fixed**; parity tests now check scope and substance.
3. Unsupported core absorption — **fixed** at [api_runner.py:520](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/api_runner.py:520>).
4. Unsafe resume prerequisites/invalidation — **fixed** by `9aa32357`.
5. Inaccurate planner — **fixed** by `9ed314c6`.
6. Report lacks observable diff — **partially fixed**; final states and repair regeneration were added, original states remain absent.
7. Grounding missing-file/case behavior — **fixed** by `990a6f79`.
8. Both-record and dotted report claims — **fixed** by `990a6f79`.
9. Broad `schema_moved` suppression — **fixed** by per-slot digest history in `9ed314c6`.
10. Baseline reproducibility — **fixed** by `990a6f79`; script reproduces 370/397/613.
11. v4/v5 comparability — **reframed, not fully cleaned up** by `4a5173bc`; record-based confounds exist, but the analysis plan states the wrong result for `comparable_conditions`.
12. Arbitrary agentic phase names/completion — **not fixed**. `_parse_phases` still accepts any bare name as completed at [cli/provenance.py:21](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/provenance.py:21>).
13. Batch ignoring post-generation checks — **fixed** by `990a6f79` and the later canary-stop correction.
14. VOICE prefix filter — **fixed** with exact filename matching at [cli/provenance.py:562](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/cli/provenance.py:562>).

### Review dated 2026-08-17

1. Identifier/minting contradiction — **fixed** by `437f6af3`.
2. v5 absent from agentic condition registry — **fixed** by `437f6af3`.
3. Four-vs-five rule metadata — **claimed fixed but still present** in both the prompt rationale and analysis plan.
4. Same-tier superseded releases — **fixed** by `9aa32357`; 32 source-priority tests passed.
5. Ranking leakage into single-source arms — **fixed** at [api_runner.py:597](</Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/src/data_sheets_schema/api_runner.py:597>).
6. Missing baseline passing — **fixed** by `9aa32357`.
7. Completed canary unable to re-gate — **fixed** by `9aa32357`.
8. Missing prediction metrics — **fixed** by `864fe33a`.
9. Mode-blind/opt-in record schema — **fixed for normal writers** by `68006080`; latent null-value issue #614 remains open but does not affect the constructed API record.
10. Contradictory schema descriptions — **fixed** by `68006080`.
11. Non-transitive, unbound resume invalidation — **fixed** by `9aa32357`.
12. Weak audit-shape check — **fixed** by `62c7b01c`.
13. Report before/after and post-repair staleness — **partially fixed**; repair regeneration fixed, missing original inputs remain.
14. Flat-output provenance paths — **fixed** by `62c7b01c`.

## Minimum actions to reach GO

1. Correct and freeze the analysis contract: five rules, current assembly digest, accurate `comparable_conditions` wording, and either remove/narrow prediction 5’s agentic clause or add a defined agentic-v5 arm.
2. Give the report phase original and final full/core snapshots—or stop asking it to report a before/after change account—and test the actual assembled request.
3. In a writable launch environment, run `d4d schema check-digest --strict` and the real lock/resume tests. Confirm lock creation and completed progress resume end to end.
4. Use a fresh, collision-free label prefix and preferably a clean worktree. Do not reuse `2026-08-16_claude-opus-5-api-generic-v5`.
5. Only after all preceding changes are pinned, run a fresh AI_READI canary against `2026-08-13_claude-opus-5-api-generic-v4`. Proceed with the remaining eleven runs only if that current canary passes all seven gated metrics.

No files were modified and no provider call was made.
