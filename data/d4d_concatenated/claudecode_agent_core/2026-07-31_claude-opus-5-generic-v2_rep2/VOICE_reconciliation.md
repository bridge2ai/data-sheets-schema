# Reconciliation Report — VOICE

**Project:** VOICE (Bridge2AI-Voice)
**Version label:** `2026-07-31_claude-opus-5-generic-v2_rep2`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/VOICE_preprocessed.txt` (11 files)
**Phase:** 4 — strict reconciliation following Phase 3 source/provenance audit

---

## 1. Referent decision

`Dataset` admits one referent. The declared bundle documents several candidate referents: the Bridge2AI-Voice *project* (NIH RePORTER, IRB protocol, white paper), the adult PhysioNet dataset `b2ai-voice`, the pediatric PhysioNet dataset `b2ai-voice-pediatric`, the superseded Health Data Nexus v1.0 release, and the REDCap instrument library.

**Chosen referent:** the **adult Bridge2AI-Voice dataset as published on PhysioNet** (`physionet.org/content/b2ai-voice/`), taken at its current release **v3.1.0** (published 2026-05-01, 833 participants), with releases 1.0 through 3.0.0 and the Health Data Nexus v1.0 treated as prior versions of that same resource.

Grounds: seven of the eleven bundle files describe this resource directly or supply its governance, protocol, and provenance; two of the eleven are its own PhysioNet landing pages; and the curation notes attached to the bundle instruct that v3.1.0 be preferred over v3.0.0 where the two disagree. The project as a whole is broader than any dataset and is not itself a dataset; the pediatric release is a sibling, not a version (see §5.1).

This choice is held consistently across the full and core records.

---

## 2. Audit summary

Phase 3 returned **13 findings**: 4 high, 4 medium, 5 low.

The full record was found substantively sound — roughly 80 populated slots, near-uniformly grounded, with disciplined handling of several genuine source disagreements already in place (Rudzicz's Dalhousie/Toronto affiliation split, Ravitsky's Hastings Center/Montreal split, the Siu/Sui name variance, the four divergent renderings of the NIH award number, and the tension between the healthsheet's "no confidential data" answer and the controlled-access rationale for raw audio). Version-specific detail was verified accurate: per-version DOIs, the v3.1.0 feature record counts, the 18 diagnosis tables and 7 task tables in the v3.1.0 phenotype layout, and the migration of `adhd_adult`, `ptsd_adult`, and `psychiatric_history` from `diagnosis/` to `questionnaire/` between 3.0.0 and 3.1.0.

The defects clustered structurally rather than factually, and concentrated in the block following the `# Completed core record` marker. All 13 findings were dispositioned; 11 produced edits, 2 were retained with reasons recorded.

---

## 3. Changes to the full record

| # | Slot | Severity | Action |
|---|------|----------|--------|
| 5 | `related_datasets` | medium | Added |
| 7 | `purposes` | medium | Rewritten to represent disagreement |
| 8 | `regulatory_restrictions` | medium | Corrected — source was misquoted |
| 9 | `updates` | low | Derived figure removed |
| 11 | `creators` (Siu) | low | Role attribution trimmed |
| 12 | `creators` (Ghosh) | low | Role attribution trimmed |
| 13 | `creators` (Bolser) | low | Characterization removed |

### 3.1 `related_datasets` — added (finding 5)

The slot was unpopulated despite three clearly evidenced typed relationships. Added three `DatasetRelationship` objects, each carrying the required `relationship_type` and `target_dataset`:

- **Pediatric dataset** — `physionet.org/content/b2ai-voice-pediatric/`. The two PhysioNet notices cross-link each other explicitly ("Note that the Bridge2AI-Voice Pediatric Dataset is also available on PhysioNet" / "Note that the Bridge2AI-Voice Adult Dataset is also available on PhysioNet"). Typed as a sibling relation, not a part-of relation, per §5.1.
- **Health Data Nexus v1.0** — DOI `10.57764/qb6h-em84`, cited in every PhysioNet release note as reference [9] and described there as "the first release of the Bridge2AI voice as a biomarker of health dataset." Typed as a prior version of the same resource.
- **REDCap instrument and metadata repository** — `github.com/eipm/bridge2ai-redcap`, Zenodo DOI `10.5281/zenodo.12760724`, which the documentation names as the source of the data dictionary and instrument PDFs and asks users to cite alongside the dataset.

