# Reconciliation Report — AI_READI

**Project:** AI_READI (the Bridge2AI Salutogenesis Grand Challenge)
**Label:** 2026-08-28d_claude-opus-5-api-generic-v7_rep1
**Records:** full (`Dataset`) and core (`CoreDataset`)
**Phase:** 4 — strict reconciliation against the Phase 3 source/provenance audit

---

## 1. Audit summary

The Phase 3 audit returned 23 findings: 6 high, 9 medium, 8 low. It found no fabricated dataset facts — figures, dates, DOIs, device names, standards and license terms all traced to the declared bundle, and the existing `source_caveats` block correctly documented the acronym, publisher, lead-organization, enrollment-target and de-identification conflicts with the source ranking applied.

The defects clustered in three areas:

1. **Structured fields left empty while their content sat in prose** — `creators` omitted entirely; `funders[].grants` unpopulated; `data_governance.committee_contact` and `license_and_use_terms.contact_person` omitted.
2. **One unsupported value and two shape problems** — an invented organization name in `ethical_reviews[1].reviewing_organization`; source attribution and a postal address embedded inside `human_subject_research.ethics_review_board`; a homepage URL in the `uriorcurie`-ranged `publisher` slot.
3. **Supported omissions of attested negatives** — `labeling_strategies`, `existing_uses`, `use_repository`, `errata`, `discouraged_uses`, `annotation_analyses`.

Plus minor issues: unreferenced minted split fragments, an unflagged contradiction between `sensitive_elements` siblings, an unrecorded license-name disagreement, and unpopulated numeric fields in `variables`.

---

## 2. Changes made — full record

### 2.1 High severity

**`conforms_to_standard` (finding 1) — left as-is.** The audit itself concluded that all seven values (`CDS`, `WFDB`, `OMOP_CDM`, `ESDS`, `DICOM`, `OPEN_MHEALTH`, `RO_CRATE`) are declared members of `DataStandardEnum` and that "no repair required". The list is unchanged in the reconciled record.

**`instances[0].data_topic` (finding 2) — caveat added; value retained.** `B2AI_TOPIC:43` remains. A new `source_caveats` was added to the instance object recording that the slot admits a single term, that Diabetes was chosen because the bundle names type 2 diabetes as the resource type and subject, that the collection equally supports Clinical Observations, Ophthalmic Imaging, mHealth, Waveform, Survey and Environment, and that `data_substrate` is omitted because the bundle states instances span tabular, imaging and physiological signal/waveform substrates with no single covering term.

**`publisher` (finding 3) — slot removed.** The value `https://fairhub.io/` — a homepage URL in a `uriorcurie` slot with no declared prefix covering FAIRhub — has been deleted from the full record. The existing `source_caveats` item (2) was rewritten to state that the two tier-1 sources disagree (FAIRhub vs AI-READI Consortium), that neither supplies an identifier for a publishing entity, and that the slot is therefore left unpopulated with both statements recorded.

**`creators` (finding 4) — slot added.** A `Creator` entry was added with `id: ROR:01yc7t268`, `name: AI-READI Consortium`, a `description` covering the organizational creator declaration and the constituent institutions, `principal_investigator: Aaron Lee`, `notes` carrying the ORCID CURIE `ORCID:0000-0002-7452-1648`, degree, role and contact email, and a `source_caveats` explaining that the ROR is the organization identifier the bundle supplies for the managing organization (not for the Consortium itself, for which no identifier is attested) and recording the equally-ranked disagreement about the PI's affiliation.

**`funders[].grants` (finding 5) — structured field populated.** Three of the five funder entries now carry `grants` lists:
- Entry 1: a `Grant` with `id: https://reporter.nih.gov/project-details/10471118`, `name: 'Bridge2AI: Salutogenesis Data Generation Project'`, and a `description` holding the award number, application ID, project number, PI, awardee organization, amount and dates. The `notes` field retains the ROR CURIE for NIH and the statement that the funder does not create or manage the dataset.
- Entries 2 and 3 (P30 DK035816, UL1TR003096): `Grant` objects with fragment identifiers minted on the attested RePORTER URL, plus `source_caveats` explaining why the fragment was minted.
- Entries 4 and 5 (Research to Prevent Blindness, Microsoft AI for Good Lab): no `grants` — no award number is attested for either.

