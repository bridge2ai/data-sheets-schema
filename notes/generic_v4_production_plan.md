# generic v4 production run

Registered before the fan-out, on 2026-08-13. Supersedes
`notes/generic_v1_v3_analysis_plan.md`, which is retracted at its head and not
deleted.

## What this is, and what it is not

**This is a production run, not an experiment.** The goal is the best records
the pipeline can currently produce, for all five projects. It is deliberately
single-armed.

It therefore **cannot** answer whether v4 is better than v1, v2 or v3. Nothing
here is evidence for a promotion decision, and no comparison should be drawn
from it against an earlier arm — every earlier arm sits at a different schema
digest, and most at a different prompt pin as well.

## Configuration

| | |
|---|---|
| condition | `generic_v4` |
| projects | AI_READI, CHORUS, CM4AI, VOICE, VOICE_PEDIATRIC |
| replicates | 3 |
| runs | **15** |
| arm | `baseline` (input documents only) |
| runtime | Claude API, via CBORG |
| model | `claude-opus-5`, temperature 0.0 |
| schema digest | **`622e6d03`** (`Dataset`), `45f3687b` (`CoreDataset`) |
| label prefix | `2026-08-13_claude-opus-5-api-generic-v4` |

## Why v4

The conditions are cumulative, not alternatives:

- **v1** — four original rules.
- **v2** — v1 plus three uniform decision rules.
- **v3** — v2 plus the hollow-object rule: populate a class-ranged slot's
  declared fields rather than restating their content in free-text
  `description`.
- **v4** — v3 plus its companion: do *not* put structure where structure does
  not belong. `target_dataset` is `range: string` and takes an identifier, and
  #297 established that LinkML cannot express a string-or-inline-object range,
  so only validation catches an inline object there. All three 2026-07-31 VOICE
  replicates failed on `related_datasets` (#292) and one failed exactly this
  way.

v4 is the companion v3 needs rather than a correction of it, which is why
running v3 without v4 would reproduce a known failure.

**v4 had never been run before today.** It carries 0 records, so it gets its own
canary rather than inheriting confidence from any earlier run.

## One digest, deliberately

The digest moved five times on 2026-08-12–13 (#510, #504, #403, #486, #535) and
the prompt pins rotated once (#515). Every run of this arm is generated after
all of that, at `622e6d03`.

This is the direct lesson of #517: the 2026-08-11 agentic arm straddled a schema
change, with rep1 at `488bd732` and rep2/rep3 at `659aae67`, which turned part
of a replicate-variance measurement into a schema effect. `d4d runs check` now
reports a straddled series, so a repeat is visible rather than discovered
afterwards.

**If the digest moves mid-arm, stop and restart the whole arm.** Do not finish
it and note the straddle.

## What the canary must show before the fan-out

One CHORUS run, through the same `d4d api batch` launcher the fan-out uses, and
verified on disk rather than by exit code:

- `gate=match`, `pin=canonical`, `bundle drift=current`, `playbook=current`
- `verdict=valid`
- generation digest `622e6d03`
- all five artifacts present and non-empty — full, core, reconciliation,
  provenance, reasoning log
- the run lock registered while running and released after

If the canary needs a fix, re-canary. Fixing and fanning out in the same step is
the failure the canary rule exists to prevent.

## Known limits of this arm, stated in advance

- **The API repair loop is shape-only and evidence-blind.** `_repair_invalid`
  runs `linkml-validate` and repairs against the findings for up to 4 rounds,
  but `build_repair` deliberately excludes the input bundle. It can restructure
  a record; it cannot return to the evidence to fill a slot left empty. An empty
  `affiliations` is valid shape, so no repair round will touch it. This is the
  substantive difference from the agentic path's non-skippable
  validate-and-iterate step (#479), and it is why an agentic rerun is a
  different instrument rather than a replicate of this one.
- **Reasoning text is unavailable through CBORG.** The thinking block arrives
  signed and empty, so the logs record `reasoning_present: true,
  reasoning_available: false`. `reasoning_tokens_estimate` is the only surviving
  measure and is sound for comparison, not for cost attribution.
- **AI_READI's bundle changed on 2026-08-12** (#539) — it gained the release
  3.0.0 RO-Crate and the v2.0 licence. Its records will differ from earlier
  AI_READI records for that reason as well as any other, and the crate is the
  only source in the corpus stating `contentSize`, `deidentified`,
  `fdaRegulated`, `humanSubjectResearch` and `dataGovernanceCommittee`.
- **`B2AI_TOPIC` has no term for CHORUS's subject.** Acute and critical care is
  absent from all 56 terms (#538), so CHORUS should omit `data_topic` at the
  dataset level rather than approximate. The rendered vocabulary now says so
  explicitly; a near-neighbour appearing there is a finding, not a success.

## What remains open, and is not blocked by this run

#378 and #457 (identifier resolution and the `uriorcurie` migration), #531 (the
canonical prefix — the registry answer is `B2AI_DATA:N`), #537 (prose in a slot
that asks for omission — this run is the test of whether #538 fixed it), and
#517 (which describes the superseded arm).

None of them changes what a v4 run produces. All of them are about values
already on disk, or decisions with no code attached.
