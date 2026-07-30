# Next tasks

Open work, most blocking first. Each item states what is true now, not only what
should happen, so an item can be checked rather than believed.

Last verified: 2026-07-29.

---

## 1. Decide whether to archive unattestable runs

**Not urgent.** `d4d runs archive --unattested` moves runs into `data/ATTIC/`,
out of `discover()` and therefore out of every analysis. Nothing is deleted;
`d4d runs restore` is the same move reversed.

Dry run today: **16 run directories across 8 labels** — the 2026-04-10 sonnet
baseline and the 2026-07-23 GPT series. Their bundles were first committed on
2026-07-28 (`fa90b4ec`), after those runs executed, and the working tree at the
time is unrecorded — so the bytes they consumed are *unverifiable*, not merely
unrecorded. That is the whole loss: the GPT-5.5 and GPT-5.6 comparisons.

**`record_mode` is the wrong thing to gate on**, and an earlier version of this
item said otherwise. Attestation has four levels:

| level | meaning | count |
|---|---|---|
| `live` | the run wrote its own provenance | 49 |
| `attested` | reconstructed, but inputs verified and schema/model/outputs pinned | 33 |
| `partial` | a gap in something that determines the output | 23 |
| `none` | no record | 5 |

**82 of 110 runs can be placed and reproduced.** The entire 2026-07-27 tuned arm
is `attested`: it pins the bundle by *verified* md5, the schema by md5, the model,
and every output hash. Its only gap is the hardware, which cannot affect a
generation. Gating on `live` would have dropped all 24 records for that.

Prefer `--require-attested` on `compare`/`arm-delta` — it excludes the same runs
per-analysis without moving anything. `--require-live` remains available and is
usually the wrong choice.

---

## 2. Enforce live provenance for *new* runs

`d4d-full-core.md` lists it as a completion criterion — *"The live provenance
record is present and its `record_mode` is `live`"* — but nothing checks it, so a
run that never writes one still completes.

Worth doing for new runs, where it is free. Not worth applying backwards: the
2026-07-27 arm shows a reconstructed record can be fully attestable, so the
useful invariant is attestation, not authorship of the record.

---

## 3. Ship merged records — provenance done, playbook carve-out remains

**Done:** `record_mode: derived` exists. A merged record now carries a provenance
record naming every contributing replicate by md5, how many slots each supplied,
and the rule that combined them, with `model`, `prompts` and `inputs.bundle_md5`
explicitly marked not-applicable rather than left absent. All four guarded merges
under `2026-07-29_guarded-union/` have one.

**Remains:** the playbook forbids cross-label reads in four places, and a merged
record is cross-label by definition. That needs an explicit carve-out rather than
a quiet exception, since the rule exists to stop factual leakage between runs and
a merge is the one case where crossing is intended.

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
