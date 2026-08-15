# generic v5 — what the block predicts, registered before any run

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

## What this plan does not license

Comparing v5 against anything other than v4. Every earlier arm sits at a
different schema digest and most at a different pin. And attributing any part of
the result to one of the four rules — see above; that resolution is not
available from this design.
