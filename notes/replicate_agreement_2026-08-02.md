# How much do replicates actually agree?

CHORUS, `2026-07-31_claude-opus-5-generic-v2_rep{1,2,3}`, 48 slots held by two
or more replicates. Reproduce with `src/data_sheets_schema/agreement.py`;
judgements and embeddings are cached under
`data/evaluation_llm/agreement_cache/`.

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

## What this changes for #169

The premise can now be measured, which it could not be before. Whether n=3
resolves anything depends on a quantity that is 37.5%, not 2%, and the next step
is to compute it for the other three projects and for a second config, so that
between-config differences can be compared against within-config spread.

Not done here: that is four more projects times two configs, and the point of
this note is that the instrument now exists and reads sensibly.
