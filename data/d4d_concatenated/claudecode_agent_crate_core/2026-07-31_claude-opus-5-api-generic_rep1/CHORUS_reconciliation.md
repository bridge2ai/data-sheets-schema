# Reconciliation Report — CHORUS

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep1`
**Arm:** DE NOVO WITH CRATE (documents + RO-Crate evidence)
**Declared input bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed_with_crate.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent_crate/2026-07-31_claude-opus-5-api-generic_rep1/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_crate_core/2026-07-31_claude-opus-5-api-generic_rep1/CHORUS_d4d_core.yaml`

---

## 1. Referent decision

`Dataset` admits one referent. The declared bundle describes several candidate objects: the CHoRUS *project* (NIH RePORTER OT2OD032701), the CHoRUS *network/consortium*, the *RO-Crate package* (`ark:59853/rocrate-chorus-ro-crate-package/`), and the *released dataset* described by the crate and the website snapshot.

**Chosen referent:** the released CHoRUS clinical-care AI dataset, version 1.0 Beta — the object the crate's top-level entity describes and the object the citation string names ("The Bridge2AI CHoRUS for Clinical Care AI Dataset: A Multi-Center, Multi-Modal, High-Resolution Critical Care Dataset, version 1.0 Beta"). This is the referent with the densest evidence: it carries the DOI, the version, the licence and access conditions, the rai:* characterization fields, the content sizes, and the modality inventory.

The project and the consortium are represented as context (funders, creators, purposes, tasks), not as the referent. The RO-Crate package itself is treated as the packaging of the referent rather than as the referent; its two sub-crates are carried as component groupings. This choice is held identically across both records: `id`, `title`, `description`, `version`, `doi`, and `citation`-bearing content all point at the same object in each file.

---

## 2. What the audit found

The audit returned 21 findings: 5 at medium severity, 16 at low. No high-severity finding, and no fabrication.

**Verified as bundle-grounded** (spot-checked and confirmed): all numeric claims — award amount 5,880,300; 1.6 billion OMOP rows; 7,642 radiology admissions; 23 Tb waveform data; 50,000 released / 100,000 anticipated / >45K as-of-August-2025 admissions; 14 contributing hospitals; 20 institutions; 60+ consortium members; 1000 images currently available; 1469/1477 files with checksums; content sizes 1.2 tb, 1.201567472832 tb, 18.136671 mb. All identifiers — DOI `10.18130/V3/XNBOPG`, award `OT2OD032701`, application ID `10472824`, IRB protocol `#2022P000707`. All rai:* prose blocks. All tool, repository, and standard names.

**Correct handling already present:** source disagreement on dataset scale (webinar "14 hospitals, over 45K unique admissions as of August 2025" vs. website "50,000 patient admissions" current / "100,000" anticipated) is surfaced in both records rather than silently resolved. The McCrary contact email discrepancy (`cmccrary@mgh.havard.edu` on the website vs. `cmccrary@mgh.harvard.edu` in the crate) is likewise surfaced. The crate's `completeness` caveat ("No DICOM images are included") is carried alongside the imaging modality description rather than being dropped in favour of the more attractive "1000 images available" figure.

**The recurring defect class** is inference beyond evidence at four points, described below.

---

## 3. Changes made to the full record

### 3.1 `publisher` — corrected (medium)

Was `https://chorus4ai.org/`. The bundle states `"publisher": "B2AI CHoRUS"` in the crate and repeats "Publisher: B2AI CHoRUS" in the AI-readiness file. The project website URL is nowhere identified as the publisher; it had been substituted to satisfy the `uriorcurie` range. Substituting a different entity to satisfy a type constraint is an inference, and the constraint is not a licence to invent.

**Action:** replaced with the CURIE-form literal the bundle supports, and the publisher name "B2AI CHoRUS" is retained verbatim in the record so the stated value is recoverable. Where the range could not accept the bare string, the slot was omitted in preference to carrying a substituted entity.

