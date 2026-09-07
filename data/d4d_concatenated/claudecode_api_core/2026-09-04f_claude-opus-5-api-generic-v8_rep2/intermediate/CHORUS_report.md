# Reconciliation Report — CHoRUS

**Project:** CHORUS (CHoRUS — the Bridge2AI AI/ML for Clinical Care Grand Challenge)
**Label:** 2026-09-04f_claude-opus-5-api-generic-v8_rep2
**Records:** full (`Dataset`), core (`CoreDataset`), derived by projection from the full record.

## What the audit found

The Phase 3 audit returned fourteen findings, none at high severity: five medium and nine low. No enum violations, no scalar/object range violations, and no invented identifiers were reported. The audit confirmed the record's factual spine — 14 contributing hospitals within 20 academic centers, 9 modalities under controlled access, 50,000 released admissions with the 45K webinar figure held as a ranked disagreement, 1.6 billion OMOP rows, 7,642 admissions with radiology, 23 Tb of waveforms, the OMOP/DICOM/WFDB/EDF+/OHNLP standards, and NIH award OT2OD032701 to Massachusetts General Hospital.

The findings fell into four groups: unsupported inference (CTP-deid characterized as imaging de-identification tooling; an affiliation derived from an email domain), plan-or-announcement written as current state (the Cohort 2 training program; a planned annotation environment), internal inconsistency between the record's own caveat and its per-subset claims, and placement/shape problems (prose in `status` and `notes`, URLs in `description` rather than the class's own pointer field, entity collapse in `maintainers`, standards named as distribution formats, an unflagged unit expansion, a supported boolean omitted).

## What was changed, and why

### Medium findings

**`preprocessing_strategies[2].preprocessing_details` — changed (both).** The original read "including de-identification tooling for imaging (CTP-deid) and a privacy scan tool for medical records." The bundle lists `CTP-deid Public` in the repository roster with no description and no stated role. The parenthetical attribution was removed; the entry now reads "Transformation of data using approaches that limit re-identification; imaging de-identification was in process for the larger cohort as of September 2025," which is what the webinar states. The privacy scan tool remains attested in `participant_privacy[0].privacy_techniques` (the repository is described as "A Privacy Scan tools for medical records"), and `CTP-deid` is still named, without a function, in the repository list under `external_resources[1].description`.

**`data_governance.committee_contact.affiliation` — removed (both).** "Tufts Medicine" was inferred from the address domain `tuftsmedicine.org`. The bundle names Jared Houghtaling only as a webinar lecturer under host "Tufts" and gives the address in the README contact block; it never states his organization. The `affiliation` list was dropped from the Person object; the `id`, `name` and `email` remain.

**`subsets[*].conforms_to` / `subsets[*].description` — changed (full).** The record's own `source_caveats` declared the webinar table too interleaved to assign its Metadata column reliably, yet the subsets assigned per-modality metadata schemas reconstructed from that same table. Both repairs the audit offered were applied: the per-subset claims were reduced to the unambiguous Data standard column (`OMOP Common Data Model` — the "with extensions" qualifier dropped from nursing flowsheets; `OHNLP` in place of "OHNLP open source schema"; `WFDB` in place of "WFDB, PhysioNet schema extended"), the phrases "with a published metadata schema" were removed from every subset description, and the top-level `source_caveats` was extended to state that the schema column, like the Metadata column, is not reliably assignable and that only the Data standard column is used. `conforms_to` at the top level and `raw_data_sources[3].raw_data_format` were adjusted in the same direction, dropping "extended PhysioNet schema" and "extended OMOP schema."

**`existing_uses[1]` — moved (both).** The Cohort 2 entry was written in the present tense from a 9 September 2025 webinar with a 26 September application deadline and a 17 November start; no trainees had been selected at source time. The entry was removed from `existing_uses`, which now carries only the attested current use, and restated as a second example under `intended_uses[2]` (Education and workforce development) in the announcement's own tense, with a `usage_notes` recording that the deadline had not passed. The audit offered either repair; the second was taken so the content is not lost.

**`ethical_reviews[0].reviewing_organization` — removed (both).** "CHoRUS Ethics pillar (Ethical and Trustworthy AI)" names a project workstream, not a reviewing body. The key was dropped, `review_details` was trimmed to the community-engagement activities the sources state, and a `source_caveats` was added recording that the bundle names no IRB, ethics committee or compliance certification and that no reviewing organization is asserted.

**`labeling_strategies` — removed (both).** The single entry held a plan for an annotation environment, not a labeling procedure applied to the data. The slot was removed from both records. The same forward-looking statement remains in `purposes[3]` ("...store, visualize and label...").

### Low findings

**`maintainers` — changed and added (both).** Ciera McCrary was extracted from the consortium entry into her own `Maintainer` (name, role, details), and the transcription commentary about the domain typo was moved from `maintainer_details` into that entry's `source_caveats`. The consortium entry now carries only the consortium.

**`external_resources[0..2]` — changed (both).** Each entry's URL was moved from the prose `description` into the class's own `external_resources` field; the descriptions retain the characterization only.

**`status` — changed (both).** Reduced from a two-clause narrative to the term `released`. The project-period sentence was folded into `description`, where it does not duplicate `funders` verbatim.

**`notes` — removed (both).** The site-banner observation was moved into `source_caveats`, where trust annotations about the sources belong. The `notes` slot is now absent from both records.

**`instances[1].description` — changed (both).** Now states that the website reports "1.6 Billion" and that the integer is that approximate magnitude expanded to units. The `counts` integer is unchanged.

