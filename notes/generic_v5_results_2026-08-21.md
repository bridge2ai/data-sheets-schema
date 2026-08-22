# v5 arm results against the pre-registered predictions

- **Arm:** `2026-08-20b_claude-opus-5-api-generic-v5` — 12 runs (4 projects × 3
  replicates), condition `generic_v5`, model `claude-opus-5` via CBORG,
  launched 2026-08-20 under the documented gate override recorded in
  `notes/generic_v5_analysis_plan.md` and #650. Completed 2026-08-21:
  **12 succeeded, 0 failed**; all 12 records conform to the generation-record
  schema; `runs check --strict` exit 0; prompts at pin.
- **Spend:** 5,393,885 input / 2,192,390 output tokens, **summed from the
  `api_usage` blocks of the 12 records** (plus the three gate canaries in the
  plan's canary history). One known omission (#656): the CBORG budget
  interruption at run 12 killed an invocation whose paid `full`+`core` calls
  are on no record — provenance is written at run end, so a killed invocation's
  usage is lost. By analogy with the sibling VOICE runs that is roughly ~1–4%
  of the total. The run itself lost nothing: the phases were snapshotted and
  the resume consumed them.
- **Comparison scope, per the plan:** v4-vs-v5 measures *the five v5 rules plus
  a schema change plus procedure changes* (`reconcile_full` inputs, audit
  clause, report before-states). No attribution to any single rule is
  available, and none is claimed. Pair-error counts are additionally
  non-comparable at face value across arms (#650).

## Verdicts

| # | prediction (as registered) | verdict |
|---|---|---|
| 1 | ungrounded identifiers fall | **confirmed, to the floor** — 0 on all 12 records; v4 had 19 (VOICE rep1) and 10 (CM4AI rep3) |
| 2 | minted fragments rise or hold | **confirmed as intended, with one registered test firing on its letter** — minted rose and the named failure mode (omission without anchoring) did not occur, but falsification test 1 fires on its letter via AI_READI's creators correction; see "The registered falsification tests", where the post-hoc judgment is labeled as such |
| 3 | organisational identifiers carry no person fragments | **confirmed, to the floor** — 0 on all 12; v4 had 7 (VOICE rep1) |
| 4 | invented-prefix population stops growing | **exceeded** — v5 records add zero undeclared-prefix occurrences on all 12; v4 worsts were 15 / 228 / 86 / 0 |
| 5 | British spellings fall on the API arm (narrowed 2026-08-19) | **confirmed and understated by the instrument** — gated 613 → 84; genuine ≈ 545 → 24 (60 of v5's 84 are the "analyses" false positive; of the 24 genuine, 22 use forms the AI_READI and VOICE bundles carry — the remaining 2, VOICE rep3's `programme`, occur nowhere in VOICE's bundle and are model-written). Full decomposition: #653 and `notes/british_spelling_analysis_2026-08-21.md`, extended to VOICE here |

## The full table — v5 replicates vs the v4 worst

| metric | AI_READI | CHORUS | CM4AI | VOICE |
|---|---|---|---|---|
| ungrounded identifiers | 0,0,0 (v4 worst 0) | 0,0,0 (0) | **0,0,0 (10)** | **0,0,0 (19)** |
| resolver URLs in identifier slots | 0,0,0 (0) | 0,0,0 (0) | 0,0,0 (0) | 0,0,0 (0) |
| organisational fragments | 0,0,0 (0) | 0,0,0 (0) | 0,0,0 (0) | **0,0,0 (7)** |
| undeclared prefixes | **0,0,0 (15)** | **0,0,0 (228)** | **0,0,0 (86)** | 0,0,0 (0) |
| British spellings | 28,22,8 (146) | 4,0,4 (28) | 0,2,2 (55) | 3,6,5 (49) |
| pair errors | 12,9,6 (10) † | 3,3,6 (6) | 10,6,3 (9) † | 8,4,7 (9) |
| report findings | 1,0,0 (2) | 0,0,0 (0) | 0,0,0 (4) | 4,0,1 (2) † |

† above the v4 worst; discussed under "The three cells above baseline".

## Prediction 2 in detail — the one with a named failure mode

The plan pre-registered the diagnostic: *if `absent` falls while minted
fragments do not rise, the model is omitting identifiers rather than anchoring
them, and that must not be reported as the intended outcome.*

| project | v4 minted (3 reps) | v5 minted (3 reps) |
|---|---|---|
| AI_READI | 17, 14, 13 | 14, 0, 12 |
| CHORUS | 0, 0, 0 | 0, 0, 0 |
| CM4AI | 12, 0, 0 | 17, 10, 10 |
| VOICE | 0, 0, 14 | 8, 8, 8 |
| **arm total** | **70** | **87** |

`absent` fell to zero everywhere **and** minted rose (70 → 87; a first draft of
this note mis-summed its own table as 79 — #655 review). The intended
redirection, not the omission failure mode. More telling than the total is the
consistency: v4 minted erratically (VOICE 0, 0, 14; CM4AI 12, 0, 0), v5 mints
the same way every run (VOICE 8, 8, 8; CM4AI 17, 10, 10) — rule 3 turned an
occasional improvisation into a stable convention.

## The registered falsification tests, each evaluated

The plan registered three ways the block would be falsified rather than
confirmed. The first version of this note never confronted them; the #655
review caught that, and on its letter the first one **fires**:

**1. "`absent` falls but total external identifiers falls further… watch
`grounded`; it should hold."** Measured: absent 29 → 0 (−29); total
grounded+minted+absent 206 → 171 (−35 — further); grounded 107 → 84 (did not
hold). **Decomposed, the entire firing is AI_READI**: its grounded fell 47 → 20
and minted 44 → 26, while *excluding* AI_READI the arm's total identifiers
**rose** 115 → 125 and grounded rose 60 → 64. The AI_READI fall is the
creators correction diagnosed in #650's entity-drop analysis: v4 promoted
clinical-trial investigators (bundle-grounded ORCIDs) into `creators`, a claim
the release's own citation contradicts; v5's source-priority rule rejects the
promotion. The bullet was written to catch wholesale dropping of legitimate
identifiers; what happened is targeted removal of identifiers attached to a
wrong claim. **We judge the test's letter fired and its spirit did not — and
that judgment is post-hoc and labeled as such.** A reader who weighs the
registered letter over the post-hoc diagnosis should discount prediction 2's
"as intended" accordingly.

**2. "minted rises on values whose base is not in the bundle (shows up as
`absent`)."** Did not fire: absent is 0 on all 12 records, so every minted
fragment hangs off a bundle-attested base.

**3. "Pair divergence rises — a regression watch, not a prediction."** Fired
modestly and was caught live: the canary gate stopped two sweeps on it, the
three-run diagnosis found the divergences benign (extra precision in core that
`reconcile_full` does not absorb), and the arm proceeded under the documented
override (#650). Post-arm engineering is tracked there.

## The three cells above baseline

1. **AI_READI pair errors {12, 9, 6} vs worst 10** — the diagnosed, overridden
   case (#650): finding-level analysis on three runs showed granularity and
   extra-precision divergences, nothing wrong or lost; the arm's own replicates
   regressed to the mean.
2. **CM4AI rep1 pair 10 vs worst 9** — one count over, same class.
3. **VOICE rep1 report findings 4 vs 2** — all `false_schema_claim`, three of
   them the same claim about `splits` repeated; the report-claims checker
   catching one run's report over-asserting. reps 2–3: 0 and 1.

Post-arm engineering for the pair-error class is tracked in #650 (teach
`reconcile_full` to absorb core's extra precision; the byte-identical
`acquisition_methods` divergence across runs is the test case).

## Instrument caveats carried into any downstream use

- **British spellings** (#653): the gated counter counts American "analyses"
  as British and misses `colour`; both arms measured by the same instrument,
  so the *change* is valid and understated, the absolute values are not.
- **Pair errors** (#650): counts disagreements without weighing them; v5 runs
  ~2 higher on a class shown benign.
- **companions.reasoning_log.md5** (#652): hashes a prefix of the log; use
  `validation.artifacts` for integrity.

## What this arm does not show

Which of the five rules produced which effect (the plan's own constraint: the
step is five rules plus schema plus procedure, measured as a sum). Anything
about the agentic arm (prediction 5 was narrowed to the API arm before
generation, with the cost stated in the plan). Anything scored by rubric —
the evaluation instruments are not domain-neutral and `curated` is not a
reference (#177, #627).

## Next steps

1. Canonical selection per project (`d4d runs select`) — within-arm, same
   instrument, unaffected by the cross-arm caveats.
2. #650 reconcile absorption; #653 spelling instrument; #652 companion hashes;
   #646 `doi` pattern anchoring — all post-arm by design, now unblocked.
