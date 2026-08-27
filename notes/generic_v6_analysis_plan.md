# generic v6 — one rule, one procedure change, and what each can be held to

Written 2026-08-27, before any v6 generation. Its purpose is the same as the
v5 plan's: to hold the predictions **out** of the prompt, and to state before
the run what a v5-against-v6 comparison can and cannot attribute.

## What v6 changes

Two things, and they are attributable to different metrics:

1. **The minting density norm** (#685) — the one rule in the `ADDED IN v6`
   block. v5's fragment rule said when minting is right and nothing about how
   much; under it VOICE minted 3 / 14 / 130 across three agentic replicates
   and CM4AI 42 / 55 / 51 (v5 API: 0–8 and 10–16). The norm: mint a fragment
   only where something else in the record refers to the part.
2. **The derived core** (#694, landed in #704 before this version) — the core
   is a projection of the audited full record on both runtimes, and v6's
   prompt text says so in the Phase 2 sentence and the core header. This is
   a procedure change that the prompt merely stops contradicting; it moved
   the assembly digest when it landed, so a v6 run is under a new assembly
   as well as a new prompt.

The v5 plan's confound caveat applies in its strongest form: **v5 against v6
measures the rule and the derivation together.** What keeps them separable
is that they touch different metrics, below.

## Predictions, registered

| # | metric | attributed to | prediction |
|---|---|---|---|
| 1 | minted fragments (reported) | the norm | falls on the projects that minted most (VOICE, CM4AI) and the within-project spread collapses: on every project the replicates' max − min is ≤ 5, where v5's agentic VOICE spread was 127 |
| 2 | ungrounded identifiers (gated) | neither | stays at 0 — the norm removes fragments, it does not push identifiers anywhere else |
| 3 | pair errors (gated) | the derivation | 0 on every run of both arms, by construction — the API arm's 0–18 disappears for a procedural reason, not a modelling one |
| 4 | British spellings (gated) | the derivation, partly | the API arm's full/core spelling splits (#675) cannot occur, so no API run exceeds its v5 arm's per-project worst (30/0/0/4); the full-record count itself is not predicted to move |
| 5 | populated slots | neither, and watched | should not fall: the norm removes identifiers on parts, not the parts. A fall would mean the norm was read as "omit the part", which is the failure mode to name |
| 6 | core-only content | the derivation | zero by construction; the generated core's ability to add bundle-supported fields the full lacked is gone, and the audit phase's back-port into the full is the only route (stated in `derive_core.py`) |

### Falsification tests

- **The norm suppresses referred-to fragments.** If `minted` falls to 0 on a
  record whose full record has splits a task names or subsets a distribution
  cites, the norm was over-read. Check the four canonicals' `splits`/`subsets`
  by hand against their minted set.
- **The norm moves minting into prose.** If populated-slot counts hold but
  `notes`/`description` grow with sentences naming parts that were previously
  identified, the label moved rather than disappeared. Reported, not gated.
- **Derivation loses something the report claims was in the core.** The
  report-claims checker (#684) and the pair check both run on the derived
  pair; a `removal_not_performed` on a core-only slot would show a report
  describing a core that no longer exists.

## What v6 can and cannot be compared against

- Against **2026-08-22c (API, v5)** and **2026-08-24 (agentic, v5)**: prompt
  base v5 → v6 (one step; `comparable_conditions` true) *and* assembly digest
  moved (#704). `d4d runs compare-arms` will list both. Attribution per the
  table above; nothing finer.
- The **instrument caveats carry over unchanged**: #674 (GC title collision),
  #684 (report-claims vacuity on prose reports; the v6 playbook prescribes a
  parseable `## Claims` section, so this may improve without any generation
  change), #675 (now moot on the API arm by construction).
- **Spend** remains incomparable across arms (#681/#682); within the API arm
  a v5→v6 fall in `api_usage` is the two retired phases, not efficiency.

## Canary rule

One run per arm before any fan-out (the standing rule): the API canary gated
against the 22c worst-of-arm, the agentic canary against the 24 worst-of-arm.
The gate's `minted` is reported-only; prediction 1 is judged at analysis, not
by the gate, and a canary that mints *more* than v5 is a stop regardless.
