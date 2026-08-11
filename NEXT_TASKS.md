# Next tasks

Open work, most blocking first. Each item states what is true now, not only what
should happen, so an item can be checked rather than believed.

Last verified: 2026-08-11.

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
different denominators. A test now fails if the two drift apart again.

**The two stale 84s are gone** (re-checked 2026-08-08).
`RUBRIC20_MAX_SCORE` is now derived — `RUBRIC20_NUMERIC_QUESTIONS * 5 +
RUBRIC20_PASS_FAIL_QUESTIONS` = 88 — so it cannot drift from the questions
again, and `summarize_rubric20_results.py` has no live `84` left: every
remaining occurrence is a comment explaining the history for the 167 records
that *were* scored out of 84.

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

## 6. generic-v2 vs v3 — both have now run; the promotion decision is still open

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

Rule 1 eliminated the defect it named — collapsed cardinality **42 → 7**, −83% —
and produced a different one under the same label: **hollow objects 8 → 50**,
one object per entity exactly as instructed, with everything crammed into
free-text `description` while `name`, `id`, `affiliations`, `start_date`,
`end_date` go unused.

⚠️ These are the **classifier** figures from
`notes/form_defect_split_2026-08-03.md`, and they **include the `both` bucket**
(collapsed cardinality 34 + 8 = 42 → 2 + 5 = 7; hollow object 0 + 8 = 8 →
45 + 5 = 50). An arm counted excluding `both` compares against a baseline of 34,
not 42, and is wrong by more than several of the effects being claimed (#461).

Earlier revisions of this section quoted **27 → 0** and **2 → 33**. Those are
the note's *manual read*, which the classifier superseded — the note keeps both
and explains the difference as boundary-drawing, the human retreating to
"unclear" (37 in `other`) where a judge asked one question per value does not
(12). The manual read is why the split was built; it is not the measurement. `collection_timeframes` newly fails form in all four projects;
`creators`, `distribution_formats`, `distribution_dates` in three. Systematic,
not sampling noise.

**Consequence for any rerun:** promoting rule 1 as written reproduces the hollow
-object failure at whatever scale the rerun runs at. Either promote rules 2 and
3 and rework 1, or split the `form` class into collapsed-cardinality and hollow
-object before rerunning, so the next comparison can see what this one could not.
The rules are still **not** in the playbook, so a run today gets v1 behaviour
unless it explicitly selects a condition.

### v3 has run — but on two projects, and never comparably (#458)

This section said v3 was "drafted, wired and tested but unrun", then said it had
"20 runs across four labels". Both were wrong. Fifteen of those twenty are the
2026-08-07 sweep, which hashed the **generic** prompt, not v3 (#454). Here is
every run that actually hashed `d4d_generic_arm_prompt_v3.md`, against the v2
series it would be compared with:

Replicate counts are per project, measured from the provenance records.

| label | prompt | schema digest | route | replicates |
|---|---|---|---|---|
| `2026-07-31_…generic-v2` | v2 | `34d24ff3` (1.0.0) | `google/claude-opus-5-high` | AI_READI 3, CHORUS 3, CM4AI 3, VOICE 3 |
| `2026-08-05_…generic-v3` | v3 | `b065e1cd` (1.0.0) | `google/claude-opus-5-high` | AI_READI 1, CHORUS 1 |
| `2026-08-05_…1m-generic-v3` | v3 | `b065e1cd` (1.0.0) | `claude-opus-5` (1m) | AI_READI 3, CHORUS 1 |
| `2026-08-06_…1m-generic-v3-schema2` | v3 | `583d79c1` (2.0.0) | `claude-opus-5` (1m) | AI_READI 3, CHORUS 3 |
| `2026-08-07_…claudecode-generic-v3` | **generic (v1)** | *none recorded* (2.0.0) | `claude-opus-5` | all five, 3 each |

v3 totals: **AI_READI 7, CHORUS 5, CM4AI 0, VOICE 0, VOICE_PEDIATRIC 0.**

**The v2-vs-v3 comparison is not merely unwritten — it is not derivable.** Three
independent defects, any one sufficient:

1. **Coverage.** CM4AI, VOICE and VOICE_PEDIATRIC have never run under v3, so no
   comparison covering the corpus is possible.
2. **Schema confound.** Every v3 label sits on a different digest than v2's
   `34d24ff3`, and the delta includes the trap-slot work (#376, #382) that moves
   the exact defect classes `form_defects` counts.
3. **Route confound.** Three of four v3 labels ran `claude-opus-5` (1m) where v2
   ran `google/claude-opus-5-high`.

Note the shape of 2 and 3 together: the only v3 series with three replicates on
two projects is `2026-08-06_…1m-generic-v3-schema2`, which is confounded against
v2 on **both** axes at once. The best-powered v3 data is also the most
confounded (#460).

`notes/generic_v3_analysis_plan.md` pre-registered "same four projects, three
replicates, same model and settings as the v1 and v2 series." No label meets it.

**The instrument already enforced this**, which is why it went unnoticed: all
1441 cached fitness judgements are keyed `(34d24ff3, google/claude-opus-5-high)`,
so no v3 record was ever a cache hit and no arms were silently mixed. What the
guard could not do is announce that the arm it protected had never been
generated — an absent cache entry and an absent run look identical.

**Decided, 2026-08-11: generate both arms fresh.** v1 and v3, five projects ×
three replicates = 30 runs, at today's digest `e802cdc3`, on the agentic path,
with instructions rendered rather than typed. Registered in
`notes/generic_v1_v3_analysis_plan.md` before any run. The pairing is v1-vs-v3
rather than v2-vs-v3 because v1 is the playbook default, so that is the
comparison the promotion decision rests on; the mechanism question (does rule 4
alone do what it says?) stays open and needs a v2 arm at the same digest.

Until those runs land the playbook keeps v1 behaviour by default, which is the
safe state but not a decision.

Guards in place:

- v1 is untouched and must stay so — it produced the 2026-07-28 baseline this is
  measured against.
- Tests assert v2 differs from v1 *only* within the marked block, that the block
  names no project, dataset identifier or quantity, and that every project
  receives byte-identical text after mechanical substitution — **for the four
  projects the test hardcodes.** VOICE_PEDIATRIC is not among them, so the
  byte-identity guarantee is unasserted for the fifth project (#467).
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

Landed 2026-08-03, PR #261. **PR #265 merged 2026-08-04.**

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

**The guard is in place** (PR #265): `scripts/check_large_files.py` runs on every
pull request and refuses files over 10 MB, plus a budget on every tracked cache
under `agreement_cache/`. Exercised repeatedly since — the 2026-08-07 sweep
passed it at 290 files / 11.05 MB total, largest 1.34 MB.

---

## 9. Split VOICE into two datasets — done (2026-08-07, PR #395)

`VOICE_PEDIATRIC` is a project as of #298. The companion pediatric dataset has
its own DOI (10.13026/h995-bt35), protocol and Research Ethics Board approval,
and was being represented as a nested object inside VOICE's `related_datasets` —
which is why no VOICE replicate validated (#292).

**Done:** the registry, the shared-corpus declaration, and the schema correction
that made the nested form wrong rather than ambiguous. Adding the fifth project
broke nothing *visible*, and the four-project list is prose in most of the 26
files that carry it.

⚠️ **Not in all of them.** `form_defects._value_index` hardcoded the four as a
runtime list, so any VOICE_PEDIATRIC failure would have attributed as
`unattributed` — silently, since nothing distinguishes "a project we did not
open" from "a value that matched nothing". Fixed to read `PROJECTS` (#463).
Two four-project literals are still live and are *not* prose:
`agreement.DEFAULT_PROJECTS`, and the byte-identity assertion in
`tests/test_download/test_generic_v2_prompt.py` (#467). "Broke nothing" held
because nothing from the fifth project had reached those code paths yet, not
because they were generic.

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
- **A generation run — done.** Both projects were generated in the 2026-08-07
  five-project sweep (`2026-08-07_claude-opus-5-claudecode-generic-v3_rep{1,2,3}`,
  PR #395). `VOICE_PEDIATRIC` was generated from its own 204 KB bundle as its
  own project, which is what the fork was for.

  ⚠️ **Not "under v3", despite the label.** That sweep hashed
  `d4d_generic_arm_prompt.md` — the plain generic prompt (#454, and see §6).
  The run is fine for what this section claims about it; the condition name is
  not.

  **#292 is closed.** All three VOICE replicates validate; `d4d evaluate
  related-datasets` reports 0 defects across the canonical set; and VOICE
  carries the pediatric reference the way the slot intends — `target_dataset:
  https://doi.org/10.13026/h995-bt35`, `relationship_type: references`, a DOI
  rather than an inline object. The enum casing normaliser is on the write path
  and no replicate emitted `related_to`, so the one failure mode a re-run was
  not guaranteed to avoid did not recur.

  **Canonical records now exist for all five projects** (#293, merged
  2026-08-04). VOICE is no longer the gap; `d4d runs canonical` marks
  AI_READI, CHORUS, CM4AI, VOICE and VOICE_PEDIATRIC, all from the 2026-08-07
  label.

  ⚠️ **That label is the one #454 is about.** It ran the generic prompt under a
  `generic-v3` name, carries no recorded instruction (it predates #419), and its
  launch text was not uniform — VOICE and VOICE_PEDIATRIC got a scope paragraph
  the other three projects did not. The records are internally honest: every
  header names `d4d_generic_arm_prompt.md` and says "generic prompt", so only the
  directory label misstates the condition. Within-project replicate variance
  still stands on this set; cross-condition claims do not. It is being superseded
  by the fresh v1 arm in §6, after which these records are annotated and kept as
  historical rather than renamed — renaming 30 records, their provenance paths
  and five canonical marks would assert a uniformity that does not hold.

  **That supersession has not happened yet.** The fresh arm is decided and
  pre-registered (§6), not generated; `e802cdc3` appears in no record and no
  judgement. Until it does, these remain the canonical records and the caveat
  above is the whole of the mitigation.

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

## 10. The six-phase API pipeline hardening — landed, unlogged until now

Roughly thirty PRs between 2026-08-05 and 2026-08-07 that never reached this
file. Recorded here so the thread can be picked up cold.

**Repair loop.** The API runner now repairs invalid records from the validator's
own findings before failing the run (#361), repeating while findings strictly
decrease, up to four rounds (#365), and keeping prior accounting when resuming a
completed run (#363).

**Trap slots.** `d4d runs trap-inventory` mines every record's validation
failures schema-first (#375). The narrative family was scalarized and
`Organization.id` made optional to defuse the commonest traps (#376, #382), and
the post-rerun inventory shows the schema-2 records contributing **zero**
findings (#384).

**Telemetry.** `d4d runs telemetry` collects per-phase process measurements
(#367), excludes quarantined runs and measures invocation gaps end-to-start
(#383), with retroactive reports for the superseded `-high` label and the 7-31
v2 sweep (#368).

**Provenance depth.** Every intermediate phase record is snapshotted and listed
hashed in provenance (#370); an assembly fingerprint is recorded (#353/#359);
and published artifacts are reproduced on the recorded instrument rather than
the live one (#355).

**Prompt/slot discipline.** Slot-filling order — structured slots, then
`description`, `notes` last (#385/#387); a `notes` escape hatch with
only-declared-keys instructions (#380/#381); DCAT distribution slots and the
`source_caveats` evidence channel (#388); and playbook parity so the agentic
paths carry the API pipeline's tuned guidance (#394).

**Not logged as open work** — all merged. Listed because the next person reading
§6 needs to know what changed between v2 and v3 besides the prompt.

---

## 11. Instrument hygiene: the verifiable checker and the test debt — done 2026-08-08

Five PRs (#405, #411, #414, #415, #416) closing seven issues (#404, #406, #407,
#408, #409, #410, #412, #413). The theme: **the instruments were wrong, not the
records.**

`d4d evaluate verifiable` reported 1869/2044 = 91.4% grounded. After four
matcher fixes it reports **1991/2033 = 97.9%**, and — the actual finding —
**no unsupported value anywhere in the sweep**. All 42 remaining ungrounded
values are correct derivations that are simply not literal in the sources
(`publisher: https://dataverse.lib.virginia.edu/`, a host the bundle carries
only as a prefix; `counts: 1600000000` where the bundle says "1.6 Billion").

The four defects, three false-negative and one false-positive:

| defect | values | cause |
|---|---|---|
| trailing-slash URLs | 104 | `normalise` strips the slash, the bundle keeps it, `/` continues a URL |
| delimiter comma read as a thousands separator | 10 | `_CONTINUES["count"]` was `[\d,]`; JSON writes `"size": 123,` |
| abbreviated months | 11 | `renderings` emitted only full month names |
| digit runs inside dotted identifiers | 11 | `extract` applied no boundary rule while `grounded_in` applied a careful one |

The last one moves the **denominator** (2044 → 2033) and four of the eleven had
been counted as *grounded* by coincidence, so it biases the rate the opposite way
to the other three. Both directions had to be settled before any figure from
this check could be quoted.

⚠️ **Rates published from this check before 2026-08-08 are lower bounds.**
Anything quoting the old 91.4%, or comparing arms or replicates on it, should be
re-derived.

**Two guard tests were found asserting the bug they guarded.**
`test_the_known_voice_finding_is_still_detected` claimed three VOICE dates were
"absent from the bundle in any format" and called them the check's first real
positive; all three were present, abbreviated, so the check had no confirmed true
positive on that record. `test_voice_is_absent_rather_than_guessed` rested on
#292 staying open and failed for the best possible reason. Both replaced with
constructed fixtures.

**`d4d runs archive` was destroying documentation** — it rebuilt the ATTIC README
from each invocation, so four archiving runs deleted the rationale for the
2026-04 and 2026-07-23 series (#412). Now appends; the function had no direct
test coverage, which is how a clobbering writer survived.

`make test` went from 5 failures to **1365 passed, 0 failed**, and the working
tree from 23 untracked entries to none.

---

## 12. Pipeline genericity: the launch path, not the code — 2026-08-10

Audited in `notes/PIPELINE_GENERICITY_AUDIT.md` (#418) against the goal of a
pipeline applicable to many kinds of dataset.

**The code is generic.** No project-keyed conditional anywhere in `src/`; all
103 GC-name occurrences are registries, defaults or prose. Every generic
prompt's *body* is free of GC and domain terms, and `prompt_body()` discards the
header where the names live. A sixth dataset needs no code change.

**The launch path was not.** Agentic runs are not launched from the prompt file
— they were launched from a hand-composed task prompt, and the VOICE run of
2026-08-07 was sent a `CRITICAL SCOPE BOUNDARY` paragraph naming the project,
the pediatric dataset and #292. Factual disambiguation plus a quality warning,
both excluded from the generic condition by the repository's own taxonomy, and
invisible to the prompt-condition tests because they inspect the file rather
than what was sent.

Acted on the same day:

| finding | issue | status |
|---|---|---|
| bundles carried curator prose, unequally per project | #421 | **fixed** (#424) |
| re-recording discarded the validation verdict | #396 | **fixed** (#423) |
| the launch prompt was typed, not rendered | #419, #422 | **addressed** (#425) |
| per-GC scope lived in the launch prompt | #422 | **closed** — declared in the manifest |
| label says `generic-v3`, provenance hashes v1 | #420, #454 | check landed; records **not yet** superseded — §6's fresh v1 arm is decided, not run |
| v3 never ran on 3 of 5 projects; every v3 label confounded | #458 | open — gates §6 |
| `verification_url` still injected; 0 values depend on it | #427 | open, cosmetic |
| a verdict does not pin the schema it was reached against | #426 | **fixed** |
| the render gate cannot see an edit made *before* rendering | #432 | **closed** |

**What #424 caught.** 4 values in the canonical sweep were grounded only by a
curation note, all the same DOI — `10.60775/fairhub.4`, cited by AI_READI
records. It names FAIRhub's "Mini Version", which appears in **no source
document**; the manifest mentions it only to say it was *not* captured. All five
bundle hashes changed; `source_manifest.yaml: bundle_hash_history` maps
before/after, because 55 provenance records reference the old ones.

**What was left, and is now built.** Rendering made intervention *avoidable*;
the render gate (#429) made an instruction edited after rendering *detectable*;
the canonical prompt registry (#432) closes the remaining direction — an edit
made to the prompt file *before* rendering, which re-renders to itself and
reports `match`. Three comparisons now: the recorded instruction, a fresh
render, and the hash this repo declared for that condition
(`src/download/prompts/canonical_hashes.yaml`).

The registry is not tamper-proofing and does not claim to be — anyone who can
edit a prompt can rotate its pin. What it buys is that the two are separate,
deliberate acts, and a rotation leaves a dated line with a stated reason in a
small file, rather than a paragraph inside a 200-line prompt.

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