This is also where the pediatric dataset now lives after its removal from `resources` in the core record (§4.4).

### 3.2 `purposes` — rewritten (finding 7)

The prior value reported only the 10,000-voice enrollment target. The bundle disagrees with itself on this figure and the record was silently selecting one side:

- **10,000** — project documentation ("a flagship, standardized, and ethically sourced dataset of 10,000 voices") and study metadata ("Enrollment Count (Anticipated by 2027): 10,000").
- **30,000** — the audiomics white paper ("our primary deliverable to build a publicly available database of 30 000 human voices") and the IRB protocol, twice ("Sample Size 30 000 participants"; "The total number of 30 000 participants will be reached by collaboration with other participating institutions and existing cohorts").

The revised value states both targets and attributes each to its sources. No revision or supersession is asserted between them: although the 30,000 figure appears in the earlier documents (IRB v1, January 2023; white paper, February 2024) and 10,000 in the current documentation, no source in the bundle states that the target was changed, and inferring a downward revision would go beyond the evidence.

### 3.3 `regulatory_restrictions` — corrected (finding 8)

The prior value asserted that "the data are nonetheless governed by HIPAA," citing the Data Transfer and Use Agreement. The DTUA states the opposite. Attachment 2, clause 1 reads in full:

> The Data is Personally Identifiable Information, as that is defined in OMB Memorandum M-07-16, **and not covered under HIPAA, FERPA, or similar laws or regulations** governing personal information that require the addition of special terms beyond those included in this Attachment.

The prior value quoted the first clause and dropped the operative negation, inverting the source. Corrected to state that the DTUA characterizes the transferred data as PII under OMB M-07-16 and expressly not covered under HIPAA or FERPA.

The corrected value also now carries the two regulatory facts that were previously absent or subordinate:

- The DTUA's checked Certificate of Confidentiality box, with its obligation that the certificate "must be asserted against compulsory legal demands, such as court orders and subpoenas."
- The Florida forced-labour warranty under §787.06 F.S., breach of which immediately terminates the agreement.

The documentation's plain statement that "no export controls apply to the dataset" is retained.

Note that this correction does not conflict with the healthsheet's "Does this dataset apply the HIPAA de-identification rules? Yes" or with the IRB's HIPAA-compliant storage requirements. Those describe the treatment applied during de-identification and collection; the DTUA describes the regulatory status of the resulting shared data. Both are now stated in their respective slots without collapsing them.

### 3.4 `updates` — derived figure removed (finding 9)

The prior value read "participant counts grew from 306 at version 1.0 to 442 at version 2.0 to 833." The figure **442** appears nowhere in the bundle; it is `306 + 136` presented as a reported count. The arithmetic is consistent with the release notes, but the intermediate total is not attested.

Replaced with the figures the bundle actually states: 306 participants at v1.0; "an additional 136 new participants" at v2.0; "new data for an additional 391 participants" at v3.0.0; 833 participants at v3.0.0 and v3.1.0. The semi-annual release cadence stated in the healthsheet is retained.

### 3.5 `creators` — three role attributions trimmed (findings 11–13)

Each of these described a role by inference from institutional affiliation rather than from an assignment stated in the bundle.

