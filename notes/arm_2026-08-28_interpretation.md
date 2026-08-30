# What the 2026-08-28 arms say: agentic v6 (complete) and API v7 (partial)

Written 2026-08-30 from `notes/arm_comparison.md` (regenerated), the run
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
| snippets verbatim in the bundle | not measured | **3,400 / 3,400** | 1 non-verbatim in 809 (a paraphrase, 28c AI_READI) |
| snippets in the chunk cited | not measured | 3,400 / 3,400 | **~96%**: 9.7 ± 2.1 of ~220 on AI_READI and 2 of ~105 on CHORUS cite the neighbouring chunk |
| slots receipted (of receiptable leaves) | — | 45–95% by run | 40–70% |

Reading: the agentic protocol — read a chunk, write its entry, move on —
produces exact attribution; the API arm, holding the whole bundle in one
context, mis-attributes ~3–4% of its quotes to the chunk next door, always
at or near a boundary. Support (is the text in the bundle at all) is
essentially perfect on both arms: one paraphrase in 4,209 snippets. The
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
| British spellings | ≤ 4 on every run | 0 on 11 runs, **35** on VOICE rep2 | one outlier run; the arm is otherwise cleaner |
| undeclared prefixes | 0 | 2 on CM4AI rep1 (one `mailto:` URI) | one run |
| populated leaves, AI_READI | 641 ± 38 | 603 ± 57 | −6% |
| populated leaves, CHORUS | 287 ± 38 | **228 ± 46** | −21% |
| populated leaves, CM4AI | 928 ± 84 | **706 ± 191** | −24% |
| populated leaves, VOICE | 543 ± 94 | 546 ± 80 | unchanged |
| spend (Mtok, transcript) | 216.6 (388 min) | **378.7 (599 min)** | +75% tokens, +54% wall |

Predictions of `notes/generic_v6_analysis_plan.md`: 2, 3, 6 held; 1 half
(VOICE yes, CM4AI no); 4 falsified once (VOICE rep2). **Prediction 5 —
populated slots should not fall — is the one to take seriously.** Leaves
fell by a fifth on CHORUS and CM4AI. Two candidate causes, and the arm
cannot separate them: the minting norm removed parts that were only
labelled (CM4AI minted 51/15/51 — the run that minted 15 is the one with
493 leaves against 765 and 860), and the receipt protocol makes every value
cost a verbatim quote, which discourages the inferred and restated values
v5 carried freely. The CHORUS review's adverse items (inferred
`scope_impact`, award period standing in for a collection timeframe) are
exactly the kind of value that v5 had more of and v6 still has some of; on
this evidence the fall is at least partly the removal of content the rules
never allowed, not a loss of support. A per-slot diff of a v5 and a v6 CHORUS
record against the bundle would settle it and is the right next review.

The cost is the protocol: reading 28 chunks one call at a time and writing
28 receipt entries is ~1.75× the tokens of v5's reading. It buys the top
table.

## 3. API v5 → v7 (partial): what the receipt rule changed

| metric | v5 API (22c) | v7 API canaries | reading |
|---|---|---|---|
| pair errors, AI_READI / CHORUS | 8.7 ± 8.3 / 1.0 ± 1.0 | **0 / 0** | the derived core (#694), a procedure change that landed between the arms |
| British spellings, AI_READI | 19 ± 18.5 | 18.3 ± 8.3 | unchanged; the v5 rule is not reaching AI_READI on either arm |
| minted, AI_READI | 9.0 ± 7.8 | 5.7 ± 6.4 | within spread |
| organisational fragments / resolver URLs | 0 | one run (28b) had 1 and 2; the re-canaries 0 | one-run noise, not systematic |
| populated leaves, AI_READI | 674 ± 124 | **522 ± 142** [446, 434, 685] | −23%, high variance |
| populated leaves, CHORUS | 242 ± 48 | 202 ± 10 | −16% |
| cost per run (CBORG rates) | $11.2 mean (9 calls) | **$8.0** (6–7 calls) | the two generated core phases are gone; the receipt adds ~9k output tokens |
| full-phase output, AI_READI | 55–74k | **72–96k** (thinking ~70% of it) | hit the 96k cap once; raised to 128k for receipt conditions (#768) |

The leaves fall on the API arm too, and the mechanism there is visible in
the token accounting: the `full` phase writes the record *and* the receipt
in one output budget that thinking already fills to ~70%, and AI_READI's
first attempt truncated at the cap. Whether the leaner records are leaner
in unsupported content (as the rules intend) or in supported content (a
budget effect) is, again, a per-slot question the review agent can answer
and the gate cannot.

## 4. Across the arms

With a receipt on both sides, the first like-for-like cross-arm statement
is possible: on the same bundles, under the same rules, **the agentic arm
quotes with exact attribution and the API arm with ~96% attribution; both
quote verbatim; the agentic arm carries ~15% more populated leaves on
AI_READI and ~13% on CHORUS, at roughly 5× the token spend** (378.7 Mtok
subscription tokens for 12 runs against ~$8 × 12 ≈ $96 of metered API
spend — different quantities, not a cost comparison, #400). Report-claims
findings are 0ᵘ on nearly every run of every arm (#684): still unmeasured.

## 5. What is not here

- **Rubric10/rubric20-semantic scores** for the new arms: the evaluator
  subagents hit the account's weekly limit on 2026-08-30 (resets 2026-09-01);
  `notes/arm_comparison.md` shows the rubric rows for v4/v5 only. To be run
  with the fan-out.
- **The arm-wide review pass** (`d4d-review-record` on all 12 v6 runs and the
  v7 canaries) — one record reviewed so far.
- **Canonical selection** for v6 (safe since #677) — after the review pass.
- The v7 arm's other 7 runs, and with them any v7 statement about CM4AI and
  VOICE.
