# CM4AI — Phase 4 Reconciliation Report

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep1`
**Arm:** BASELINE (input documents only)
**Declared bundle:** `data/preprocessed/concatenated/CM4AI_preprocessed.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-api-generic_rep1/CM4AI_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-api-generic_rep1/CM4AI_d4d_core.yaml`

---

## 1. Referent decision

`Dataset` admits one referent. The bundle describes a quarterly release *series* (May 2024, March 2025, June 2025, October 2025, June 2026) in which each release carries its own DOI, version, and file inventory.

**Decision held:** the record's referent is the **current release, DOI `10.18130/V3/HIGT4C` (June 2026, version 2.0)**, with series-level context carried only in slots that are inherently longitudinal (`distribution_dates`, `version_access`, `errata`, `updates`).

This is unchanged from Phases 1–2 and is applied identically in both records. Consequence acknowledged in §5: the `id` resolves to one release, not the series.

---

## 2. Audit outcome in brief

No fabricated dataset facts were found. All quantitative values — DOI, version, publication and release timestamps, MD5 checksums, file sizes, file count, NIH award numbers, RRIDs, ORCIDs, cell-line identifiers — trace to the declared bundle. Boundary discipline against the largest document in the bundle (the U2OS *Nature* study) held: that study's findings are confined to `external_resources` and explicitly marked as not part of this release.

Findings by severity: **0 high**, **11 medium**, **34 low**.

The dominant medium-severity cluster is **inherited file descriptions**, addressed in §3.1.

---

## 3. Changes applied

### 3.1 Inherited file descriptions — full and core (medium)

The June 2026 Dataverse listing supplies filenames, sizes, MD5 checksums, and publication dates, but **no per-file descriptions**. Phase 1/2 characterizations of the IF, SEC-MS, and Perturb-seq archives (laboratory attribution, cell-system coverage, the 11,739-gene atlas figure) were carried over from same-named files in the October 2025 and June 2025 listings — files whose checksums *differ* from the June 2026 artifacts:

| Archive | Oct 2025 MD5 | Jun 2026 MD5 |
|---|---|---|
| `cm4ai_ifimages_MDA-MB-468_paclitaxel.zip` | `0d972b80…` | `6c1a8652…` |
| `cm4ai_mass-spec_KOLF2.zip` | `fb04933a…` | `f250bf0b…` |
| `cm4ai_mass-spec_MDA-MB-468.zip` | `662d62ce…` | `9aed30b6…` |
| `cm4ai_perturb-seq_KOLF2_cell_atlas.zip` | `15dc5931…` | `291a3628…` |
| `cm4ai_perturb-seq_KOLF2_raw_sra.zip` | `1cfc4e8e…` | `8bb3f365…` |

The artifacts are therefore not identical, and the descriptions are not stated for the released files.

**Action:** descriptions retained (they are almost certainly accurate) but re-scoped in both records to attribute the characterization to the prior-release listings of same-named files, with the checksum divergence noted. Applied to `file_collections[if-images | sec-ms | perturb-seq]` in the full record and the corresponding `distribution_formats` entries in the core record.

### 3.2 Core record — invalid slot name (medium)

The core record used a `distributions` slot. `distributions` is not a `CoreDataset` slot; the record would not have validated.

**Action:** renamed to `distribution_formats`. Narrative content preserved. Per-collection `file_count` values dropped (unsupported by `DistributionFormat`) and the aggregate carried instead via `total_file_count` (§3.3).

### 3.3 Full/core parity gaps (low)

Six slots present in the full record were absent from the core record. Each was checked against `data_sheets_schema_core_all.yaml`:

| Slot | In `CoreDataset`? | Action |
|---|---|---|
| `citation` | yes | **Added** to core (verbatim Dataverse citation string) |
| `total_file_count` | yes | **Added** to core (`10`) |
| `variables` | no | Structural omission — no change |
| `relationships` | no | Structural omission — no change |
| `direct_collection` | no | Structural omission; facts partly carried by `is_deidentified` and `human_subject_research` |
| `third_party_sharing` | no | Structural omission; content partly carried by `external_resources` and `license_and_use_terms` |

### 3.4 Empty-list vs omission inconsistency (low/medium)

The full record declared explicit empty lists for `anomalies`, `content_warnings`, and `sensitive_elements`; the core record omitted all three.

**Action:** harmonized to **omission in both records**. Under the prefer-omission rule an empty list is a positive assertion of absence, which is stronger than the bundle supports — particularly for `anomalies`, where the March 2025 → later-release IF protein-count divergence (563 → 464) is a candidate anomaly already carried under `errata` and `sampling_strategies`. The affirmative de-identification facts (`Human Subjects: No`, `De-identified Samples: Yes`) remain in `is_deidentified` and `human_subject_research`.

### 3.5 Tense error — `existing_uses` (low)

The Yale/UCSD internship was recorded as a realized use. The bundle describes it prospectively ("*will* be hosted", "*will* provide participants with the opportunity").

**Action:** entry **removed** from `existing_uses` in both records. Not relocated: educational/workforce use is already represented in `other_tasks`. The March 2024 CodeFest entry (38 registrants) is retained — the bundle describes it as having occurred.

### 3.6 UI boilerplate mistaken for dataset metadata (low)

- `retention_limit` contained "*files are not removed from previously published versions*", which is Dataverse delete-dialog modal text, not a retention policy for this deposit. **Sentence removed**; the substantive retention content (long-term preservation in UVA Dataverse, committed institutional funds) retained.
- `distribution_formats` reports per-selection ZIP download ceilings (1.9 GB / 953.7 MB). **Retained** — this is interface configuration rather than dataset metadata, but it materially affects access and was already hedged as "at capture". Hedge strengthened to name it explicitly as Dataverse interface state.

### 3.7 Absence-of-evidence stated as a value (low)

`regulatory_restrictions` asserted that "*no export-control or other regulatory restrictions are documented in the source material*".

**Action:** clause **removed**. The grounded content (`FDA Regulated: No`, license governance, Bridge2AI Code of Conduct, collection-level notice) retained.

### 3.8 Inferred attributions narrowed (low)

| Slot | Change |
|---|---|
| `data_collectors` — Mali | Reworded: Mali named as CM4AI investigator and senior author on the perturbation atlas preprint, not as laboratory of record. The bundle attributes SEC-MS to the Krogan lab and IF to the Lundberg lab explicitly; it makes no equivalent statement for Perturb-seq. |
| `data_collectors` — Ideker lab | **Removed.** The Tools Module produces cell maps, which are *not* in this release; the bundle names Ideker as PI and Point of Contact, not his laboratory as module operator. |
| `acquisition_methods[2]` | Reworded: the "simple MTA" is HipSci's stated availability route for KOLF2.1J generally, not necessarily CM4AI's own acquisition mechanism. |
| `extension_mechanism` | Reworded: the Dataverse *Contact Owner* function, Data Governance Committee, and program manager are stated as contacts, without asserting they constitute a defined contribution/correction pathway. |
| `other_tasks[1]` | **Removed** — reuse of the AI-readiness packaging approach as an exemplar is not a task the dataset supports. Entries 2–4 retained. |
| `collection_mechanisms[0]` | Temporal qualifier strengthened: the 17-tagged / 34-in-progress figures are from the May 2024 preprint; the June 2026 release ships AP-MS for treated MDA-MB-468 without stating gene counts. |
| `purposes[1]` | Temporal qualifier added: the "100 chromatin modifiers and 100 metabolic enzymes" figure is the project's Year-1 objective; the realized scope in this release includes a genome-scale iPSC atlas of 11,739 genes. |

### 3.9 Scope signalling in `description` (low)

**Action:** `description` reworded in both records to state the convention explicitly — the record describes the June 2026 deposit, except where a slot is inherently longitudinal (`distribution_dates`, `version_access`, `errata`, `updates`), which span the release series.

---

## 4. Source disagreements — preserved, not resolved

Per the uniform decision rules, conflicting evidence is represented rather than adjudicated. All five were verified as still correctly surfaced after reconciliation:

| Conflict | Sources | Slot |
|---|---|---|
| Project end date | NIH RePORTER `2026-08-31` vs release maintenance plan "November 2026" | `collection_timeframes` |
| IF protein count | 563 (Mar 2025) / 464 (Jun–Oct 2025) / 523 (cm4ai.org) | `sampling_strategies[2]` |
| Sali affiliation | UCSD (Dataverse) vs UCSF (CM4AI preprint, *Nature*) | `creators` |
| June 2026 release date | "June 2026 Data Release" labelled "Released on: June 17, 2025" on cm4ai.org; Dataverse gives publication `2026-06-17`, v2 released `2026-07-15T20:28:19Z` | `distribution_dates` |
| Version label | Citation string says `V2`; page header says `Version 2.0` | `version`, `version_access` |

**One change made:** `updates` and `retention_limit` both restated "November 2026" without re-flagging the RePORTER conflict. A cross-reference to `collection_timeframes` was added to each so the disagreement is visible to a reader of those slots alone.

---

## 5. Retained as-is, with rationale

| Finding | Rationale for no change |
|---|---|
| `id` resolves to one release, not the series | Consequence of the declared referent decision (§1). Any alternative — a synthesized series URI — would be less resolvable and less grounded. |
| Synthesized `file_collections[].id` and `subsets[].id` | Schema requires `id`; the bundle assigns none to logical groupings. Documented here as record-level structuring, not source-stated collections. |
| Core `resources` carrying the seven strata | `CoreDataset` has no `subsets` slot; `resources` is the nearest structural fit. Caveat stands: these are cell-system/treatment strata, not separately deposited sub-datasets. |
| `total_size_bytes` omitted | Only rounded display values are available (3.8 GB, 4.6 GB, …). No exact integer is derivable; omission is correct under prefer-omission. |
| `created_on: 2025-02-27` | Source-stated as both *Data Creation Date* and *Deposit Date* for this deposit. The underlying experimental work predates it, but a `datetime` slot cannot carry the qualification; noted here instead. |
| `variables` covers IF channels only | The bundle documents column-level structure for no other modality. The asymmetry reflects the evidence, not selective effort. |
| `known_biases` — two of three entries interpretive | Characterization is intrinsic to the slot. Reworded to foreground the source-stated fact (donor/disease background; panel-driven target selection; incomplete cross-modality overlap) before the bias framing. |
| `discouraged_uses` — all three interpretive | Same reasoning. Contrast preserved with `prohibited_uses`, which quotes the release's explicit clinical-use prohibition verbatim. |
| `use_repository` download counts | Dataverse "Dataset Metrics" are undefined in the bundle but are source-stated and correctly hedged as "as captured". |
| `status` composing three source statements | All three (the "(Beta)" label, the completeness text, the collection-level Administration-directives notice) are quoted accurately, and the value states that the notice applies to the hosting collection. |
| `instances[3]` Perturb-seq wording | The 73.3 KB `raw_sra` archive plainly holds accession references, which the existing phrasing "referenced to SRA" already conveys. |
| `existing_uses[1]` CodeFest / first-release linkage | The bundle does not state whether the March 2024 CodeFest distributed the artifacts later deposited as the May 2024 release. Existing wording does not assert identity. |
| `conforms_to_schema` RO-Crate/FAIRSCAPE detail | A project-level claim applied to a specific deposit, but supported: the release ships `cm4ai_release_metadata.zip` and prior releases shipped `ro-crate-metadata.json`. |
| `was_derived_from` listing iPSC-derived types alongside source lines | Accurate for release contents; "together with" is adequate given that the derivation relationship is stated in `acquisition_methods` and `subsets`. |
| U2OS/*Nature* content confined to `external_resources` | Correct boundary. The study's figures (5,147 proteins, 275 assemblies, HEK293 comparison, paediatric cancer analysis) are excluded from every descriptive slot. |

---

## 6. Post-reconciliation state

| | Before Phase 4 | After Phase 4 |
|---|---|---|
| Full — populated slots | 74 | **71** |
| Core — populated slots | 39 | **41** |
| Full — validates against `Dataset` | yes | **yes** |
| Core — validates against `CoreDataset` | **no** (invalid `distributions` slot) | **yes** |

Full-record delta: −3 (empty-list declarations for `anomalies`, `content_warnings`, `sensitive_elements` converted to omission). Within-slot edits — list-entry removals in `data_collectors`, `other_tasks`, `existing_uses`, and rewording across eleven slots — do not change the populated-slot count.

Core-record delta: +2 (`citation`, `total_file_count`), plus the `distributions` → `distribution_formats` rename that restored validation.

Both records remain consistent on the referent, on all five preserved source disagreements, and on every quantitative value.