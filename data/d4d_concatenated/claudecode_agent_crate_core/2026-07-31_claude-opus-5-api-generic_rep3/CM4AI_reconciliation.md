# Reconciliation Report — CM4AI

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep3`
**Arm:** DE NOVO WITH CRATE (documents + RO-Crate evidence)
**Declared bundle:** `data/preprocessed/concatenated/CM4AI_preprocessed_with_crate.txt`
**Records reconciled:** `CM4AI_d4d.yaml` (full, `Dataset`) and `CM4AI_d4d_core.yaml` (core, `CoreDataset`)
**Phase 3 findings reviewed:** 31 (1 high, 5 medium, 21 low, 4 informational; 3 self-retracted by the audit)

---

## 1. Referent and scope — unchanged

Both records take the **June 2026 Data Release, DOI `10.18130/V3/HIGT4C`, version 2.0** as the single `Dataset` referent, with the October 2025 (`K7TGEM`), June 2025 (`F3TD5R`) and March 2025 (`B35XWX`) deposits represented as version history rather than as co-equal referents.

This was audited as defensible and is **left as-is**. The bundle's own curation note on the October 2025 file states that release is "superseded upstream by the June 2026 HIGT4C release," and the HIGT4C source file is annotated as the current release. The crate's top-level entity is the June 2026 release. Choosing the sheet-selected October release as referent would contradict the bundle's explicit curation guidance; choosing the release *series* as referent would require a `Dataset` with no single DOI, publication date, or file inventory. The choice is applied identically in both records.

No evidence of prior-D4D reuse was found in either record. All factual content traces to the declared bundle.

---

## 2. Changes made

### 2.1 Count and size assertions — the one high-severity defect

**`total_file_count` (full) — removed.**

Phase 1 populated this with `53877`, taken from the crate's `evi:datasetCount`. The bundle distinguishes three separate figures — `evi:datasetCount` 53,877, `evi:totalEntities` 55,859, and the ten files actually deposited at Dataverse — and none of them is a file inventory. `evi:datasetCount` counts dataset entities in the provenance graph, which includes directory-group entities and derived records. Asserting it as "total number of files" is a unit error, not a transcription error, and the schema slot definition is explicit about the unit. Since no attested file count exists for the dataset as a whole, the slot is now omitted. The three conflicting figures remain documented narratively in `known_limitations` and `errata`, where they were already correctly flagged as irreconcilable.

**`total_size_bytes` (full) — removed.**

Phase 1 asserted `21051331945400` from `evi:totalContentSizeBytes` (≈21.05 TB) while the same record's `errata` entry correctly noted that the release crate declares `contentSize` "19.9 TB" and the CM4AI portal reports 21.4 TB. Selecting one figure in a structured slot while flagging the disagreement in prose is internally inconsistent and violates the standing rule to represent disagreement rather than silently resolve it. The slot is now omitted; all three figures, with their sources, remain in `errata`.

**`file_collections[].file_count` (full) — partially removed.**

Retained where the crate's entity list corresponds one-to-one with files: the three immunofluorescence collections, whose `EVI#outputs` enumerate individual per-channel image entities (`B2AI_5_Paclitaxel_H12_R8_z01_blue` and siblings). Removed for the AP-MS collections (555, 718), the SEC-MS collections (862, 18) and the Perturb-seq collections (103, 3), where the crate's own `evi:formats` list includes `.d directory group` and the counted entities are provenance datasets rather than files. This is the same category error as `total_file_count`, applied at collection level.

### 2.2 Fabricated identifier

**`file_collections` tenth entry (full) — removed.**

The entry used `https://doi.org/10.18130/V3/HIGT4C#cm4ai_release_metadata`, a fragment IRI that appears nowhere in the bundle. Every other entry uses a genuine ARK from the crate graph. `FileCollection` requires `id`, so there is no way to retain the entry without minting an identifier. The release-metadata archive (`cm4ai_release_metadata.zip`, 1.1 MB, MD5 `318deb7c5edab0d2fa55e26fcb67b440`) is instead described under `distribution_formats`, which imposes no identifier requirement. No information is lost; a synthetic identifier is.

### 2.3 Cross-study contamination (Schaffer et al. 2025 → CM4AI)

The bundle contains two distinct dataset contexts: the CM4AI release itself, and the Schaffer et al. *Nature* 2025 U2OS multimodal cell map, included as a related publication. Phase 1 handled this correctly in `external_resources` (explicit disclaimer that the U2OS map is a distinct dataset) but leaked U2OS-specific mechanism into three CM4AI-scoped slots.

