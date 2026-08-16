# generic v5 — a production run, and what it can honestly be compared against

**v5 is a production run, not an experiment.** Decided 2026-08-15. The goal is
the best records the pipeline can currently produce. Comparisons against v4 are
made where the records support them and reported with their confounds, rather
than presented as an isolating measurement.

That decision is what #576 resolves. It is not a workaround: an isolating v4-v5
comparison was never available, and the honest options were to regenerate both
arms at one digest or to stop claiming it. This is the second.

Written 2026-08-14, before any v5 generation. Its purpose is to hold the
predictions **out** of the prompt: a prompt that states the result a run is
meant to test instructs the model to produce it.

## What v5 changes

Four rules, in one block. This breaks the one-rule-per-version convention that
v2, v3 and v4 kept, and the cost is stated rather than hidden: **a v4-against-v5
comparison measures the whole block and cannot attribute any effect to a rule
within it.**

Two of the four are not new instructions. American English (#502) and CURIE form
were added to `.claude/commands/d4d-full-core.md` mid-arm, deliberately, to
avoid rotating a pin while runs were in flight. They have reached the agentic
path since and the API path never (#545). Bringing them into the condition
prompt is a parity fix, and their expected effect on the agentic arm is nil by
construction — that arm has been reading them all along.

The other two are new and are one subject: where an identifier may come from
(#547) and what to write when the evidence supplies none (#531).

## What v5 can and cannot be compared against

`d4d runs compare-arms --a <v5 prefix> --b <v4 prefix>` reads what the records
state rather than reasoning from condition names, and prints every field that
differs. Against the 2026-08-13 v4 arm the differences are already known:

| field | v4 | v5 |
|---|---|---|
| schema digest | `622e6d03` | `44d29023` |
| assembly digest | `77331f08` | `2c1442fc` |
| condition | `generic_v4` | `generic_v5` |

So a v4-v5 difference measures **the four v5 rules, plus a schema change, plus
`reconcile_full` gaining the core record and the audit gaining a clause**.
`comparable_conditions('generic_v4', 'generic_v5')` now returns False, and
`MULTI_RULE_BASES` records why: a step that adds four rules cannot have a
difference attributed to one of them.

### What is still worth comparing

Quantities that are **counts of a defect**, not measurements of an effect size.
Each is a property of a record on its own, so a schema change between the arms
does not invalidate it — it only means the two arms are not a controlled pair:

- ungrounded external identifiers (v4: 19 in VOICE rep1, 10 in CM4AI rep3)
- person fragments on organisational identifiers (v4: 7 in VOICE rep1)
- undeclared CURIE prefixes and URL-valued identifier slots
- British spellings in generated prose
- full/core pair divergence (v4: 11 of 12)
- report claims contradicted by the record (v4: 19 findings)

If v5 shows fewer, that is worth stating as *what the current pipeline
produces* — not as evidence that a particular rule caused it.

### What is not worth comparing

Anything whose value depends on the schema: slot counts, density, coverage
against the inventory, and any per-slot presence rate. The digest moved, so
those are not like-for-like and no caveat repairs them.

## Predictions

Stated so they can be wrong.

1. **Ungrounded external identifiers fall toward zero on the API arm.** The
   measurement exists: `grounding.absent`, distinct per pair, now recorded by
   every run and backfilled across the corpus (#552). The v4 baseline is 19 in
   VOICE rep1 and 10 in CM4AI rep3, 0 in the other ten records.
2. **Minted-fragment counts rise, or hold.** Rule three redirects invention
   rather than forbidding it. If `absent` falls while `minted_fragment` does not
   rise, the model is omitting identifiers rather than anchoring them — a
   different outcome from the intended one, and not obviously worse, but it must
   not be reported as the intended one.
3. **Organisational identifiers carry no person fragments.** v4 baseline: 7
   distinct in VOICE rep1, 0 elsewhere.
4. **The invented-prefix population stops growing.** ~12,000 values across the
   corpus today (#531), five spellings for the VOICE namespace alone. v5 records
   should add none; existing records are not rewritten (#520).
5. **British spellings fall on the API arm and are unchanged on the agentic
   arm.** This is the parity fix's own test. If the agentic arm moves, something
   other than the rule moved with it.

## Measured v4 baselines

Produced by `poetry run python scripts/v5_baselines.py`, committed so the v5
figures are produced the same way. **Three of these were wrong or undefined in
the first version** (#577), which is why the script exists rather than an ad-hoc
pass.

| project | rep | grounded | minted | absent | org-frag |
|---|---|---|---|---|---|
| AI_READI | 1 | 27 | 17 | 0 | 0 |
| AI_READI | 2 | 10 | **14** | 0 | 0 |
| AI_READI | 3 | 10 | **13** | 0 | 0 |
| CHORUS | 1–3 | 0 | 0 | 0 | 0 |
| CM4AI | 1 | 9 | 12 | 0 | 0 |
| CM4AI | 2 | 2 | 0 | 0 | 0 |
| CM4AI | 3 | 40 | 0 | **10** | 0 |
| VOICE | 1 | 5 | 0 | **19** | **7** |
| VOICE | 2 | 2 | 0 | 0 | 0 |
| VOICE | 3 | 2 | 14 | 0 | 0 |

| corpus-wide | |
|---|---|
| undeclared CURIE prefixes (occurrences) | **370** — `chorus:` 226, `cm4ai:` 86, `urn:` 41, `ark:` 9, `nih:` 8 |
| URL-valued identifier slots | **397** — VOICE 330, CHORUS 40, AI_READI 21, CM4AI 6 |
| British spellings in generated prose | **613** — `licence` 199, `analyse` 85, `organisation` 81 |
| full/core pairs diverging on content | 11 of 12 |

### The counting rules, stated so the v5 figure matches

- **Distinct per record pair, not per occurrence.** Every identifier appears in
  both records, so an occurrence count is exactly double and reads as twice the
  problem (#556).
- **"Undeclared" means the schema's `prefixes:` block does not declare it.**
  `urn:` and `ark:` are counted here. Classifying them instead as no-authority
  URI schemes gives 320; both are defensible and the plan previously stated
  neither, so the v5 figure could have been compared against the other one.
- **British spellings in generated prose only** — spans inside double quotes
  are removed first, because the rule exempts quoted material. That is the
  difference between 613 and the ~626 a naive count gives.
- **`B2AI_TOPIC` and `B2AI_SUBSTRATE` are declared prefixes**, not invented
  ones. Counting them among the undeclared put 192 legitimate values in the
  defect column on a first pass.

### What the first version got wrong

It said minted fragments were "17 / 12 / 14 in AI_READI rep1, CM4AI rep1, VOICE
rep3; **0 elsewhere**". AI-READI rep2 and rep3 have 14 and 13. Prediction 2 —
that minted-fragment counts rise or hold — would have been evaluated against a
baseline 27 too low.

The 397 URL-valued slots are not defects under the v4 rules: the playbook in
force for that arm said a resolvable URL is correct where no prefix is declared.
Since #573 both texts say the same thing, so this is a baseline for v5's rule,
not evidence v4 broke its own.

## What would falsify the block rather than confirm it

- `absent` falls but total external identifiers falls further — the model
  responded by dropping identifiers wholesale, including grounded ones. Watch
  `grounded` as well; it should hold.
- `minted_fragment` rises on values whose base is not in the bundle. The
  grounding check reports those as `absent`, so this shows up as rule three
  being followed in form and not in substance.
- Pair divergence rises. Four new rules touching `id` fields across both records
  is exactly the kind of change that can push full and core apart, and 80% of
  the corpus already diverges (#550). This is a regression watch, not a
  prediction.

## Before the arm starts: the schema must be current

`make check-digest` (or `d4d schema check-digest --strict`) rebuilds each merged
schema from its source and compares. `d4d api run` now performs the same check
and refuses to start when it fails, because a merged schema built from stale
source makes every record in the arm attest to a digest describing a schema this
repository no longer holds — invisibly, since the record correctly hashes the
file it did read.

Verified in sync at the time of writing: `Dataset` `44d29023`, `CoreDataset`
`dff487bc`, both byte-identical to a fresh build.

**This does not resolve #576.** The check establishes that the digest describes
today's source; it says nothing about whether today's source is the same one v4
was generated against. It is not — v4 recorded `622e6d03` — and that remains a
decision about the comparison rather than a defect to fix here.

## The canary is AI-READI, and the context risk is smaller than first stated

The v4 arm canaried CHORUS, whose largest request is 64k tokens against
AI-READI's 285k. #566 adds the core record to `reconcile_full`, so the canary
must be **AI-READI** — the project that can actually fail — and it must be
verified to have completed, not merely started. A CHORUS canary exercises
credentials, persistence, the run lock and every gate, and says nothing about
the one thing this arm changed that could break.

**Two corrections to the first version of this section**, both from measuring
rather than reasoning (#568):

- The peak phase is `reconcile_core`, not `reconcile_full`. It receives the
  reconciled full record, the core record and the audit findings, and it is the
  largest request in 56 of 67 API runs; `reconcile_full` peaks in 3.
- **The corpus has already sent 363,261 tokens successfully** — VOICE, rep3 of
  the 2026-07-31 arm. AI-READI's v4 peak of 285,113 is well inside that, and
  #566 raising `reconcile_full` toward ~279k puts it below a size this pipeline
  has demonstrably handled. The risk is real but it is headroom-unknown, not
  headroom-exceeded.

Every API record now carries `model.context.peak_request_tokens`, so the next
person answers this from the corpus instead of re-deriving it. The *limit*
stays null and says why: no route states it and the provider does not return
it, and a guess would make headroom computable and wrong.

## What this plan does not license

Comparing v5 against anything other than v4. Every earlier arm sits at a
different schema digest and most at a different pin. And attributing any part of
the result to one of the four rules — see above; that resolution is not
available from this design.
