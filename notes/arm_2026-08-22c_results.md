# 2026-08-22c arm results

- **Arm:** `2026-08-22c_claude-opus-5-api-generic-v5` — 12 runs (4 projects ×
  3 replicates), condition `generic_v5`, model `claude-opus-5` via CBORG.
  Launched 2026-08-23 after the pre-generation sequence settled: reconcile
  absorption (#650) and its symmetric core mirror, the anchored `doi` pattern
  (#646), the GC naming rule and manifest `naming:` block (#668/#669), the
  British-spelling instrument v2.1 and undeclared-prefix classification v2.1
  (#653/#671), and the agentic-recorder fixes (#659/#642/#672). Assembly
  digest `e0162f60`, prompt pin `c4bbcc41`, schema digest `580992ed` — the
  condition the six-canary history in `notes/generic_v5_analysis_plan.md`
  validated, gated against baseline `2026-08-20b` (canary rep1 passed all 7
  gates; re-verified on relaunch).
- **Outcome: 12 succeeded, 0 failed.** `d4d runs check --strict` exit 0.
- **Spend: 5,356,022 input / 2,259,472 output tokens recorded** — the sum of
  the 12 records' `api_usage` blocks. **This understates real spend**: AI_READI
  rep2's record carries only its post-resume phases (repair and re-report);
  its six generation phases ran in the first launch, before the #664 hang,
  and their usage is on no record — the #656 class. By analogy with its
  sibling rep3 that is roughly 360k input / 170k output unrecorded (~6–8% of
  the total). Separately, rep1's AI_READI phases were the pre-validated
  canary, resumed at re-check cost.
- **Comparison scope:** against `2026-08-20b` this measures the sum of the
  post-arm changes listed above, not any one of them. Pair-error counts are
  additionally instrument-coupled with spelling (#675, below).

## The table — three replicates per cell, 2026-08-20b worst in parens

Parentheticals are the **2026-08-20b arm's own per-project worsts, recomputed
from its committed records under the current (v2.1) instruments** — the same
values the canary gate's recorded baseline carries. (A first draft of this
note copied v4 worsts from the previous note's table under a header claiming
they were 20b's; the #676 review caught it, and the correction exposed a third
above-baseline cell, discussed below.)

| metric | AI_READI | CHORUS | CM4AI | VOICE |
|---|---|---|---|---|
| ungrounded identifiers | 0,0,0 (0) | 0,0,0 (0) | 0,0,0 (0) | 0,0,0 (0) |
| resolver URLs in identifier slots | 0,0,0 (0) | 0,0,0 (0) | 0,0,0 (0) | 0,0,0 (0) |
| organisational fragments | 0,0,0 (0) | 0,0,0 (0) | 0,0,0 (0) | 0,0,0 (0) |
| undeclared prefixes | 0,0,0 (0) | 0,0,0 (0) | 0,0,0 (0) | 0,0,0 (0) |
| British spellings | 20,37,0 (30) | 0,0,0 (0) | 0,0,0 (0) | 2,0,6 (4) |
| pair errors | 2,18,6 (12) | 1,0,2 (6) | 4,5,9 (10) | 7,5,5 (8) |
| report findings | 0,1,0 (1) | 0,0,0 (0) | 2,0,0 (0) | 0,1,1 (4) |
| minted fragments *(reported)* | 0,13,14 (14) | 0,0,0 (0) | 15,10,16 (17) | 0,0,8 (8) |
| GC label variants *(reported)* | 1,0,0 (0) | 0,0,0 (0) | 0,0,0 (0) | 53,71,73 (57)‡ |

‡ entirely the dataset's own proper title — see below.

The four identifier metrics are **0 on all 12 runs** — and 0 on all 12 of the
20b baseline's too: the v5 floors held through the procedure changes, which is
the claim; the table shows holding, not improvement. CHORUS is the arm's
cleanest (pair 1/0/2, all else zero). **Eight** of twelve runs have zero
British spellings.

## The cells above the 20b worst, each explained

**AI_READI rep2: pair=18 (worst 12), British=37 (worst 30) — coupled, not two
regressions (#675).** Finding-level classification: 11 of the 18 divergences
are spelling-only — the full record wrote British forms (`licence`,
`enrolment`, …) where the core wrote American, and normalizing spelling makes
the values byte-identical (`external_resources[0].restrictions[0]` differs in
exactly one character, licen**c**e/licen**s**e). The remaining 7 are the known
benign classes: `acquisition_methods` full=4/core=5 is #650's named test case;
the rest are precision/granularity value-differs. The British forms were
written by the original `full` phase at 13:31, **before** the run's network
stall, so the stall/resume path (#664) is exonerated — this is the documented
model nondeterminism drawn unluckily and asymmetrically across the pair.
Substantive divergence is ~7, under the worst.

**CM4AI rep1: report findings=2 (worst 0)** — the cell the baseline
correction exposed. Both findings, like all five in the arm and all five in
the 20b baseline, are the single known class `false_schema_claim`: the run's
own report asserting a slot is "not declared in the supplied digest" when it
is (`distributions`, declared on CoreDataset, 4× arm-wide; `citation`,
declared on Dataset, 1×). The checker is catching the report over-asserting
about the schema, not a record defect; 20b's CM4AI drew zero of them where its
VOICE drew four. Same class, different project this time.

**VOICE GC label variants 53/71/73 (worst 57; reported-only) — the
instrument, not the records (#674).** Every match is `Bridge2AI-Voice`
(39/56/59) or `Bridge2AI Voice` (14/15/14); zero raw `VOICE`, zero
`B2AI-VOICE` — the forms the naming rule targets. In context these are the
dataset's **own official title**: the PhysioNet release title, the citation,
`created_by: Bridge2AI-Voice Consortium`, the record's `name:` slot, and the
pediatric companion's name. The run-pinned bundle carries the two forms 152
times (114 hyphenated + 38 spaced). All lawful under the rule's proper-noun
carve-out; the counter's docstring states it cannot see source-stated proper
nouns in unquoted slots, and for VOICE that limitation is the entire signal.
The other three projects sit at 0–1, which is what rule compliance looks like
when the dataset's title does not collide with the project's label.

## Incident: the watchdog's first live test, and it lost (#664)

Run 2/12 hung ~70 minutes after its six phases completed: main thread blocked
in `_ssl__SSLSocket_read` → `poll` on a connection the peer/NAT had dropped
(no TCP socket remained), the 3600s watchdog Timer had fired and exited
**without unblocking the read** — cross-thread stream close does not
interrupt a thread already inside the SSL read on this platform. Recovery was
the documented path: `d4d api stop` (SIGTERM breaks the poll), relaunch,
resume from snapshots. No generation work was lost; the accounting loss is
the unrecorded-phases gap stated under Spend. Candidate fixes and the stack
evidence are on #664.

## Canonical selection (`d4d runs select`, validity first, coverage second)

| project | canonical | slots | margin |
|---|---|---|---|
| AI-READI | rep2 | 85 | +4 |
| CHoRUS | rep3 | 58 | +3 |
| CM4AI | rep1 | 74 | +1 |
| Voice | rep2 | 88 | +3 |

All twelve replicates validate, so validity eliminated nothing; margins are
thin and the tool's own caveat applies — "no reason to prefer another", not
"clearly best". Noted for downstream readers: AI_READI's canonical is rep2,
whose **full** record carries the arm's 37 British spellings (its core is
house-style American); selection weighs validity and coverage only. If house
style should join the criterion, that is a selection-instrument change for a
condition boundary, not a re-selection now.

Selection replaced the four 2026-08-20b records' `canonical` blocks with
`canonical_superseded_by` pointers (the tool's design). That removes from the
live corpus the 20b blocks' own evidence — including VOICE 20b's
`margin_over_runner_up: 0`, a tie — and the backward links to the 2026-08-11
marks they superseded; both survive in git history. Filed as #677.

## Instrument caveats carried forward

- GC label variants: inflated ~100% for VOICE by the title collision (#674).
- pair errors: coupled with spelling divergence (#675); rep2's 18 ≈ 7
  substantive.
- reasoning text: CBORG strips thinking-block plaintext; estimates only.
- No rubric scores here — the evaluation instruments are not domain-neutral
  and `curated` is not a reference (#177).

Per-run metric lines were printed to `data/.batch_2026-08-22c_fanout.log`,
which is gitignored; every number above is independently recoverable from the
committed provenance records, which are the citable source.
