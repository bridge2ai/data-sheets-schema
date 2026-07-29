# D4D Generation Arms — measuring what upstream structured metadata adds

**Date:** 2026-07-24 (updated 2026-07-28)
**Encoded in code:** `GENERATION_ARMS` in `src/data_sheets_schema/constants/methods.py`

> **⚠️ Headline conclusions below the "Comparison" heading were measured with
> primed prompts and are superseded.** The de-primed replication completed
> 2026-07-28 (label `2026-07-28_claude-opus-5-deprimed_rep{1,2,3}`, 18 runs)
> changes the verdict for VOICE from *marginal* to **not resolvable** and for
> CHORUS from *real* to **marginal**. Read
> [De-primed replication](#de-primed-replication--2026-07-28) first; treat the
> 2026-07-27 figures as a primed condition, not as the result.

Five arms measuring what upstream structured metadata — RO-Crate packages, and
AI-READI's Healthsheet — contributes to a D4D record beyond the documents.
Arms are defined in constants rather than prose alone, so the input paths the
runner uses and the design described here cannot drift apart.

## The arms

| Arm | Method | Model? | Input | Measures |
|-----|--------|--------|-------|----------|
| **baseline** | `claudecode_agent` (+`_core`) | yes | `{project}_preprocessed.txt` | what the document corpus alone supports |
| **deterministic_upstream** | `rocrate_mapped` | **no** | `{project}_crate_d4d.yaml` | fidelity of **upstream's** crate→D4D mapping |
| **deterministic_ours** | `rocrate_static_map` | **no** | `{project}_crate_mapped_d4d.yaml` | fidelity of **our** mapping table, with per-field declared quality |
| **healthsheet_only** | `claudecode_agent_healthsheet` | yes | `{project}_healthsheet_only.txt` | **AI-READI only** — what one structured source yields alone |
| **de novo** | `claudecode_agent_crate` (+`_core`) | yes | `{project}_preprocessed_with_crate.txt` | extraction — what an agent recovers from documents **plus** crate evidence |

### Two deterministic arms, not one

They consume different things and can therefore claim different things:

- **`deterministic_upstream`** repairs `ro-crate-linkml.yaml`, a D4D-shaped
  rendering produced upstream. It runs only where upstream ships one — so **not
  for VOICE** — and is opaque about how good each mapping is.
- **`deterministic_ours`** (`d4d rocrate map`) reads `ro-crate-metadata.json`,
  which every crate has, and applies
  `data/ro-crate_mapping/d4d_rocrate_interface_mapping.tsv` (136 rows). It runs
  for **all three crates**, and every filled field carries its declared SKOS
  mapping type and information loss, so the result is graded rather than flat.

Keeping both is what makes the comparison possible; collapsing them under one
method name would have hidden that they measure different mappings.

### Running both mappings diagnosed the table — and fixed it

Comparing the two arms surfaced defects in our mapping table that neither arm
would have revealed alone. Table went **133 → 136 rows** on 2026-07-27.

| | upstream fills | ours (before) | ours (after) | upstream-only remaining |
|---|---|---|---|---|
| CHORUS | 21 | 28 | **32** | 2 |
| CM4AI | 26 | 34 | **42** | 1 |
| VOICE | n/a | 39 | **44** | — |

Counts are top-level slots in the emitted record. `d4d rocrate map` separately
reports *filled table rows* — CHORUS 32, CM4AI 42, VOICE 48 — which is higher
for VOICE because several rows populate nested objects rather than new
top-level slots.

**Added (3)** — present in all three crates, absent from the table:
`Dataset.name`, `Dataset.citation`, `Dataset.total_size_bytes`.

**Prefix corrections (5)** — the systematic defect: the table declared a
prefixed or unprefixed property name that no crate emits. Found by sweeping
every `@graph[?@type='Dataset'][...]` row against all three crate roots, not by
chasing them one at a time.

| Row | Table declared | Crates emit | Applied |
|---|---|---|---|
| `created_by` | `creator` | `author` | ✅ |
| `ethical_reviews` | `rai:ethicalReview` | `ethicalReview` | ✅ |
| `prohibited_uses` | `rai:prohibitedUses` | `prohibitedUses` | ✅ |
| `discouraged_uses` | `rai:prohibitedUses` | `prohibitedUses` | ✅ |
| `collection_timeframes` | `d4d:dataCollectionTimeframe` | `rai:dataCollectionTimeframe` | ✅ |
| `is_deidentified` | `rai:confidentialityLevel` | `confidentialityLevel` | ❌ see below |
| `vulnerable_populations` | `rai:atRiskPopulations` | `d4d:atRiskPopulations` | ❌ see below |

Every applied fix changed **only** the property name. Target slot, SKOS relation
and information-loss annotation were left untouched — those encode reviewed
judgment, and altering them would change what the arm measures.

### Two left deliberately unfixed

- **`Dataset.is_deidentified`** — the prefix is wrong, but correcting it would
  newly populate the field with semantically wrong content. Its range is
  `Deidentification` (slots: `method`, `identifiers_removed`,
  `identifiable_elements_present`), while `confidentialityLevel` holds an
  access classification: `"HL7:2V (very restricted)"`, `"Unrestricted"`,
  `"Limited dataset available with Data Use Agreement"`. That is not a
  de-identification statement. The crates *do* carry a separate `deidentified`
  boolean, which is the semantically right source — but choosing it, and
  deciding how a boolean lands in a `Deidentification` object, is a mapping
  decision rather than a typo fix.
- **`Dataset.vulnerable_populations`** — `vulnerable_populations` is **not a
  slot on `Dataset`** at all, so the row is `unplaceable` regardless of its
  path. It looks like a stale reference to a renamed or removed slot; it needs
  re-targeting, not a prefix change.

### What remains upstream-only, and why it is correct

- **`conforms_to`** (all projects) — `conformsTo` is genuinely absent from every
  crate graph. Upstream's rendering carries `conforms_to: D4D Schema` because
  that file self-declares its own conformance, not because the crate states it.
  Our row is right; the data is simply not there. *(An earlier revision of this
  note listed this as a path mismatch. It was not.)*
- **`total_size_bytes`** (CHORUS, VOICE) — deliberately mapped from
  `evi:totalContentSizeBytes`, which only CM4AI carries. The alternative,
  `contentSize`, is a rounded human string: CHORUS's exact size is
  1,319,413,953,331 bytes but `"1.2 tb"` parses to 1.2e12 — a ~9% error dressed
  as an exact byte count. Reporting the field empty is the honest outcome.

## Why the two with-crate forks must not share an input

This is the load-bearing design decision.

The crates ship `ro-crate-linkml.yaml`, an upstream-authored rendering that is
*already* D4D-shaped — it declares `conforms_to: D4D Schema` and uses our slot
names. The deterministic fork consumes exactly that (repaired). If the de novo
fork were handed the same artifact, it would be transcribing a finished record
rather than extracting from evidence, and the two forks would collapse into one
measurement wearing two labels.

So the de novo fork gets **crate evidence, not crate conclusions**:

**Included** — `{project}_crate_metadata_reduced.json` (the substantive
`rai:*` limitations/biases, ethics, IRB, access conditions, maintenance plan,
provenance), and `ai_ready_score.json`.

**Withheld** — `{project}_crate_d4d.yaml` (the deterministic fork's own output),
`ro-crate-linkml.yaml` (upstream's D4D-shaped mapping), `ro-crate-datasheet.html`
(an upstream-authored datasheet — the very artifact being generated), and the
`ro-crate-preview.html` file listings.

The exclusion is **enforced in code**, not just documented: `DE_NOVO_EXCLUDE` in
`rocrate_normalize.py`, with `assert_de_novo_safe()` raising `DeNovoPolicyError`
if a withheld artifact would ever reach the bundle. Four tests cover it, plus
one that asserts the include and exclude lists are disjoint.

Verified on the built bundle: the normalizer-only marker
`urn:d4d:org:university-of-virginia` and the linkml marker
`conforms_to: D4D Schema` are both absent from
`CM4AI_preprocessed_with_crate.txt`.

Each bundle also names, in its own header, every artifact that was withheld and
why — so the omission is visible to anyone reading the input rather than being a
silent filter.

## Running the arms

```bash
# once per crate refresh
d4d rocrate normalize                       # -> {PROJECT}/processed/
d4d rocrate bundle                          # -> {PROJECT}_preprocessed_with_crate.txt

# deterministic arms (no model, seconds)
d4d rocrate map                             # our mapping -> {PROJECT}_crate_mapped_d4d.yaml
d4d rocrate emit-arm     --version 2026-07-24_deterministic-v1   # upstream's mapping
d4d rocrate emit-map-arm --version 2026-07-27_ourmap-v2          # our mapping

# healthsheet-only input (AI-READI, no model)
d4d healthsheet bundle                      # -> AI_READI_healthsheet_only.txt

# baseline and de novo arms (model, via the four-phase playbook)
/d4d-full-core 2026-07-24_claude-opus-5             # baseline
/d4d-full-core 2026-07-24_claude-opus-5-crate       # de novo, crate-augmented input
```

Both emit commands refuse to overwrite a populated version directory (exit 1),
matching the playbook's "never overwrite a published run" rule.

## Status

| | CHORUS | CM4AI | VOICE | AI_READI |
|---|---|---|---|---|
| Crate ingested | ✅ | ✅ | ✅ supplied locally 2026-07-27 | none yet — expected |
| Normalized | ✅ | ✅ | ✅ | — |
| Crate-augmented bundle | ✅ 66 KB | ✅ 490 KB | ✅ 728 KB | — |
| Healthsheet-only input | — | — | — | ✅ 56 KB, 84 questions |

### Results by arm — populated top-level slots (full / core)

Every model arm produces a **paired full + core record**. Cells read
`full/core`, one per replicate (`rep1  rep2  rep3`), all from byte-identical
prompts and inputs. Deterministic arms are idempotent, so they carry a single
figure and produce **full records only** — the crate renderings map to
`Dataset`, and no core counterpart is generated.

Ceilings differ: `Dataset` has **94** induced slots, `CoreDataset` has **79**.
A core record is the semantic exchange-layer subset, so it is always smaller;
that is by design, not loss.

| Arm | Model? | CHORUS | CM4AI | VOICE | AI_READI |
|---|---|---|---|---|---|
| **baseline** | yes | 53/48  54/48  53/47 | 76/68  84/72  81/71 | 75/63  75/64  75/64 | 81/66  84/69  82/68 |
| **de_novo** (with crate) | yes | 75/64  70/63  73/63 | 84/72  70/66  83/71 | 81/71  85/72  83/72 | n/a — no crate |
| **healthsheet_only** | yes | n/a | n/a | n/a | 66/56  69/58  69/57 |
| **deterministic_upstream** | no | 21 (full only) | 26 (full only) | n/a — no `ro-crate-linkml.yaml` | n/a |
| **deterministic_ours** | no | 32 (full only) | 42 (full only) | 44 (full only) | n/a |

Arms restricted to a single project are shown rather than omitted:
`healthsheet_only` runs only for AI-READI, which is the sole GC publishing a
Healthsheet; `deterministic_upstream` cannot run for VOICE, whose crate ships no
upstream D4D rendering. Those `n/a` cells are results — they record that the
arm is inapplicable, not that it was skipped.

The deterministic arms are **not comparable to the model arms** on this scale.
They populate only what their crate states in D4D terms (21–44 of 94) with no
inference at all, so a low figure is the expected outcome and not a deficiency.
Their value is as a precision reference for what the crate actually asserts.

### Core tracks full closely, and every pair reconciles

Core/full ratios sit in a band of **0.815–0.943** across all 16 completed pairs,
with no arm or project systematically out of line. Core is not lagging behind
full anywhere. The extremes are AI-READI baseline rep1 (81/66) at the low end
and CM4AI de_novo rep2 (70/66) at the high end.

All 16 pairs pass `d4d_pair_consistency` at **76 schema-identical slots**, run
without `--sync-core` as an independent check. The recurring
`file_collections ↔ distributions` warning is expected — those are related but
non-identical representations that Phase 4 reviews semantically, and every
reconciliation report documents that review.

One asymmetry worth noting: `subsets`, `file_collections`, `total_file_count`,
`total_size_bytes`, `variables`, `citation` and several others exist on
`Dataset` but not on `CoreDataset`, so a crate contribution landing in those
slots raises the full count without moving core. CHORUS de_novo rep1 is the
clearest case — full gained 22 slots over baseline while core gained 16.

### Crate contribution: de_novo minus baseline, paired within replicate (full / core)

All three replicates complete. Deltas are computed within a replicate, so
run-to-run variation partly cancels. `noise` is the larger of the two arms'
three-way disagreement.

| | rep1 | rep2 | rep3 | noise | verdict |
|---|---|---|---|---|---|
| **CHORUS** | +22/+16 | +16/+15 | +20/+16 | ±13 | **real — clears the band in all three** |
| **VOICE** | +6/+8 | +10/+8 | +8/+8 | ±7 | **real on core** (+8, +8, +8); marginal on full |
| **CM4AI** | +8/+4 | −14/−6 | +2/0 | ±20 | **not resolvable — sign flips** |

AI-READI has no crate, so it runs the analogous comparison for its own
structured source — full corpus minus healthsheet-alone. It is the
best-powered contrast in the set, because its baseline is the most stable
measurement anywhere (4 varying slots, 95.2% agreement):

| | rep1 | rep2 | rep3 | noise | verdict |
|---|---|---|---|---|---|
| **AI_READI** (corpus − healthsheet) | +15/+10 | +15/+11 | +13/+11 | ±10 | **real** |

Note the asymmetry: **no slot appeared in a healthsheet run that was missing
from the corresponding baseline, in any replicate** (0, 0, 0). The healthsheet
is a strict subset of what the full corpus supports — it never contributes
anything the other nine sources miss.

### Combined result — all four projects

One row per project. **The contrast runs in opposite directions**, and the rows
are not interchangeable:

| | Smaller arm | Larger arm | What is being added |
|---|---|---|---|
| CHORUS, CM4AI, VOICE | `baseline` — documents only | `de_novo` — documents **+ crate** | a structured metadata package added to prose |
| AI_READI | `healthsheet_only` — one source | `baseline` — all 10 documents | nine documents added to a structured source |

So the crate rows ask *what does structured metadata add to documents?* and the
AI-READI row asks the inverse, *what do documents add to structured metadata?*
Arithmetically both are `larger − smaller`; conceptually they are mirror images.
**Do not average these rows.**

Two clarifications the table has previously invited confusion on:

- `baseline` is **documents only, for every project** — no baseline bundle
  contains crate content (verified: zero `CRATE EVIDENCE` sections in all four).
- AI-READI has no `de_novo` row because it has **no RO-Crate**, so no
  crate-augmented bundle exists. It is pending, not omitted.
- AI-READI's `baseline` *includes* the healthsheet as one of its 10 sources,
  which is precisely why subtracting `healthsheet_only` isolates the other nine.

| Project | Contrast | Δ full (rep1,2,3) | Δ core (rep1,2,3) | Noise | Stable added slots | Verdict |
|---|---|---|---|---|---|---|
| **CHORUS** | de_novo − baseline *(crate added)* | +22, +16, +20 | +16, +15, +16 | ±13 | **12** | **real** |
| **AI_READI** | baseline − healthsheet *(9 docs added)* | +15, +15, +13 | +10, +11, +11 | ±10 | **8** | **real** |
| **VOICE** | de_novo − baseline *(crate added)* | +6, +10, +8 | **+8, +8, +8** | ±7 | 4 | **real on core** |
| **CM4AI** | de_novo − baseline *(crate added)* | +8, −14, +2 | +4, −6, 0 | ±20 | **0** | **not resolvable** |

Ordered by strength of evidence. `Noise` is the larger of the two arms' three-way
varying-slot count. `Stable added slots` counts slots present in the larger arm
and absent from the smaller one in **all three** replicates — the figure that does
not depend on a count clearing a threshold.

Read the last two columns together. CHORUS and AI-READI show both a delta above
noise *and* a substantial reproducible field set. VOICE shows a small but
perfectly stable core delta with only 4 stable fields. CM4AI shows neither: its
delta changes sign and **no** slot is consistently attributable to its crate.

### The reproducible result is a field set, not a delta

Slot-count deltas proved fragile. What survives three replicates is *which*
slots came only from the crate in **every** run:

| | crate-only per replicate | stable across all three |
|---|---|---|
| **CHORUS** | 22, 19, 21 | **12** — `anomalies`, `citation`, `discouraged_uses`, `doi`, `informed_consent`, `ip_restrictions`, `issued`, `license`, `prohibited_uses`, `total_file_count`, `total_size_bytes`, `version` |
| **VOICE** | 8, 10, 8 | **4** — `created_by`, `doi`, `imputation_protocols`, `version` |
| **CM4AI** | 11, 1, 6 | **0** |
| **AI_READI** (corpus vs healthsheet) | 15, 15, 13 | **8** — `at_risk_populations`, `conforms_to_schema`, `download_url`, `file_collections`, `issued`, `keywords`, `total_file_count`, `total_size_bytes` |

AI-READI's eight are the reproducible boundary of what a Healthsheet can carry:
file and distribution structure, discovery metadata, and lifecycle dates. The
healthsheet arm's rep1 gap list named 15 items; only 8 recur in all three runs.
The other 7 (`citation`, `conforms_to`, `language`, `prohibited_uses`,
`subsets`, …) are borderline calls where runs disagree about whether the source
supports an assertion — those describe the reader, not the source.

CM4AI's zero is the strongest form of the negative result: across three runs, not
one slot was consistently attributable to its crate. This confirms the
redundancy finding — its crate restates Dataverse text already in the corpus —
by a route independent of the phrase-overlap test that first suggested it.

Roughly half of each project's crate-attributed slots are stable and half are
run-dependent, matching the judgment-variance pattern seen throughout.

### Core is the steadier instrument

Core deltas move far less than full ones:

- CHORUS: core +16, +15, +16 while full swings 22→16→20
- VOICE: core **+8, +8, +8** — invariant — while full moves 6→10→8

`CoreDataset` (79 slots) is smaller and more constrained than `Dataset` (94), so
it absorbs less judgment variance. Where full and core disagree on whether an
effect is real, core is the more reliable read. This inverted the VOICE verdict:
marginal on full, unambiguous on core.

Full-only slots explain the magnitude gap — `subsets`, `file_collections`,
`total_file_count`, `total_size_bytes`, `variables` and `citation` exist on
`Dataset` but not `CoreDataset`, so crate content landing there moves full
without moving core.

### CM4AI follow-up: pinning the referent (2026-07-28)

CM4AI's 2026-07-27 result was `not resolvable` because runs disagreed about
**what the dataset is** — rep2 modelled the release *programme* (4 releases as
`resources`, 0 `file_collections`), rep1/rep3 modelled the *June 2026 release*
(9 modality sub-crates as `resources`, 10 `file_collections`). CM4AI is the only
project with three decomposition layers (programme → 4 releases → 10
modalities), and `Dataset` forces one referent.

A follow-up condition pinned it: **the subject is the quarterly release
programme**, releases are `resources`, and `file_collections` must still describe
the current release. Label `2026-07-28_claude-opus-5-programme-deprimed_rep{1,2,3}`,
6 runs, both arms. The prompts were also **de-primed** — every expectation
statement removed ("expected to be largely redundant", "do not manufacture
novelty", the crate data-quality warnings).

**The pin held in all six runs**: 4 release resources, 10 `file_collections`,
empty top-level `doi`/`version`/`issued`/`total_size_bytes`. Structural variance
was eliminated. It also achieved what neither original model did — the programme
framing *with* the file inventory retained.

| | unpinned + primed | pinned + neutral |
|---|---|---|
| baseline counts | 76, 84, 81 | 63, 69, 60 |
| crate counts | 84, 70, 83 | 65, 69, 69 |
| **deltas** | +8, **−14**, +2 | **+2, 0, +9** |
| noise (three-way) | ±20 | **±16** |
| baseline agreement | 88.2% | **77.8%** |
| crate agreement | 77.0% | **92.9%** |
| stable crate-only slots | 0 | **0** |
| verdict | not resolvable | **not resolvable** |

Three findings:

1. **The pin fixed the pathology, not the verdict.** Deltas stopped changing
   sign and noise fell modestly (±20 → ±16 three-way), but the effect shrank
   faster than the noise. `+2, 0, +9` against ±16 is not demonstrable — one
   replicate is exactly zero. CM4AI's crate
   now has **two independent conditions** showing no reproducible slot-level
   contribution, which is stronger evidence than either alone.

2. **Pinning helped the arm that needed it.** Crate-arm agreement rose 77.0% →
   92.9%, because the crate arm carried the worst structural ambiguity (its ten
   modality sub-crates were the third layer). Baseline agreement *fell*
   88.2% → 77.8%.

3. **De-priming probably increased variance, and that is uncomfortable.** Two
   variables changed at once, so this is not separable. But the baseline losing
   ~18 slots and 10 points of agreement is consistent with the primed prompts
   having *suppressed* judgment variation — every run agreeing with the prompt
   rather than with each other. If so, **the 2026-07-27 noise floors across all
   arms are understated**, since every prompt in that series carried directive
   language. Testing this needs a pinned + primed condition, which was launched
   and then killed in favour of de-priming.

**Prompt-priming confound (applies to the whole 2026-07-27 series).** Each
project's prompt carried custom content, and some of it stated expectations:
CHORUS and VOICE crate arms were told the crate was "expected to be genuinely
additive"; CM4AI's was told "largely redundant"; CHORUS baseline was told to
"prefer omission over inference"; the healthsheet arm was told "sparse output is
the correct result". The reported ordering (CHORUS ≫ VOICE ≫ CM4AI) matches the
priming.

Measured extent for CHORUS: of its 12 stable crate-only slots, only **1**
(`total_size_bytes`) corresponds to content named in the prompt. The named items
(IRB `#2022P000707`, `HL7:2V`, "no DICOM", DUA) appear in the records but land in
slots the baseline also populated, so they are not in the stable set. **The
field-set findings are therefore largely robust to the priming; the deltas are
not.**

### Replicate agreement — three-way

Fraction of slots present in **all three** replicates. Three-way agreement is
necessarily lower than pairwise; the pairwise figures reported mid-series were
optimistic and are superseded here.

| Arm | CHORUS | CM4AI | VOICE | AI_READI |
|---|---|---|---|---|
| baseline | 84.2% | 88.2% | 91.0% | **95.2%** |
| de_novo | 83.3% | **77.0%** | 91.9% | n/a |
| healthsheet_only | n/a | n/a | n/a | 86.3% |

Range 77–95%, i.e. **a working noise floor of 7–20 varying slots**. The crate
arm is consistently noisier than baseline for the same project: more evidence
means more judgment calls about what it supports.

**Slot count badly overstates stability.** VOICE's baseline scored exactly 75
slots in all three replicates while 7 slots differed; CHORUS's scored 53, 54, 53
with 9 differing. Any check based on record size would report near-perfect
reproducibility for both.

| Arm | CHORUS | CM4AI | VOICE | AI_READI |
|---|---|---|---|---|
| baseline | 91.1% | 88.2% | 94.8% | 96.4% |
| de_novo | 85.9% | — | 93.0% | n/a |
| healthsheet_only | n/a | n/a | n/a | 90.1% |

VOICE's baseline scored 75 slots in both replicates while four slots differed —
identical counts, different content. Slot count alone would have read as perfect
reproducibility.


### VOICE and the missing upstream rendering — resolved

CHORUS and CM4AI ship `ro-crate-linkml.yaml`; the VOICE crate does not, so
`deterministic_upstream` cannot run for VOICE and is reported as not applicable
rather than substituted.

This was the reason for building `deterministic_ours`: it reads
`ro-crate-metadata.json`, which VOICE does have, so VOICE now has a deterministic
arm — under its own method name, so it is never confused with upstream's
mapping. VOICE actually fills the most table rows of the three (48), because its
crate carries the richest `rai:` set.

Asking the crate producers for a VOICE `ro-crate-linkml.yaml` is still worth
doing; it would restore the fourth cell of the comparison.

Also note the VOICE crate describes **PhysioNet v3.0.0**, while the document
corpus prefers **v3.1.0**. Crate-derived facts are evidence about 3.0.0, and any
version-sensitive comparison (participant counts, file inventories) must account
for that.

## AI-READI's corpus now contains a datasheet

Added 2026-07-27: `fairhub_dataset_v3_api` brings an **84-question healthsheet
(81 answered)** into the AI-READI document corpus — motivation, composition,
collection, preprocessing, labeling, uses, distribution, maintenance.

This is legitimate published documentation and belongs in the corpus. But note
the tension with the rule applied one section up: `ro-crate-datasheet.html` is
withheld from the de novo fork precisely *because* a datasheet is the artifact
being generated. A healthsheet is a datasheet, in the same Gebru-derived
lineage the D4D schema comes from.

The difference is one of role, not kind. The crate datasheet is withheld from a
**fork designed to isolate extraction from transcription**. The healthsheet
enters the **baseline corpus**, which has no such isolation requirement — the
baseline is meant to represent what the cited sources actually say, and FAIRhub
is a cited source that genuinely says this.

The consequence is still real and should be stated when results are reported:
**for AI-READI, part of the baseline arm is transcription rather than
extraction.** A high AI-READI baseline score is therefore not comparable to a
high CHORUS baseline score — CHORUS's corpus contains no datasheet-shaped
source. This is a per-project property of the corpus, not a property of the
method, and it is a fifth reason not to aggregate scores across projects.

### Decision 2026-07-27: keep it in the corpus, do not split the bundle

An earlier revision of this note recommended splitting the healthsheet out of
the AI-READI corpus so its baseline would match the other projects'. **That
recommendation is withdrawn.**

The reasoning behind it treated cross-project comparability as the thing to
optimize. But only one GC publishes a Healthsheet, and the corpus is meant to
represent *what upstream actually publishes for each project*. Removing a real,
cited source to make four projects look alike would make AI-READI's baseline
less true, not more comparable — it would measure a corpus that does not exist.

The asymmetry is therefore documented rather than engineered away. The
comparability caveat above stands in full; it is a fact about the projects, not
a defect to be corrected.

## Arm: healthsheet-only (AI-READI)

Instead of splitting the corpus, the healthsheet supports an **additional** arm:
generate a D4D record from the Healthsheet **alone** — no publications, no
documentation, no license, no IRB protocol.

- Input: `data/preprocessed/concatenated/AI_READI_healthsheet_only.txt`
  (`d4d healthsheet bundle`), 56 KB, 14 sections, 84 questions, 81 answered
- Method: `claudecode_agent_healthsheet`
- Restricted in code to `AI_READI` via `GENERATION_ARMS[...]["projects"]`, since
  no other GC has a healthsheet to run it on

**What it measures:** the standalone sufficiency of one structured upstream
source. That makes it the model-based counterpart to `deterministic_ours` —
both ask "how far does a single upstream structured artifact get you?", one by
static mapping over a crate, one by generation over a healthsheet.

The 3 unanswered questions (`composition:13`, `preprocessing:1`,
`maintenance:3`) are rendered explicitly as `(no response provided)` rather than
omitted, so the input's own coverage gaps are visible to the generator and in
any later audit.

**It is not a baseline substitute**, and the bundle header says so in its own
text: AI-READI's baseline remains the full corpus. Comparing healthsheet-only
against AI-READI's baseline measures what the other 9 sources add on top of the
healthsheet — a within-project comparison that is clean, because the corpus
snapshot is identical apart from the input restriction.

## Pending: AI-READI RO-Crate

An AI-READI crate is expected. When it lands, AI-READI gains
`deterministic_ours` and `de_novo` (and `deterministic_upstream` if the crate
ships `ro-crate-linkml.yaml`), making it the only project able to run every
arm — five in total.

Two things to get right at that point:

1. **AI-READI's de novo bundle will contain both the healthsheet and the
   crate**, because the healthsheet is a standard corpus source. Its de novo arm
   will therefore not be the same experiment as CHORUS's or VOICE's. Expect a
   smaller crate delta for AI-READI, since the healthsheet may already cover
   what the crate would add.
2. **Run `d4d rocrate map` and re-check redundancy** as was done for the other
   three: whether the crate's content is already present in the corpus is the
   question that decides whether AI-READI is an informative case or another
   near-null like CM4AI. With a healthsheet already in the corpus, near-null is
   the more likely outcome.

## Reading the results honestly

Five things will otherwise be misread:

1. **The deterministic arm is not a competitor.** It can only populate fields the
   crate covers — 21 top-level slots for CHORUS, 26 for CM4AI, against the 94
   available on `Dataset`. Low coverage is the expected result, not a failure. It
   is a **floor and a precision reference**: whatever it states came from the
   crate verbatim, so it is the arm to check the other two *against*, not rank
   beside.

2. **Only two projects have crates.** AI_READI and VOICE can currently run the
   baseline arm only. Any cross-project aggregate mixing crate and non-crate
   projects will be confounded.

3. **Two of the three arms are stochastic** (`STOCHASTIC_ARMS`). A baseline-vs-de
   novo difference on a single run is not evidence of a crate contribution
   until it survives a repeat run — the existing evaluation history in
   `data/evaluation_llm/` shows run-to-run variance on identical inputs.

4. **The de novo arm changes two variables at once** relative to baseline: it
   adds crate evidence *and* enlarges the input by 30–170 KB. A difference could
   be the crate's content or simply more context. If that distinction matters,
   an arm with size-matched filler would be needed; it is not built.
5. **`healthsheet_only` is AI-READI-only and within-project.** It is not
   comparable to any other project's arm, and it is not a baseline. Its one
   clean comparison is against AI-READI's own baseline, which measures what the
   other nine corpus sources add on top of the healthsheet.

## Comparison

Existing tooling works on these arms unchanged, since the methods are registered
in `METHODS`:

```bash
d4d evaluate presence --method rocrate_mapped
d4d evaluate presence --method claudecode_agent_crate
make eval-summary
```

The primary question is not which arm scores highest. It is **which fields the
crate supplies that the document corpus does not** — answered by a field-level
diff of baseline vs de novo, not by an aggregate score.

### Results, 2026-07-27 — and what the predictions got wrong

Predictions were written into this note **before** any generation, from a
phrase-overlap redundancy test. Recording both, because the mismatch is the
useful part. Final figures are the three-replicate ones above.

| | predicted | actual (3 replicates) | outcome |
|---|---|---|---|
| **CHORUS** | real delta | +22/+16/+20 full, 12 stable crate-only slots | ✅ as predicted |
| **VOICE** | real delta | +8 core in all three; 4 stable crate-only slots | ✅ but only visible on core |
| **CM4AI** | near-zero | sign flips (+8, −14, +2); **0** stable crate-only slots | ✅ in substance, ❌ in the reasoning I gave |

Predicted ordering: CHORUS ≈ VOICE ≫ CM4AI. Actual: **CHORUS ≫ VOICE ≫ CM4AI**,
with CM4AI at exactly zero reproducible contribution.

The rank order was right. The magnitudes were not, and the mid-series
interpretations I published from one and two replicates were wrong twice: I
called CM4AI "understated" from a single +8 that later flipped sign, and VOICE
"noise-dominated" from a +12 read off an unfinished run (true value +10).

### Why the prediction method failed

The redundancy test searched for **distinctive multi-word phrases** from the
crates' RAI narrative fields in each document corpus. That measures *prose
novelty*. It was then used to predict *record-level field gain*. Those are
different quantities, and the gap between them explains both errors:

- **CM4AI understated.** Its gains were **structured scalars** — `total_size_bytes`,
  `created_on`, `issued`, `download_url`, `compression`, `splits`,
  `conforms_to_schema`. A byte count or a date has no distinctive phrasing, so a
  phrase test is blind to it by construction. The crate-arm agent's own verdict:
  the prediction is *"confirmed for the narrative governance fields and refuted
  for a small, specific set of structured fields."* Every RAI narrative field it
  checked contributed nothing, exactly as predicted.
- **VOICE overstated.** Its crate prose genuinely was absent from the corpus
  (the 0/26 result was correct). But VOICE's baseline was already rich — 75
  slots, second only to AI-READI — so novel prose largely landed in slots the
  documents had already populated. Novel text does not imply a new field.

**The lesson, stated so it is not repeated:** phrase-absence predicts whether
crate *text* is new. It does not predict whether a *slot* will be newly filled.
Predicting field-level delta requires a field-level test — map each crate
property to its target slot and ask whether the documents already populate that
slot. That test was available (`d4d rocrate map` does exactly this mapping) and
was not used for prediction.

### The redundancy rule still holds — but it is about content, not coverage

The rule stands: **a crate adds content where the cited repository record does
not already carry that content.** CM4AI's Dataverse description holds the full
governance narrative; PhysioNet's pages do not; CHORUS's crate DOI is not cited
at all. That correctly explains *which* text is novel, and CM4AI's narrative
fields contributing nothing confirms it.

What it does not do is predict how much of a datasheet changes as a result.

Consequences, revised:

1. **Do not aggregate across projects.** Unchanged, and now empirically
   supported — the three deltas span +8% to +41%.
2. **CM4AI is not a clean null control.** It gained 11 slots and lost 3. The
   losses were inter-agent judgment differences (`extension_mechanism`,
   `language`, `subsets` — the crate-arm agent judged the sources insufficient
   where the baseline agent asserted them), not evidence changes. A control that
   moves ±11 slots cannot detect a small effect.
3. **Single-run deltas at this scale are noise-limited.** The gap separating
   VOICE (+6) from CM4AI (+8 net) is the same order as the unexplained CM4AI
   movement. Distinguishing them needs repeat runs, which have not been done.
4. **CHORUS is the one unambiguous result.** +22 slots, 0 lost, 28 crate-only
   fields covering the entire governance surface, and its baseline was the
   sparsest of the four — the cleanest headroom for a crate to fill.

Corollary for CHORUS still stands: citing `XNBOPG` in the sheet (discrepancy §6)
would shrink its delta, because the crate would become a cited source.

## Run naming and replicate tracking

**Convention** (`d4d runs list`, `d4d runs compare`):

```
data/d4d_concatenated/{METHOD}/{DATE}_{MODEL}_rep{N}/{PROJECT}_d4d[_core].yaml
```

METHOD encodes the arm, `{DATE}_{MODEL}` the configuration, `rep{N}` the
replicate. The label is **identical across arms of one round**: hold the label
constant and vary METHOD to compare arms; hold METHOD constant and vary `rep{N}`
to compare replicates. The 2026-07-27 run was relabelled to this form, with every
embedded path reference in headers and reports rewritten so provenance claims
still resolve (verified: 16/16).

**Why `_rep{N}` and not `_r{N}`.** An interim version of this convention used
`_r{N}`, which sat one character away from the legacy `-r{N}` *revision* marker
while meaning the opposite. Two opposite meanings separated by hyphen-vs-
underscore is a silent-error generator, so the replicate token was made
unmistakable. `rev{N}` (legacy, hyphen) and `rep{N}` (replicate, underscore)
cannot be confused at a glance or under a typo.

**Replicate, not seed.** These runs expose no seed, and temperature 0.0 does not
make an agentic run deterministic — tool-call ordering and context assembly
vary. `r{N}` labels an independent sample of an uncontrolled process; calling it
a seed would imply reproducibility we do not have.

Deterministic arms (`rocrate_mapped`, `rocrate_static_map`) are excluded from
the convention: re-running them over unchanged inputs is idempotent, so a
replicate index would imply sampling that does not occur.

### The r-index was already ambiguous — and it nearly produced a false result

The existing `2026-07-23_gpt-5.5-high-fast`, `-r2`, `-r3` directories look like
a three-replicate set. Compared naively they show slot counts of 34 / 67 / 75
for CHORUS and 33 / 63 / 84 for AI-READI — which would suggest an enormous
sampling noise floor, large enough to swamp every arm delta reported above.

They are not replicates. Their headers declare three different procedures:

| label | Generation Method |
|---|---|
| `…-high-fast` | Claude Code Agent Deterministic |
| `…-high-fast-r2` | Codex CLI Agentic |
| `…-high-fast-r3` | schema-grounded agentic, phase 1 |

The monotonic increase is an improving pipeline, not variance. The old `-r{N}`
suffix meant *revision*; the new `_r{N}` means *replicate*.

Two guards now exist, at both ends of the lifecycle:

- **At creation** — `check_replicate()` compares a new `_rep{N}` against its
  established siblings and raises `ReplicateMismatch` if the procedure
  fingerprint differs, with the message *"a changed pipeline is a revision, not
  a replicate — give it a new config label instead of a rep index."* This is the
  guard that actually prevents the mislabelling; catching it at compare time is
  already too late.
- **At comparison** — `d4d runs compare` refuses to present differing procedures
  as replicate variance, printing the conflicting pipelines instead.

`d4d runs list` renders the two families distinctly: `rep1`, `rep2` for
replicates; `rev2`, `rev3` for legacy revisions; `det` for deterministic arms.
Historical runs are left untouched — the new convention carries the burden of
being unambiguous, rather than rewriting another session's outputs.

The noise floor therefore remains **unmeasured** — no genuine replicate set
exists yet.

## Run record — 2026-07-27

Eight full/core pairs, three version labels, all independently re-validated by
the orchestrator rather than accepted on the generating agent's report:

| Label | Arm | Projects |
|---|---|---|
| `2026-07-27_claude-opus-5` | baseline | AI_READI, CHORUS, CM4AI, VOICE |
| `2026-07-27_claude-opus-5-crate` | de novo | CHORUS, CM4AI, VOICE |
| `2026-07-27_claude-opus-5-healthsheet` | healthsheet-only | AI_READI |

- 16/16 schema validations clean; 8/8 pair-consistency PASS at 76 shared slots.
- **Isolation verified, not assumed.** No crate arm contains the fingerprints of
  a withheld artifact (`urn:d4d:org:` from our normalizer, `conforms_to: D4D
  Schema` from upstream's LinkML). The healthsheet arm's 46 distinctive factual
  tokens all trace to its single source, with none appearing only in the wider
  corpus.
- **Nothing pre-existing was touched**: 280 files fingerprinted before the run,
  304 after — 0 modified, 0 deleted, 24 added.

### Cross-check: the healthsheet gap list predicted the corpus gain

AI-READI ran two arms whose agents never saw each other's output. The
healthsheet-only agent listed the D4D areas its single source could not support;
the baseline agent, with nine more sources, filled 15 additional slots. **14 of
those 15 had been named in advance** — only `raw_data_sources` was unforeseen.

The healthsheet alone reached 66 of the baseline's 81 slots (81% of coverage
from a single 56 KB source against a 421 KB corpus), and its weaknesses are
structural: dense on *how data were collected*, near-empty on *what the artifact
is*.

## De-primed replication — 2026-07-28

The whole 2026-07-27 series carried expectation statements in its prompts (see
*Prompt-priming confound* above). CM4AI was re-run on 2026-07-28 with the
referent pinned and the prompt neutral. This series completes the correction for
the other three projects: **18 runs**, label
`2026-07-28_claude-opus-5-deprimed_rep{1,2,3}`, covering CHORUS baseline +
de_novo, VOICE baseline + de_novo, AI-READI baseline + healthsheet.

Prompts were made structurally identical across arms — same phases, same
constraints, same header shape — differing only in the declared input bundle and
output paths. Every expectation statement was removed and replaced with an
explicit "there is no target slot count and no expected outcome". Two factual
notes were retained because omitting them would hide a known property of the
corpus rather than remove a bias: VOICE runs are told the bundle covers adult and
pediatric releases as distinct cohorts, and AI-READI baseline runs are told the
bundle holds multiple dataset versions that disagree on figures. Neither states
an expected output.

All 18 validate against `Dataset`/`CoreDataset`, and each carries a **live**
provenance record with no `unrecoverable` fields and a recorded input md5.

### Replicate agreement — primed vs de-primed (full records)

| project | arm | counts (primed) | agree | counts (neutral) | agree |
|---|---|---|---|---|---|
| CHORUS | baseline | 53, 54, 53 | 84.2% | 48, 59, 61 | **72.3%** |
| CHORUS | de_novo | 75, 70, 73 | 83.3% | 76, 71, 75 | 84.0% |
| VOICE | baseline | 75, 75, 75 | 91.0% | 76, 76, 77 | 92.4% |
| VOICE | de_novo | 81, 85, 83 | 91.9% | 76, 77, 77 | **96.2%** |
| AI-READI | baseline | 81, 84, 82 | 95.2% | 78, 82, 83 | 91.7% |
| AI-READI | healthsheet | 66, 69, 69 | 86.3% | 74, 72, 74 | 87.0% |

### Contribution verdicts — the substantive change

| project | arm | primed | de-primed |
|---|---|---|---|
| CHORUS | crate | `+22,+16,+20` ±13 → **real**, 12 stable | `+28,+12,+14` ±18 → **marginal**, 10 stable |
| VOICE | crate | `+6,+10,+8` ±7 → **marginal**, 4 stable | `0,+1,0` ±6 → **not resolvable**, 1 stable |
| AI-READI | healthsheet | `−15,−15,−13` ±10 → not resolvable, 0 | `−4,−10,−9` ±10 → not resolvable, 0 |

**VOICE's crate contribution was substantially a priming artifact.** Told the
crate was "expected to be genuinely additive", the arm produced 81/85/83 slots
against a 75/75/75 baseline. Told nothing, it produces 76/77/77 against 76/76/77
— deltas of `0, +1, 0`. Its stable crate-only set falls from 4 slots to 1
(`imputation_protocols`); `created_by`, `doi`, and `version` do not survive.
Note the de_novo arm also became *more* self-consistent (91.9% → 96.2%) while
shedding ~6 slots: the priming was inflating count without adding reproducible
content.

**CHORUS survives, weakened.** The de_novo arm was essentially untouched
(spread 5→5, agreement 83.3%→84.0%, stable 65→68). The verdict fell because the
*baseline* destabilised — spread 1→13, agreement 84.2%→72.3% — raising the noise
floor above the smallest delta. Nine of its twelve stable crate-only slots
survive and are the defensible claim:

`anomalies`, `citation`, `doi`, `informed_consent`, `issued`, `license`,
`prohibited_uses`, `total_file_count`, `version`

The three lost are `discouraged_uses`, `ip_restrictions`, and — notably —
`total_size_bytes`, the one slot the primed analysis had already identified as
corresponding to prompt-named content. Its disappearance is a direct
confirmation of that analysis.

### crate_only, de-primed — 9 runs

Label `2026-07-28_claude-opus-5-crateonly-deprimed_rep{1,2,3}`. The primed
crate_only prompts carried crate data-quality warnings. All 18 files validate;
all 9 carry live provenance.

| project | condition | counts | spread | stable | agreement |
|---|---|---|---|---|---|
| CHORUS | primed | 56, 59, 54 | 5 | 46 | 68.7% |
| | neutral | 62, 58, 57 | 5 | **50** | **74.6%** |
| VOICE | primed | 68, 68, 67 | 1 | 64 | 90.1% |
| | neutral | 70, 73, 70 | 3 | **67** | **90.5%** |
| CM4AI | primed | 55, 56, 50 | 6 | 47 | 78.3% |
| | neutral | 60, 62, 60 | 2 | **57** | **89.1%** |

Every arm improved; none got worse. CM4AI gained most (+10 stable slots,
+10.8 points, spread 6→2) — the warnings were suppressing content from the arm
whose crate they described, and CHORUS's 68.7% is no longer the study's lowest
floor.

CM4AI's primed comparator is the `-denoised` condition; the original
`crateonly` runs have no recoverable input fingerprint and are not a valid pair.

### Revised ordering

The primed series reported CHORUS ≫ VOICE ≫ CM4AI and observed that this
"matches the priming". De-primed, VOICE drops to CM4AI's level:

> **CHORUS (marginal) > VOICE = CM4AI (not resolvable)**

Of four Grand Challenges, only CHORUS shows any reproducible crate contribution,
and only at *marginal*. That is the finding.

### Priming type determines the effect — retire "de-priming raises variance"

The CM4AI result suggested de-priming increases variance. Across three more
projects that does not hold; what matters is *what kind* of statement the
priming made:

| priming type | example | effect of removal |
|---|---|---|
| **decision rule** | CHORUS baseline: "prefer omission over inference" | agreement collapses 84.2% → 72.3% |
| **density target** | healthsheet: "sparse output is the correct result" | level rises (66–69 → 72–74), agreement steady |
| **quality warning** | crate_only: crate data-quality caveats | level and agreement both rise in all three projects |
| **outcome expectation** | CHORUS de_novo: "expected to be genuinely additive" | little change to stability; count inflation only |

A decision rule manufactures agreement: three runs obeying one instruction look
consistent without converging on the evidence. CHORUS baseline's 84.2% was
measuring compliance, not reproducibility, and 72.3% is the truer number. VOICE
and AI-READI baselines, which carried no decision rule, came through de-priming
at 92.4% and 91.7%.

**Consequence for every noise floor in this document:** figures from arms whose
prompts carried decision rules are understated. The de-primed figures supersede
them.

## Open

- AI_READI RO-Crate — expected; will add `deterministic_ours` and `de_novo`.
- ~~**Re-run the crate_only arms de-primed?**~~ **Done 2026-07-28** — 9 runs,
  see *crate_only, de-primed*. The deterministic arms are model-free, so
  priming does not apply to them.
- Whether the deterministic arms should also produce core records. They produce
  full only, since the crate renderings map to `Dataset`.
- ~~**Repeat runs.** Every delta here is single-run.~~ **Done.** All four
  projects now have three de-primed replicates per stochastic arm; every verdict
  in *De-primed replication* is three-way and completeness-gated.
- **A field-level redundancy test** to replace phrase-overlap for prediction.
- Whether to re-run VOICE's crate arm once a `ro-crate-linkml.yaml` exists, so
  `deterministic_upstream` covers all three crates.
