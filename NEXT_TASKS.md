# Next tasks

Open work, most blocking first. Each item states what is true now, not only what
should happen, so an item can be checked rather than believed.

Last verified: 2026-07-29.

---

## 1. Merge PR #179 — blocks reproducibility from a clone

`cborg-provider` carries the CBORG generation path, the scoring modules, the
reasoning capture and the playbook's prompt-condition section. Until it lands,
**a clone of `main` cannot reproduce any of the 2026-07 results.**

Missing from `main` today:

| path | status |
|---|---|
| `src/data_sheets_schema/evidence_score.py` | branch only |
| `src/data_sheets_schema/reasoning.py` | branch only |
| `src/data_sheets_schema/merge.py` | branch only |
| `.claude/commands/d4d-full-core.md` → Prompt Conditions | branch only |

Already on `main`: the source manifest, the four preprocessed bundles, the
playbook, the provenance guard, `fetch.py`, `api_runner.py`, `schema_digest.py`,
`runs.py`, and the crate `raw/` inputs (29 files; only the extracted `crate/`
tree is gitignored).

---

## 2. Make the live provenance record enforced, not just requested

`d4d-full-core.md` lists it as a completion criterion — *"The live provenance
record is present and its `record_mode` is `live`"* — but nothing checks it.
`record_mode` appears nowhere in `src/` outside `provenance.py`, so a run that
never writes one still completes and still gets analysed.

The corpus shows the effect:

```
record_mode:  live 49,  reconstructed 59
complete runs 98,  without any provenance record 0
```

Every run has *a* record, but most were backfilled afterwards. A reconstructed
record cannot attest to conditions nobody observed, which is the whole point of
requiring a live one.

Concretely: add `live` to what `is_complete()` or a `d4d runs audit` command
gates on, so a run lacking a live record is reported as incomplete rather than
silently pooled with runs that have one. Note this will reclassify 59 existing
runs — that is the correct outcome, but it changes every downstream count and
should land deliberately rather than as a side effect.

---

## 3. Unblock merged records from shipping (#176, step 2)

Step 1 is **done** — feasibility measured across all four projects, results in
#176. Guarded merge validates everywhere and gains +0.023 to +0.042 mean fitness;
the coverage gain is only +1 to +4 slots, so the case for merging rests on
shared-field quality, not coverage.

Two things block a merged record from being usable, neither of them measurement:

- **`provenance.py` cannot express "consumed other generated records."** A merged
  record therefore cannot honestly claim `record_mode: live`, and claiming it
  would be the unobserved provenance assertion that module exists to prevent.
  Needs a `derived_from` block naming every contributing label and md5.
- **The playbook forbids cross-label reads in four places.** A merged record is
  cross-label by definition and needs an explicit carve-out, not a quiet
  exception.

Artifacts are under `data/d4d_concatenated/claudecode_agent_merged/` with a
README marking them non-shippable.

## 4. Fix rubric20's stub scoring

`src/evaluation/evaluate_d4d.py:352-361` returns literally 0 or 4, never 1/2/3/5.
This is why rubric20 reports 71/88 for every record in the corpus and cannot rank
anything. Independent of all other work.

---

## 5. Complete the generic arm (#166)

`de_novo` and `crate_only` are unrun under the generic prompt — 18 runs. Until
they exist, generic-vs-tuned comparisons cover the baseline arm only.

---

## 6. Feed fitness failures back into generation

Fitness scoring found systematic defects across all four projects that grounding
rated ≥0.95. The `form` cluster looks like one prompt or schema-digest fix
affecting many fields:

- `creators` — ~47 people collapsed into 2 objects
- `intended_uses` — 4 distinct uses in 1 object
- `other_tasks`, `existing_uses` — same shape

The `substance` cluster is different: values that assert documentation exists
without supplying it (`cleaning_strategies`: "QC is pending"). AI-READI is
substance-dominated, CM4AI form-dominated, so a single fix will not cover both.

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
