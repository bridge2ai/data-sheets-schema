# Reconciliation Report — AI_READI

**Version label:** 2026-09-01_claude-opus-5-api-generic-v7_rep1
**Records reconciled:** full (`AI_READI_d4d.yaml`, class `Dataset`) and core (`AI_READI_d4d_core.yaml`, class `CoreDataset`)
**Declared referent:** the public FAIRhub v3.0.0 release, `doi:10.60775/fairhub.3` — unchanged through reconciliation.

---

## 1. Audit summary

The Phase 3 audit returned sixteen findings against the full record: one major, eleven minor, four informational. The core record was audited as a projection of the full record and produced no independent findings; every core change below is the downstream consequence of a full-record change.

---

## 2. Findings repaired

### 2.1 (major) Synthesized "four to ten percent" follow-up figure

**Where:** `collection_timeframes[1].timeframe_details` and `relationships[0].relationship_details`.

**Before (both slots):** "Approximately four to ten percent of participants are expected to return for a follow-up examination in year four."

**After — `collection_timeframes[1]`:** the sentence now reads "The healthsheet states that approximately 4% of participants are expected to undergo a follow-up examination in year four," and a new `source_caveats` key was added to that object recording that the FAIRhub healthsheet gives 4% while the FAIRhub README, the RO-Crate description and NIH RePORTER give 10% of the study cohort, and that healthsheet and README share tier 1 so the ranking does not settle it.

**After — `relationships[0]`:** now states "the healthsheet states that approximately 4% of participants are expected to undergo a follow-up examination in year four of the project, while the FAIRhub README, the RO-Crate and NIH RePORTER describe longitudinal data being collected from 10% of the study cohort."

A sixth numbered item was added to the top-level `source_caveats` recording this conflict. The core record inherits the repaired `collection_timeframes[1]` including its new `source_caveats`, and the repaired top-level `source_caveats`. (`relationships` is not present in the core record.)

### 2.2 (minor) `download_url` pointing at the access-request page

`download_url: https://fairhub.io/datasets/3/access` was removed from the full record and from the core record. The access route it carried was not discarded: `data_governance.access_review_process` now includes "The access route for version 3.0.0 is the FAIRhub access page at https://fairhub.io/datasets/3/access." in both records.

### 2.3 (minor) Coined committee name

`data_governance.committee_name` changed from `AI-READI Data Access Committee` to `AI-READI Consortium`, the attested RO-Crate `dataGovernanceCommittee` value. The object's `source_caveats` was extended with a first sentence recording that the tier 1 RO-Crate gives "AI-READI Consortium" while the tier 3 BMJ Open protocol refers to an unnamed "Data Access Committee". Both records.

### 2.4 (minor) Unsupported role attribution on the access committee

`data_governance.committee_contact` (Aaron Lee, ORCID:0000-0002-7452-1648) was removed from both records. The same object under `license_and_use_terms.contact_person` was also removed, for the same reason: no source attaches Aaron Lee to license contact either. His attested contact role is preserved in `maintainers[0].maintainer_details`, which now ends "naming Aaron Lee as central contact," and his attested PI role remains in `creators[0].principal_investigator`.

### 2.5 (minor) Referent drift in `sensitive_elements`

The second `SensitiveElement` object, which asserted `sensitive_elements_present: true` about the controlled-access dataset, was removed from both records. Its content was not lost: `sensitive_elements[0].sensitivity_details` now carries the controlled-access holdings as prose ("The healthsheet notes that the separate controlled-access dataset, which is not this release, does contain data regarding racial and ethnic origins…"), and the top-level `description` gained a closing sentence naming those holdings and the access condition. The record now makes exactly one boolean assertion about its declared referent, and it is `false`.

### 2.6 (minor) `data_protection_impacts` populated with an absence

The slot was removed from both records. The fact moved into the full record's top-level `notes`, which now records that no data protection impact analysis has been conducted.

### 2.7 (minor) `extension_mechanism` populated with an absence

The slot was removed from both records. The fact moved into the full record's top-level `notes`, alongside the other healthsheet negatives.

### 2.8 (minor) Empty declared field on `InformedConsent`

`informed_consent[0].withdrawal_mechanism` was added in both records, carrying the healthsheet's statement that participants could withdraw at any time and that already-shared data remain in the dataset. `consent_revocations` in the full record was left in place; it answers a different slot and the duplication is between two slots the schema declares separately.

### 2.9 (minor) Collapsed environmental variables

