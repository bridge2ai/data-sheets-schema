# CHORUS — D4D Reconciliation Report

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep3`
**Arm:** DE NOVO WITH CRATE (documents + RO-Crate evidence)
**Declared input bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed_with_crate.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent_crate/2026-07-31_claude-opus-5-api-generic_rep3/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-31_claude-opus-5-api-generic_rep3/CHORUS_d4d_core.yaml`

---

## 1. Referent declaration

`Dataset` admits one referent. Both records take the referent to be:

> **The Bridge2AI CHoRUS for Clinical Care AI Dataset, version 1.0 Beta**, as packaged in the CHoRUS RO-Crate Package (`ark:59853/rocrate-chorus-ro-crate-package/`, DOI `10.18130/V3/XNBOPG`), publisher B2AI CHoRUS.

This is the referent the declared bundle supports most directly: it is the only entity in the bundle carrying a DOI, a stated citation, a version string, a license/DUA, a conditions-of-access statement, an IRB protocol, and file-level provenance.

Two adjacent entities are deliberately **not** treated as the referent, and appear only as context:

- **The NIH award OT2OD032701 / CHoRUS data generation project** (NIH RePORTER, chorus4ai.org). Recorded under `funders`, `purposes`, `addressing_gaps`, `tasks` and in narrative description as the programme that produced the dataset — not as the dataset itself.
- **The AIM-AHEAD Bridge2AI for Clinical Care Training Program (Cohort 2)**. Recorded under `existing_uses` and `license_and_use_terms` as a downstream consumer with its own access route — not as the dataset itself.

The bundle also carries **three different size/scope snapshots** of CHoRUS data (webinar, August 2025: 14 hospitals / 45K+ admissions; chorus4ai.org "Current Released Dataset": 50,000 admissions, 1.6 B OMOP rows, 23 Tb waveform; crate v1.0 Beta: `contentSize` 1.2 tb, "interim release with partial data … No DICOM images are included"). These are **not** merged. Each is carried with its source and as-of scope attached.

---

## 2. What the audit found

The audit returned **15 findings: 0 high, 4 medium, 11 low.** No breach of the evidence boundary was found — no fact in either record traces to a prior D4D, and no cross-source merge of distinct entities occurred. The defects cluster into four kinds:

| Kind | Findings |
|---|---|
| Derived/normalized values not asserted in the bundle | EHR sub-crate `issued`; `total_size_bytes`; `funders` currency unit |
| Existence-of-artifact read as use-in-production | `machine_annotation_tools` (three repos); geocoding as preprocessing/sensitive element; children's-hospital site attribution |
| Slot-fit mismatches | de-identification tools under `machine_annotation_tools`; split design under core `sampling_strategies`; trainee eligibility under `regulatory_restrictions`; unverifiable core `distributions` |
| Minor inferential embellishment | `language`; adult ICU population; TSV↔OMOP binding; notebook distribution claim; unqualified size claims |

---

## 3. Changes made

### 3.1 Full record

**`total_size_bytes` — removed.**
The value `1201585609503` was a sum of the two sub-crate `contentSize` strings under an unstated decimal-power-of-ten reading of "tb"/"mb". No byte count is asserted anywhere in the bundle, and the top-level crate independently gives a rounder, non-reconciling `1.2 tb`. Under *prefer omission over inference*, the derived integer is dropped. The stated strings are retained verbatim on the corresponding `file_collections` / `resources` entries, so no evidence is lost.

**`machine_annotation_tools` — removed entirely.**
Two distinct problems, one remedy:
- `privacy_scan_tool`, `CTP-deid` and `UF-Geocoding` are evidenced only as repositories in the `chorus-ai` GitHub organization. Repository existence is not a claim of application to the released dataset.
- RSNA Clinical Trial Processor and IbisWorks EICON *are* evidenced as applied, but as **de-identification** tooling (`rai:dataCollection`), not annotation. They were already correctly carried under `preprocessing_strategies`, which is unchanged.

The GitHub repositories are retained under `external_resources` with existence-only framing ("repository in the chorus-ai GitHub organization").

**`preprocessing_strategies` / `sensitive_elements` — geocoding entries removed.**
`rai:dataCollection` enumerates EHR→OMOP extraction, imaging de-identification, waveform→WFDB capture, and harmonization. Geocoding of OMOP Location entities via DeGauss is not among them; the only evidence is the forked `UF-Geocoding` repo. Removed from both slots; the repo remains under `external_resources`.

