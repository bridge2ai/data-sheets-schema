# Reconciliation Report — AI_READI D4D Records

**Version label:** `2026-08-22c_claude-opus-5-api-generic-v5_rep3`
**Arm:** BASELINE (input documents only)
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Phase:** 4 (strict reconciliation following Phase 3 source/provenance audit)

---

## 1. Audit summary

The Phase 3 audit returned 23 findings: 4 medium, 15 low, 4 informational. No fabricated dataset facts were identified. Participant counts, file counts, byte totals, split tables, laboratory reference ranges, device inventories, dates and DOIs were all found traceable to the declared bundle and internally consistent. The medium findings concerned application of the declared decision rules (source ranking, multivalued-slot expansion, core-projection fidelity) rather than invention. The low findings concerned slot shape, value placement, supported omissions, and identifier hygiene.

---

## 2. Changes made

### 2.1 Medium findings

**F1 — `sampling_strategies[0].is_sample` in core (content added in projection).**
Changed. The core record originally carried `is_sample: true`, a value the full record did not assert and which contradicted the tier-1 healthsheet ("The dataset contains all possible instances") and both records' own prose. The key was removed from the reconciled core record; the reconciled core `sampling_strategies` object now carries only `is_random`, `is_representative`, `strategies`, `why_not_representative`, `source_data` and `source_caveats`, matching the full record exactly.

**F2 — acronym expansion in `description` (source-ranking rule).**
Changed in both records. "Artificial Intelligence Ready and Equitable Atlas for Diabetes Insights" was replaced with "Artificial Intelligence Ready and Exploratory Atlas for Diabetes Insights", the form given by the tier-1 FAIRhub study description and README and the tier-2 healthsheet. The BMJ Open article title in `external_resources` retains "Equitable" because it is quoted source text. `source_caveats` item (8) was rewritten in both records to state which sources give which form, that "Exploratory" is the higher-ranked value, and that it is the form used.

**F3 — IRB naming caveat misstated the ranking.**
Changed in both records. The original preferred the tier-2/tier-3 value (University of Washington) while claiming the ranking did not settle the discrepancy. The reconciled records apply the rule as declared: `ethical_reviews[0].reviewing_organization` and `human_subject_research.ethics_review_board` now name the tier-1 RO-Crate value, "Washington University IRB", with the University of Washington reading recorded in the caveat and in the `ethics_review_board` prose. The `source_caveats` text was rewritten to state the tiers correctly and to note that the RO-Crate's own address, contact and protocol number support the lower-ranked reading. Full-record `source_caveats` item (4) was updated to match.

**F4 — `funders` collapsed a multivalued slot.**
Changed in both records. The single FundingMechanism object was expanded into six: NIH/OT2OD032644, NIH/P30DK035816, NIH/UL1TR003096, Research to Prevent Blindness, Microsoft AI for Good Lab, and device manufacturers (in-kind). The award number was moved out of the `Grant.name` field (see F19).

### 2.2 Low findings

**F5 — `distribution_formats[4].format` held an access route.**
Changed in both records. The object with `format: "FAIRhub portal with Azure Storage access"` was replaced by an object with no `format` key, carrying only `access_urls` and `notes`. Two additional format objects (TSV, WFDB) were added, since the bundle names both and neither was previously represented.

**F6 — `variables[monofilament_test_response].categories` collapsed two values.**
Changed in the full record. `["yes; no"]` became `["yes", "no"]`.

**F7 — `conforms_to_standard: RO_CRATE`.**
Changed in both records. `RO_CRATE` was removed from `conforms_to_standard`, and the RO-Crate sentence was removed from `conforms_to`. The RO-Crate is now represented as an `external_resources` entry describing the release, with a note stating that it is a separate description rather than a file within the distributed dataset.

**F8 — `regulatory_restrictions.confidentiality_level`.**
Value left as `restricted` (no enum term matches "HL7:2N (normal)"), but the `notes` were rewritten in both records to open with "No source states a value from this slot's enumeration" and to identify the value explicitly as this record's mapping. Also flagged in full-record `source_caveats` item (12).

**F9 — `data_governance.committee_name` was a coinage.**
Changed in both records. "AI-READI Data Access Committee" became "AI-READI Consortium", the tier-1 RO-Crate value. The Data Access Committee is retained where the BMJ Open protocol places it — in `access_review_process`, in a `stewardship_roles` entry, and in `notes`, which now states that the two names come from different sources.

**F10 — "six devices" vs. seven in `acquisition_methods[0]`.**
Changed in both records. "retinal imaging on six devices" became "retinal imaging on seven devices", and the corresponding `collection_mechanisms` entry now opens "Retinal imaging devices, seven in total".

**F11 — `raw_sources[0].access_url` pointed at documentation.**
Changed in the full record. The `access_url` key was removed; the `raw_data_details` text now states that no access point is offered and that the documentation describes the processing.

