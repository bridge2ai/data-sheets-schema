# Reconciliation Report — AI_READI

Version label: `2026-08-28d_claude-opus-5-api-generic-v7_rep1`
Records: full (`Dataset`) and core (`CoreDataset`), both validated after reconciliation.

## 1. Scope and referent

The referent is unchanged: **version 3.0.0 of the "Flagship Dataset of Type 2 Diabetes from the AI-READI Project"**, DOI `10.60775/fairhub.3`, released 2025-11-17, 2,280 participants, 356,343 files, 3,815,969,779,678 bytes. Both records name that single release throughout; the earlier versions (1.0.0, 2.0.0) appear only as `related_datasets` targets and inside `version_access`, and the biorepository appears only as a raw source that is explicitly not part of the release.

## 2. Audit summary

The audit returned 23 findings: 6 high, 9 medium, 8 low. It found no fabricated dataset facts — counts, sizes, dates, DOIs, device names, standards and license terms all traced to the declared bundle. The defects clustered in three groups: (a) declared structured fields left empty while their content sat in prose; (b) one unsupported value and two shape problems; (c) supported omissions of attested negatives.

## 3. Findings addressed, with the change made

### 3.1 High severity

**`conforms_to_standard` (enum conformance)** — The audit itself recorded this as verification, not a defect requiring repair: all seven values (`CDS`, `WFDB`, `OMOP_CDM`, `ESDS`, `DICOM`, `OPEN_MHEALTH`, `RO_CRATE`) are permitted members of `DataStandardEnum`. **Left as-is** in both records; the lists are identical before and after.

**`instances[0]` — undocumented single-topic selection and omitted substrate.** Added `source_caveats` to the instance object recording that `data_topic` admits one term, that `B2AI_TOPIC:43` (Diabetes) was chosen because the bundle names type 2 diabetes as the resource type, that the collection equally supports Clinical Observations, Ophthalmic Imaging, mHealth, Waveform, Survey and Environment, and that `data_substrate` is omitted because no single term covers tabular + imaging + waveform. `data_topic` itself is unchanged. Mirrored in core.

**`publisher` — homepage URL in a `uriorcurie` slot.** The slot held `https://fairhub.io/`, a web page rather than an entity identifier, and no declared prefix covers FAIRhub. **The slot was removed from both records.** The two conflicting publisher claims (FAIRhub per structured metadata; AI-READI Consortium per RO-Crate, both tier 1) are now recorded in top-level `source_caveats` item (2), which was rewritten to say the slot is left unpopulated for want of an identifier.

**`creators` — omitted entirely.** Added to both records: one `Creator` object for the AI-READI Consortium with `id: ROR:01yc7t268`, `name`, a `description` naming the participating institutions, and a nested `principal_investigator` Person (`id: ORCID:0000-0002-7452-1648`, Aaron Lee). A `source_caveats` on the Creator records that the ROR identifier is the one the bundle supplies for the managing organization (Washington University in St. Louis) rather than a separate identifier for the Consortium, and that the tier-1 sources disagree on the PI's affiliation (University of Washington vs. Washington University in St. Louis), so both are recorded. `created_by` was retained unchanged.

**`funders[].grants` — unpopulated while award data sat in `notes`.** Restructured all three NIH entries. `funders[0]` now carries a `Grant` with `id: https://reporter.nih.gov/project-details/10471118`, `name: 'Bridge2AI: Salutogenesis Data Generation Project'`, and a `description` holding the award number, application ID, project number, PI, awardee organization, amount and dates; its `notes` now carries only the NIH ROR identifier and the funder/creator distinction. `funders[1]` (P30 DK035816) and `funders[2]` (UL1TR003096) each gained a `Grant` whose `id` is a fragment minted on the attested RePORTER URL, with a `source_caveats` explaining that minting. `funders[3]` (Research to Prevent Blindness) and `funders[4]` (Microsoft AI for Good Lab) keep prose `notes` — no award number is attested for either — but their notes were expanded to name the source. Mirrored in core.

