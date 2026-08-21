# CHORUS D4D — Phase 4 Reconciliation Report

Version label: `2026-08-20b_claude-opus-5-api-generic-v5_rep1`
Records reconciled: full (`CHORUS_d4d.yaml`, class `Dataset`) and core (`CHORUS_d4d_core.yaml`, class `CoreDataset`).
Referent held across both records: the CHoRUS for Equitable AI multicenter acute/critical-care dataset — not the CHoRUS project, not the AIM-AHEAD training program, not the chorus-ai software organization.

---

## 1. Audit summary

The Phase 3 audit returned 39 findings: 4 high, 10 medium, 15 low, 10 informational. No finding alleged a value contradicted by the declared bundle; no finding alleged an enum value outside a declared vocabulary. The dominant class of defect was structural — evidence the bundle supports being carried in free-text fields (`notes`, `description`) while the declared fields of the same object stayed empty — followed by two identifier problems and one full/core structural divergence.

---

## 2. Changes made

### 2.1 Creators — names moved out of commentary (high, both records)

**Original (both records):** five of six `Creator` objects carried only `affiliations`, with the personal name buried inside a `notes` value that also editorialized about the schema: *"Azra Bihorac, listed on the Bridge2AI CHoRUS leadership team slide … The Creator class provides no personal-name slot for a contributor who is not recorded as principal investigator."*

**Reconciled (both records):** each `notes` value now carries only the name and affiliation as content — `Azra Bihorac, University of Florida.` — and the evidential material (which slide, which source, why no PI claim is made) moved to `source_caveats` on the same object. Five objects changed identically in both records: Bihorac, Jiang, Strekalova, Rashidi, Kwong. The Rosenthal object is unchanged.

**What was *not* done, and why.** The audit's preferred remedy was to place each name in a declared Person-valued field. The only Person-ranged field `Creator` declares is `principal_investigator`. NIH RePORTER names exactly one PI for OT2OD032701 — Rosenthal — and the cohort 2 webinar slide gives the other five a leadership affiliation and nothing more. Promoting five people to `principal_investigator` would manufacture a role the bundle contradicts. The remaining defect is therefore a schema/evidence mismatch rather than a generation error, and it is now recorded as such in each object's `source_caveats` instead of as commentary in `notes`.

### 2.2 Grant identifier (high, both records) — **not changed**, caveat added

The audit objected to `funders[0].grants[0].id` holding `https://reporter.nih.gov/project-details/10472824`, a page URL, where the attested award identifier is OT2OD032701.

Both records still carry that URL. The v5 identifier rule directs a `uriorcurie` slot to a CURIE **where the schema declares a prefix**; the schema digest declares no prefix for NIH awards, and the "uri" half of `uriorcurie` is the fallback for exactly that case. A bare `OT2OD032701` is not a URI or a CURIE. The award number remains in `name`, and a new `source_caveats` on the funder object now states that the award is identified in the sources by core project number OT2OD032701, that the number is carried in `name`, and that the RePORTER URL is used because no registry prefix is available. The finding is answered by disclosure rather than by a value change.

### 2.3 Dataset identity separated from landing page (medium, both records)

**Original:** `id: https://chorus4ai.org/` and `page: https://chorus4ai.org/` — identical, conflating the dataset with its web page.

**Reconciled:** `id: https://chorus4ai.org/#dataset` in both records; `page` unchanged. The fragment is minted on the one persistent identifier the bundle supplies, consistent with the minting rule, and the top-level `source_caveats` in both records now states that no DOI or repository accession is attested. The nine per-modality fragments are unchanged and remain siblings of `#dataset` on the same base.

### 2.4 Full/core divergence on the nine modalities (medium, core) — **structure unchanged**, divergence disclosed

The audit flagged that the nine modalities are `subsets` (DataSubset, with `is_data_split`/`is_subpopulation`) in the full record and `resources` (Dataset) in the core record, asserting different relationships.

Both records retain their original slot. The core record's `resources` entries still omit `is_data_split`/`is_subpopulation`; those two keys are listed in the digest as additions available on `DataSubset`, not on `Dataset`, so they cannot be carried in a `resources` entry. The core `source_caveats` now states explicitly that the nine entries are logical modality subsets of a single dataset rather than independently distributed component datasets, and that CoreDataset provides no subset slot, so they are carried under `resources`. Reader-visible divergence replaced by disclosed divergence; the intended reading is now identical across records.

### 2.5 Empty `relationships` list removed (medium, full)