In the full record, `variables[particulate_matter]` was replaced by four entries — `particulate_matter_pm1_0`, `particulate_matter_pm2_5`, `particulate_matter_pm4`, `particulate_matter_pm10` — and `variables[nitrogen_oxides]` by two, `nitric_oxide` and `nitrogen_dioxide`. `multispectral_light_intensity` was **not** split: it remains a single `array`-typed entry, with a new `notes` key explaining that the sources describe eleven measurements collectively without naming the channels, so eleven named variables cannot be grounded. `variables` is not present in the core record.

### 2.10 (minor) Duplicated split representation

The three `DataSubset` objects (`#split-train`, `#split-validation`, `#split-test`) were removed from the full record, together with the whole `subsets` slot. Their per-partition counts were folded into `splits[0].split_details`, which now enumerates the composition of each of the three partitions. This also removes three minted fragment ids that nothing in the record referenced. Neither `subsets` nor `splits` is present in the core record.

### 2.11 (minor) Organizational creator carried only in `notes`

`creators[0].affiliations` now leads with `{id: https://aireadi.org/, name: AI-READI Consortium}`, so the attested organizational creator is carried structurally rather than only as commentary. `creators[0].notes` was rewritten to say so. Both records.

### 2.12 (minor) Unsourced enum mapping on `confidentiality_level`

`regulatory_restrictions.confidentiality_level: restricted` was retained, and a `source_caveats` key was added to that object stating explicitly that the value is this record's mapping onto the schema enum, that the RO-Crate gives "HL7:2N (normal)" and FAIRhub gives "PublicDownloadSelfAttestationRequired", and that neither source states an enum-equivalent term. The duplicated recitation of those two source values was removed from `other_compliance`, which now carries only the FDA-regulation facts. Both records.

### 2.13 (info) Caveat describing an unexercised resolution

Item (1) of the top-level `source_caveats` was rewritten. It previously claimed the FAIRhub expansion "is used in this record where the expansion is needed"; it now ends "the record does not expand the acronym in its own prose, so the conflict is recorded rather than resolved." Both records.

### 2.14 (info) Inconsistent `subpopulations` treatment

All four entries now carry `subpopulation_elements_present`: `false` for race/ethnicity and sex (withheld from the public release), `true` for diabetes status and age (not among the withheld variables). The slot-wide commentary that had sat in `subpopulations[3].notes` was removed from that entry and rewritten as per-entry `source_caveats` on entries [0] and [1], the two the healthsheet's "No" answer actually bears on. Both records.

### 2.15 (info) String-typed sub-slots emitted as lists

The digest declares no multivalence for these, so lists could not be confirmed conformant. Three were consolidated to single-element lists carrying merged prose rather than restructured blind:

- `ip_restrictions.restrictions` — four items merged into one.
- `data_governance.stewardship_roles` — four items merged into one; the RO-Crate governance-committee item was dropped from here as redundant with `committee_name` and its new caveat.
- `human_subject_research.irb_approval`, `regulatory_compliance`, `special_populations` and `at_risk_populations.special_protections` and `regulatory_restrictions.regulatory_restrictions` were already single-element and were left in that shape.

Both records validated in this form, so the list shape is conformant; the consolidation removes the ambiguity without asserting a scalar range the digest does not support.

### 2.16 (info) Rights URI embedded in the license name

`license` changed from `AI-READI custom license v2.0 (https://doi.org/10.5281/zenodo.17555036)` to `AI-READI custom license v2.0` in both records. The URI remains in `license_and_use_terms.license_terms`.

---

## 3. Findings left as-is

None. Every finding above resulted in at least one visible change, though three were resolved by annotation rather than by altering the value:

- **2.12** — `confidentiality_level: restricted` was kept and caveated rather than removed, because the audit's objection was to the absence of the caveat rather than to the mapping itself.
- **2.9, in part** — `multispectral_light_intensity` was left unsplit and annotated, because the eleven channels are not individually named in any source and eleven invented variable names would be a worse defect than one honest array.
- **2.15** — the list shapes were kept, since both records validate; only the item counts were consolidated.

---

## 4. Verification

Both files were validated after reconciliation:

- full — `linkml-validate -s data_sheets_schema_all.yaml -C Dataset` → passed
- core — `linkml-validate -s data_sheets_schema_core_all.yaml -C CoreDataset` → passed

Cross-record consistency after the edits: the two records agree on the declared referent, on the repaired 4%/10% treatment, on the removal of `download_url`, `data_protection_impacts`, `extension_mechanism`, `committee_contact`, `contact_person` and the second `sensitive_elements` entry, on the `committee_name` and `license` values, and on the added `withdrawal_mechanism`, `affiliations[0]` and the three new `source_caveats`. The nine data `file_collections` still sum to 356,334 files against a declared total of 356,343; `file_count: 9` was added to the root-metadata collection, so the parts now reconcile exactly to the whole.