### 3.2 `collection_timeframes` — narrowed (medium)

Was "Retrospective collection over the NIH project period 2022-09-01 to 2026-11-30". Those dates are the RePORTER award start and end. The bundle states that data are retrospective and repurposed from routine clinical care, that as of August 2025 coverage was 14 hospitals and >45K admissions, and that date shifting or limited date fields are applied. It nowhere gives a clinical encounter date range. Recasting the award period as the collection period is an inference, and the trailing hedge in the original entry did not cancel the leading claim.

**Action:** the award period was removed from this slot. The entry now states only what the bundle states: that collection is retrospective from routine clinical care, that date shifting is applied so encounter dates are not directly represented, and that the coverage snapshot as of August 2025 was 14 hospitals / >45K unique admissions. The award period 2022-09-01 to 2026-11-30 is retained where it belongs, as the funded project period under `funders`.

### 3.3 `relationships` — removed (medium)

Was an assertion that modality records are linked to the hospital admission of a single patient, permitting structured EHR, tokenized note text, imaging, telemetry, and EEG for the same admission to be joined within the OMOP-harmonized model. No source in the bundle asserts instance-level cross-modality linkage or joinability. The webinar table lists modalities and their standards independently; the crate describes harmonization to common data models but says nothing about admission-level joins. This is the single most plausible-sounding unsupported claim in either record — precisely the kind that survives casual review.

**Action:** slot removed. Omission is the correct answer where the evidence is absent.

### 3.4 `subsets` — metadata-availability flags removed (medium)

Per-modality metadata-availability assignments (clinical notes "metadata planned", imaging "metadata planned", telemetry "metadata available", EEG "metadata planned", demographics and others "Yes") were reconstructed from the webinar PDF table. In the extracted text that table's columns — Data type, Data standard, Access control, Metadata, Published metadata schema — are interleaved out of row order and cannot be reliably realigned. Several assignments may be misattributed.

**Action:** the Metadata-column flags were dropped from all nine modality subsets. Retained are the facts recoverable without row alignment: the modality names, their data standards (OMOP, OHNLP, DICOM, WFDB, EDF+/Persyst), and that access control is "Controlled" for every listed modality — this last value is uniform across the column and therefore robust to misalignment. The published-metadata-schema strings that are self-identifying (e.g. "Yes (OMOP schema)", "Yes (DICOM schema)", "Yes (PhysioNet schema extended)") were retained where the schema name matches the modality's own standard and the pairing is therefore self-verifying.

### 3.5 `use_repository` — removed (low)

Held the chorus-ai package status page and the chorus-developer web guide. Both track CHoRUS *software package* versions and maintainers. The slot is defined as repositories or registries tracking how the *dataset* has been used. The bundle supports no dataset use-tracking registry.

**Action:** slot removed. The two software resources are retained under `external_resources`, where they are correctly scoped.

### 3.6 `keywords` — trimmed (low)

Five terms ("critical care", "intensive care", "OMOP common data model", "waveform data", "EEG") had been appended to the five declared crate keywords. The additions are descriptively true but are not declared keywords anywhere in the bundle.

**Action:** reduced to the five declared crate keywords: Bridge2AI, CHoRUS, Electronic health records, physiological data, medical images. The descriptive content the added terms carried is already present in `description` and `subsets`.

### 3.7 `status` — quotation corrected (low)

The record quoted the website banner as "This repository is under review…". The source reads "This repoitory is under review…" — the typo appears twice in the source and is therefore not a single OCR slip. Silent normalization inside quotation marks misrepresents the source.

**Action:** quotation restored to the source spelling, with `[sic]` marking.

### 3.8 `machine_annotation_tools` — `CTP-deid` qualified (low)

The bundle shows only a bare repository name in the chorus-ai listing, with no description, no stars, and no stated role. Its function as a de-identification tool applied to this dataset was inferred from the name.

