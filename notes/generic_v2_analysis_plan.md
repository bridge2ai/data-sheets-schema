# generic-v2: analysis plan, registered before any run

Written 2026-07-30, **before** any `-generic-v2` generation has executed. That
ordering is the point of the file.

## Why this is a separate file and not a section of the prompt

The prediction below is an outcome expectation. Written into
`d4d_generic_arm_prompt_v2.md` it would instruct the model to produce the result
this experiment is meant to test, and the run would confirm the prompt rather
than the rules. The playbook's priming taxonomy excludes outcome expectations
from *both* the generic and tuned arms for exactly this reason.

So the expectation lives here, and the prompt states only the rules.

## What changed

v2 is v1 plus three uniform decision rules, and nothing else — a test asserts the
diff is confined to the `ADDED IN v2` block:

1. multivalued slots get one object per distinct entity
2. a slot carries the information asked for, not a pointer to it or a note that
   it is pending
3. the field asked is the field populated, not its neighbour

Each was stated without naming a project, which is what makes it admissible in a
generic arm. The project-specific forms were excluded deliberately; see the v2
prompt header.

## Baseline

`2026-07-28_claude-opus-5-generic_rep{1,2,3}`, four projects, 12 records. Fitness
failures under v1, from `data/evaluation_llm/judgement_cache/*_fitness.jsonl`:

| class | AI_READI | CHORUS | CM4AI | VOICE | total |
|---|---|---|---|---|---|
| form | 14 | 12 | 16 | 8 | 50 |
| substance | 17 | 12 | 5 | 6 | 40 |
| target | 6 | 12 | 18 | 5 | 41 |
| **total** | **37** | **36** | **39** | **19** | **131** |

Mean fitness by project: AI_READI 0.901, CHORUS 0.847, CM4AI 0.850, VOICE 0.912.

## Prediction

Each rule targets one class, so each class is tested separately rather than by a
single aggregate that could move for the wrong reason.

- **form** falls by more than half, in every project. This is the most
  mechanical of the three — "one object per entity" is checkable against the
  schema without judgement — so if any rule works, this one should.
- **substance** falls, but by less. "Pointer instead of content" is partly a
  property of the corpus: where the documents genuinely only say where
  information lives, omitting the slot is the correct response, and that shows up
  as a *lower slot count*, not a lower substance count.
- **target** is least likely to move. Choosing the right field among neighbours
  requires reading the schema carefully, and an instruction to do so may not
  change whether it happens.

## What would count as the rules failing

Stated now so it cannot be reinterpreted afterwards:

- form failures do not fall materially → the rule did not land, and the others
  are unlikely to have.
- total slot counts fall sharply while failures fall → the rules bought
  correctness by suppressing content, which is not the trade wanted. Watch mean
  fitness *and* slot count together; a record that omits everything scores
  perfectly on fitness.
- mean fitness rises while failure counts are flat → something else moved, and
  the attribution is wrong.
- failures fall only in one project → the rules were not uniform in effect, and
  a generic framing may be the wrong vehicle.

## Method

1. Run `-generic-v2`, three replicates, four projects, `condition="generic_v2"`.
2. Score with the **same** fitness rubric and schema. The judgement cache is
   keyed on `(axis, model, rubric, corpus, schema)`, so any drift in either
   invalidates the comparison automatically rather than silently — do not edit
   `FITNESS_SYSTEM` between the two arms.
3. Compare failure counts by class and project, plus slot counts and mean
   fitness.
4. `d4d runs compare --require-attested` for agreement; v2 runs must write live
   provenance.
5. Compare **v2 against v1 only**. `comparable_conditions()` permits it because
   the two differ on one axis (base). It refuses `generic_v2` vs `tuned`, which
   differ on both base and tuning, so a difference there could not be attributed
   to either — if v2 is promoted, a matching `tuned_v2` is needed before the
   generic/tuned comparison resumes.

## Confounds to state in any result

- **n=3 per project.** A drop of one or two failures in a class is not a result.
- v1 and v2 differ only in prompt text, but generation is stochastic; the
  comparison is between distributions, not records.
- Fitness scoring itself is not validated against a reference — there is no gold
  standard (#177). It measures agreement with the schema specification, which is
  what the rules address, so the instrument matches the intervention. It does not
  measure whether the record is *true*.
