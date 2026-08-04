# Next tasks

Open work, most blocking first. Each item states what is true now, not only what
should happen, so an item can be checked rather than believed.

Last verified: 2026-08-03.

---

## 1. Archiving unattestable runs — done

`d4d runs archive --unattested --execute` moved the 2026-04-10 sonnet baseline
and the four 2026-07-23 GPT series into `data/ATTIC/`, then CM4AI's three
`crateonly` records. Their bundles were first committed after those runs, so the
bytes they consumed are unverifiable rather than merely unrecorded. Nothing was
deleted — `d4d runs restore --execute` reverses it.

**Corpus: partial 23 → 0.**

The level table below is **as of 2026-07-29** and has not been re-derived; the
corpus has since grown to 123 runs, so treat the counts as a record of that day
rather than of today. What still holds, re-checked 2026-08-03:
`d4d runs archive --unattested` reports *"No unattestable runs found — every run
in the corpus can be placed."* The property the section is about survived the
growth even though its arithmetic is stale (#270).

| level (2026-07-29) | count |
|---|---|
| live | 49 |
| attested | 33 |
| derived | 4 |
| none | 1 |

The single `none` is `2026-07-29_coverage-union`, the deliberately-kept
incoherent unguarded merge; it has no provenance because it was written by a
probe, and its README says so.

Archiving operates on **files**, so whole-label and per-project moves are one
code path. That was needed because a label is not a unit of attestation:
`2026-07-28_claude-opus-5-crateonly` held CHORUS and VOICE *live* alongside CM4AI
*partial*. An earlier version skipped such labels to avoid collateral, which
prevented data loss and also prevented the archive doing its job. Naming the
project moves exactly the unplaceable records.

**What left the active corpus:** the GPT-5.5, GPT-5.6 and sonnet-4.6 comparisons,
and CM4AI's crateonly arm. All restorable in one command, and `--require-attested`
was already excluding them from any analysis that asked.

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

Corpus on 2026-08-03: **131 runs checked, 49 subject to the requirement, 0
failing** (`d4d runs check --strict`, exit 0).

The "0 subject" recorded here on 2026-07-29 was true only because no run had yet
crossed the 2026-07-30 cutoff — it described a gate that had never fired. Every
run made since is subject to it and every one satisfies it, which is the
evidence this section was written to be able to claim.

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
different denominators. A test now fails if the two drift apart again. **The 84 is still in two places
and both are wrong** (checked 2026-08-03):

- `constants/evaluation.py: RUBRIC20_MAX_SCORE = 84` — exported from
  `constants/__init__.py` and imported by nothing. Dead *and* wrong, which is
  the combination that gets picked up by the next person who needs a
  denominator.
- `scripts/summarize_rubric20_results.py` — `overall.get('max_points', 84)` as
  a fallback in three places, and one hardcoded `/84` in the markdown table
  (line 186) that ignores `max_points` entirely, so the printed denominator is
  84 even when the data says 88.

Small and self-contained.

---

## 5. Complete the generic arm (#166) — done

Both missing arms ran on 2026-07-31 under
`2026-07-31_claude-opus-5-api-generic_rep{1,2,3}`:

| arm | method | replicates | projects |
|---|---|---|---|
| baseline | `claudecode_agent` | 3 | AI_READI, CHORUS, CM4AI, VOICE |
| **crate_only** | `claudecode_agent_crate_only` | 3 | CHORUS, CM4AI, VOICE |
| **de_novo** | `claudecode_agent_crate` | 3 | CHORUS, CM4AI, VOICE |
| healthsheet_only | `claudecode_agent_healthsheet` | 3 | AI_READI |

#166 asked for `de_novo` and `crate_only` on CHORUS/CM4AI/VOICE at three
replicates. Both are there with exactly those project sets, so it is complete.

The AI_READI split is the design, not a gap: AI_READI has a healthsheet and no
crate, so it is covered by `baseline` + `healthsheet_only` while the other three
get `crate_only` + `de_novo`. Each project gets the arms its input type supports.

⚠️ **`de_novo` is an arm, not a directory name** — its method directory is
`claudecode_agent_crate`. `ls data/d4d_concatenated/*de_novo*` returns nothing
and means nothing. Ask `d4d runs list --arm de_novo`. An earlier version of this
section concluded the arm had never run on exactly that mistake (#269).

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

**Run on 2026-07-31**, under `2026-07-31_claude-opus-5-generic-v2_rep{1,2,3}`
rather than the staged `2026-07-30` label. Results in
`notes/generic_v2_results.md`; fitness fell **131 → 87** defective fields,
falling in all four projects.

### The promotion decision is open, and v2 is not a clean win

§6 says to promote the three rules into the playbook "only if v2 validates".
It validated on the headline, and the breakdown says to read that carefully:

| axis | v1 → v2 | |
|---|---|---|
| substance | 40 → 15 | −62% |
| target | 41 → 16 | −61% |
| **form** | **50 → 56** | **worse** |

Rule 1 eliminated the defect it named — collapsed cardinality **27 → 0** — and
produced a different one under the same label: **hollow objects 2 → 33**, one
object per entity exactly as instructed, with everything crammed into free-text
`description` while `name`, `id`, `affiliations`, `start_date`, `end_date` go
unused. `collection_timeframes` newly fails form in all four projects;
`creators`, `distribution_formats`, `distribution_dates` in three. Systematic,
not sampling noise.

**Consequence for any rerun:** promoting rule 1 as written reproduces the hollow
-object failure at whatever scale the rerun runs at. Either promote rules 2 and
3 and rework 1, or split the `form` class into collapsed-cardinality and hollow
-object before rerunning, so the next comparison can see what this one could not.
The rules are still **not** in the playbook, so a run today gets v1 behaviour
unless it explicitly selects `condition="generic_v2"`.

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

## 7. Replicate agreement — measured, and the design question is settled (#169)

Landed 2026-08-03 across PRs #240, #248, #252, #256. Not previously logged here.

The figure three issues rested on — "replicates disagree on 77–98% of shared
slots" — was byte equality over nested free text, and returned the same answer
regardless of input. Judged on whether values state the same *fact*, replicates
agree on roughly half of shared slots (**261/540 = 48.3%**, 37%–58% by project).

**#169 is confirmed on evidence and can stop being an open question about
method**: the between-config effect is −2.9 points against a per-project delta
sd of 10.9, and the four deltas do not agree in sign. Resolving an effect that
size needs ~110 projects; there are four. More replicates do not help — the
variance is between projects, not within them. Report agreement as a descriptive
property of a configuration; stop treating between-config differences in it as
findings.

Two instrument defects were found and fixed while measuring, both of the same
shape — evidence silently withheld:

- the judge saw only the first 4000 characters of each value, asymmetrically
  between the configs being compared. Re-judging on full text flipped **nine
  verdicts, every one from "equivalent" to "different"** (#244).
- the embedding endpoint truncates at 2048 tokens and returns HTTP 200. Two
  values contradicting each other past that point come back byte-identical,
  cosine **1.000000** (#251). The published table was unaffected — its longest
  value is ~719 tokens — but this makes embedding similarity unusable on long
  values regardless of the separate finding that it does not discriminate here
  (0.923 vs 0.914).

`python -m data_sheets_schema.agreement --offline --embed` rebuilds every figure
from cache with no paid call, and the suite asserts it.

---

## 8. Repository hygiene — a 3.19 GB orphan, and the guard for the next one

Landed 2026-08-03, PR #261; PR #265 open.

A single unreferenced blob — a 3.19 GB ZIP of CM4AI `untreated` images, staged
then unstaged in March — was 96% of a 3.3 GB local `.git`. Never committed,
never pushed; GitHub stayed 60 MB throughout. Extracted to
`data/ro-crate_packages/CM4AI/raw/cm4ai_images_untreated.zip` (verified
bit-for-bit by `git hash-object`) and the single-object pack removed. `.git` is
now 85 MB.

⚠️ **That file is the only local copy of 3.19 GB, and it is gitignored** — so
nothing in this repo backs it up. It is also one of three image conditions;
`paclitaxel` and `vorinostat` were never on this machine, and no download URL is
recorded in the bundled metadata. Copy it somewhere durable or delete it
deliberately; do not leave the decision to the next `rm`.

**PR #265 (open)** adds the guard that would have stopped it: a CI check on the
PR diff refusing files over 10 MB (largest tracked file today is 3.94 MB), plus
a budget on every tracked cache under `agreement_cache/`.

---

## 9. Split VOICE into two datasets — registered, not generated

`VOICE_PEDIATRIC` is a project as of #298. The companion pediatric dataset has
its own DOI (10.13026/h995-bt35), protocol and Research Ethics Board approval,
and was being represented as a nested object inside VOICE's `related_datasets` —
which is why no VOICE replicate validated (#292).

**Done:** the registry, the shared-corpus declaration, and the schema correction
that made the nested form wrong rather than ambiguous. Adding the fifth project
broke nothing; the four-project list in 26 files is prose, not logic.

**Not done, and each needs a decision:**

- **A scoped bundle — done.** `{MANIFEST_LINE}` was the wrong mechanism and the
  claim here was wrong: it is substituted into the *output record's* header
  block as a provenance comment, not into the instruction. The frozen body says
  "DECLARED INPUT BUNDLE — your only source of dataset facts: {BUNDLE}", so the
  bundle is the scope. `VOICE_PEDIATRIC` now has a manifest selection of six
  sources — the pediatric PhysioNet record plus the programme documents that
  cover it — and its own 204 KB bundle. The three adult version pages and the
  two adult-cohort papers are excluded: they carry no pediatric content, and
  including them would import adult facts into a pediatric datasheet, which is
  the failure the fitness axis calls `target`.

  The VOICE bundle is byte-identical (md5 `e637eb75`, what 49 runs attest), and
  a test pins it.
- **A generation run — deferred to v3, by decision.** Running under v2 now would
  mean running again when v3 lands, so `VOICE_PEDIATRIC` is generated with
  whichever config the v2-vs-v3 comparison settles on. v3 is drafted, wired and
  tested (#272) but unrun.

  `VOICE_PEDIATRIC` cannot join that comparison itself — it has no v1 or v2
  baseline, so it is generated once under the winning config rather than as a
  third arm.

  **Regenerate VOICE in the same run.** Its three 2026-07-31 replicates are the
  reason no VOICE record is canonical (#292), and both causes are now addressed
  for future runs but not for those records:

  - the enum values: `References` normalises to `references` on the write path,
    and `related_to` still fails, which is correct — it names nothing in the
    vocabulary;
  - the inline object in `target_dataset`: the slot is `range: string` with
    `slot_uri: dcterms:relation` — an **identifier**, not a pointer to a record
    we hold. rep2 and rep3 already put a URL there and that slot passed; they
    failed on `relationship_type` alone. The pediatric DOI appears 11 times in
    VOICE's own bundle, so VOICE can reference it whether or not a pediatric
    datasheet exists.

  **There is no ordering constraint.** An earlier version of this section said
  the pediatric record had to exist before VOICE could point at it. That was
  wrong, and it conflated two things: referencing a dataset by identifier, which
  needs only the DOI in the input documents, and referencing a D4D record we
  produced, which is not what this slot holds. VOICE and `VOICE_PEDIATRIC` can
  be generated in either order, or independently.

  The fork stands on its own reasoning — a dataset with its own DOI, protocol
  and ethics approval is its own datasheet (#292) — not on VOICE needing it.

  So a v3 run is the first opportunity for VOICE to have a canonical record,
  because it is the first run under the corrected enum handling and the
  clarified slot description.

  On canonical counts: there are **none at all** on `main` today — the three
  marks for AI_READI, CHORUS and CM4AI are in #293, still open. Once that lands
  it is three of four, and VOICE is the gap.
- **Whether `VOICE` becomes `VOICE_main` — decided: no.** Attempted and reverted.
  The path moves were clean (567 files, no clashes), but the content rewrite
  broke attestation two ways that no amount of care avoids: record bodies carry
  `VOICE` in titles and prose and their byte counts are recorded in provenance,
  so rewriting them failed 33 runs outright; and `source_manifest.yaml` is keyed
  by project and its md5 is recorded by **115 runs**, so renaming the project
  necessarily changes a file those runs attest.

  Renaming would convert attested runs into reconstructed ones — the same
  property that got the 2026-04-10 series archived. `VOICE` therefore keeps its
  identifier and `VOICE_PEDIATRIC` carries the distinction.

**Consequence for #169.** The power argument counts four projects. These two
share a source corpus, so they are not two independent samples, and
`SHARED_CORPUS_GROUPS` records that for any analysis that would otherwise
count them as such.

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