- **Jennifer Siu** — "Lead for the pediatric cohort" removed. The bundle lists her among lead investigators at Hospital for Sick Children and as a PhysioNet author; SickKids is separately identified as the sole pediatric recruitment site. No source connects the two into a role assignment, and the IRB Annex C role table does not list her. Retained: lead investigator, Hospital for Sick Children, with the Siu/Sui rendering variance already noted.
- **Satrajit Ghosh** — "lead for the data processing pipeline (b2aiprep, senselab)" removed. The bundle assigns him one role explicitly: IRB Annex C lists "MIT — Satrajit Ghosh, PhD — Lead Mood Disorders." He is a listed author of the b2aiprep software citation, which is retained as such; authorship of a tool is not leadership of a pipeline.
- **Donald Bolser** — "Pulmonary and cough science" removed. He is listed as a lead investigator at University of Florida in the documentation and as a consortium member in the feasibility paper; IRB Annex C does not assign him a role. The pulmonary terms in the NIH RePORTER preferred-term list are project-level and attach to no individual.

---

## 4. Changes to the core record

The core record required regeneration rather than repair. Findings 1, 2, and 3 together establish that the block following the `# Completed core record` marker was not a `CoreDataset` record at all: it had no header comment block, no top-level `id`, `name`, `title`, or `description`, and continued the full record's `Dataset`-shaped slot sequence. It carried two keys absent from any schema in play.

### 4.1 Record regenerated with required header and identity (finding 3)

The core record was regenerated from scratch as a `CoreDataset` record. It now carries the mandated header block with the phase-2 designation and the core schema path, and the required `id`, together with `name`, `title`, and `description` consistent with the referent decision in §1.

`id` is required by the schema; its absence alone would have failed validation.

### 4.2 `_distributions` — removed (finding 1)

`_distributions` is not a slot in the 94-slot `Dataset` inventory and is not a `CoreDataset` slot. An underscore-prefixed key is not schema-defined at any level. Its content — per-version access tier, DOI, publication date, and PhysioNet view counts — is already correctly distributed across `distribution_dates`, `distribution_formats`, `version_access`, and `license_and_use_terms` in the full record. Nothing was lost by removing it. The view counts (208/801, 165/801, 93/801, 42/119) were dropped entirely: they are page-traffic telemetry, not dataset facts, and no schema slot asks for them.

### 4.3 `dialect` — removed (finding 2)

`dialect` is likewise not a slot in the declared inventory. The TSV separator and header-row conventions and the JSON-sidecar pairing it described are already stated in `distribution_formats`, where they belong.

### 4.4 `resources` — pediatric dataset removed, relationship relocated (finding 4)

`resources` is documented as "Sub-resources or component datasets that are part of this dataset," a hasPart relation. Nesting the pediatric dataset there asserted that it is part of the adult dataset. The bundle states the opposite in terms, in the pediatric source's own curation note:

> This is a separate PhysioNet project from the adult b2ai-voice dataset, not a version of it; the two releases are distinct cohorts collected under a separate pediatric protocol, with pediatric participants recruited at the Hospital for Sick Children (SickKids).

The nesting also contradicted the full record's own `description`, which correctly calls the pediatric dataset "a distinct PhysioNet project rather than a version of this one." The supporting evidence for separateness is substantial: separate PhysioNet project and DOI series (`10.13026/h995-bt35` vs `10.13026/8xbn-nq66`), separate ethics approval (SickKids REB vs USF IRB), separate raw-audio Synapse repository (`syn73617068` vs `syn72370534`), separate collection software (`reproschema-ui` vs the Bridge2AI-Voice iOS app), and an independent version series beginning at 1.0.0.

The pediatric dataset was removed from `resources` and the relationship relocated to `related_datasets` as a sibling relation (§3.1). `resources` is now unpopulated, which is the correct answer: the bundle documents no component datasets of the adult release.

### 4.5 `compression` — removed (finding 6)

`compression: gzip` had no support anywhere in the bundle. The distribution formats described are Parquet ("an open-source column-oriented data file format"), TSV, JSON, and WAV. Parquet's internal codec is unspecified in the bundle and is not gzip by default. The value was inferred from file format alone. Removed.

### 4.6 `is_tabular` — removed (finding 10)

`is_tabular: false` was asserted without direct support, and the underlying reality is mixed: the entire `phenotype/` tree is TSV tables with header rows and one row per participant or per session, while the feature payloads are variable-length tensors stored in column-oriented Parquet. The bundle never characterizes the dataset either way. Under the omission-over-inference rule, the slot is now unpopulated.

