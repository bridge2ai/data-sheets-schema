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
| judge input cap | 100,000 chars/value — above the corpus maximum of 29,024, so nothing is truncated (was 4000; see #244) |
| embeddings | `lbl/nomic-embed-text` via CBORG, capped at 8000 chars by the model's 8192-token input limit |
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

**A gap of 0.008.** The measure cannot separate the two classes. Everything
scores ~0.92 because every value is schema-shaped prose about the same dataset,
so the embedding captures topic rather than assertion — and topic is held
constant by construction here.

This was worth establishing rather than assuming: the plan was to calibrate the
cheap measure against the judge and then use the cheap one at scale. That is not
available. Judged equivalence has to be paid for.

Sanity check that the embeddings themselves are fine: on a hand-built pair they
score 0.865 for a paraphrase against 0.564 for unrelated text. The failure is
specific to this population, not the model.

### The endpoint also truncates at 2048 tokens, and does not say so

Found while fixing #251, and independent of the topic-collapse result above.

`lbl/nomic-embed-text` through CBORG accepts a 30,000-character input, returns
**HTTP 200**, and reports `prompt_tokens: 2048`. Everything past that is
discarded silently. nomic-embed-text is documented at 8192 tokens; this endpoint
is not that, which is why the number here is measured rather than cited.

The consequence is not a slightly worse number, it is a maximally wrong one:

| | cosine |
|---|---|
| two values contradicting each other **past** the ceiling | **1.000000** (byte-identical vectors) |
| the same contradiction, short enough to fit | 0.843 |

So the endpoint will report perfect agreement between two values that contradict
each other, provided the contradiction is late enough.

**The published table is unaffected.** The only cell ever embedded is CHORUS v2,
whose longest value is 2,876 characters — roughly 719 tokens, about a third of
the ceiling. Verified live: at the 8000-character client cap the endpoint
returns a genuine vector for the corpus's longest value; raised to 40,000 it
truncates and the client now refuses.

Across the whole corpus 17 of 1619 values would exceed the ceiling. None are
cached, because none are in CHORUS v2 — so this is a trap for reviving the
measure, not a defect in the result reported here. A character cap cannot fix
it, since characters per token vary with the text; what the client can do is
read `usage.prompt_tokens` back and refuse to build a cosine on a prefix, which
is what it now does.

## Cost

44 judge calls and 127 embeddings for one project's three replicates. One call
per slot, not per pair. At that rate the four projects cost roughly 180 judge
calls per config — affordable for a decision, not for a hot path.

## What the judge did not see, and what changed when it did

The first version of this measurement cut every value to 4000 characters before
the judge saw it. A cut can only hide a disagreement that lives past it, so a
truncated slot is biased towards "equivalent" — and the exposure was
**asymmetric between the two configurations being compared**: 21 affected slots
in v1 against 9 in v2. Across all eight project-configs, 59 of 1576 rendered
values (3.7%) exceeded the cap, over 30 of 540 shared slots (5.6%); the longest
value ran to 29,024 characters, of which the judge saw 14%.

The cap is now 100,000 characters and nothing in the corpus reaches it. Those 30
slots were re-judged on their full text (issue #244).

**Nine verdicts changed, every one of them from "equivalent" to "different".**
Not one moved the other way. That is the direction truncation predicts — the cut
was hiding disagreement, exactly as claimed, and never manufacturing it.

| | published (4000-char cap) | corrected (full text) |
|---|---|---|
| pooled rate | 270/540 = 50.0% | **261/540 = 48.3%** |
| mean v1 | 51.1% | 49.6% |
| mean v2 | 48.1% | 46.7% |
| **mean delta** | **−3.1** | **−2.9** |
| sd of per-project deltas | 10.85 | 10.86 |

Per project, the affected cells:

| cell | published | corrected | slots re-judged |
|---|---|---|---|
| v1 AI_READI | 62.0% | 58.2% | 6 |
| v1 VOICE | 39.7% | 37.2% | 9 |
| v1 CM4AI | 48.4% | 48.4% | 5 (no verdict changed) |
| v1 CHORUS | 54.5% | 54.5% | 1 (no verdict changed) |
| v2 AI_READI | 55.7% | 52.9% | 4 |
| v2 CM4AI | 52.9% | 51.4% | 3 |
| v2 VOICE | 46.2% | 44.9% | 2 |
| v2 CHORUS | 37.5% | 37.5% | 0 — unaffected |

The CHORUS section above therefore stands unchanged: none of its v2 slots were
ever truncated, so 18/48 = 37.5% and the embedding table were measured on full
text all along.

**The conclusion is unchanged**, and the pre-registered bound held: the
worst-case estimate made before re-judging (delta −1.9, assuming every cut hid a
real disagreement) bracketed the true value of −2.9 against the published −3.1.
The correction moved the effect by 0.2 points and the noise not at all.

A caveat this does *not* remove: it was the same judge model, at a cap wide
enough to see everything, but still the model family that generated the records.
Fixing what the judge could see does not make it a disinterested reader.

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
| AI_READI | 58.2% | 52.9% | −5.4 |
| CHORUS | 54.5% | 37.5% | −17.0 |
| CM4AI | 48.4% | 51.4% | +3.0 |
| VOICE | 37.2% | 44.9% | +7.7 |
| **mean** | **49.6%** | **46.7%** | **−2.9** |

## #169 is confirmed, on evidence

| quantity | value |
|---|---|
| between-config effect | **−2.9** points |
| within-config spread across projects | 21.0 (v1), 15.4 (v2) points |
| sd of the four per-project deltas | **10.9** points |
| deltas agreeing in sign | **no** — −5.4, −17.0, +3.0, +7.7 |

The effect is roughly a quarter of the noise, and the per-project deltas do not
agree in sign: two projects go up, two go down. With four projects the standard
error of the mean delta is 10.9/√4 ≈ 5.4, so a 2.9-point difference is not
distinguishable from zero.

Detecting an effect this size against this spread would need on the order of 110
projects. There are four. **The design cannot resolve differences in replicate
agreement between prompt configurations, and no number of replicates fixes that
— the variance is between projects, not within them.**

## What this does not say

It does not say v2 failed. The registered v2 experiment was about *fitness*
failures, and there the effect was large and consistent: 131 → 87 defective
fields, falling in all four projects, with the targeted defect all but
eliminated — **42 → 7**, −83% (`notes/generic_v2_results.md`; the classifier
figure, folding `both` into each named subtype). This note originally read
"eliminated 27 → 0", the manual read the classifier superseded the following
day; the substantive point is unchanged and the direction is the same (#461).

So the two quantities behave differently. Fitness moved enough to measure with
four projects; agreement did not. That is worth stating precisely, because "the
design is underpowered" is true of this quantity and false of that one.

## Consequence for the study

Report agreement as a descriptive property of a configuration — roughly half of
shared slots state the same fact, varying by project from 37% to 58% — and stop
treating differences between configurations in it as findings. Where an effect
must be resolved, use a measure with a larger effect-to-noise ratio; fitness is
the one already demonstrated to have it.

Cost: 464 judge calls across eight project-configs — 434 for the original matrix
and 30 to re-judge the truncated slots on their full text. All cached; re-running
the matrix from that cache is free and is exercised by the test suite.

## Known limits

- **#244 — fixed.** The 4000-character cap is gone and the affected slots were
  re-judged; what it cost is quantified above. Worth recording *how* it nearly
  survived being fixed: the cache keyed verdicts on the full values rather than
  on the truncated text actually sent, so raising the cap would have re-served
  every stale verdict and the correction would have shown a change of exactly
  zero. The key now hashes what the judge saw.

Filed rather than fixed, so they are on the record either way:

- **#242** — the cache key for the 434 original verdicts had no separator
  between the slot name and the values, so distinct inputs could collide. The
  scheme is fixed going forward; the surviving records are frozen and read
  through the legacy index rather than re-bought.
- **#243** — those same records do not carry the judge model. It is recovered
  above from the run configuration, not from the cache. The 30 re-judged records
  do carry it, along with the cap they were judged under.
- **#247 — kept, and the reasons first given for both keeping and worrying
  about it were wrong.** The file is 1.4 MB in the working tree but 587 KB
  packed, which is 0.017% of this repository's 3.25 GiB of objects and does not
  appear in its fifteen largest blobs. It is also already in history, so
  deleting it from HEAD would reclaim exactly nothing — only a history rewrite
  would, which is not a thing to do to a shared `main` over half a megabyte.
  And it is *not* what makes the negative result reproducible: the 0.923 /
  0.914 table recomputes from the 24 KB `CHORUS_v2_rows.json`, with no vectors
  involved. That table is now asserted by the test suite rather than left to be
  re-derived. What remains real is growth — embedding the whole corpus would be
  1439 vectors rather than 136, about 14 MB, tracked permanently — so a test
  bounds the count and makes that a decision instead of a side effect.
- **#251 — fixed.** Vectors are keyed on the text sent rather than the value it
  came from, mirroring #244, and the client now reads `usage.prompt_tokens` back
  and refuses to build a cosine on a prefix. Nothing was orphaned: no cached
  vector was ever truncated, so every key was already the key of what was sent.
  The reason originally given for deferring this — that fixing it would orphan
  the cache — was simply wrong, and checking cost less than the sentence
  asserting it.
- **Not filed, but true**: the judge is the same model family that wrote the
  records. See the provenance section.