**`ethical_reviews[1].reviewing_organization` (finding 6) — unsupported value removed.** The invented label "AI-READI ethics team" has been deleted. The entry now carries only `review_details` (rewritten to say the review is attributed to "four named individuals") and a new `source_caveats` recording that the RO-Crate gives four personal names with no organizational affiliation, so the field is left unpopulated rather than invented.

### 2.2 Medium severity

**`data_governance.committee_contact` (finding 7) — populated.** Set to `Aaron Lee`. Supporting detail (ORCID CURIE, role, email, README pointer) moved into `data_governance.notes`. Additionally `accountable_organization` was populated as an `Organization` with `id: ROR:01yc7t268`, and `stewardship_roles` was split from one long entry into four distinct entries.

**`license_and_use_terms.contact_person` (finding 8) — populated.** Set to `Aaron Lee`, with ORCID CURIE and contact routes in a new `notes` field on the object.

**`human_subject_research.ethics_review_board` (finding 9) — value narrowed.** Reduced from the prose paragraph (which opened "The RO-Crate metadata names the reviewing body…" and embedded a postal address) to the bare board name `Washington University IRB`. The reliance-agreement detail, contact point and postal address moved into `notes`; a new `source_caveats` records that the RO-Crate wording is used over the publication's "Institutional Review Board of the University of Washington" on tier grounds while noting the two denote the same board.

**`sensitive_elements` (finding 10) — cross-references added.** Entry [0] gained a `source_caveats` naming the conflicting RO-Crate statement, noting it is recorded as a separate entry, and stating that both sources are tier 1 so the ranking cannot settle it. Entry [2]'s existing caveat was rewritten to point back at entry [0] symmetrically. Boolean values unchanged.

**`external_resources` (finding 11) — declared fields populated.** All eight entries now carry `archival`; `future_guarantees` added to entries 1, 2, 3, 5 and 6; `restrictions` added to the BMJ Open entry (CC BY-NC 4.0). The `external_resources` inner field was also converted from a scalar string to a list on every entry, matching its multivalued declaration.

**`labeling_strategies` (finding 12) — slot added.** One entry recording that no labeling was performed, no gold-standard or proxy definition applied, no labellers engaged, no labeling software used, the RO-Crate `rai:dataAnnotationProtocol` value, and the absence of guidelines for future labellers.

**`existing_uses` (finding 13) — slot added.** One entry with `examples` recording the attested "No" plus the FAIRhub citation count of zero and view count of 24,636.

**`use_repository` (finding 14) — slot added.** One entry recording that no use-tracking repository exists and describing the FAIRhub "Dataset Uses" panel.

**`errata` (finding 15) — slot added.** One entry recording that the healthsheet posed the erratum question and the response field is blank, with a `source_caveats` stating the blank is reported as a blank rather than read as a denial.

**`discouraged_uses` (finding 16) — slot added.** One entry recording that the healthsheet answers both the discouraged-use and should-not-be-used questions by reference to the license, with a `source_caveats` noting that the hard restrictions are itemized under `prohibited_uses` and no separately-discouraged-but-permitted use is attested.

### 2.3 Low severity

**`created_on` (finding 17) — populated.** Set to `'2025-11-17T00:00:00Z'`, from the FAIRhub API `created_at: 1763366400`.

**`was_derived_from` (finding 18) — populated.** Set to `doi:10.60775/fairhub.2`.

**`is_tabular` (finding 19) — value retained, caveat added.** Still `false`. A new item (9) in the top-level `source_caveats` records that the collection is mixed — imaging, waveform and JSON dominant but `clinical_data` entirely CSV mapped to OMOP tables — and that a single boolean cannot represent the mixture.

**`license` (finding 20) — value retained, caveat added.** Still `AI-READI custom license v2.0`. A `source_caveats` on `license_and_use_terms` records the equally-ranked landing-page label "Health Data License", and item (8) was added to the top-level caveat block pointing at it.

**`subsets` (finding 21) — fragments now referenced.** Rather than removing the three minted fragments, `splits[0].split_details` was rewritten to name all three identifiers explicitly with their participant counts, so each fragment is now pointed at by another value in the record. Each subset `description` was also expanded with the per-split race/ethnicity, sex, diabetes-status and mean-age figures from the README table.

**`annotation_analyses` (finding 22) — slot added.** One entry recording the attested negative for every labeller-related question.

**`collection_timeframes[0].source_caveats` (finding 23) — rewritten.** Now names the tier of each source (structured metadata tier 1, BMJ Open tier 3) and states that the ranking settles the one-day discrepancy.