**`at_risk_populations` — site attribution clause removed.**
The clause naming Seattle Children's Hospital and Nationwide Children's Hospital / OSU as *contributing institutions* was struck. The bundle lists them only as author affiliations and never enumerates the 14 Data Acquisition centers. The minors/at-risk claim itself is retained, now resting solely on the supported statement that admissions come from "ICU, PICU, and NICU".

**`subpopulations` — reworded.**
"spanning adult, pediatric and neonatal critical care populations" replaced with the bundle's own unqualified enumeration ("ICU, PICU, and NICU"). "ICU" alone does not assert an adult population.

**`distribution_formats` — two entries rewritten.**
- The TSV entry no longer binds `text/tab-separated-values` to the OMOP EHR component; it now states that TSV is among the formats present in the crate (per `ai_ready_score.computability.standardized`), which is what the bundle says.
- The notebook entry no longer claims `.ipynb` files are "distributed alongside the data within the Collaborative Cloud environment." It now records `.ipynb` as a format present in the crate, and the training-program canonical notebooks are described separately under `existing_uses`, where they are actually attested.

**`funders` — currency unit removed.** `5880300` as stated in NIH RePORTER; "USD" was added.

**`regulatory_restrictions` — narrowed.**
Removed (a) the AIM-AHEAD trainee citizenship / permanent-residency / visa eligibility rules, which the bundle attributes to *training-program eligibility*, not to regulatory constraints on the data, and (b) the closing meta-statement that the bundle does not name ITAR/EAR, which is commentary about the evidence rather than a dataset fact. Retained: HIPAA, HIPAA exemption 4 (45 CFR 46.104(d)(4)), NIH Bridge2AI OT terms, NIST 800-53 alignment, FDA-regulated flag, and the `.edu` email / DUA access conditions. The trainee eligibility rules now sit only in the `existing_uses` training-program entry, where they are correctly attributed.

**Size-claim scoping — qualifiers added.**
The `instances` entry carrying "23 Tb waveform data" and the crate `contentSize` statements now each carry their source and as-of scope inline (chorus4ai.org "Current Released Dataset" snapshot vs. crate v1.0 Beta interim release, "not all patients in the CHoRUS full cohort are included"). The two figures no longer read as a contradiction; they read as two differently-scoped statements, which is what they are.

**Sub-crate `issued` — disambiguation basis recorded.**
The EHR sub-crate `datePublished` string `03/04/2026` is left verbatim in the entry description, but a note now records that the top-level crate pairs `datePublished: 2026-04-03` with `releaseDate: 03/04/2026`, disambiguating the format as day/month/year within this crate. This makes the full record's treatment explicit and lets the core record's normalization be checked against it.

**`language` — removed.** `en` is nowhere declared for the dataset; it was inferred from the language of the source documents.

### 3.2 Core record

**EHR sub-resource `issued` — corrected to `2026-04-03T00:00:00`.**
This was the most consequential defect. The core record read the identical string `03/04/2026` as 4 March for the EHR sub-crate and as 3 April for the waveforms sub-crate. The crate disambiguates itself (`datePublished: 2026-04-03` = `releaseDate: 03/04/2026`), so day/month/year is the reading the evidence supports. Both sub-resources now carry `2026-04-03T00:00:00`, consistent with each other, with the top-level `datePublished`, and with the full record's newly-explicit note.

**`distributions` — removed; content remapped.**
The slot could not be verified against `CoreDataset` from the declared inputs, and its content duplicated material already carried under `file_collections` / `subsets` in the full record. Content was remapped onto `distribution_formats` and the `resources` sub-entries, which are schema-verified. Validation confirms the remapping.

**`citation` — added.**
The bundle states an explicit recommended citation ("The CHoRUS for Clinical Care AI Network. *The Bridge2AI CHoRUS for Clinical Care AI Dataset: A Multi-Center, Multi-Modal, High-Resolution Critical Care Dataset*, version 1.0 Beta. Harvard Dataverse, Apr. 2026."). It was present in the full record and absent from the core one; a clearly-stated, citation-bearing fact should not be dropped in reduction.

**`sampling_strategies` — hold-out/split entry relocated to `known_limitations`.**
The entry described hold-out availability and the need for internal overfitting controls in development splits — split design, not sampling methodology. It now sits where the full record puts it. The underlying facts (from `rai:dataLimitations`) are unchanged; only placement moved. Federated access / balanced-cohort sampling remains under `sampling_strategies`, which is where the GitHub overview's statement actually belongs.