**`collection_mechanisms` (full) — re-attributed.**
The `cellmaps_*` package roster (`cellmaps_imagedownloader`, `cellmaps_ppidownloader`, `cellmaps_image_embedding`, `cellmaps_ppi_embedding`, `cellmaps_coembedding`, `cellmaps_generate_hierarchy`, `cellmaps_hierarchyeval`) is named only in the *Nature* paper's description of the U2OS Cell Mapping Toolkit. The CM4AI preprint describes the equivalent pipeline stages without naming packages. The entry now attributes the package names to the U2OS toolkit and states that CM4AI's Tools module implements the analogous stages, rather than presenting the roster as CM4AI's own collection mechanism.

**`preprocessing_strategies` (both) — attribution added, content retained.**
The mechanistic detail (node2vec parameters, DenseNet-121 image featurization, the reconstruction-plus-contrastive training objective, multi-resolution community detection) is drawn from the U2OS methods; the CM4AI preprint describes the same pipeline in general terms and names node2vec and the HPA model explicitly. The entries are retained because CM4AI does describe this pipeline as its own, but each now carries an explicit source attribution, and the existing caveat that no computed cell maps are present in this release is preserved.

**`known_biases` (both) — two entries rescoped, one clause deleted.**

- *Antibody and reagent availability bias*: the claim that IF coverage "systematically under-samples some protein classes" transfers a U2OS finding (under-representation of transmembrane and immunoglobulin proteins) to CM4AI's MDA-MB-468 imaging, where the bundle makes no such measurement. Rescoped to what the bundle supports for CM4AI: coverage is bounded by HPA antibody availability and validation, and the release covers 464 proteins of a much larger proteome.
- *Modality detection bias*: the scale-dependence claim (imaging resolves large assemblies, AP-MS small ones) is a U2OS result. Rescoped to the CM4AI preprint's own framing — that the three modalities are complementary and interrogate incompletely overlapping protein sets, which the crate states directly.
- *Disease-state and treatment-state bias*: **"aneuploid" deleted.** The bundle establishes MDA-MB-468 as a triple-negative breast cancer line from a metastatic pleural effusion; it never states ploidy.

### 2.4 De-identification and sensitivity framing

**`is_deidentified` (both) — clause removed.**
The assertion that "donor-of-record characteristics for each line are publicly documented in cell line registries" is unsupported: the bundle supplies donor characteristics from the CM4AI preprint text and supplies Cellosaurus accessions (`CVCL_0419`, `CVCL_B5P3`) as identifiers, but quotes no registry content. The Cellosaurus identifiers are retained as identifiers; the claim about where donor characteristics are documented is removed.

**`sensitive_elements` (both) — framing corrected.**
The donor descriptors are retained verbatim in substance (MDA-MB-468: 51-year-old Black female, metastatic mammary adenocarcinoma; KOLF2.1J: healthy male Northern European donor) because the bundle states them. The framing "identified donors of record" is replaced: the bundle's consistent position, in both the crate and the preprint, is that these are commercially sourced de-identified lines that "cannot be matched, with current knowledge, to a human subject." The residual-identifiability implication overstated the evidence in the opposite direction from the record's own `human_subject_research` and `at_risk_populations` determinations, which were correct.

### 2.5 Attribution and role claims

**`creators` (full) — three entries corrected.**

- *Andrej Sali*: compound affiliation "University of California San Francisco / University of California San Diego" replaced with the affiliation as listed in the release Dataverse metadata (UCSD), with the UCSF affiliation from the *Nature* and CM4AI preprint author lists noted rather than merged. The bundle does not perform this reconciliation and neither should the record. The verb "leads" for integrative structure modeling is replaced with the attributed activity ("designed and performed structural modelling," per the preprint contributions statement).
- *Timothy Clark*: "leads the Standards module" replaced with attested facts — first author of the CM4AI preprint, University of Virginia, FAIRSCAPE framework. The bundle associates Standards-module work with UVA and names Clark first among authors but never designates a module lead.
- *Vardit Ravitsky*: University of Montreal added per the Dataverse author list; the Hastings Center contact address given in the crate's `ethicalReview` field is noted separately rather than left to imply an affiliation.

**`data_collectors` (both) — roster trimmed.**
Hu M, Qian G and Ideker T removed from the MuSIC/Tools implementation roster. The bundle's supporting sentence — "L.V.S., C.C., J.L. and D.P. designed and implemented the cell map toolkit" — is from the *Nature* contributions statement and names four people. The three additional names were not attested for this role in any source.

### 2.6 Scope and precision corrections

