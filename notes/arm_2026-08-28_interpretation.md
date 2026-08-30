# What the 2026-08-28 arms say: agentic v6 (complete) and API v7 (partial)

Written 2026-08-29/30 from `notes/arm_comparison.md` (regenerated), the run
records, and the first `d4d-review-record` review. Two arms are new since
the 2026-08-24 analysis:

- **v6 agentic** — 12/12 runs, condition `generic_v6` (v5 + the minting
  density norm) under the receipt protocol (#709) and the derived core.
- **v7 API — partial** — five canary runs (CHORUS ×2, AI_READI ×3) under
  `generic_v7` (v6 + the receipt rule); the fan-out of the remaining runs is
  deferred to 2026-08-31 after two nights of proxy stalls in the 02:00–10:00
  UTC window (#777). Every v7 number below is n=2 or n=3, and CM4AI and VOICE
  have none.

Comparisons are against **v5 API (2026-08-22c)** and **v5 agentic
(2026-08-24)**, both n=3 per project. Mean ± SD over replicates; the
replicate values are in `notes/arm_comparison.md`.

## 1. The receipt, as a measurement

The first thing the two arms establish is that coverage and support are
now *measured* rather than inferred:

| | v5 agentic | v6 agentic | v7 API (partial) |
|---|---|---|---|
| bundle chunks reviewed | ~80% of AI_READI/CM4AI/VOICE by transcript forensics (#700) | **100%**, 12/12, by receipt + transcript cross-check | 100% by construction (bundle in context; receipt 28/28, 8/8) |
| snippets verbatim in the bundle | not measured | **3,400 / 3,400** | 857 / 859: two non-verbatim (a garbled extraction span on 28b AI_READI, a paraphrase on 28c AI_READI) |
| snippets in the chunk cited | not measured | 3,400 / 3,400 | **96.2%** (824 of 857): 33 cite another chunk — 32 the neighbouring one, 1 elsewhere; 4.4% on AI_READI, 1.9% on CHORUS |
| slots receipted (of receiptable leaves) | — | 24–95% by run | 25–44% |

Reading: the agentic protocol — read a chunk, write its entry, move on —
produces exact attribution; the API arm, holding the whole bundle in one
context, mis-attributes ~4% of its quotes, nearly always to the chunk next
door (32 of 33). Support (is the text in the bundle at all) is essentially
perfect on both arms: two non-verbatim snippets in 4,259. The
receipted-slot fraction is similar across arms and low in both — a model
receipts the leaf it copied from, and sibling leaves of the same entry go
unreceipted. That is a reporting convention, not missing evidence, but it
means "slots with a receipt" is not yet a coverage-of-record number.

Everything the receipt cannot see is what the first `d4d-review-record`
review found on CHORUS v6 rep1 (66 items: 6 adverse — 2 verbatim snippets
that do not answer their slot, 1 inferred value, 3 rule violations). A
record every deterministic gate called clean carried them. That review is
one record; the arm-wide review pass is the next evaluation step.

## 2. Agentic v5 → v6: what the one rule and the protocol changed

| metric | v5 agentic | v6 agentic | reading |
|---|---|---|---|
| ungrounded identifiers | 0 on 12/12 | 0 on 12/12 | held |
| pair errors | 0 (derived core) | 0 | held by construction |
| minted fragments, VOICE | 49 ± 70 [3, 14, 130] | **13.7 ± 5.5 [19, 8, 14]** | the norm removed the 130 outlier; spread 127 → 11 |
| minted fragments, CM4AI | 49.3 ± 6.7 [42, 55, 51] | 39 ± 20.8 [51, 15, 51] | did not converge; two runs minted as before |
| minted fragments, AI_READI / CHORUS | 10.3 / 0 | 10.7 / 0 | unchanged |
| British spellings | ≤ 4 on every run | 0 on 10 runs, 2 on CM4AI rep2, **35** on VOICE rep2 | one outlier run; the arm is otherwise cleaner |
| undeclared prefixes | 0 | 2 on CM4AI rep1 (one `mailto:` URI) | one run |
| populated leaves, AI_READI | 641 ± 38 | 603 ± 57 | −6% |
| populated leaves, CHORUS | 287 ± 38 | **228 ± 46** | −21% |
| populated leaves, CM4AI | 928 ± 84 | **706 ± 191** | −24% |
| populated leaves, VOICE | 543 ± 94 | 546 ± 80 | unchanged |
| spend (Mtok, transcript) | 216.6 (389 min) | **378.8 (597 min)** | +75% tokens, +54% wall; CHORUS rep1's 138 min is the canary's launch-to-finish span, an outlier against 26–27 for its siblings |

Predictions of `notes/generic_v6_analysis_plan.md`: 2, 3, 6 held; 1 half
(VOICE yes, CM4AI no); 4 — which concerns the *API* arm's spelling against
v5's per-project worst (30/0/0/4) — held on the v7 canaries (AI_READI
25/9/21); the agentic VOICE rep2 outlier is not what it predicts.
**Prediction 5 —
populated slots should not fall — is the one to take seriously.** Leaves
fell by a fifth on CHORUS and CM4AI. Two candidate causes, and the arm
cannot separate them: the minting norm removed parts that were only
labelled (CM4AI minted 51/15/51 — the run that minted 15 is the one with
493 leaves against 765 and 860), and the receipt protocol makes every value
cost a verbatim quote, which discourages the inferred and restated values
v5 carried freely. One reviewed record (CHORUS v6 rep1) still carried
adverse items of that kind (an inferred `scope_impact`, an award period
standing in for a collection timeframe), which suggests — one record is
not evidence — that v5's extra leaves were partly such values. A per-slot
diff of a v5 and a v6 CHORUS record against the bundle would settle it and
is the right next review.

The cost is the protocol: a v6 run spends ~1.75× the tokens of a v5 run
(whole-run transcript totals; the reading share is not separated). It buys
the top table.

## 3. API v5 → v7 (partial): what the receipt rule changed

| metric | v5 API (22c) | v7 API canaries | reading |
|---|---|---|---|
| pair errors, AI_READI / CHORUS | 8.7 ± 8.3 / 1.0 ± 1.0 | **0 / 0** | the derived core (#694), a procedure change that landed between the arms |
| British spellings, AI_READI | 19 ± 18.5 | 18.3 ± 8.3 | unchanged; the v5 rule is not reaching AI_READI on either arm |
| minted, AI_READI | 9.0 ± 7.8 | 5.7 ± 6.4 | within spread |
| organisational fragments / resolver URLs | 0 | one run (28b) had 1 and 2; the re-canaries 0 | one-run noise, not systematic |
| populated leaves, AI_READI | 674 ± 124 | **522 ± 142** [446, 434, 685] | −23%, high variance |
| populated leaves, CHORUS | 242 ± 48 | 202 ± 10 | −16% |
| cost per run (CBORG rates), by project | AI_READI $18.2 / $15.2; CHORUS $5.2 / $4.7 / $6.0 (9 calls) | AI_READI $12.6 / $8.6 / $11.5; CHORUS $3.4 / $4.1 (6–7 calls) | the three generated core calls (core, reconcile_core, repair_core) are gone; 22c AI_READI rep2's usage is partial (repair calls only) and is excluded from the v5 figures |
| full-phase output, AI_READI | 55–74k | **72–96k** (thinking ~70% of it) | hit the 96k cap once; raised to 128k for receipt conditions (#768) |

The leaves fall on the API arm too. One candidate mechanism is measured
but its link to the fall is not: the `full` phase writes the record *and*
the receipt in one output budget that thinking already fills to 66–73%,
and AI_READI's first attempt truncated at the 96k cap. Whether the leaner
records are leaner in unsupported content (as the rules intend) or in
supported content (a budget effect) is, again, a per-slot question the
review agent can answer and the gate cannot.

## 4. Across the arms

With a receipt on both sides, the first like-for-like cross-arm statement
is possible: on the same bundles, under the same rules, **the agentic arm
quotes with exact attribution and the API arm with 96% attribution; both
quote verbatim; the agentic arm carries 15.6% more populated leaves on
AI_READI and 12.7% on CHORUS.** Spend is not comparable across arms
(transcript-observed tokens against metered API dollars, #400): the
agentic arm's 378.8 Mtok for 12 runs stands beside ~$8–13 per API run on
the same projects, and neither converts to the other. Report-claims
findings are 0ᵘ on nearly every run of every arm (#684): still unmeasured.

## 5. Rubric10-semantic (same evaluator, claude-fable-5; every replicate)

| project | v5 API (22c, canonical) | v5 agentic (24, canonical) | **v6 agentic** (3 reps) | **v7 API** canaries |
|---|---|---|---|---|
| AI_READI | 49/50 | 48/50 | **50, 48, 49** /50 | 49, 49, 49 /50 |
| CHORUS | 36/49 | 32/49 | **30, 26, 30** /49 | 32, 31 /49 |
| CM4AI | 47/50 | 47/50 | **39, 40, 42** /45 (Element 4 N/A: cell lines, no human subjects) | – |
| VOICE | 50/50 | 49/50 | **49, 47, 49** /50 | – |

Reading, with the caveat that the earlier arms show one selected record
each and the new arms all three:

- **AI_READI and VOICE are at the ceiling on every arm** (47–50/50); the
  points lost are the same two everywhere — `variables` absent, and no
  `software_and_tools` entry despite a linked GitHub organisation. Neither
  the receipt protocol nor the minting norm moved these.
- **CHORUS is where the arms differ, and the direction is down for v6
  agentic**: 30/26/30 against 32 (v5 agentic) and 36 (v5 API); the v7 API
  canaries sit at 32/31. Every evaluator names the same gaps — no persistent
  identifier, no IRB/consent basis for PICU/NICU patient data, no
  version/publisher/download URL — and every one of them is a gap *in the
  bundle*: CHORUS's sources do not state them. The v6 records lost points
  for declining to assert what the sources do not say; the v5 API record
  scored higher partly by asserting more (the review of v6 rep1 found its
  remaining adverse items to be exactly such assertions). On CHORUS the
  rubric rewards coverage the evidence cannot support, and the leaner v6
  record is the more faithful one.
- **CM4AI**: the v6 evaluations excluded Element 4 (human subjects) as
  not applicable — the record describes cell lines — where the v5
  evaluations scored it; 39–42/45 is 87–93%, against 94% for v5. The
  denominator moved, so the raw points are not comparable; the lost
  points are `variables`, `anomalies` and a related-dataset link.
- Rubric10 does not see the receipt at all: a 100% score (AI_READI v6
  rep1) and the CHORUS records with six adverse review items are scored
  by the same instrument on the same terms. Presence-and-quality and
  evidence-and-support are different axes, and the arm comparison now has
  both.

## 6. What is not here

- **Rubric20-semantic** for the new arms — running at the time of writing;
  `notes/arm_comparison.md` regenerates with it.
- **The arm-wide review pass** (`d4d-review-record` on all 12 v6 runs and the
  v7 canaries) — one record reviewed so far.
- **Canonical selection** for v6 (safe since #677) — after the review pass.
- The v7 arm's other 7 runs, and with them any v7 statement about CM4AI and
  VOICE.
