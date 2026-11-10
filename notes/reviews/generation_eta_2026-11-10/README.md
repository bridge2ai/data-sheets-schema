# D4D generation ETA from retained timestamps

Snapshot: 2026-11-10 about 02:30 UTC (November 9 evening PST).

Plan for **2–4 more calendar days to the first accepted native D4D**, approximately
November 11–13 PST, assuming sustained sessions and prompt owner decisions.
Confidence is low. This is a conditional planning range, not a statistical
prediction interval. The previous 1–2-day estimate omitted the observed rework
pattern and remaining acceptance/probe work. No defensible numeric full-campaign
completion date follows from the available evidence.

## Evidence and method

`timestamps.json` and `timestamps.tsv` inventory 84 assignment/review files with
birth and modification timestamps and SHA-256 digests; the JSON retains 141
relevant coordination event lines. Explicit filesystem globbing includes ignored
and untracked files. The scope is primary `notes/coordination` and sibling
`d4d-executions/plans/reviews`, not the whole disk. These sibling artifacts are
included because the primary coordination log points to them.

Assignment-file creation is a proxy for when work became available. Completion
times below come from explicit STATUS handoffs, not file modification alone.
Waiting and interruptions are included. File creation can reflect copying, and
modification can reflect later addenda; neither proves work or success. H's shared
report includes later I work, and J's report includes J2, so their latest mtimes
are not counted as independent completed-round durations.

| Round | Assignment created (UTC) | Handoff (UTC) | Elapsed | Interpretation |
|---|---|---|---:|---|
| U3-F | Nov 9 01:34:25 | Nov 9 02:49 | 1 h 15 m | Repair handoff; historical census remained blocked |
| U3-F2 | Nov 9 03:38:07 | Nov 9 04:21:14 | 43 m | Review repairs delivered |
| U3-G | Nov 9 05:45:24 | Nov 9 09:06:28 | 3 h 21 m | Local integration; acceptance still pending |
| U3-J2 | Nov 9 20:05:37 | Nov 9 23:28:56 | 3 h 23 m | Validation delivered with unresolved failures |

Median for these four selected rounds: **2.30 hours**. Three implementation-report
to review-report modification gaps were **49, 117 and 78 minutes**. These are
small convenience samples, not independent draws from a completion distribution.
The rapid I harness repair (17 minutes) and J mandatory stop (6 minutes) are
retained in the JSON but excluded from the broad-round sample.

U3-E's blocked combined handoff was November 9 01:33 UTC. U3-K's latest inspected
report, modified November 10 02:23 UTC, still reports blocked acceptance: nearly
**25 hours** later. Initial U1 assignment dates to November 6 01:51 UTC, about four
days before this snapshot. These intervals show continuing work, not four days
spent on K alone. An unfinished blocker cannot be modeled by counting only
quick completed subtasks.

## Current critical path and inference

1. Finish K's freshness repair and validate it. Both once-only public synthetic
   tests still fail before reservation (636.33 and 666.35 seconds); no successful
   capture-to-reservation measurement exists. The report's larger snapshot
   redesign is proposed, not implemented. F1/F2 remain blockers; F4 is another
   refusal-order test failure.
2. L: scanner/D128 closure, with review for any unapproved difference.
3. M: sync to pinned main, rederive the runner packet, rerun parity and cohorts,
   obtain approval for the new postimage.
4. Integrated acceptance, independent review, CI, approved merge, final procedure
   and installed-assets checks. U4/U5 prep already combined locally should not be
   counted again as wholly unimplemented work.
5. Separately authorized real-binary probe, reviewed registration, hash-bound
   launch word, fresh quota observation, then live canary and saved-output review.

At roughly 2.3 hours per substantial round plus 0.8–2 hours of observed review
gaps, even one round each for K/L/M consumes a large part of a day before the
remaining acceptance and probe steps. The observed sequence repeatedly exposed
another gate. Allowing additional repair/retest cycles and coordination gives the
**2–4-day planning range**. Approval waits, load restrictions, outages and model
availability can extend it; there is no measured upper bound.

**12–24 hours is only an optimistic scenario** in which the next K repair and all
subsequent gates pass promptly. **5–7 days or longer remains possible** if another
structural failure appears. These are scenarios, not probability percentiles.

Sources: primary `notes/coordination/2026-11-09-codex-native-u3{k,l,m}.md`,
`notes/coordination/STATUS.md`; sibling reports `native_u3k_2026-11-09.md`,
`native_u4b_claude_recheck2_f704188d3_2026-11-09.md`, and
`native_u4u7_readiness_2026-11-08.md`. The older readiness plan's 3–6 engineering
days was a planning allowance before much U4/U5 prep shipped; it is not added
wholesale to the current estimate.

## Generation throughput and full campaign

The separate runtime extraction enumerated **317 local provenance YAML files**
under `data/` without ignore filtering. It also used the retained budget extraction
pinned to `2cfc4666c2d81003d9cf5f432248b4217ef477e1`, because archived v10 files
are not materialized in this older primary checkout. Sources are labeled in
`../../historical_generation_runtime_20261110.json`.

| Historical assisted API run | First recorded call to last call end | Sum of completed-call durations |
|---|---:|---:|
| v10 CHORUS 10-20a | 22 h 09 m 41 s | 70.34 m |
| v10 CHORUS 10-22a | 6 h 44 m 07 s | 51.00 m |

Both include transport errors and assistance. Calendar spans include interruption
and intervention; usage-row sums are not total wall time. Neither is current
native acceptance. Historical v8 reference runs ranged from 16–51 minutes across
four projects, but those methods/conditions are also unsuitable as direct native
or BC1 forecasts. Old synthetic native successes used Python peers and zero
model calls; they cannot establish generation throughput.

The retained budget plan lists **15 remaining API runs**; the native first canary
is a separate n=1 experiment. There is no fixed full native matrix or measured
current-native success throughput in the inspected evidence. Do not invent a
5–10-day batch ETA from these records. After the accepted canary, estimate
production from the approved run roster, measured runtime, allowed concurrency,
and observed failure/recovery costs. Evaluation and human review are separate.

## Reproduction

Run from the analysis worktree, pointing at the original primary checkout:

```sh
python3 scripts/adhoc/measure_generation_eta_20261110.py \
  --repo /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema \
  --output notes/reviews/generation_eta_2026-11-10

/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python \
  scripts/adhoc/summarize_historical_generation_runtime_20261110.py \
  --repo /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema \
  --evidence /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-budget/budget_evidence.json \
  > notes/historical_generation_runtime_20261110.json
```

Later reruns intentionally observe later mtimes; retain this snapshot for audit.