**`sampling_strategies` (both) — 200-gene figure rescoped.**
The portal's "Perturb-seq of 200 genes" describes the flagship curated TNBC dataset in general. The June 2026 release description says only "Perturb-seq data for MDA-MB-468 breast cancer cells +/- treatment," with no gene count. The figure is retained but attributed to the portal's flagship-dataset description rather than asserted as the target count for this release's component. The "100 chromatin regulators" figure from the CM4AI preprint's Year 1 design is retained with its own attribution.

**`collection_timeframes` (both) — false equivalence removed.**
The crate's `rai:dataCollectionTimeframe` (2022-09-01 to 2026-06-01) and the NIH RePORTER project period (2022-09-01 to 2026-08-31) have different end dates and are therefore not coextensive. Both ranges are now stated separately with their sources; the equivalence claim is deleted.

**`instances` (full) — RGB carry-forward rescoped.**
"RGB composites added in a 2025 revision" is attributed to the June 2025 release revision (`F3TD5R` v2.1), which states it explicitly. The June 2026 IF archives carry different MD5 checksums from the June 2025 ones, and no source states whether they include RGB composites. The claim is now scoped to the release that asserts it.

**`distribution_formats` (both) — datasheet artifact rescoped.**
`release-ro-crate-datasheet.html` is scoped to the June 2025 release, where it appears in the file listing. The June 2026 deposit's ten files contain no such artifact.

**`raw_data_sources` (both) — split into two entries.**
The June 2026 release lists two separately labelled embargoed Perturb-seq resources (KOLF2.1J and MDA-MB-468); only the June 2025 release labels an SRA BioProject, and only once. Consolidating both under a single SRA BioProject was inference. Each embargoed resource is now a separate entry, with the SRA BioProject attribution restricted to the June 2025 listing.

**`existing_uses` (both) — boilerplate finding removed.**
Download counts (302 / 256 / 405 / 181) are retained; they are rendered values. The added claim that "Dataverse reports no registered Crossref/DataCite citations for these deposits" is removed: "Sorry, no citations were found" appears inside a modal dialog template in the scraped HTML, alongside other unrendered UI strings, and is boilerplate rather than a result for these deposits.

**`purposes` (both) — fourth purpose softened.**
The stated purpose that other biomedical data generation projects can reuse CM4AI's packaging approach is an extrapolation. Retained in the weaker form the CM4AI preprint supports — that the Standards module provides "important and reusable enabling capabilities for this work" and that FAIRSCAPE is released under an open licence — without asserting cross-project reuse as a project purpose.

**`anomalies` (core) — trailing-comma entry reworded.**
Malformed `isPartOf` identifiers (`...data-release,`) are observable in the supplied crate JSON, but the bundle presents a *reduced* crate ("file inventories collapsed"), so the artifact may originate in preprocessing rather than upstream. The entry now states what is observable and flags the provenance ambiguity, rather than attributing the defect to the upstream record.

### 2.7 Full/core asymmetries closed

Three slots present in both schemas were populated in only one record, on identical evidence:

| Slot | Was | Now |
|---|---|---|
| `anomalies` | core only | both |
| `content_warnings` | core only | both |
| `third_party_sharing` | full only | both |

`anomalies` and `content_warnings` were added to the full record. `content_warnings` is a negative assertion — no offensive, disturbing or harmful content; the dataset comprises microscopy images, mass spectra and sequencing counts from established cell lines — which is as well supported in full as in core. `anomalies` in full is cross-referenced to the overlapping `known_limitations` and `errata` entries rather than duplicating them.

`third_party_sharing` was added to core: the bundle documents MassIVE deposits under CC0, Figshare, SRA/BioProject, and Bridge2AI Open House access subject to Code-of-Conduct attestation. There was no basis for its absence.

`distributions` remains core-only; the full schema has no analogue.

---

## 3. Left as-is

**Three audit findings self-retracted and require no action.** The auditor withdrew (a) the `subpopulations` finding — the four-state KOLF2.1J breakdown is supported by the KOLF2 SEC-MS crate; (b) the `acquisition_methods` pipetting-robot finding — the CM4AI preprint states "established automated fixation and permeabilization protocols for the pipetting robot" verbatim; (c) the `future_use_impacts` Code-of-Conduct finding — the preprint states the attestation requirement directly.

**`acquisition_methods` AP-MS replicate and batch structure — retained, scope narrowed only.** Both treated-arm crates state four biological replicates and the untagged-parental / ten-tagged-line / positive-control / DMSO-vehicle batch design in identical language. The only adjustment was to make explicit that this describes the two treated MDA-MB-468 arms, not all AP-MS in the release.