The full record's `relationships: []` is gone. An empty list populates a slot without asserting anything; the bundle says nothing about inter-instance relationships. The core record never carried the slot and is unchanged in this respect.

### 2.6 Committee contact withdrawn (medium, both records)

**Original (both):** `data_governance.committee_contact: {name: Jared Houghtaling}`.

**Reconciled (both):** the `committee_contact` key is removed. Houghtaling appears in the bundle only as one of two equally-attested "Request access" addresses (the other being dbold@emory.edu); no committee is named anywhere. Both addresses remain where the evidence puts them, in `access_review_process`, and the `source_caveats` now states that the documents name no data access committee and no committee contact, and that the two access-request addresses were recorded in the access review process rather than promoted to a committee role.

### 2.7 Imaging counts decomposed (medium, both records)

**Original (both):** a single Instance in the Imaging subset with `counts: 7642` and `instance_type: Hospital admission with associated radiology imaging data`; the 1,000-image figure appeared only in the subset `description` and `source_caveats`.

**Reconciled (both):** two Instance objects. The first keeps `counts: 7642` at admission level with a caveat naming the tier-2 project website. The second is new — `instance_type: De-identified radiology image available in the enclave`, `counts: 1000`, `data_substrate: B2AI_SUBSTRATE:11` — with a caveat naming the tier-4 webinar, the August 2025 date, and the fact that the two figures count different units and are therefore not in conflict. `B2AI_SUBSTRATE:11` (DICOM) moved from the admission instance, where it did not belong, to the image instance. The subset `description` no longer restates either count.

### 2.8 Distribution formats reduced to formats (medium, both records)

**Original (both):** five entries mixing standard and coverage, e.g. `OMOP Common Data Model tables for demographics, medication administration, procedures, nursing flowsheets and diagnoses`.

**Reconciled (both):** six entries naming formats only — `OMOP Common Data Model tables`, `OHNLP tokenized clinical text`, `DICOM`, `WFDB`, `EDF+`, `Persyst`. EDF+ and Persyst are now separate entries rather than one compound value. Modality coverage remains where it belongs, in the subsets/resources.

### 2.9 `status` shortened, duplication removed (low, both records)

**Original (both):** two clauses, the second of which restated the Administration-directives notice verbatim from `regulatory_restrictions`.

**Reconciled (both):** `Partially released under controlled access and actively growing`. The directives notice survives only in `regulatory_restrictions`, which was itself split from one long entry into two — the legal-framework statement and the November 2025 review notice as separate list items.

### 2.10 Unsupported acquisition booleans dropped (low, both records)

`was_directly_observed: false` and `was_inferred_derived: false` are removed from `acquisition_methods[0]` in both records. The bundle describes retrospective extraction of clinical records but does not characterize the data against either axis; the second acquisition object never set them, so the record was also internally inconsistent about whether the axes were answerable. Both objects now carry `acquisition_details` alone.

### 2.11 Collector roles aligned to source wording (low, full; propagated to core)