---

## 5. Left as-is, with reasons

### 5.1 The sibling relationship type

The audit flagged the `resources` nesting as contradicting the evidence, and it was removed. It is worth recording what was *not* asserted in its place. The bundle establishes that the adult and pediatric datasets are distinct projects sharing a consortium, a funding award, a processing library, and a data-use agreement. It does not state that either derives from the other, that one supplements the other, or that both are parts of a named umbrella dataset. The relationship recorded is therefore the weakest one the evidence supports — a cross-referenced sibling release under a common project — and nothing stronger.

### 5.2 `file_collections` identifiers (finding 13, low)

The four `FileCollection` entries carry constructed URL identifiers such as `https://physionet.org/content/b2ai-voice/3.1.0/features/`. The audit correctly notes the bundle names these directories ("features subfolder," "metadata folder," "phenotype subfolder") without attesting the URLs as resolvable.

**Retained.** `FileCollection` requires an `id`, so some identifier must be supplied. Both components of each identifier are attested independently: the versioned project URL appears verbatim in the bundle, and the directory names are given in the Data Description sections and in the rendered directory tree. The composition follows PhysioNet's own path convention rather than making a new factual claim about the dataset. Substituting bare directory names would not improve grounding and would lose the disambiguation between the adult and pediatric trees, which use overlapping directory names.

---

## 6. Source disagreements represented rather than resolved

Per the uniform decision rules, the following divergences are carried in both records as divergences. None was silently resolved.

| Subject | Divergence | Disposition |
|---|---|---|
| Enrollment target | 10,000 (documentation, study metadata) vs 30,000 (white paper, IRB ×2) | Both stated with attribution — **newly added in this phase** (§3.2) |
| NIH award number | `OT2OD032720`, `3OT2OD032720-01S1`, `3OT2OD032720-01S3`, `3Tf-OTOD03272001S2`, `3TF-OT2ActfOD032720Projectf01S1` | All renderings recorded; core project number identified as `OT2OD032720` |
| Frank Rudzicz affiliation | Dalhousie University (feasibility paper) vs University of Toronto (documentation, IRB) | Both recorded |
| Vardit Ravitsky affiliation | University of Montreal (feasibility paper) vs The Hastings Center (documentation, white paper) | Both recorded |
| Jennifer Siu / Sui | Two spellings across documentation and PhysioNet author lists | Both recorded as variants of one person |
| Confidentiality | Healthsheet answers "No" to confidential data; governance memorandum and controlled-access tier exist precisely because raw audio is re-identifying | Both recorded; the distinction is between the released feature-only tier and the withheld raw audio |
| Hosting platform | Health Data Nexus (healthsheet, v1.0) vs PhysioNet (v1.1 onward) vs Synapse (raw audio) | All three recorded against their respective tiers and versions |
| Data collection period | "over a period of 12 months" (healthsheet) vs the IRB's four-year phased schedule | Both recorded; the healthsheet figure is scoped to the released cohort |

---

## 7. Outcome

| | Before | After |
|---|---|---|
| Full record — populated slots | ~80 | **81** of 94 |
| Full record — non-schema keys | 0 | 0 |
| Core record — valid `CoreDataset` | no | **yes** |
| Core record — populated slots | — | **34** |
| Core record — non-schema keys | 2 (`_distributions`, `dialect`) | 0 |
| Missing required `id` | 1 (core) | 0 |
| Unsupported values | 3 (`compression`, `is_tabular`, 442) | 0 |
| Misquoted sources | 1 (`regulatory_restrictions`) | 0 |
| Contradicted relations | 1 (`resources` hasPart) | 0 |

**Validation:**

- Full — `linkml-validate -s data_sheets_schema_all.yaml -C Dataset` → **pass**
- Core — `linkml-validate -s data_sheets_schema_core_all.yaml -C CoreDataset` → **pass**

**Provenance:** no previously generated D4D record was read, opened, or consulted at any phase. Factual inputs were the declared bundle and the two schema files only.