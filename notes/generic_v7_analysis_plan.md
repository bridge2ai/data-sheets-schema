# generic v7 — the receipt rule on the API arm, and what it can be held to

Written 2026-08-27, before any v7 generation. Same purpose as the v5 and v6
plans: predictions out of the prompt, and a statement of what a v6-against-v7
comparison can and cannot attribute.

## What v7 changes

One rule (`ADDED IN v7`): the `full` phase's output is the record followed by
its coverage receipt (#710), the artifact the agentic playbook writes during
Phase 1 (#709), validated by the same check (#708) against the same chunk
manifest (#707). Two things move with it that are not prompt text:

1. the cached bundle carries a `[cNNN]` marker line at the start of every
   manifest chunk, so the model can cite chunks — the bundle the model reads
   is not byte-identical to what v6 read;
2. the `full` phase instruction gains the receipt request, so the assembly
   digest moves.

**v6 against v7 measures the receipt rule together with the markers.** They
cannot be separated by this comparison; a marker-only control condition
would separate them and is not planned unless prediction 3 fails.

## Predictions, registered

| # | metric | attributed to | prediction |
|---|---|---|---|
| 1 | receipt gate (chunks unreviewed, snippets unverified, findings, vacuity) | the rule | 0 on every v7 run: the model has the whole bundle in context, so a complete, verbatim receipt is a matter of compliance, not access |
| 2 | slots without a receipt (reported) | the rule | small and named — the residue is runner-set/minted slots outside the denominator plus back-ported values from `reconcile_full`, which under v7 have no receipt route on the API path (the agentic playbook has one, #734) |
| 3 | populated slots | the markers, watched | should not fall against v6: a marker line is not content. A fall would mean the markers displaced reading, the confound this plan names |
| 4 | pair errors, ungrounded identifiers, British spellings, minted fragments | neither | unchanged from v6 within replicate spread; the rule adds an output, it does not touch these |
| 5 | per-slot attribution of the arm gap | the rule (the point of v7) | for every slot the API arm populates and the agentic arm does not, the API receipt names the chunk; the agentic receipt for that chunk says `extracted` (then the agentic arm read it and did not use it), `nothing_relevant` (a judgement disagreement, reviewable), or the chunk is unopened (coverage) — a per-slot answer to CHORUS 49 vs 58 |
| 6 | spend | the rule | `full` phase output tokens rise by roughly the receipt's size; incomparable across arms as before (#681) |

### Falsification tests

- **The receipt is filled, not written.** If snippets verify but are
  generic (the same phrase receipting many slots, or the chunk's first line
  everywhere), the model satisfied the check without attesting support.
  Sample: distinct snippets per receipt / snippet count; a ratio far below
  the agentic arm's is the signature.
- **Markers leak into the record.** A `[cNNN]` token in any record value is
  the markers read as content; grounding will not catch it (it is not an
  identifier), so grep the records.
- **The receipt reshapes the record.** If v7 populated-slot counts fall on
  slots whose evidence is prose-heavy while structured slots hold, the
  model economised on what it would have to receipt.

## What v7 can and cannot be compared against

- Against **the agentic arm under the receipt protocol** (#709, v6 playbook):
  same manifest, same validator, same counts — the first like-for-like
  cross-arm measurement of coverage and support. Prediction 5 is that
  comparison.
- Against **2026-08-22c (API v5)** and a v6 API arm: prompt base one step
  (`comparable_conditions` true from v6 only), assembly digest moved, bundle
  bytes-as-seen moved (markers). `d4d runs compare-arms` lists the first two;
  the third is recorded in the record's `receipts.artifacts.manifest`.
- The instrument caveats of the v6 plan carry over.

## Canary outcome and a revised gate (2026-08-28)

Two CHORUS canaries (`2026-08-28_…v7_rep1`, `2026-08-28b_…v7_rep1`) held
every floor except one: **2/109 and 3/98 snippets did not verify against the
chunk cited**, and every such snippet is verbatim in the bundle one chunk
away (one of the three was an instrument defect, a per-part minimum
rejecting a numeric anchor). **Prediction 1 is falsified at ~2%** on the
attribution half of the receipt, and holds on the support half. The gate is
revised accordingly, recorded here before the fan-out: a snippet found in a
chunk other than the one cited is `adjacent` or `elsewhere` — reported
under "snippets in another chunk", never gated — and the floor of 0 stays
for text found nowhere in the bundle. The fan-out proceeds under the
revised gate with the canary records re-checked offline, not with a third
run. **This is an interpretation of the canary rule, not something it
grants**: the rule says a fixed canary is re-run and names no instrument
exception. The reading taken is that the checker is not on the generation
path — nothing the model receives or does changed — so re-running would
produce a third record of the same procedure and test nothing the two
existing records, re-checked with every floor held, do not already test.

## Canary rule

One run before any fan-out, gated against the v6 API worst-of-arm on the
existing metrics and against the receipt floors (0) on the new ones; the
gate treats an absent receipt as UNMEASURABLE because `receipt_expected` is
true for this condition. Sequencing per #710: after the agentic arm has run
under the receipt protocol once, so prediction 5 has its other side.
