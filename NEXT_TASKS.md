# Next tasks

Open work, most blocking first. Each item states what is true now, not only what
should happen, so an item can be checked rather than believed.

Last verified: 2026-07-29.

---

## 1. Decide whether to archive reconstructed-provenance runs

**Not urgent, and deliberately not done automatically.** `d4d runs archive
--reconstructed` moves runs whose provenance was backfilled rather than observed
into `data/ATTIC/`, taking them out of `discover()` and therefore out of every
analysis. Nothing is deleted; `d4d runs restore` is the same move reversed.

Dry run today: **52 run directories across 17 labels.** What leaves the active
corpus:

| series | records | what is lost |
|---|---|---|
| `2026-07-27_claude-opus-5` | 24 | **the entire tuned arm** |
| `2026-07-23_gpt-5.5-high-fast` ×3 | 12 | GPT-5.5 comparison |
| `2026-07-23_gpt-5.6-sol-ultra-fast` | 4 | GPT-5.6 comparison |
| `2026-04-10_sonnet-4.6` | 4 | sonnet baseline |
| `crateonly-denoised`, `programme-deprimed` | 9 | partial arms |

What remains is one model under three prompt conditions on a single date.
Generic-vs-tuned becomes impossible, because tuned has zero live runs.

**The lighter option is already in place and needs no decision.** `compare` and
`arm_delta` take `--require-live`, off by default, and always report the
live/reconstructed split whether or not it is set — so a permissive result can
never look uniform, and the strict view is one flag away. Prefer that unless
there is a reason to shrink the corpus itself.

Deterministic mappings and the merged records are excluded from `--reconstructed`
selection: the former are not stochastic generations, and the latter have *no*
provenance for a known and tracked reason (item 3), which archiving would
misrepresent as unattestable.

---

## 2. Enforce live provenance for *new* runs

`d4d-full-core.md` lists it as a completion criterion — *"The live provenance
record is present and its `record_mode` is `live`"* — but nothing checks it.
`record_mode` is not consulted in `src/` outside `provenance.py` and the
reporting added above, so a run that never writes one still completes.

Corpus today: **49 live, 59 reconstructed.** Gating going forward is what stops
that ratio moving in the wrong direction. Gating backward is item 1, and is a
different and much more expensive decision.

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
