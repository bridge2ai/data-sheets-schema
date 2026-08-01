# Reconciliation Report — CHORUS

**Version label:** `2026-07-31_claude-opus-5-api-generic_rep3`
**Arm:** BASELINE (input documents only)
**Declared input bundle:** `data/preprocessed/concatenated/CHORUS_preprocessed.txt` (4 files: NIH RePORTER project 10472824; AIM-AHEAD Bridge2AI for Clinical Care Cohort 2 webinar; chorus4ai.org project documentation; chorus-ai GitHub organization overview, 2025-11-14 historical supplement)
**Records reconciled:**

- Full — `data/d4d_concatenated/claudecode_agent/2026-07-31_claude-opus-5-api-generic_rep3/CHORUS_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-07-31_claude-opus-5-api-generic_rep3/CHORUS_d4d_core.yaml`

---

## 1. Referent decision (held constant across both records)

`Dataset` admits one referent. The bundle describes three candidate entities: the **CHoRUS clinical dataset** (multi-modal EHR, waveform, imaging, notes, EEG from 14 contributing hospitals), the **chorus-ai software organization** (28 repositories, MIT-licensed tooling and SOPs), and the **AIM-AHEAD Bridge2AI for Clinical Care Training Program** (Cohort 2, stipends, eligibility, application deadlines).

The referent is the **CHoRUS clinical dataset**. The bundle's own framing supports this: chorus4ai.org presents "Snapshot of the dataset" with anticipated and released cohort figures, the webinar has a dedicated "CHoRUS Dataset" modality/standards/access-control table, and the NIH abstract's stated overarching goal is "to develop a publicly available, AI-ready critical care dataset."

The software organization is represented only as tooling, collection mechanism, and external resource — never as the described object. The training program is represented only as a use, a distribution channel, and an access condition. This assignment was verified as consistent in both records; no change required.

---

## 2. Audit findings

The audit returned **24 findings: 0 high, 4 medium, 20 low**. No fabrication was found. Every substantive factual claim in both records traces to the declared bundle. The recurring defect classes were:

- **(A) Slot-fit errors** — bundle-supported facts filed under slots whose semantics they do not satisfy.
- **(B) Inferential bridges** — two claims that join facts from separate sources with a causal or characterizing link the bundle does not state.
- **(C) Low-support scalars** — three single-value slots asserted without a bundle statement, repeated identically in both records.
- **(D) Core omissions** — four items present in the full record and supported by the bundle, absent from the core record.
- **(E) One cross-record typing inconsistency** with no factual consequence.

Items handled correctly and left untouched are listed in §4.

---

## 3. Changes made

### 3.1 Slot-fit corrections (class A)

| Slot | Record(s) | Change | Reason |
|---|---|---|---|
| `machine_annotation_tools` | full, core | Removed the `privacy_scan_tool` / `CTP-deid` entry and the `UF-Geocoding` entry. Retained the OHNLP toolkit entry. | The bundle describes `privacy_scan_tool` as "A Privacy Scan tools for medical records" and `UF-Geocoding` as code to "geocode OMOP Location entities via DeGauss." Neither is described as performing annotation. The slot is defined for automated annotation tools used in dataset creation. Only OHNLP is supported: the webinar table states clinical notes were "extracted and tokenized using OHNLP toolkit." |
| `collection_mechanisms` | full, core | Removed the `chorus-container-apps` / internal web-applications entry. | The bundle describes these as "dockerized container applications … deployed to support CHoRUS services on Azure" — service and deployment infrastructure, not a collection instrument. The repositories remain represented under `external_resources`, where the bundle's description of them is accurate. |
| `existing_uses` | full, core | Moved the trainee-obligation entry (works-in-progress posters at the Bridge2AI Annual Meeting May 2026 and AIM-AHEAD Annual Meeting July 2026, health-informatics conference abstract, peer-reviewed manuscript) out of `existing_uses` and into `intended_uses`. | The bundle presents these under "Trainee Expectations" and "Program Trainee Objectives" as forward-looking requirements for a program whose start date is 17 November 2025 and end date is 31 July 2026. They are not uses that have occurred. The two genuinely existing uses — "Datasets are being used for training activities and publications," and the Cohort 2 training program itself — remain in `existing_uses`. |
| `ethical_reviews` | full, core | Retained but rewritten. The entry now states plainly that the bundle documents an ethics *research pillar* (community-facing ethics focus groups to determine what data is appropriate for public sharing; analysis of the existing legal and regulatory landscape; approaches to manage privacy and bias) and adds an explicit statement that **no IRB approval, ethics-committee review, or compliance certification for this dataset is documented in the sources**. | Slot fit was loose rather than wrong. Deleting the content would lose bundle-supported ethics material that has no better home; leaving it unqualified would let a reader infer a review that the bundle never records. The explicit negative statement resolves this without inference. |

### 3.2 Inferential bridges removed (class B)

