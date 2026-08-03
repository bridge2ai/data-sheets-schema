# Does the effort tier change replicate agreement?

Run 2026-08-02 to test whether the `-high` suffix — this model family's sampling
control, since `temperature` is deprecated for it — explains the replicate
disagreement reported in #229 and assumed by #169.

## Design

CHORUS, baseline arm, `generic_v2` prompt, three replicates each.

**Not everything was held constant, and this was missed until review (#239).**
The `-high` replicates ran on 2026-07-31, *before* #220 merged; at that point
v2's `{DATE}` placeholder was not substituted, so the literal string `{DATE}`
reached the model. The bare replicates ran after, and received a real date:

    -high  # Generated: 2026-07-31   <- the model inferred it from {LABEL}
    bare   # Generated: 2026-08-03   <- substituted by resolve_prompt

Same prompt *file* in both arms (`4780613475ef2a62`), different resolved text.
The `-high` runs carry no `prompts.resolved` hash at all, because that field did
not exist until #220 — which is the marker for any arm generated before it.

One header line in ~4,400 characters is unlikely to move slot-level agreement,
but "unlikely" is not "held constant", and it compounds with the measurement
problem below: a confounded design on top of a saturated metric establishes
nothing in either direction.

| arm | model route | label |
|---|---|---|
| existing | `google/claude-opus-5-high` | `2026-07-31_claude-opus-5-generic-v2_rep{1,2,3}` |
| new | `google/claude-opus-5` | `2026-08-02_claude-opus-5-bare_rep{1,2,3}` |

Only two opus-5 routes exist on CBORG — bare and `-high`. The `-low`,
`-medium`, `-xhigh` and `-max` tiers return 400 *Invalid model*; they exist for
`sonnet-5`, `opus-4-7` and `opus-4-8`, but not for opus-5. So this is the whole
available gradient for this model, not a sample of it.

## Result

| arm | slot counts | shared slots | identical values | rate |
|---|---|---|---|---|
| `-high` | 47, 49, 50 | 48 | 1 | 2.1% |
| bare | 45, 49, 50 | 49 | 2 | 4.1% |

## The experiment is uninformative, not negative

The difference is one slot. Splitting by value shape shows why that cannot be
read as "no effect":

| arm | scalar slots | list/dict slots |
|---|---|---|
| `-high` | 1/9 agree (11%) | **0/39 (0%)** |
| bare | 2/9 agree (22%) | **0/40 (0%)** |

**Zero of ~40 object-valued slots agree in either arm.** The measure is
saturated: exact equality over nested objects carrying free-text descriptions
essentially never holds, so it cannot register a change in either direction. The
only place it has resolution is 9 scalar slots, where 1 against 2 at n=3 is
noise.

So this says nothing about whether the effort tier matters. It says the
instrument cannot answer the question as posed — and the design would not have
supported a clean answer even with a working instrument (#239).

## What this corrects

The figure "replicates disagree on 77-98% of the slots they share" (#229, and
repeated in #176 and #236) is **exact string equality on prose-bearing
objects**. Two records that describe the same collection method in different
words count as disagreeing. That number is therefore an upper bound on
disagreement and a poor estimate of the substantive kind.

It was sound for the purpose it was computed for — showing a coverage merge
cannot adjudicate values, which remains true, since a merge must pick bytes and
the bytes do differ. It is not sound as evidence that the generator is unstable,
and #169's premise rests on the second reading.

## What to do instead

Measuring semantic agreement needs a comparison that survives rewording:

1. **Scalar-only agreement** as a free floor — already computed here, and it is
   the only part of the current metric with any resolution.
2. **Field-level judged equivalence** — ask whether two values state the same
   fact, the way `evidence_score.py` already judges fitness per field. Costs
   API calls, but on the axis that matters.
3. **Presence-and-shape agreement** — do replicates populate the same slots with
   the same cardinality, ignoring wording. Free, and closer to what a datasheet
   reader cares about than byte identity.

Until one of those exists, "how much do replicates really differ" is unanswered,
and n=3 cannot be judged adequate or inadequate.

## Cost

Six runs total, three of them new. ~35 minutes. The negative-looking result was
worth having: it cost little and it caught a measurement problem that three open
issues were building on.

Not re-run to remove the prompt confound. The result is already uninformative
for the metric reason, so three more runs would buy a cleaner version of an
experiment that still cannot answer the question. When the metric is replaced
with one that has resolution, re-run with both arms on the current prompt
resolution.