**`notes` (finding 24) — trimmed.** The biospecimen paragraph was removed and relocated to a new ninth `raw_data_sources` entry with `source_type: biorepository`, carrying the specimen types, blood volume, shipping arrangements and the finite-sample access limitation. `notes` now holds only the administrative-review banner and the device loan/discount acknowledgements.

**`variables` (finding 25) — expanded from 22 to 47 entries.** Twenty-five laboratory analytes were added from the tabulated reference ranges, each with `unit` and, where the range is a plain numeric interval, `minimum_value` and `maximum_value`. The existing HbA1c entry gained `unit: '%'`, bounds 4.0–6.0 and a corrected measurement technique. Where the source range is sex- or age-specific (Troponin-T, creatinine, NT-proBNP) or absent (urine creatinine, urine albumin), no numeric bounds were set and `quality_notes` explains why. Every bounded entry states in `quality_notes` that the bounds are the laboratory reference range, not the observed data range.

### 2.4 Incidental repair found during comparison

**`distribution_dates[0].release_dates`** was converted from a scalar string to a single-item list in both records, matching its multivalued declaration.

---

## 3. Changes made — core record

The core record was re-derived by projection from the reconciled full record. Changes mirror the full record wherever the core schema declares the slot:

- **Added:** `creators`, `labeling_strategies`, `annotation_analyses`, `existing_uses`, `use_repository`, `errata`, `discouraged_uses`, `created_on`, `was_derived_from`.
- **Removed:** `publisher`.
- **Populated/restructured:** `funders[].grants`; `data_governance.committee_contact`, `.accountable_organization`, `.notes`, and the four-way split of `.stewardship_roles`; `license_and_use_terms.contact_person` and `.notes`; `regulatory_restrictions.governance_committee_contact`; `human_subject_research.ethics_review_board` narrowed with detail moved to `notes`; `informed_consent[0].withdrawal_mechanism`; the ninth biorepository entry in `raw_data_sources`; `external_resources` archival/guarantee/restriction fields and list-valued inner field; `subpopulations[0].distribution` expanded with whole-cohort counts.
- **Caveats added or rewritten:** `instances[0]`, `sensitive_elements[0]` and `[2]`, `collection_timeframes[0]`, `ethical_reviews[1]`, `human_subject_research`, `data_governance`, `license_and_use_terms`, and the top-level `source_caveats` block.
- **Unsupported value removed:** `ethical_reviews[1].reviewing_organization`.
- **`notes` trimmed** identically to the full record.

`distributions` (the core counterpart of `file_collections`) is unchanged. The core schema does not carry `subsets`, `splits` or `variables`, so findings 21 and 25 have no core counterpart.

The header block gained `# Phase 4 reconciliation: completed`.

---

## 4. Findings left as-is

| Finding | Slot | Reason |
|---|---|---|
| 1 | `conforms_to_standard` | The audit verified enum conformance and stated no repair was required. The list is byte-identical between the original and reconciled records. |
| 2 (partial) | `instances[0].data_topic` | Value retained: `B2AI_TOPIC:43` is a valid term and the best single fit the bundle supports. Only a caveat was added. `data_substrate` remains omitted — the vocabulary offers no term covering a mixed tabular/imaging/waveform collection, and the rule directs omission over approximation. |
| 19 | `is_tabular` | Value retained as `false`. The slot is a boolean and cannot represent a mixed collection; the choice is now documented rather than changed. |
| 20 | `license` | Value retained. Both candidate names are tier 1, so the ranking cannot decide; the structured-metadata name is kept in the scalar slot and the landing-page label is recorded in a caveat. |
| 21 | `subsets` | Fragments retained rather than removed. The minting rule permits a fragment where another value points at it; the fix was to add the pointer in `splits[0]`, not to delete the labels. |

---

## 5. Verification

Both records validated after reconciliation:

- Full: `linkml-validate -s data_sheets_schema_all.yaml -C Dataset` — passed.
- Core: `linkml-validate -s data_sheets_schema_core_all.yaml -C CoreDataset` — passed.

No fabricated fact was introduced. Every value added in Phase 4 traces to a passage in the declared bundle: the creator declarations in the FAIRhub structured metadata and RO-Crate, the award record in NIH RePORTER and the FAIRhub funding reference, the healthsheet's attested negatives on labeling, existing uses and use repositories, the blank erratum response, the laboratory reference-range tables in the BMJ Open protocol, the split summary table in the FAIRhub README, and the biospecimen tables in the protocol publication.