# How much do replicates actually agree?

CHORUS, `2026-07-31_claude-opus-5-generic-v2_rep{1,2,3}`, 48 slots held by two
or more replicates.

## Provenance

| | |
|---|---|
| records | `data/d4d_concatenated/claudecode_agent/{LABEL}_rep{1,2,3}/{PROJECT}_d4d.yaml` |
| | the **full** records, not `_core` — on CHORUS the core records share 43 slots, not 48 |
| slot | a top-level key of the record, held by ≥2 replicates |
| judge | `google/claude-opus-5-high` via CBORG, rubric `EQUIVALENCE_SYSTEM` |
| embeddings | `lbl/nomic-embed-text` via CBORG |
| cache | `data/evaluation_llm/agreement_cache/` |

Rebuild every figure below from the cache, without making a paid call:

```bash
python -m data_sheets_schema.agreement --offline --embed --write
```

`--offline` raises on a cache miss rather than billing, so the command either
reproduces the published numbers or fails. `tests/test_agreement.py` asserts
that it does reproduce them.

**The judge is the same model family that generated the records.** That is not
neutral — a generator is the reader most likely to find its own two phrasings
equivalent — and no independent judge was run to bound the effect. Read the
rates as "how consistent does this model consider itself", which is still the
right quantity for #169's question about resolving power, but is not the same as
inter-rater agreement against a disinterested reader.

| measure | agreeing slots | rate |
|---|---|---|
| exact byte equality | 1 / 48 | 2.1% |
| **judged equivalent** | **18 / 48** | **37.5%** |
| mean embedding similarity | — | 0.918 |

## The headline number was wrong by about 18×

"Replicates disagree on 77-98% of the slots they share" (#229, repeated in
#176, #236, #238) is byte equality. Judged on whether the values *state the
same fact*, replicates agree on **37.5%** of shared slots, not 2%.

`title` is the clean example: three different strings, judged equivalent —
"all three name the same CHoRUS dataset, differing only in phrasing". Byte
equality counted that as disagreement.

So the generator is substantially more stable than the figure implied. It is
still not stable — 62% of shared slots do carry different facts, which is a
real result rather than an artifact.

## Embedding similarity does not work as a proxy

| slots | mean cosine |
|---|---|
| judged equivalent (n=18) | 0.923 |
| judged different (n=30) | 0.914 |

**A gap of 0.009.** The measure cannot separate the two classes. Everything
scores ~0.92 because every value is schema-shaped prose about the same dataset,
so the embedding captures topic rather than assertion — and topic is held
constant by construction here.

This was worth establishing rather than assuming: the plan was to calibrate the
cheap measure against the judge and then use the cheap one at scale. That is not
available. Judged equivalence has to be paid for.

Sanity check that the embeddings themselves are fine: on a hand-built pair they
score 0.865 for a paraphrase against 0.564 for unrelated text. The failure is
specific to this population, not the model.

## Cost

44 judge calls and 127 embeddings for one project's three replicates. One call
per slot, not per pair. At that rate the four projects cost roughly 180 judge
calls per config — affordable for a decision, not for a hot path.

## What the judge did not see

Values are cut to 4000 characters before reaching the judge (8000 for the
embedder). A cut can only hide a disagreement that lives past it, so a truncated
slot is biased towards "equivalent".

This is live in the matrix below, not hypothetical, and it is **asymmetric
between the two configurations being compared**:

| | v1 | v2 |
|---|---|---|
| shared slots with ≥1 truncated value | 21 / 274 | 9 / 266 |
| of those, judged equivalent | 9 (43%) | 8 (89%) |

Across all eight project-configs: 59 of 1576 rendered values (3.7%) exceeded the
cap, over 30 of 540 shared slots (5.6%); the longest value was 29,024 characters,
of which the judge saw 14%.

**The conclusion survives it.** Flipping every truncated-and-equivalent verdict
to "different" — the worst case, assuming the cut hid a real disagreement every
single time — moves the pooled rates from 51.1% / 48.9% to 47.8% / 45.9%. The
delta goes from −2.2 to −1.9, which is still a fraction of the ±10.9-point
between-project spread that the argument below turns on. The bias also runs
against v2, so correcting it would shrink the reported effect rather than
rescue it.

`truncated` is now recorded per slot in `{PROJECT}_{v1,v2}_rows.json`. Issue
#244 tracks removing the cap.

## What this changes for #169

The premise can now be measured, which it could not be before. Whether n=3
resolves anything depends on a quantity that is 37.5%, not 2%, and the next step
is to compute it for the other three projects and for a second config, so that
between-config differences can be compared against within-config spread.

Not done here: that is four more projects times two configs, and the point of
this note is that the instrument now exists and reads sensibly.

## The full matrix: v1 against v2, four projects

Judged equivalence, three replicates each, one judge call per shared slot.

| project | v1 (2026-07-28) | v2 (2026-07-31) | delta |
|---|---|---|---|
| AI_READI | 62.0% | 55.7% | −6.3 |
| CHORUS | 54.5% | 37.5% | −17.0 |
| CM4AI | 48.4% | 52.9% | +4.5 |
| VOICE | 39.7% | 46.2% | +6.5 |
| **mean** | **51.2%** | **48.1%** | **−3.1** |

## #169 is confirmed, on evidence

| quantity | value |
|---|---|
| between-config effect | **−3.1** points |
| within-config spread across projects | 22.3 (v1), 18.2 (v2) points |
| sd of the four per-project deltas | **10.9** points |
| deltas agreeing in sign | **no** — −6.3, −17.0, +4.5, +6.5 |

The effect is a third of the noise, and the per-project deltas do not agree in
sign: two projects go up, two go down. With four projects the standard error of
the mean delta is 10.9/√4 ≈ 5.5, so a 3.1-point difference is not distinguishable
from zero.

Detecting an effect this size against this spread would need on the order of 100
projects. There are four. **The design cannot resolve differences in replicate
agreement between prompt configurations, and no number of replicates fixes that
— the variance is between projects, not within them.**

## What this does not say

It does not say v2 failed. The registered v2 experiment was about *fitness*
failures, and there the effect was large and consistent: 131 → 87 defective
fields, falling in all four projects, with the targeted defect eliminated 27 → 0
(`notes/generic_v2_results.md`).

So the two quantities behave differently. Fitness moved enough to measure with
four projects; agreement did not. That is worth stating precisely, because "the
design is underpowered" is true of this quantity and false of that one.

## Consequence for the study

Report agreement as a descriptive property of a configuration — roughly half of
shared slots state the same fact, varying by project from 38% to 62% — and stop
treating differences between configurations in it as findings. Where an effect
must be resolved, use a measure with a larger effect-to-noise ratio; fitness is
the one already demonstrated to have it.

Cost: 434 judge calls across eight project-configs, cached. Re-running the
matrix from that cache is free and is exercised by the test suite.

## Known limits

Filed rather than fixed here, so they are on the record either way:

- **#242** — the cache key for the 434 published verdicts had no separator
  between the slot name and the values, so distinct inputs could collide. The
  scheme is fixed going forward; the published records are frozen and read
  through the legacy index rather than re-bought.
- **#243** — those same records do not carry the judge model. It is recovered
  above from the run configuration, not from the cache.
- **#244** — the 4000-character cap, quantified above.
- **#247** — `embeddings.jsonl` is 1.4 MB of vectors for a proxy this note
  concludes does not work. Kept, because it is what makes `--offline --embed`
  reproduce the 0.923 / 0.914 table rather than print nulls.