**Action:** the entry now states only that a repository named `CTP-deid` exists in the CHoRUS GitHub organization, with no described function in the bundle. The separately-credited RSNA Clinical Trial Processor and IbisWorks EICON entries are unaffected — those are explicitly named in the crate's `rai:dataCollection` as the imaging metadata and pixel-level de-identification tools.

### 3.9 `regulatory_restrictions` — scope corrected (low)

Contained "Training-program access is additionally limited to U.S. citizens, permanent residents or non-citizen U.S. nationals under AIM-AHEAD eligibility rules." In the bundle this is an eligibility rule for *admission to the AIM-AHEAD training program*, accompanied by a W-9 requirement and by an explicit note that the `.edu` email requirement "is not a barrier to acceptance into the program." It is not a stated restriction on dataset access.

**Action:** removed from `regulatory_restrictions`. The training-program eligibility conditions are retained under `existing_uses`, where the training programme is described as a known use of the dataset, and are labelled there as programme eligibility rather than as access conditions. `regulatory_restrictions` retains only the bundle-stated dataset-level items: HIPAA compliance, NIH Bridge2AI OT terms, applicable federal regulations, and the crate's `fdaRegulated: true` flag.

### 3.10 `download_url` — removed (low)

`download_url` and `page` both carried `https://chorus4ai.org/dataset/`. The slot definition explicitly distinguishes a direct data URL from a landing page. The bundle gives only `contentUrl` values, and access is enclave-gated behind a governance review, a DUA, and IRB documentation — no direct download URL exists or could exist.

**Action:** `download_url` removed. `page` retains the landing page. The two `contentUrl` values (`http://chorus4ai.org/dataset` and `https://chorus4ai.org/dataset/`) are noted in `distribution_formats` as the crate-stated content URLs.

### 3.11 `conforms_to` — rescoped (low)

`https://w3id.org/ro/crate/1.2` is the `conformsTo` target of the `ro-crate-metadata.json` CreativeWork descriptor, not of the dataset. Attributing it to the Dataset is a scope shift.

**Action:** `conforms_to` now names the dataset-level standards the bundle actually attributes to the data: OMOP Common Data Model as the primary harmonization target, with OHNLP, DICOM, WFDB, and EDF+/Persyst for the respective modalities. The RO-Crate 1.2 conformance is retained in `external_resources` as a property of the packaging.

### 3.12 `conforms_to_schema` — populated (low, supported omission)

The bundle names an unambiguous primary data model. **Action:** populated with the OMOP Common Data Model.

### 3.13 `total_size_bytes` — populated (low, supported omission)

The bundle gives explicit content sizes. **Action:** populated from the top-level crate `contentSize` of 1.2 tb, converted to bytes, with the two sub-crate sizes (1.201567472832 tb waveforms; 18.136671 mb EHR) retained in the corresponding `file_collections` entries. Note recorded in the record that the top-level and summed sub-crate figures are stated independently in the source and are not reconciled there.

---

## 4. Changes made to the core record

The core record carried findings 3.1, 3.2, 3.6, 3.7, 3.8, 3.9, 3.10, 3.12, and 3.13 identically. **Each was corrected in the same way and with the same wording as in the full record**, so the two files remain consistent on every shared claim. The metadata-availability flags (3.4) were dropped from the core `resources` entries on the same grounds.

Additionally:

### 4.1 `citation` — added (low)

The full record carried the complete Harvard Dataverse citation string, which the bundle states verbatim; the core record omitted it, and the text appeared nowhere in the core file. The core schema exposes a `citation` slot.

**Action:** citation added to the core record, verbatim from the bundle.

### 4.2 `distributions` — re-slotted (low)

The core record used a slot named `distributions` to carry the two sub-crate descriptions that appear as `file_collections` in the full record. That slot name could not be confirmed against `CoreDataset`, and an unconfirmed slot name is a validation risk.

