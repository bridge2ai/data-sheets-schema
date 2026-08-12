# Decision: cross-slot repetition is accepted (#501)

**Decided 2026-08-12. Records generated after this date repeat facts across
slots on purpose.**

## The question

Camille Nebeker's review of the AI-READI and CHORUS ethics and privacy content:

> Redundancy in content vs potential new content, some fields have redundant
> content (eg multiple mentions of SAFE Harbor). … we also want to prioritize
> new informative content vs redundant content.

Confirmed. In the canonical AI_READI record the HIPAA Safe Harbor fact appears
in five slots — `human_subject_research`, `participant_privacy`,
`preprocessing_strategies`, `regulatory_restrictions`, `is_deidentified` —
across eight values.

## What was measured first

Across the whole canonical set (the 2026-08-11 v1 arm), sentence-level, content-
word Jaccard ≥ 0.6:

| project | sentences | prose restatements | rate | structural |
|---|---|---|---|---|
| AI_READI | 451 | 39 | 8.6% | 3 |
| CHORUS | 192 | 17 | 8.9% | 0 |
| CM4AI | 324 | 19 | 5.9% | 30 |
| VOICE | 364 | 18 | 4.9% | 9 |
| VOICE_PEDIATRIC | 255 | 23 | 9.0% | 2 |
| **total** | **1586** | **116** | **7.3%** | 44 |

Between 4.9% and 9.0% across five projects, so this is uniform behaviour rather
than one project's quirk, and any rule would have moved every record.

Two corrections came out of measuring rather than assuming:

- **They are paraphrases, not copies.** "removed from", "stripped from",
  "excludes" — three slots, three wordings, one fact. An exact-match pass finds
  8 restatements in AI_READI and misses the Safe Harbor family entirely. So no
  mechanical post-pass could have implemented the alternative; it would have had
  to be an instruction.
- **Structural repetition is not redundancy.** A URL beside the format it
  belongs to, or a nested `CoreDataset` under `resources` repeating its parent's
  title. 44 pairs, almost all CM4AI Dataverse URLs. Counting them would have
  overstated the figure by about a third.

## The decision

**Per-slot completeness wins. The repetition is the accepted cost.**

The core record is read one slot at a time — by a consumer deciding whether to
ingest, by a mapping into RO-Crate or DCAT, by a reviewer checking one question.
A reader who opens `is_deidentified` alone must learn that the release is Safe
Harbor de-identified. The alternative rule — state a fact in its most specific
slot and cross-reference elsewhere — gives that reader a pointer instead of an
answer, and a machine consuming one slot cannot follow a pointer at all.

The document reads repetitively end to end. That is the price, and it is paid
knowingly.

## What made the alternative worse than it looks

`is_deidentified` records that FAIRhub gives `deIdentType: "NoDeIdentification"`
while the Nature Metabolism comment states Safe Harbor. **`participant_privacy`
carries that same disagreement.** So the contradiction is itself restated — and
it is the most valuable content in either slot.

Any "state it once" rule needs an explicit exemption for preserved
disagreements, or it deletes the best sentence in the record to save the
third-best. That exemption is exactly the kind of clause that is easy to write
and hard for a run to apply consistently.

## What was built instead

`d4d runs redundancy` measures the rate and never fails. The number exists to be
watched, not met: at 7.3% the behaviour is as decided; a later arm at 30% would
mean something changed that nobody chose.

```bash
d4d runs redundancy                     # each project's canonical record
d4d runs redundancy --label <label>     # one arm
d4d runs redundancy --threshold 0.75    # stricter notion of "same statement"
```

`tests/test_redundancy.py` holds the exit code at zero. A change that turned
this into a gate would reverse this decision silently, which is the specific
failure the test exists to prevent.

## What this does not settle

- Whether *within-slot* repetition is acceptable. Not measured here — the
  comparison is deliberately cross-slot only.
- Whether the five slots carrying Safe Harbor are each the right slot. That is
  the ownership question, and it is separate from how many slots may carry it.
- Nothing about `notes` (#385) or undeclared keys (#380), both closed.