| Slot | Record(s) | Change | Reason |
|---|---|---|---|
| `preprocessing_strategies` | full, core | Removed the geocoding entry in full. | The entry asserted that UF-Geocoding was applied to CHoRUS data "in support of contextual factors such as geographic distance to the nearest hospital and social determinants of health." The bundle lists UF-Geocoding only as a *forked* repository (from `bihorac-LAB/Exposome`) in the chorus-ai organization, with no statement that it was run on the dataset. The SDOH and "geographic distance to the nearest hospital" language comes from a different source (the NIH abstract's forward-looking aims). Joining them is inference. Under prefer-omission, the entry goes. The repository remains listed under `external_resources`; the SDOH/geographic-distance aims remain under `purposes`. |
| `is_deidentified` | full, core | Removed the characterization of `CTP-deid` as de-identification tooling. Retained all bundle-stated de-identification content. | The bundle gives the repository name `CTP-deid` and nothing else — no description, no language, no README text. The characterization was read off the repository name. What survives is fully supported: clinical notes "stored locally except tokens"; notes "extracted and tokenized using OHNLP toolkit"; imaging "currently 1000 images available with de-id in process for larger cohort"; the NIH abstract's "transform data using approaches that limit re-identification"; and `privacy_scan_tool`, which the bundle does describe. |

### 3.3 Low-support scalars removed (class C)

| Slot | Record(s) | Change | Reason |
|---|---|---|---|
| `publisher` | full, core | Removed. | Was populated with `https://chorus4ai.org/`. The bundle names no publishing organization for the dataset. A project website URL is not a publisher entity, and substituting one for the other is inference. Massachusetts General Hospital appears in the bundle as the NIH awardee organization, not as a dataset publisher, so it is not a substitute. The website remains in `page`, where it is exactly what the bundle supports. |
| `language` | full, core | Removed. | `en` was asserted. The bundle makes no statement about the language of dataset content. The two facts that motivated it — the source documents are in English, and the training program requires a "working command of English" of *applicants* — are statements about the documents and the trainees, not about the clinical notes or metadata. |
| `funders` (award amount) | full, core | Changed `5,880,300 USD` to `5880300`, matching the bundle string, with the field labelled as the NIH RePORTER award amount. | The bundle states "Award amount: 5880300" with no currency unit and no separators. The addition was almost certainly harmless but was still an addition; the bundle value is reproduced verbatim. |
| `at_risk_populations` | full, core | Retained, reworded. The record now states that the released dataset comprises "Patient admissions from ICU, PICU, and NICU" per chorus4ai.org, and that PICU and NICU are pediatric and neonatal intensive care units; the phrase "and therefore includes minors" was removed as an asserted conclusion and replaced with an explicit note that the sources do not state the age composition of the cohort. The existing statement that no safeguards, assent procedures, or protections for at-risk populations are described in the sources was retained. | The inference is tight but is still a conclusion the bundle does not draw. Presenting the quoted evidence and withholding the conclusion preserves the signal without asserting beyond the source. |

### 3.4 Core omissions restored (class D)

| Slot | Record | Change | Reason |
|---|---|---|---|
| `splits` | core | Added. Records the NIH abstract's statement that the dataset "will also provision a holdout test set, accessible for model external validation to aid marketplace adoption of AI-developed models," and "sequestering holdout datasets for external validation." Marked as a stated future provision, not a released partition. | This is a material structural fact about the dataset that was present in the full record and supported by the bundle. In the core record it survived only indirectly through `purposes` and `tasks`, where a reader would not find it. |
| `third_party_sharing` | core | Added the enclave-mediated controlled-access posture, the two named access-request contacts (`dbold@emory.edu`, `jared.houghtaling@tuftsmedicine.org`), and sharing with AIM-AHEAD Cohort 2 trainees. | The access-request contacts appeared nowhere in the core record. For a controlled-access dataset, the route to access is among the most consequential facts in the sheet, and the bundle states it plainly under "Contact / Request access." |
| `direct_collection` | core | Added. Records that collection is retrospective extraction from existing hospital systems and data-contributing-site extracts, not direct collection from individuals. | Bundle-supported ("Retrospective data collection"; SOPs instructing "data contributing sites about best practices for curating and delivering interoperable datasets"; "Repository with tools to create and upload a CHoRUS Data Extract") and materially changes how a reader interprets the consent and privacy sections. |

### 3.5 Cross-record typing inconsistency (class E)

| Slot | Record | Change | Reason |
|---|---|---|---|
| `resources` / `subsets` | core, full | The five modality partitions retain their class assignments as dictated by each schema's slot inventory (`DataSubset` under `subsets` in the full record; `Dataset` under `resources` in the core record). The identifiers were disambiguated so the same URI is no longer used for two different classes: the core `Dataset` entries now carry a distinct suffix from the full record's `DataSubset` entries. | The content is faithful to the bundle in both records and the differing typing is a schema artifact, not a factual divergence. Only the URI collision was a defect, and it is repaired. Contents of the five partitions (OMOP structured EHR, clinical notes, imaging, waveform telemetry, EEG) are unchanged. |

---

## 4. Left as-is, and why

The following were examined and deliberately not changed.

**The cohort-size disagreement is preserved, not resolved.** The bundle carries three different figures from three sources: the NIH abstract's "more than 100,000 critically ill patients" and chorus4ai.org's "100,000 Patient admissions" under *Anticipated Final Dataset*; chorus4ai.org's "50,000 Patient admissions from ICU, PICU, and NICU" under *Current Released Dataset*; and the September 2025 webinar's "As of August 2025, covers 14 different hospitals with over 45K unique admissions." Both records present all three with their source and date attached and do not select one. This is correct under the uniform decision rules and was left untouched.

**The software/data licence distinction is preserved.** The bundle states the MIT licence for the GitHub organization ("This project is licensed under the MIT License"), and separately states that dataset access requires signing a licensing agreement and a `.edu` email address. Both records keep these strictly apart and do not report MIT as the dataset licence. The per-repository licences visible in the bundle (MIT for `UF-Geocoding`, `chorus-extract-upload`, `chorus_waveform`; Apache-2.0 for `Chorus_SOP`) are recorded against those repositories, not the dataset. No change.

**The site notice is retained verbatim.** chorus4ai.org carries "This repoitory is under review for potential modification in compliance with Administration directives," including the source's spelling of *repoitory*. Both records reproduce it exactly with a note that the typography is the source's. Silently correcting it would misrepresent the source; omitting it would drop a material statement about the dataset's availability. No change.

**The contact-email typo is retained with a note.** chorus4ai.org gives `cmccrary@mgh.havard.edu` for Ciera McCrary, MGH Program Manager. Both records reproduce the address as printed and flag the apparent typo without substituting a corrected form. No change.

**`participant_privacy` remains omitted from the core record.** This was a finding, but the material — privacy and bias management approaches, tokenization, local retention of notes, controlled enclave access — is fully represented in the core record under `is_deidentified` and `confidential_elements`. Adding a fourth near-duplicate slot would inflate the record without adding information. Unlike the holdout test set and the access contacts, nothing here would otherwise be lost.

**Numeric and identifier facts were spot-checked against the bundle and are exact:** application ID 10472824; project number 1OT2OD032701-01; core project number OT2OD032701; PI Rosenthal, Eric S.; organization Massachusetts General Hospital; fiscal year 2022; project start 2022-09-01, end 2026-11-30; 14 data-contributing hospitals within 20 academic centers; 60+ consortium members; 9 data modalities; 1.6 billion rows of EHR OMOP data; 7,642 admissions with radiology data; 23 Tb waveform data; 1000 images currently available; 37 GitHub followers; 28 repositories. No change.

**Standards and access controls were verified against the webinar table** — OMOP (demographics, medication administration, procedures, nursing flowsheets, diagnoses), OHNLP (clinical notes), DICOM (imaging from PACS), WFDB with PhysioNet schema extended (waveform telemetry), EDF+ and Persyst (waveform EEG) — together with the per-modality access control value of *Controlled* throughout and the metadata status values (*Yes* / *Planned*). All correctly transcribed. No change.

**Named people and affiliations** (Rosenthal/MGH, Bihorac/UF, Jiang/UTHealth Houston, Strekalova/UF, Rashidi/UF, Kwong/Tufts) are recorded as the bundle presents them, as the CHoRUS leadership team. NIH and AIM-AHEAD programme staff are not recorded as dataset creators, since the bundle does not describe them as such. No change.

**Header blocks, phase labels, and schema paths** were verified: the full record reads `phase 1` with `data_sheets_schema_all.yaml`; the core record reads `phase 2` with `data_sheets_schema_core_all.yaml`. All other header lines are byte-identical to the specified block in both files. No change.

---

## 5. Outcome

| | Before Phase 4 | After Phase 4 |
|---|---|---|
| Full record — populated slots | 63 | 61 |
| Core record — populated slots | 45 | 45 |

Full record: two slots removed (`publisher`, `language`); four slots edited in place with entries removed or rewritten (`machine_annotation_tools`, `collection_mechanisms`, `preprocessing_strategies`, `is_deidentified`); three slots reworded without membership change (`ethical_reviews`, `at_risk_populations`, `funders`); one entry relocated between two already-populated slots (`existing_uses` → `intended_uses`).

Core record: two slots removed (`publisher`, `language`); three slots added (`splits`, `direct_collection` — and `third_party_sharing` extended rather than added, as it was already present); the same in-place edits and relocation as the full record; URI disambiguation applied to `resources`.

**Validation**

- Full — `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml -C Dataset` → **PASS**
- Core — `linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml -C CoreDataset` → **PASS**

**Reconciliation outcome: RECONCILED.** No high-severity defects. All 4 medium findings resolved. Of the 20 low findings, 16 resolved and 4 accepted with reasons recorded above (`participant_privacy` core omission as redundant; `ethical_reviews` and `at_risk_populations` retained with qualifying language rather than deleted; `resources`/`subsets` typing retained as a schema artifact with the URI collision repaired). The two records are now consistent with each other and with the declared bundle on every retained claim.

**Provenance:** no previously generated D4D record was read or consulted at any phase. Sole factual inputs were `data/preprocessed/concatenated/CHORUS_preprocessed.txt` and the two schema files.