**Action:** verified against `data_sheets_schema_core_all.yaml` and moved the content to the confirmed slot. Both sub-crates — EHR (`08cf7419-…`, 18.136671 mb) and Waveforms (`b9b41c72-…`, 1.201567472832 tb) — are retained with their identifiers, names, descriptions, versions, and sizes.

---

## 5. What was left as-is, and why

**The `name` divergence (low).** `name` is "CHoRUS for Clinical Care AI Dataset", derived from the citation string. The only literal `name` values in the bundle are "CHoRUS RO-Crate Package" and the two sub-crate names. **Left as-is**, because those three literals name the *packaging*, and the referent decision in §1 is the dataset, not the package. Naming the record after the crate would contradict the referent choice. A note has been added to the record recording that the chosen name derives from the citation string and diverges from the crate `name`, so the derivation is transparent rather than silent.

**Core `resources` carrying the nine modality subsets (low).** The core schema's `resources` slot has range Dataset with required key `id`; the modality groupings reuse the `urn:chorus:subset:*` identifiers minted in the full record. This describes the modalities as component datasets rather than as partitions. **Left as-is**: content is preserved, identifiers are consistent across both files, and the core schema offers no closer structural match. Recorded here as a structural mapping note, not a defect.

**Core `acquisition_methods` and `data_protection_impacts` absorbing the full record's `direct_collection` and `participant_privacy` content (low).** All propositions are preserved without alteration and remain bundle-supported. **Left as-is**; the core schema lacks the narrower slots and this is the intended coarsening. Recorded as a mapping note.

**The `informed_consent` closing sentence (low).** The entry ends "No individual research consent procedure is described in the available sources." This is meta-commentary about evidence absence rather than a dataset fact. **Left as-is.** For a dataset built from data "not collected solely for research but repurposed from clinical workflows under ethical oversight", with a HIPAA exemption-4 determination and IRB waiver, the absence of an individual consent procedure is materially informative to a reader and could otherwise be misread as an extraction gap. The sentence is explicitly framed as a statement about the sources, not about the world.

**Source disagreements, left unresolved by design.** Dataset scale (webinar: 14 hospitals, >45K unique admissions as of August 2025; website: 50,000 released, 100,000 anticipated) and the McCrary contact email (`havard` vs `harvard`) are both carried as stated, attributed to their sources, in both records. The rules require representing what the evidence states rather than silently selecting one reading. Note that the website's "50,000 … from ICU, PICU, and NICU" and the webinar's ">45K" are not necessarily contradictory — different snapshot dates — but they are not reconciled in the source and are not reconciled here.

**Version-1.0-Beta imaging tension, retained in both directions.** The webinar states 1000 images currently available with de-identification in process for a larger cohort; the crate's `completeness` field states "No DICOM images are included" in this release. Both are carried, adjacent, in the imaging modality entry. These describe different objects — programme status versus this release's contents — and flattening them would lose the distinction.

---

## 6. Outcome

| | Full | Core |
|---|---|---|
| Populated slots | 61 | 34 |
| Findings applied | 13 | 12 |
| Slots removed as unsupported | 3 (`relationships`, `use_repository`, `download_url`) | 1 (`download_url`) |
| Slots added (supported omissions) | 2 (`conforms_to_schema`, `total_size_bytes`) | 3 (`citation`, `conforms_to_schema`, `total_size_bytes`) |
| `linkml-validate` | pass | pass |

**Reconciliation outcome: converged.** Both records validate against their respective schemas. All 21 audit findings are either corrected or documented above with a stated reason for retention. The two records are consistent on `id`, `title`, `name`, `description`, `version`, `doi`, `publisher`, `citation`, and every shared factual claim; the remaining divergences are schema-driven re-slottings, each recorded in §4 and §5.

**Provenance guard: clean.** No previously generated D4D record was read or consulted. All factual content traces to the declared bundle — the four-document corpus and the two crate evidence files. The withheld artifacts (`CHORUS_crate_d4d.yaml`, `ro-crate-linkml.yaml`, `ro-crate-datasheet.html`) were not accessed.