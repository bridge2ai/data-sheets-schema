# generic v1-vs-v3 analysis plan

Registered before any generation run of this comparison. The prediction is here
rather than in the prompt because writing it there would instruct the model to
produce the result the run is meant to test — the same reason
`notes/generic_v3_analysis_plan.md` keeps it out.

Supersedes the comparison registered in `notes/generic_v3_analysis_plan.md`.
That plan is not retracted — its question is still the right *mechanism*
question — but it cannot be answered from anything on disk, for the reasons in
#458, and answering it would require generating a v2 arm as well.

v3 coverage on disk, measured per project: **AI_READI 7 replicates, CHORUS 5,
CM4AI 0, VOICE 0, VOICE_PEDIATRIC 0.** The only v3 series carrying three
replicates on two projects is `2026-08-06_…1m-generic-v3-schema2`, which is
confounded against the v2 series on both schema and route at once — so the
best-powered v3 data is also the most confounded (#460).

## Why the pairing changed, from v2-vs-v3 to v1-vs-v3

The registered plan asked for v2 against v3, because the two differ on one axis
and only that pairing isolates the companion rule. That is the mechanism
question: *does rule 4 do what it says?*

The question actually open in NEXT_TASKS §6 is the **promotion** question: *should
the playbook stop giving v1 behaviour by default?* v1 is the default, so v1
against v3 is the comparison that decides it. It measures all four rules at
once, which is the correct granularity for a decision to adopt all four.

The mechanism question stays open and is not answered here. It needs a v2 arm at
today's schema, and nothing in this plan produces one.

## Why both arms must be generated fresh

The `Dataset` schema digest today is `e802cdc3`. No run on disk carries it:

| series | digest | declared |
|---|---|---|
| v2, `2026-07-31` | `34d24ff3` | 1.0.0 |
| v3, `2026-08-05` | `b065e1cd` | 1.0.0 |
| v3, `2026-08-06` schema-2 | `583d79c1` | 2.0.0 |
| `2026-08-07` sweep (v1, mislabelled — #454) | *none recorded* | 2.0.0 |
| **this comparison** | **`e802cdc3`** | 2.0.0 |

The schema deltas between these are not cosmetic: they include the trap-slot
work (#376 scalarized the narrative family, #382 made `Organization.id`
optional), which mechanically moves the exact defect classes `form_defects`
counts. A hollow-object count is not comparable across them.

The 2026-08-07 sweep is a v1 arm at declared 2.0.0 and was considered as the
baseline. It is rejected on two grounds, either sufficient: it records no schema
digest, so it cannot be shown to sit at `e802cdc3`; and per #454 its launch text
was not uniform — VOICE and VOICE_PEDIATRIC received a scope paragraph the other
three projects did not, so two of five projects would compare against a
different condition than the other three.

## The comparison

**v1 (`generic`) against v3 (`generic_v3`)**, both generated fresh:

| | |
|---|---|
| projects | AI_READI, CHORUS, CM4AI, VOICE, VOICE_PEDIATRIC |
| replicates | 3 |
| runs | 15 per arm, **30 total** |
| runtime | Claude Code, agentic four-phase (`claudecode_agent`) |
| schema | `e802cdc3`, declared 2.0.0 |
| instruction | rendered by `d4d api render-prompt`, never typed (#425) |
| scope | from `source_manifest.yaml`, never from launch text (#422) |

Both arms are rendered through the same code path with only `--condition`
differing, so the two instructions are byte-identical outside the condition
block. That is what the 2026-08-07 sweep could not claim and is the point of
regenerating the baseline rather than reusing it.

## Prediction, registered

Against the v1 arm, under v3:

1. **Hollow objects fall.** v3's rule 4 names this defect directly and is the
   only rule that does. This is the outcome that would justify promotion.
2. **Collapsed cardinality falls.** v3 contains v2's rule 1, and v1 contains no
   cardinality rule. The v1→v2 measurement put this at 42 → 7 (−83%).
3. **The `form` total falls.** This is the figure that moved the *wrong way* on
   v1→v2 (50 → 56) while both its components were changing, which is why the
   split had to come first.

   ⚠️ The total is **not** the sum of predictions 1 and 2, in either direction.
   It also counts `other`, which neither rule addresses; and the two folded
   figures overlap, because a value classified `both` counts toward each. So
   the total can rise while both folded counts fall — `other` growing, or
   `both` growing — and predictions 1–3 can come apart without any of them
   being wrong. **Report all four raw buckets alongside the folded pair**, and
   treat a total that moves against its components as a finding about where the
   defects went rather than as a contradiction.
4. **Substance and target fall**, roughly as they did on v1→v2 (−62%, −61%).
   v3 carries v2's rules 2 and 3 unchanged.

Prediction 4 is the weakest and is registered as such: it is the one place this
comparison should reproduce a known result rather than produce a new one, so a
*failure* there is evidence about the instrument or the schema change, not about
the prompt.

## What would count as failure

- **Hollow objects flat or up.** Rule 4 is not doing what it says, and #458's
  premise — that the arm was worth generating — is weakened rather than the
  rule's.
- **Collapsed cardinality returning.** The rules are not additive; rule 1 and
  rule 4 need rewriting as one instruction rather than two.
- **A new form sub-type appearing in `other`.** The same exchange happening one
  level down. `other` is measured, so this is visible rather than inferred.
- **Substance or target moving sharply against the v1→v2 result.** Adding rules
  changes behaviour diffusely rather than at the point they name, which weakens
  the case that these rules compose at all.

## How it will be measured

Fitness scoring, then `python -m data_sheets_schema.form_defects` for the
sub-type breakdown. Neither rubric is edited.

⚠️ **Two instrument constraints have to be handled before this command can
produce the comparison** — neither is optional, and both were found reviewing
this plan:

1. **`attribute()` is wired to the historical v1/v2 labels.** Its `configs`
   default is `DEFAULT_CONFIGS`, naming the 2026-07-28 and 2026-07-31 runs. Run
   bare against the new arms, every fresh failure attributes as `unattributed`
   — or worse, to an old arm, where an identical slot/value happens to occur in
   both. Pass the new labels explicitly (`--config v1=<label> --config
   v3=<label>`).
2. **The sub-type cache key is `(slot, value)` only** — no schema, unlike the
   fitness cache which is keyed on it. So an identical slot/value under
   `e802cdc3` silently reuses a label judged against the *old* slot
   specification. That matters precisely here, because this plan's own argument
   is that the schema change moves the form classes: `Organization.id` becoming
   optional changes whether a given object is hollow. Classify the new arms
   into a **separate cache file** (`--cache <path>`) rather than the shared one,
   until the key carries the schema (#465).

The fitness rubric and the sub-type rubric are unchanged, so labels stay valid
for their own key — but "their own key" does not include the schema, which is
the whole of constraint 2.

### Counting convention — fixed here so the arms are comparable

`form_defects` classifies each form failure into `collapsed cardinality`,
`hollow object`, `both`, or `other`. **Subtype totals fold the `both` bucket
into each of the two named subtypes**, which is how the v1→v2 headline figures
were derived:

```
collapsed cardinality:  34 + 8 = 42  →  2 + 5 = 7
hollow object:           0 + 8 =  8  → 45 + 5 = 50
```

The convention was stated nowhere in the repo when this plan was written; it is
now implemented as `folded()` and printed by the CLI (#461). It is not optional
here: counted *excluding* `both`, the v1 collapsed-cardinality baseline is 34
rather than 42, and the arms differ by the size of that bucket — 8 values on v1,
5 on v2 — which is larger than several of the effects this comparison is trying
to see.

The v1 arm generated here supplies its own baseline, so the v1→v2 numbers above
are context rather than the comparison. They are quoted to fix the *convention*,
not the values.

Two further figures in circulation are the **manual read** (collapsed
cardinality 27 → 0, hollow object 2 → 33) that the classifier superseded. Do not
mix them with classifier output; `notes/form_defect_split_2026-08-03.md` keeps
both and explains why they differ.

⚠️ **No cached judgement is reusable here.** All 1441 existing fitness
judgements are keyed `(34d24ff3, google/claude-opus-5-high)`. Every record in
this comparison sits at `e802cdc3`, so both arms need judging from scratch. This
is the guard working as designed — the cache key is what prevents a silent mix
across schemas — but it means the scoring cost is for 30 records, not 15.

## Cost

Thirty agentic generations (5 projects × 3 replicates × 2 arms) on the Claude
Code path: no API spend for generation. Then fitness scoring of all 30 records
and sub-type classification of whatever form failures they produce — this part
is paid, and is roughly double what a single-arm comparison would cost, for the
cache reason above.

**Canary before fan-out.** One run — one project, one replicate, one arm —
executed end to end through the same launcher, and its outputs verified present
and non-empty on disk, before any of the remaining 29 are launched.

## What this does not settle

- The mechanism question (v2 against v3, isolating rule 4). Needs a v2 arm at
  `e802cdc3`.
- Whether the promotion generalises beyond five projects. #169 established that
  between-project variance (sd 10.9) swamps between-config effects at this
  sample size; five projects, two of which share a source corpus
  (`SHARED_CORPUS_GROUPS`), cannot resolve a small effect. This comparison is
  powered to see a *large* prompt effect on defect counts, not to estimate one.