**`ethical_reviews[1].reviewing_organization` — unsupported value.** "AI-READI ethics team" was not attested anywhere. **The `reviewing_organization` key was removed from that entry**; `review_details` now opens "attributed in the RO-Crate metadata to four named individuals" and a new `source_caveats` explains that the RO-Crate records four personal names with no organizational affiliation, so the field is left unpopulated rather than invented. Mirrored in core.

### 3.2 Medium severity

**`data_governance.committee_contact` — omitted.** Added a Person (`ORCID:0000-0002-7452-1648`, Aaron Lee) with contact email and pointers. Also added `accountable_organization` (`ROR:01yc7t268`, Washington University in St. Louis), which the audit did not flag but which the same evidence supports. `stewardship_roles` was additionally split from one long string into four entries, one per distinct role. Mirrored in core.

**`license_and_use_terms.contact_person` — omitted.** Added the same Person object. Mirrored in core.

**`human_subject_research.ethics_review_board` — source commentary and address inside an identifying value.** The field now holds just `Washington University IRB`. The reliance agreements, the IRB Reliance Team contact point and the postal address moved into the object's `notes` (joined to the existing return-of-results content); a new `source_caveats` records that the RO-Crate wording is used over the tier-3 publication's "Institutional Review Board of the University of Washington" and that the two denote the same board. Mirrored in core.

**`sensitive_elements` — unflagged contradiction between siblings.** Entry [0] (`false`) gained a `source_caveats` naming the conflict with entry [2], stating both are tier 1 and equally ranked so the ranking cannot settle it. Entry [2]'s existing caveat was rewritten to point back at entry [0] symmetrically. Entry [1] (controlled-access set) is unchanged — it describes a different artifact and is not in conflict. Mirrored in core.

**`external_resources` — `archival` and related fields populated on only the first entry.** All eight entries now carry `archival`. The Zenodo community and the two publications are `true`; documentation, project website, GitHub, RePORTER and ClinicalTrials.gov are `false`. `future_guarantees` was added to the project website and both publications and expanded on the documentation entry; `restrictions` was added to the BMJ Open entry (CC BY-NC 4.0). Mirrored in core.

**`labeling_strategies` — omitted attested negative.** Added one entry recording that no labeling was performed, that no gold-standard or proxy definition, labellers or labeling software were involved, quoting the RO-Crate `rai:dataAnnotationProtocol` value, and noting the absence of guidelines for future label creation. Mirrored in core.

**`existing_uses` — omitted attested negative.** Added one entry recording the healthsheet "No" answer plus the FAIRhub API citation count of zero and view count of 24,636. Mirrored in core.

**`use_repository` — omitted attested negative.** Added one entry recording that no use-tracking repository exists beyond Google Scholar, while noting the FAIRhub "Dataset Uses" panel. Mirrored in core.

**`errata` — question asked, source response blank.** Added one entry stating that the healthsheet poses the erratum question and the response field is blank, with a `source_caveats` making clear the blank is reported as a blank rather than read as a denial. Mirrored in core.

**`discouraged_uses` — collapsed into `prohibited_uses` without comment.** Added one `DiscouragedUse` entry recording that the healthsheet answers both the discouraged-use and should-not-be-used questions solely by reference to the license, with a `source_caveats` noting that the individual hard restrictions are recorded under `prohibited_uses` and that no separately discouraged-but-permitted use is attested. `prohibited_uses` is unchanged. Mirrored in core.

### 3.3 Low severity

**`created_on` — supported omission.** Added `'2025-11-17T00:00:00Z'` to both records, matching the FAIRhub API `created_at` timestamp.

**`was_derived_from` — supported omission.** Added `doi:10.60775/fairhub.2` to both records. `related_datasets` retains both version relationships unchanged.

**`is_tabular` — unrecorded choice.** The value remains `false`. Top-level `source_caveats` gained item (9) explaining that the release is dominated by DICOM/waveform/JSON but that the collection is mixed and `clinical_data` is entirely CSV mapped to OMOP tables, and that a single boolean cannot represent that.

