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

Five rules, in one block. This breaks the one-rule-per-version convention that
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
| assembly digest | `77331f08` | `7d0ce8f3` |
| condition | `generic_v4` | `generic_v5` |

> The v5 assembly digest has moved three times since this table was first
> written: `2c1442fc`, then `d59f8532` when the source-ranking block entered the
> layout, then `7d0ce8f3` when the report phase gained the pre-reconciliation
> records (#639). It is stated as of 2026-08-19 and **must be re-checked against
> `assembly_digest()` immediately before the canary** — a plan naming a digest
> the arm did not run against describes a different arm, which is what #638 was
> filed for.

So a v4-v5 difference measures **the five v5 rules, plus a schema change, plus
`reconcile_full` gaining the core record, the audit gaining a clause, and — as
of 2026-08-19 — the report phase receiving both records' pre-reconciliation
states (#639)**.

`comparable_conditions('generic_v4', 'generic_v5')` returns **True**, not False
as this said before it was checked (#638). That is not a contradiction of the
paragraph above: the function deliberately assesses *prompt adjacency only* —
whether one condition is the other plus one marked block — and the procedural
differences are carried by `runs.arm_confounds`, which is where a reader should
look before attributing anything. `MULTI_RULE_BASES` records the rest: a step
that adds five rules cannot have a difference attributed to one of them.

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
5. **British spellings fall on the API arm.** Narrowed to the API arm on
   2026-08-19, before generation, because the planned arm contains no agentic
   runs and the original wording — "and are unchanged on the agentic arm" —
   could not be measured by it (#638). Deciding that after seeing the results
   is what pre-registration exists to prevent, so it is decided here.

   **What the narrowing costs, stated rather than absorbed.** The agentic clause
   was the control: the agentic playbook has carried the American-English rule
   all along (`.claude/commands/d4d-uniform-rules.md:90`), so v5 changes nothing
   for that arm, and an agentic arm that moved would have shown that something
   other than rule 5 moved with it. Without it, **a fall on the API arm is
   consistent with rule 5 and equally consistent with any other corpus-wide
   change between the two dates.** The result is evidence, not attribution.

   **Calibration, measured rather than assumed.** The agentic arm already has
   this rule and is not at zero:

   | arm | n | total | mean/record | max |
   |---|---|---|---|---|
   | agentic 2026-08-11 | 15 | 461 | 30.7 | 99 |
   | API v4 2026-08-13 | 12 | 613 | 51.1 | 146 |

   So the rule's observed effect where it already applies is a lower rate, not
   elimination. A v5 API arm landing near ~31 per record would be the outcome
   this rule can produce; predicting zero would be predicting something no arm
   has achieved, including the one that has had the rule the whole time. The two
   arms differ in runtime and in which records they wrote, so this is a
   reference point and not a matched comparison.

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

## Canary history (updated as canaries run)

Four entries: three canaries, all AI-READI, and the fan-out decision.

- **2026-08-20b** — post-#644-fix, second independent draw. **REGRESSED on pair
  errors only: 12 vs baseline worst 10.** Everything else passed, several far
  better than baseline: resolver URLs 0, undeclared prefixes 0, British 28 vs
  146. That made v5 = {13, 12, 12} against v4 = {10, 8, 6} — all three v5 runs
  above v4's max, permutation p ≈ 1/20, so the shift is systematic. Content
  verified benign on all three runs with the same slots recurring
  (`acquisition_methods` full=2 vs core=3 appears identically in consecutive
  runs: core writes the "active collection" item, reconcile_full never absorbs
  it). Core carries extra grounded detail; nothing wrong, nothing lost (#650).

  **Decision (2026-08-20, Marcin): fan out with a documented override** —
  `--no-canary-gate` under the `2026-08-20b` prefix, the completed canary
  resuming free as AI_READI rep1. The baseline was not adjusted and the gate's
  verdict stands on the record; the override is the documented conclusion of a
  three-run, finding-level analysis, not a workaround for it. **Consequence for
  analysis: v5-vs-v4 pair-error counts are not comparable at face value** —
  v5 runs ~2–4 higher on a divergence class shown benign; see #650 for the
  finding-by-finding record. Post-arm engineering (absorb core's extra
  precision in reconcile_full) is tracked there.

- **2026-08-20** — post-#644-fix. REGRESSED on pair errors (12 vs 10) with the
  identifier fix confirmed completely: resolver URLs 24 → 0, and the record's
  ids went from 0/29 CURIEs to 24/25. Disproved the 2026-08-19 hypothesis that
  pair errors were downstream of the identifier defect.

The two prior canaries, neither authorising a fan-out:

- **2026-08-16** — completed and was read as a pass, but its recorded
  `grounding` block predates the resolver-URL finding, so its stored verdict is
  an absence of measurement that reads like one. Recomputed from its artifacts:
  REGRESSED, 22 resolver URLs against a v4 baseline of 0 (#640, #591).
- **2026-08-19** — run from `main` at `0e9ff4a3` through `d4d api batch` with
  the gate live. **REGRESSED, and the gate stopped the sweep**: resolver URLs
  24 vs 0, pair errors 13 vs 10. Cost one run (~786k in / 250k out) instead of
  twelve. Diagnosis (#644): rule 1's exemption said "a slot whose declared
  range is a URL takes a URL", and the schema's identifier slots are ranged
  `uriorcurie` — which satisfies that clause on a plain reading. The run's own
  reconciliation report confirms the model read it exactly that way ("the
  resolver URL for the `uriorcurie`-ranged `id`"). The result inverted the
  rule's intent: v4, with no rule at all, wrote 62/68 ids as CURIEs; v5 wrote
  0/29. The exemption now names the ranges literally (`uri`, not `uriorcurie`),
  matching the agentic playbook, whose wording always did.

  The same canary settled the 68→29 "entity drop" as **mostly intended**: the
  16 dropped ORCID creators were clinical-trial investigators promoted by v4
  from a lower-tier source, and the release's own citation names the AI-READI
  Consortium as sole creator — source priority working. The train/val/test
  split survives in prose rather than as `subsets[]` entities. The extra pair
  errors (13 vs v4's worst of 10) are 12 shared-slot-content divergences (7 of
  them in `notes` paths) plus one shared-slot-presence on `$.download_url`;
  the run's provenance shows
  repair touched *both* records, so the first version of this sentence, which
  blamed repair rewriting the full record only, was wrong (#645 review).
  Plausibly downstream of the identifier mess above; re-measure after the fix
  rather than diagnosing further from one run.

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

## VOICE_PEDIATRIC is out of the v5 arm (2026-08-18)

Decided rather than deferred, closing the last open item in #590. VOICE_PEDIATRIC
has **no v4 record**, so it has no baseline for any of the eight gated metrics.
Under `verdict(..., baseline_requested=True)` a project whose baseline resolves
to nothing is `unmeasurable` and stops the sweep — the #599 fix, working as
intended. The alternatives were to run it ungated, or to gate it against another
project's numbers.

Both are worse than skipping it. An ungated run is the v4 failure exactly: a
record that enters the "succeeded" column on schema validation alone, with
nothing able to say whether it regressed. Borrowing VOICE's baseline would
assert that two datasets of different size and documentation should exhibit the
same defect counts, which nothing supports.

So the v5 arm is **AI-READI, CHORUS, CM4AI, VOICE** — the four projects with a
v4 arm to be compared against, which is also the only comparison this plan
licenses. VOICE_PEDIATRIC is not excluded on quality grounds and needs no
inference drawn about it; it is a project this design cannot measure, and
running it anyway would produce a number with no bar beside it.

## What this plan does not license

Comparing v5 against anything other than v4. Every earlier arm sits at a
different schema digest and most at a different pin. And attributing any part of
the result to one of the five rules — see above; that resolution is not
available from this design.
