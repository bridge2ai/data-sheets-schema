# Test–retest reliability of d4d-review-record (2026-09-01)

Every review in the 2026-08-30 pass was a single rating. This measures how
stable those ratings are: six records — stratified by observed adverse rate,
both arms — were independently re-reviewed against the **same committed
packs** (`{P}_review_b.yaml`; the second rater was forbidden to read the
first review), and `d4d review agree` paired the verdicts item by item.
Cohen's κ is computed on the collapsed affirmative/adverse/cannot_tell
trichotomy — the classes every downstream count uses; exact agreement is on
the full vocabulary. Reliability blocks live in each record's provenance
(`review.reliability`).

## Per record

| record | items | class agree | exact | κ | adverse A | adverse B |
|---|---|---|---|---|---|---|
| CHORUS v6 rep1 | 66 | 87.9% | 84.8% | 0.49 | 12 | 6 |
| CHORUS v6 rep2 | 66 | 84.8% | 84.8% | 0.36 | 9 | 9 |
| AI_READI v6 rep2 | 68 | 95.6% | 89.7% | 0.55 | 4 | 3 |
| AI_READI v6 rep3 | 68 | 91.2% | 89.7% | 0.65 | 13 | 7 |
| VOICE v6 rep2 | 66 | 92.4% | 86.4% | 0.63 | 10 | 5 |
| CHORUS v7 28 | 68 | 82.4% | 80.9% | 0.50 | 20 | 10 |

**Pooled: n = 402 paired items, class agreement 89.1%, κ = 0.534, bootstrap
95% CI [0.41, 0.65]** (percentile, seed 0, 2,000 draws over pooled items —
`scripts/review_reliability_stats.py` reproduces every number in this note;
the item bootstrap ignores record clustering, and with six records a
cluster CI is unstable — the by-record mean κ is 0.531). Zero `cannot_tell`
from either rater on any item.

## What agrees and what does not

Per kind (paired items, class agreement): chunk verdicts 10, **100%**;
receiptless slots 150, **93.3%** (nine inferred↔bundle_supports-family
splits and one inferred↔exempt); receipted slots 150, **88.0%**; rules 91,
**82.4%**; the one paired `slot_reshaped` item agreed (100%) — 402 in all. The disagreement is concentrated exactly where the investigation
predicted:

- **weak ↔ supported** (16 of the 18 receipted-slot disagreements; 13 in the
  A-weak→B-supported direction). The boundary "the snippet is verbatim but
  does it *answer* the slot" is the instrument's soft spot.
- **violated ↔ followed** (14 of 16 rule disagreements: 13 A→B and one
  the other way — AI_READI v6 rep2's rule-06, where the second rater was
  stricter). The remaining 2 are violated→not_applicable, which are not
  noise at all: the second raters applied the post-#853 `id_slots`
  reasoning to rule-14, which the originals predated. Instrument
  evolution, correctly reflected.
- Receiptless `inferred ↔ bundle_supports` splits nearly evenly (5 vs 4) —
  genuine judgment noise, no directional bias.

## The severity asymmetry, and its honest confound

The confusion matrix is lopsided: 36 items A called adverse and B called
affirmative, versus 8 the other way. Total adverse over the six records:
**A 68, B 40**. Two readings, not distinguishable from this design:

1. The original raters were systematically stricter (severity drift within
   one model);
2. **The second raters ran under a different instruction route** — a
   condensed prompt naming the task "test–retest reliability" rather than
   the full `d4d-review-record` agent file, which may itself induce
   leniency. This is a real design confound: rater identity and instruction
   route moved together. A third rating under the verbatim agent file would
   separate them; it was not run.

Either way the operational conclusion is the same and is the point of the
measurement:

## Consequences

- **Adverse rates carry rater noise of roughly a factor of up to 2 on
  high-adverse records** (CHORUS v7 28: 30% → 15%). Single-rating adverse
  rates separate records only when they differ by well over the ±5pp
  sampling noise *and* this rater band — in practice: 4% vs 18% still
  separates; 9 vs 12 does not, and the cross-read's within-project
  correlations (n=3–6, built on single ratings) should be read with this
  on top of their stated caveats.
- **κ ≈ 0.53 sits in the pre-registered "usable with error bars" band
  (0.5–0.7)**: per the plan, the adverse rate may join reporting and
  coarse comparisons but should **not** become a canonical-selection
  criterion or gate (#660) without adjudication — the pre-registered
  κ ≥ 0.6 bar is not met.
- **What is stable**: chunk coverage verdicts (100%), the substantive core
  findings (both raters independently found the CTP-deid repo-name
  laundering, the award-period timeframe inference, rule-14's unforced
  fragments, rule-15's receiptless bundle values, the PI-role inflation),
  and the *direction* of every arm-level contrast. What is unstable is the
  tail of borderline `weak` receipts and rule readings.
- **Adjudication is the cheap next step**: 44 class disagreements total,
  concentrated in two boundary types. A human ruling on those (or even a
  written sharpening of "weak" — e.g. *weak = the cited passage alone would
  not let a reader reconstruct the value's claim*) would both settle the six
  records and raise future κ.
- The rep3 second rater also exposed **#859**: the British-spelling word
  list misses metre/tumour/oedema, so form counts undercount corpus-wide.

## Adjudication (2026-09-01, cross-vendor)

All 44 disagreements were adjudicated by a third rater — **which turned
out to be claude-sonnet-5, not Codex**: the agent tasked with forwarding
to Codex executed the adjudication itself and disclosed this only after
the blocks were first recorded (they have been corrected). So this is a
same-family third rating, not the intended cross-vendor one; its distinct
value is that it verified against the bundles and the schema directly,
deciding several items on grounds neither rater used. A genuine
cross-vendor ruling is tracked separately. Full rulings:
`notes/adjudication_rulings_2026-09-01.md`; the case file the adjudicator
was shown is `notes/adjudication_sheet_2026-09-01.md`, whose sha256 each
block pins as `instruction_sha256`; per-item outcomes sit in each
record's `review.reliability.adjudication` block.

**Rater A upheld 24, rater B 19, neither 1** — so the severity asymmetry
was mostly *justified* strictness: the original ratings were right on a
small majority of contested items, and the adverse totals move toward A's.
The adjudicator also settled the two boundary policies (§rulings file):
judge receipts against the cited *chunk*, not the pull-quote anchor;
"tool exists in the repo" never supports "tool was applied to this data";
rule-06 bites only on pointer-dodges, never on a source's own stated
absence; and the PI-conflation family across two projects is settled by a
bundle sentence both raters missed ("Bensoussan and Elemento are
co-principal investigators" vs ten named "lead investigators"). Two
schema-grounded reversals (items 17, 21/27) show a class of dispute that
is resolvable mechanically — the pack's `id_slots` block (#853) already
carries one of them for future reviews.

## Method notes

Second ratings: the same model, fresh context — so this measures rating
stability, not model-independence; the instruction-confound paragraph above
rests on this session's records, not on committed artifacts (the review_b
files carry only reviewer and model fields — #863 tracks recording the
instruction hash). Committed v2 packs (no
regeneration — hashes intact), one file written per record, originals never
opened. `d4d review agree` refuses reviews that pin different pack hashes;
κ is None (not 0) when marginals make chance agreement 1. The six records:
AI_READI v6 rep2/rep3, CHORUS v6 rep1/rep2, VOICE v6 rep2, CHORUS v7 28 —
chosen to span 2%→30% observed adverse before any second rating existed.
