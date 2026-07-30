# Next tasks

Open work, most blocking first. Each item states what is true now, not only what
should happen, so an item can be checked rather than believed.

Last verified: 2026-07-29.

---

## 1. Archiving unattestable runs — done

`d4d runs archive --unattested --execute` moved **10 run directories across 5
labels** into `data/ATTIC/d4d_concatenated_archived/`: the 2026-04-10 sonnet
baseline and the four 2026-07-23 GPT series. Their bundles were first committed
on 2026-07-28, after those runs, so the bytes they consumed are unverifiable.
Nothing was deleted — `d4d runs restore --execute` reverses it.

Corpus: **partial 23 → 3**. What remains partial is CM4AI under the three
`crateonly` labels.

Those three were **skipped deliberately**, and the reason is a defect the dry run
caught before anything moved: a label is not a unit of attestation.
`2026-07-28_claude-opus-5-crateonly` holds CHORUS and VOICE *live* alongside CM4AI
*partial*, so archiving by label would have moved six placeable records out with
three unplaceable ones and reported success. `archive_runs` now refuses a label
whose projects disagree, and the sweep skips them with a message.

Remaining, if wanted: archive at project granularity so CM4AI's crateonly records
can go without taking CHORUS and VOICE. Low value — `--require-attested` already
excludes them per-analysis.

**What left the active corpus:** the GPT-5.5, GPT-5.6 and sonnet-4.6 comparisons.
They are restorable in one command, and `--require-attested` was already
excluding them from any analysis that asked.

---

## 2. Live provenance for new runs — done

Required from `2026-07-30`, read from the label's date prefix. Dated rather than
corpus-wide on purpose: 33 pre-cutoff records are fully attested despite being
reconstructed, and failing them retroactively would discard placeable evidence to
enforce a rule that postdates them.

- `d4d runs check --strict` exits non-zero if any run subject to the rule lacks
  live provenance — usable as a gate after a generation step.
- `api_runner.execute()` verifies the record it just wrote and fails the run
  rather than leaving an unattestable artifact behind.
- A label with no parseable date is **subject** to the rule. Exempting anything
  unparseable is an exemption taken by accident.

Corpus today: 98 runs checked, 0 subject to the requirement, 0 failing.

---

## 3. Ship merged records — provenance done, playbook carve-out remains

**Done:** `record_mode: derived` exists. A merged record now carries a provenance
record naming every contributing replicate by md5, how many slots each supplied,
and the rule that combined them, with `model`, `prompts` and `inputs.bundle_md5`
explicitly marked not-applicable rather than left absent. All four guarded merges
under `2026-07-29_guarded-union/` have one.

**Done:** the playbook now carries an explicit carve-out. Derivation is not
generation — it consumes generated records as declared inputs rather than as a
shortcut around evidence, introduces no new facts, and states what it consumed by
md5. Five conditions bound it, and three are enforced in code rather than trusted
to prose: a source must be complete and attested, a derived record may not
contribute to another, and the output goes under a distinct method. The remaining
two (generation phases never derive; a derived record is not a replicate) are
structural.

Merged records are now shippable.

---

## 4. Rubric20 scoring — done

`_score_rubric20_question` returned 0 or a flat 4, never 1/2/3/5, so every record
in the corpus scored 71/88 and the rubric could not rank anything.

Now measured. Four questions state explicit numeric thresholds (proportion of
fields populated, character length, keyword count, distinct file types) and are
measured directly; the other thirteen describe tiers — "no X" / "basic X" /
"comprehensive X" — and are scored by how much of the question's own declared
field set is populated.

Corpus after the fix: five distinct totals spanning 59–67 of 88, an 8-point
spread. It separates projects (AI-READI 63–67 > CM4AI 63 > CHORUS 59–61) and some
replicates within a project.

⚠️ **The tiered half is a coverage proxy for depth, not a measurement of depth.**
A record that populates every field of a question shallowly still scores 5.
Judging whether content is genuinely comprehensive is what `d4d-rubric20-semantic`
is for; this path is the free, deterministic one and should not be read as more.

Also corrected: the rubric declared "84 points (16 numeric + 4 pass/fail)" while
its questions define 17 numeric + 3 pass/fail = 88. The questions are what get
scored, so the prose was stale — and it is why the presence and LLM paths used
different denominators. A test now fails if the two drift apart again. **The LLM
evaluation paths still divide by 84 and need updating to match.**

---

## 5. Complete the generic arm (#166)

`de_novo` and `crate_only` are unrun under the generic prompt — 18 runs. Until
they exist, generic-vs-tuned comparisons cover the baseline arm only.

---

## 6. Run the generic-v2 arm — staged, not run

**Staged:** `src/download/prompts/d4d_generic_arm_prompt_v2.md` is v1 plus three
uniform decision rules, with `condition="generic_v2"` wired through `RunSpec`.
The analysis plan is registered in `notes/generic_v2_analysis_plan.md`, written
before any run.

The three rules address the fitness failures, each stated without naming a
project — which is what keeps the arm generic:

1. multivalued slots get one object per distinct entity (form, 50 failures)
2. a slot carries the information asked for, not a pointer or a "pending" note
   (substance, 40)
3. the field asked is the field populated, not its neighbour (target, 41)

**Not run.** 12 generations (4 projects x 3 replicates) under
`2026-07-30_claude-opus-5-generic-v2_rep{1,2,3}`, then fitness scoring and
comparison against the v1 baseline per the plan.

Guards in place:

- v1 is untouched and must stay so — it produced the 2026-07-28 baseline this is
  measured against.
- Tests assert v2 differs from v1 *only* within the marked block, that the block
  names no project, dataset identifier or quantity, and that every project
  receives byte-identical text after mechanical substitution.
- The prediction is deliberately absent from the prompt. Written there it would
  instruct the model to produce the result the run is meant to test, which the
  priming taxonomy excludes from both arms.
- The fitness judgement cache is keyed on `(axis, model, rubric, corpus, schema)`,
  so editing `FITNESS_SYSTEM` between the two arms invalidates the comparison
  automatically instead of silently.

**The rules are NOT in the playbook's uniform decision rules.** Adding them there
would apply them to any run following the playbook, including runs labelled
generic v1, and would silently redefine the baseline. Promote them only if v2
validates.

---

## Standing constraints

- **No gold standard exists.** `curated` was generated through a ChatGPT chat
  interface and documents superseded releases (#177). Do not score against it.
- **Fitness ranks records identically to counting slots** in all four projects.
  Replicates differ in coverage, not quality — do not rebuild selection-by-score.
- **Reasoning text is unavailable through CBORG.** Thinking blocks arrive signed
  but empty. Records say `reasoning_present` / `reasoning_available` rather than
  implying no reasoning occurred.
- **CM4AI propagation is not affordable on the fitness axis** (record-level bias
  0.080 against a 0.05 tolerance), though it is on grounding (0.016) and on
  fitness for the other three projects. The axis changes the verdict; do not
  carry a saving measured on one axis over to the other.