`Data contributing site` → `Data Acquisition center` (the bundle's own term: "14 will contribute as Data Acquisition centers"), and the `collector_details` prose was rewritten to use the same term. `Consortium sub-team` is retained as a label but its details now name the Standards, Data Acquisition and Tooling sub-teams as the bundle does. Applied identically in both records.

### 2.12 Maintainer transcription note relocated (low, both records)

The parenthetical `(cmccrary@mgh.havard.edu, as printed on the site)` is gone from `maintainer_details`. The address now appears as content — `with contact address cmccrary@mgh.havard.edu` — and the observation that the site spells the domain "mgh.havard.edu" moved to a new `source_caveats` on that Maintainer object. The typo is preserved exactly as the source printed it.

### 2.13 `identifiable_elements_present` populated (low, both records)

`is_deidentified.identifiable_elements_present: true` added in both records, with a `source_caveats` explaining the basis — full-text notes retained at sites, imaging de-identification in process as of August 2025 — and noting that the sources do not say whether any released modality retains direct identifiers.

### 2.14 Human-subject and at-risk fields populated from their own evidence (low, both records)

`human_subject_research.special_populations` added in both records, stating that PICU and NICU admissions mean records of minors are present. The observation that the documents report no IRB approval moved from `notes` to `source_caveats`; `notes` now holds only the substantive statement about retrospective records from 14 hospitals.

In `at_risk_populations`, the PICU/NICU fact moved out of `notes` and into the object's `source_caveats` alongside the existing statement about absent assent and guardian-consent information; `at_risk_groups_included: true` is unchanged. `special_protections`, `assent_procedures` and `guardian_consent` remain unpopulated — the bundle supports none of them.

### 2.15 Other caveat relocations (low/info, both records)

- `subpopulations[0]`: the sentence about undisclosed ICU/PICU/NICU distribution moved from `notes` to `source_caveats`.
- `collection_timeframes[0]`: the sentence about the unstated encounter date range moved from `timeframe_details` to `source_caveats`.
- `machine_annotation_tools[0]`: the sentence about absent accuracy figures moved from `tool_descriptions` to `source_caveats`.
- `participant_privacy[0]` (full only): the re-identification-risk sentence moved from `reidentification_risk` to `source_caveats`, since it reports what the documents omit rather than a risk assessment.
- `known_biases[0]`: `bias_description` rewritten to describe the composition constraint the bundle actually states rather than asserting an observed bias; the caveat now says explicitly that the recorded `bias_type` categorizes the described constraint rather than a measurement.
- `splits[0]` (full only): rephrased from "The project will sequester…" to a passive statement of the plan, with a new caveat recording that size, composition and availability date are unstated.
- `external_resources`: all four entries rewritten in both records to lead with the resource and its URL rather than a prose paragraph; the GitHub entry no longer enumerates repository descriptions.

### 2.16 Holdout task removed from `tasks` (low, both records)

`tasks` dropped from four entries to three in both records; the "External validation of AI/ML models against a sequestered holdout test set" entry is gone. External validation is a use of the dataset, not an analytical task the data supports, and it remains stated in `purposes`, `intended_uses` and `future_use_impacts` — and, in the full record, in `splits`. Repetition reduced from four slots to three (full) and three (core).

---

## 3. Findings left as-is

| Finding | Disposition |
|---|---|
| Creator names not in a declared Person field (high, both) | Partially addressed only. Names moved from commentary into clean `notes` content and evidence into `source_caveats`; no name promoted to `principal_investigator`, because the bundle names one PI and asserting five more would be a false claim. |
| Grant `id` is a RePORTER page URL (high, both) | Value unchanged; caveat added. No NIH-award prefix is declared in the schema digest, and `uriorcurie` permits a URI where no prefix applies. |
| Nine modalities as `subsets` (full) vs `resources` (core) (medium, core) | Structure unchanged in both records; divergence now explained in the core `source_caveats`. The core schema class is CoreDataset and the two subset-specific keys are DataSubset additions, so the full record's structure cannot be reproduced exactly in core. |
| `data_collectors[].role` uses free strings (low, full) | Values revised to the bundle's wording but the slot still holds free text. The digest declares an enum for `Maintainer.role` and none for `DataCollector.role`, so free text is schema-conformant here. |
| `external_resources` nested inside `external_resources` (low, both) | Structure unchanged. This is the shape the schema declares for the ExternalResource class; only the prose was tightened. |
| `conforms_to_standard: OTHER` covering two standards (info, both) | Unchanged. The enum offers no finer term for the OHNLP schema or EDF+/Persyst, and both are named in `conforms_to`. |
| Top-level 50,000-vs-45,000 caveat handling (info, both) | Unchanged in substance — the audit judged it correct. Two sentences were appended covering the new `#dataset` identifier and (core only) the subsets/resources choice. |
| Consent, notification, revocation, DPIA, compensation slots absent (info, both) | Still absent in both records. The bundle describes community ethics focus groups and a legal framework but states nothing about individual patient consent, notification, revocation, DPIAs or compensation. |
| `participant_privacy` in full and not core; `splits`, `relationships`, `direct_collection`, `third_party_sharing` likewise | Unchanged, except that `relationships` was removed from the full record (§2.5), which narrows the gap by one slot. The remaining asymmetries reflect the core record's narrower projection; no core content lacks a full-record counterpart. |
| No unsupported value found | Confirmed. Nothing was removed on grounds of contradicting the bundle, because nothing did. |

---

## 4. Outcome

Both records were revised. Changes are structural and evidential — content relocated into the fields that declare it, evidence commentary moved into `source_caveats`, two counts separated into the two instances they measure, one unsupported governance role withdrawn, two unsupported booleans dropped, one empty list removed, one identifier disambiguated from the landing page. No factual claim was added that the declared bundle does not state, and no claim present in the originals was found to be contradicted by it. Two high-severity findings — Creator naming and the grant identifier — are answered by disclosure rather than by a value change, for the reasons recorded in §3; both are now visible to a reader of the record rather than only to a reader of this report.