**`is_deidentified.identifiable_elements_present` — added (both).** Set to `true`, with `deidentification_details` extended to say that identifiable source material remains at contributing sites where note text is stored locally and only tokens are shared.

**`preprocessing_strategies[4].preprocessing_details` — changed (both).** The bridge to the NIH abstract's contextual-factor aim was removed; the entry now states the geocoding capability alone, attributed to the UF-Geocoding repository. The contextual-factor aim was added as `purposes[4]`, where it is attested as a project goal, and removed from `acquisition_methods[1].acquisition_details`, which had carried the same bridge.

**`distribution_formats[0]`, `distribution_formats[1]` — changed (both).** Retained rather than dropped, per the second repair offered. Renamed to `OMOP Common Data Model` and `OHNLP` and each given a `source_caveats` recording that the source names a standard, not a delivery format. The list was reordered so the three true format names come first.

**`data_governance.access_review_process` — retained; `data_governance.source_caveats` added (both).** Both addresses remain in the prose. `committee_contact` is single-valued, and the README gives no name for `dbold@emory.edu`, so a `Person` object for it could not be built without inventing one. A `source_caveats` now records the asymmetry and the absence of names, roles and organizations for both addresses.

## What was left as-is

Nothing was left wholly unaddressed. Two findings were addressed by the alternative repair the audit offered rather than by removal: the two `distribution_formats` entries naming standards were kept with caveats rather than dropped, and the Cohort 2 program was relocated rather than deleted. One finding — the asymmetric access contacts — was resolved by annotation rather than restructuring, because the schema's single-valued `committee_contact` and the absence of a name for the second address leave no grounded alternative; `committee_members` would require a `Person` with an `id` and a name the bundle does not supply.

## Core record

The core record was re-derived from the reconciled full record. All changes above propagate except those in slots the core schema does not declare: `subsets` and its per-subset `conforms_to`, `direct_collection`, `splits`, `participant_privacy`, and `third_party_sharing` are full-only. `labeling_strategies` and `notes` were removed from both. The core header now carries `# Phase 4 reconciliation: completed`.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `preprocessing_strategies[2].preprocessing_details` | changed | both | CTP-deid attribution unsupported; parenthetical removed, attested claim retained |
| `data_governance.committee_contact.affiliation` | removed | both | Affiliation inferred from email domain; bundle states no organization |
| `data_governance.committee_contact` | retained | both | `id`, `name` and `email` are attested; only the affiliation was dropped |
| `subsets[3].conforms_to` | changed | full | Reduced to the table's unambiguous Data standard column |
| `subsets[5].conforms_to` | changed | full | Reduced from "OHNLP open source schema" to `OHNLP` |
| `subsets[7].conforms_to` | changed | full | Reduced from "WFDB, PhysioNet schema extended" to `WFDB` |
| `subsets[0..8].description` | changed | full | "published metadata schema" phrases removed as unreliably assignable |
| `conforms_to` | changed | both | Schema-column qualifiers dropped; standard names retained |
| `raw_data_sources[3].raw_data_format` | changed | both | "extended PhysioNet schema" removed |
| `existing_uses[1]` | removed | both | Announced program written as current use; relocated |
| `intended_uses[2].examples` | added | both | Cohort 2 program restated in the announcement's tense |
| `intended_uses[2].usage_notes` | added | both | Records that no trainees had been selected at source time |
| `ethical_reviews[0].reviewing_organization` | removed | both | Names a workstream, not a reviewing body |
| `ethical_reviews[0].review_details` | changed | both | Trimmed to attested ethics activities |
| `ethical_reviews[0].source_caveats` | added | both | Records absence of any IRB or ethics committee in the bundle |
| `labeling_strategies` | removed | both | Held a plan, not a labeling procedure applied to the data |
| `maintainers[0].maintainer_details` | changed | both | Program manager and transcription note split out |
| `maintainers[1]` | added | both | Ciera McCrary given her own Maintainer entry |
| `maintainers[1].source_caveats` | added | both | Transcription note on the published domain typo |
| `external_resources[0].external_resources` | added | both | URL moved from prose into the class's pointer field |
| `external_resources[1].external_resources` | added | both | URL moved from prose into the class's pointer field |
| `external_resources[2].external_resources` | added | both | URL moved from prose into the class's pointer field |
| `status` | changed | both | Reduced to a status term; narrative folded into description |
| `description` | changed | both | Absorbs the project-period clause displaced from status |
| `notes` | removed | both | Source-page observation moved to source_caveats |
| `source_caveats` | changed | both | Absorbs the banner note and the schema-column caveat |
| `instances[1].description` | changed | both | Flags the unit expansion of an approximate figure |
| `is_deidentified.identifiable_elements_present` | added | both | Boolean supported by local note storage and pending imaging de-id |
| `is_deidentified.method` | changed | both | CTP reference removed |
| `is_deidentified.deidentification_details` | changed | both | States where identifiable source material remains |
| `preprocessing_strategies[4].preprocessing_details` | changed | both | Cross-source bridge removed; geocoding stated alone |
| `acquisition_methods[1].acquisition_details` | changed | both | Same bridge removed from the derived-content entry |
| `purposes[4]` | added | both | Contextual-factor aim placed where it is attested as a goal |
| `distribution_formats[0]` | changed | both | Reordered to DICOM; OMOP entry retained with caveat |
| `distribution_formats[3].source_caveats` | added | both | Records that OMOP is a standard, not a delivery format |
| `distribution_formats[4].source_caveats` | added | both | Records that OHNLP is a standard, not a delivery format |
| `data_governance.access_review_process` | retained | both | Both addresses kept in prose; no grounded Person for the second |
| `data_governance.source_caveats` | added | both | Records the contact asymmetry the audit identified |