**Mirrored full-record corrections applied.**
`machine_annotation_tools` (removed), geocoding entries (removed), `at_risk_populations` site attribution (removed), `subpopulations` adult inference (reworded), `distribution_formats` bindings (rewritten), `funders` currency (removed), `regulatory_restrictions` narrowing, `language` (removed). Both records now make the same claims from the same evidence.

---

## 4. What was left as-is, and why

**`publisher: "B2AI CHoRUS"` (both records).**
The slot range is `uriorcurie`, and this value is a free-text string containing a space — not a well-formed URI or CURIE. It is nonetheless left unchanged: `B2AI CHoRUS` is the only publisher the bundle names, and minting a URI or CURIE for it would fabricate an identifier that appears nowhere in the evidence. Fidelity to the stated value is preferred over cosmetic conformance to the range. Both files validate.

**Two spellings of the contact email.**
`cmccrary@mgh.havard.edu` (chorus4ai.org, with the typo) and `cmccrary@mgh.harvard.edu` (crate `contactEmail`) are both preserved, each attributed to its source. The bundle contains both; silently normalizing would suppress a real discrepancy in the evidence.

**Three non-reconciling cohort/scale snapshots.**
14 hospitals / 45K+ admissions (webinar, Aug 2025); 50,000 admissions / 1.6 B OMOP rows / 7,642 radiology admissions / 23 Tb waveform (chorus4ai.org "Current Released Dataset"); 100,000 admissions / 9 modalities / 14 hospitals (chorus4ai.org "Anticipated Final Dataset"); 1.2 tb interim crate. All four retained, each scoped and sourced. No single figure was elected as "the" cohort size.

**Duplicated `rai:dataBiases` and `rai:potentialBiases`.**
The crate carries byte-identical text under both keys. Represented once under `known_biases`, noted as appearing under both crate properties. This is deduplication of an identical string, not selection between disagreeing sources.

**Core omissions relative to the full record.**
`participant_privacy`, `direct_collection`, `variables`, `splits`, `relationships`, `file_collections`, `third_party_sharing` are populated in the full record and absent from the core one. `participant_privacy` content was folded into `data_protection_impacts`; `third_party_sharing` into `license_and_use_terms`. These are consistent with core-schema reduction and could not be checked against the supplied inventory, which covers only the full `Dataset` class. `linkml-validate` against `CoreDataset` passes, confirming no required slot is missing. Left as-is.

**`is_deidentified`, `ethical_reviews`, `human_subject_research`, `confidential_elements`.**
Verbatim from the crate (`deidentified: true`, the named MGB IRB reviewers and local-context review, `humanSubjectResearch: "Yes"`, `irbProtocolId: #2022P000707`, `confidentialityLevel: HL7:2V`). No change needed.

**Absent modules left absent.**
`collection_consents`, `collection_notifications`, `consent_revocations`, `informed_consent`, `participant_compensation` (for data subjects), `annotation_analyses`, `imputation_protocols`, `errata`, `retention_limit`, `version_access`, `use_repository`, `extension_mechanism`. The bundle states that data are "repurposed from clinical workflows under ethical oversight" and "not collected solely for research," with a HIPAA exemption — but it never describes consent mechanics, revocation, imputation, errata, or retention schedules. These slots remain unpopulated. Absence of evidence was treated as a correct empty answer, not as an invitation to construct a plausible one.

---

## 5. Outcome

| | Full | Core |
|---|---|---|
| Populated top-level slots, pre-reconciliation | 68 | 44 |
| Slots removed | 3 | 2 |
| Slots added | 0 | 1 |
| Slots edited in place (content corrected, not removed) | 7 | 8 |
| **Populated top-level slots, post-reconciliation** | **65** | **43** |
| `linkml-validate` | **PASS** (`Dataset`) | **PASS** (`CoreDataset`) |

**Reconciliation outcome: RESOLVED.** All 15 findings are dispositioned — 11 by amendment, 4 by documented retention. The two records now assert the same facts from the same evidence, with no remaining cross-record contradiction; the `03/04/2026` normalization, the derived byte total, and the unverifiable `distributions` slot were the three substantive divergences and all three are closed. The referent is held consistently across both records. Provenance record written via `d4d provenance record`.