**`license` — unrecorded tier-1 disagreement.** The value remains `AI-READI custom license v2.0`. A `source_caveats` was added to `license_and_use_terms` recording the FAIRhub landing pages' "Health Data License" label, that both sources are tier 1 and equally ranked, and where each is recorded. Top-level `source_caveats` gained item (8) cross-referencing it.

**`subsets` — three fragments nothing pointed at.** Rather than delete them, `splits[0].split_details` was rewritten to name all three fragment identifiers explicitly with their participant counts, so the labels are now used by another value in the record. The three subset `description` fields were also expanded with the per-split race/ethnicity, sex, diabetes-status and mean-age figures from the bundle's split table. **Note:** the core schema's `distributions` projection does not carry `subsets`, so this change appears in the full record only.

**`annotation_analyses` — attested negative omitted.** Added one entry recording that no inter-annotator analysis exists because no labeling was performed, listing the sub-questions the healthsheet answers "N/A". Mirrored in core.

**`collection_timeframes[0].source_caveats` — ranking not named.** Rewritten to state that the structured metadata is tier 1 and the BMJ Open protocol tier 3, so the ranking settles the one-day discrepancy. The dates are unchanged.

**`notes` — content with structured homes.** The biospecimen paragraph was removed from `notes` and reworked into a ninth `raw_data_sources` entry (`source_type: biorepository`) carrying the specimen types, blood volume, shipping arrangements and the access statement that the samples are not part of this release. `notes` now retains only the "under review for potential modification" banner and the device loan/discount acknowledgements. Mirrored in core.

**`variables` — laboratory reference ranges omitted.** Expanded from 22 to 47 entries. New entries cover the tabulated clinical laboratory panel with `unit`, `minimum_value` and `maximum_value` taken from the reference ranges the bundle supplies (C-peptide, insulin, hs-CRP, lipids, glucose, BUN, electrolytes, protein, albumin, bilirubin, AST, CBC indices, urine creatinine and albumin, and others). Where the bundle's reference range is sex- or age-specific (Troponin-T, creatinine, NT-proBNP, alkaline phosphatase, ALT) no numeric bound was recorded and the `quality_notes` says why. `HbA1c` gained `unit`, bounds and a corrected measurement technique. Every `quality_notes` on these entries states that the bounds are the laboratory reference range, not the observed data range. **Note:** the core schema's projection does not carry `variables`, so this change appears in the full record only.

## 4. Findings left as-is

- **`conforms_to_standard` enum check** — the audit explicitly recorded no repair required; both records are byte-identical here.
- **`prohibited_uses`** — all seven entries unchanged; the audit's concern was the missing `discouraged_uses` counterpart, now added.
- **`data_topic` value** — retained as `B2AI_TOPIC:43`; only the caveat was added. No alternative term better fits a single-valued slot for this collection.
- **`is_tabular` value** — retained as `false`; only the caveat was added.
- **`license` value** — retained; only the caveat was added.

## 5. Core record

The core record was reprojected from the reconciled full record, not patched independently. Every change above that touches a slot the `CoreDataset` projection carries is present in both files with identical content. Three changes are full-record-only because the core projection does not carry those slots: the `subsets`/`splits` cross-referencing, the `variables` expansion, and the `total_file_count`/`total_size_bytes` scalars (the per-collection `bytes` values survive in `distributions`). The core header block carries `# Sources:` pointing at the full record and `# Phase 4 reconciliation: completed`.

## 6. Validation

Both files were re-validated after reconciliation:

- Full record against `data_sheets_schema_all.yaml`, class `Dataset` — passed.
- Core record against `data_sheets_schema_core_all.yaml`, class `CoreDataset` — passed.

## 7. Outcome

All 23 findings were dispositioned: 18 produced a change to one or both records, 5 were left as-is with the reasoning recorded above (and, where the audit's point was that a choice went undocumented, with a caveat added rather than the value altered). One unsupported value was removed (`ethical_reviews[1].reviewing_organization`), one ill-shaped identifier slot was removed rather than guessed at (`publisher`), and no new dataset fact was introduced that the declared bundle does not attest.