**F12 — mini-subset relationship only in `notes`.**
Changed in both records. A third `related_datasets` entry was added with `relationship_type: is_source_of` and `target_dataset: https://fairhub.io/datasets/4`, with the child-record provenance in its `notes`. The corresponding sentence was removed from the top-level `notes` of both records.

**F13 — `extension_mechanism` omitted though answered.**
Changed in both records. `extension_mechanism.extension_details` was added, recording that no mechanism exists outside the project team.

**F14 — `data_protection_impacts` omitted though answered.**
Changed in both records. A `data_protection_impacts` entry was added recording that no DPIA has been conducted.

**F15 — "Salutogenesis" keyword not in any source list.**
Changed in both records. Replaced with "Exploratory Data Collection", which appears in the FAIRhub study keyword list.

**F16 — duplicated identifier across Creator and its own affiliation.**
Changed in both records. The `https://aireadi.org` entry was removed from `creators[0].affiliations`, leaving eight institutional affiliations. The Creator node retains `id: https://aireadi.org`; the consortium name and the project-website provenance were moved into `notes`.

**F17 — `known_biases[2].affected_subsets` held prose.**
Changed in both records. The prose string was replaced by the three minted split-subset identifiers, with the cohort-wide scope stated in a new `notes` field on that object.

**F18 — citation folded into core `notes`.**
Changed in the core record. The citation is still in `notes` but now opens the field as "Recommended citation for this release: …" rather than trailing the banner sentence. `citation` was not added as a top-level core slot: the CoreDataset schema was not supplied and the audit flagged this as unverifiable, so the safer placement was retained.

**F19 — award number merged into `Grant.name`.**
Changed in both records. `"OT2OD032644: Bridge2AI: Salutogenesis Data Generation Project"` became `name: "Bridge2AI: Salutogenesis Data Generation Project"`, with the award number stated in the FundingMechanism `notes`.

**F20 — unrecorded conflict on the study-base encounter window.**
Changed in both records. The BMJ Open phrase "between 2020 and 2025" was removed from `sampling_strategies[0].strategies`; the sentence now reads "who had a medical encounter within each health system site." The `source_caveats` on that object was rewritten to record both readings and the ranking, and full-record `source_caveats` gained item (6) covering it.

### 2.3 Core-record internal consistency (F21)

Changed. The `distributions` entries for the DICOM directories and `cardiac_ecg` still carry no `format`/`media_type` keys, but each DICOM entry's `notes` now ends "Media type application/dicom", and the `environment` entry gained `format: CSV` / `media_type: text/csv` to match the record's own `distribution_formats` statement. The split composition, previously carried only by the three full-record subsets, was written into the root-metadata entry's `notes` so no split figures were lost in projection.

---

## 3. Left as-is

**F8 (enum value).** `confidentiality_level: restricted` retained — the finding was about disclosure, not the value, and no enum term matches the source string. Disclosure was strengthened instead.

**F18 (core `citation` slot).** Retained in `notes`. Adding a top-level `citation` to the core record would depend on the CoreDataset schema declaring it, which the supplied digest does not cover.

**F22 (`distributions` slot and its keys).** No change. The audit noted these do not appear in the supplied Dataset digest and can only be checked against the CoreDataset schema, which was not supplied. The slot and its `path`/`bytes`/`format`/`media_type` keys were retained as written; both records validated.

**F23 (single-item lists).** No change. `at_risk_populations.special_protections`, `human_subject_research.irb_approval`/`regulatory_compliance`/`special_populations`, `ip_restrictions.restrictions`, `data_governance.stewardship_roles`, `version_access.versions_available` and `external_resources[*].restrictions` remain lists. Several were in fact expanded from one item to several during reconciliation (`special_protections` 1→3, `regulatory_compliance` 1→5, `stewardship_roles` 1→3, `ip_restrictions.restrictions` 1→2, `versions_available` 1→3), which is consistent either way. Both records validated.

**Informational item on ROR/ORCID CURIEs.** No change to the CURIE form; all local parts are evidence-backed and both records validated.

**All arithmetic, counts, dates, reference ranges and device inventories.** No change — the audit found these sound.

---

## 4. Referent

Both records describe a single referent: version 3.0.0 of the *Flagship Dataset of Type 2 Diabetes from the AI-READI Project*, DOI `10.60775/fairhub.3`, the release distributed on FAIRhub on 2025-11-17. The AI-READI study, the biorepository, the earlier releases and the mini-subset are recorded as related entities rather than as the record's subject. This choice is unchanged from the original records and is held consistently across both.

---

## 5. One incidental correction

`creators[0].principal_investigator` was declared `Person` in the full record but is a scalar in the core record. In reconciliation the full record was set to the string `"Aaron Lee (ORCID:0000-0002-7452-1648)"` and the core record to `"Aaron Lee"`, with the ORCID stated in the core `notes`. This was not an audit finding; it emerged during validation.