**`external_resources` musicmaps.ai portal — retained.** The U2OS visualization portal is tied to the *Nature* study, not to CM4AI, and the crate does not reference it. It is retained because the entry already carries an explicit disclaimer identifying the U2OS map as a distinct dataset, and because the *Nature* paper is a declared related publication in the crate's `associatedPublication` list. Removing it would lose a real navigational link the bundle supplies; the disclaimer prevents conflation.

**Negative determinations across the ethics slots — retained unchanged.** `human_subject_research` (none; commercially available de-identified cell lines), `at_risk_populations` (none), `informed_consent` (not applicable), `collection_consents`, `collection_notifications`, `consent_revocations`, `participant_privacy`, `participant_compensation` (all omitted or negative as appropriate) are directly and repeatedly supported: the crate's `humanSubjectResearch`, `humanSubjectExemption` and `d4d:informedConsent` fields, the Dataverse "Human Subjects: No / De-identified Samples: Yes / FDA Regulated: No" block on three separate release pages, and the CM4AI preprint's statement that the data "are non-clinical (from tissue cultures) and are considered to be de-identified." This is the best-evidenced region of both records.

**`license_and_use_terms`, `ip_restrictions`, `prohibited_uses` — retained unchanged.** CC BY-NC-SA 4.0, attribution to copyright holders and authors, dual-copyright split (Regents of the University of California; Board of Trustees of Leland Stanford Junior University for spatial proteomics raw images), commercial use requiring separate negotiation, and the clinical-decision-making prohibition are all stated verbatim across the crate, the Dataverse terms block, and the preprint.

**`errata` and `known_limitations` metadata-inconsistency entries — retained.** These correctly document the release-date discrepancy (portal says "Released on: June 17, 2025" under a heading reading "June 2026 Data Release"), the three conflicting size figures, and the embargo/incompleteness disclosures. They are the reason the `total_size_bytes` deletion above is a consistency fix rather than an information loss.

**Cross-record consistency on all remaining shared slots.** `description`, `status`, `maintainers`, `updates`, `version_access`, `retention_limit`, `tasks`, `intended_uses`, `discouraged_uses`, `distribution_dates`, `ethical_reviews`, `funders`, `keywords` and the remaining shared slots were verified byte-identical or substantively identical between the two records, both before and after reconciliation. No contradiction was found in either direction.

**Slots left unpopulated in full despite arguable support.** `was_derived_from`, `related_datasets`, `download_url` and `conforms_to_class` are each partially supported (respectively: the `isPartOf` chains to four prior release DOIs; the same four DOIs as typed relationship targets; the Dataverse Data Access API base URL, which is a template stub rather than a resolvable dataset URL; and the crate's `@type: [Dataset, EVI#ROCrate]`). None is required, and each would require a judgment the bundle does not make — which relationship type applies to a quarterly beta series, whether an API base counts as a download URL, whether `EVI#ROCrate` is a schema class in the intended sense. Consistent with the preference for omission over inference, they remain unpopulated. This is recorded here so the omission is visible as a decision rather than an oversight.

---

## 4. Net effect

| | Removed | Added | Modified |
|---|---|---|---|
| **Full** | `total_file_count`; `total_size_bytes`; one `file_collections` entry (fabricated IRI); six `file_collections[].file_count` values | `anomalies`; `content_warnings` | `creators` (×3), `data_collectors`, `collection_mechanisms`, `preprocessing_strategies`, `known_biases` (×3), `is_deidentified`, `sensitive_elements`, `sampling_strategies`, `collection_timeframes`, `instances`, `distribution_formats`, `raw_data_sources`, `existing_uses`, `purposes`, `acquisition_methods` |
| **Core** | — | `third_party_sharing` | `data_collectors`, `preprocessing_strategies`, `known_biases` (×3), `is_deidentified`, `sensitive_elements`, `sampling_strategies`, `collection_timeframes`, `distribution_formats`, `raw_data_sources`, `existing_uses`, `purposes`, `acquisition_methods`, `anomalies` |

No changes altered the referent, the ethics determinations, the licensing terms, or the embargo and completeness disclosures. All changes moved the records toward what the declared bundle states and away from inference, re-interpretation, or cross-study transfer. Two changes (`total_file_count`, `total_size_bytes`) reduce populated-slot count in service of correctness; three (`anomalies`, `content_warnings`, `third_party_sharing`) increase it in service of full/core symmetry on identical evidence.

Both records were re-validated against their respective schemas after reconciliation. Final populated-slot counts are reported in the run summary alongside the validation results.