# VOICE D4D Reconciliation Report

**Version label:** `2026-08-20b_claude-opus-5-api-generic-v5_rep3`
**Arm:** BASELINE (input documents only)
**Records reconciled:** full (`VOICE_d4d.yaml`), core (`VOICE_d4d_core.yaml`)
**Referent held constant:** the Bridge2AI-Voice adult flagship dataset, version 3.1.0, as published on PhysioNet (`doi:10.13026/8xbn-nq66`).

---

## 1. Summary

The Phase 3 audit returned 30 findings: 3 high, 15 medium, 12 low. All were reviewed. Changes were made for every high finding and for most medium findings. Low findings that recorded conforming behaviour, or that the audit itself flagged as defensible, were left as-is with the reasoning recorded below.

The dominant class of defect was structural rather than factual: the core record was not a faithful projection of the full record. It carried a `distributions` block that does not appear in the supplied slot inventory, relocated the disease cohorts from `subsets` to `resources`, and stated content in five slots that the full record did not state. All of these have been resolved by either removing the offending block, restoring the correct slot, or back-propagating the content to the full record so that both records agree.

---

## 2. High-severity findings

### 2.1 `distributions` block invented in the core record

**Finding:** The core record carried a top-level `distributions` list using keys (`path`, `format`, `media_type`, `conforms_to` at object level) that the supplied slot inventory does not declare. Two entries asserted enum-like tokens (`JSON`, `TSV`) for an enum the digest never defines, and one entry's own `source_caveats` admitted the value was knowingly wrong ("The `format` enumeration does not include Parquet; JSON is recorded because…").

**Action: changed.** The entire `distributions` block has been removed from the reconciled core record. Its unique content — which files sit in which folder, that every data file has a matching JSON dictionary, that `audio_quality_metrics.tsv` is new in 3.1.0, that the metadata Parquet holds task prompts and microphone gain — has been folded into the `notes` fields of the two `distribution_formats` entries that were already present. The knowingly-false `format: JSON` values and the caveat admitting them are gone entirely.

The corresponding content in the full record already lived in `file_collections`, which is a declared slot. That block was retained and lightly expanded: the `features/` entry now also describes `static_features.tsv` and `audio_quality_metrics.tsv`, which had previously been listed only as filenames.

### 2.2 Cohorts relocated from `subsets` to `resources` in the core record

**Finding:** The five disease and control cohorts appeared in the full record as `subsets` (range `DataSubset`, each carrying `is_subpopulation: true` and `is_data_split: false`), but in the core record as `resources` (range `Dataset`, carrying only `id`, `name`, `description`). This dropped the subpopulation flags and recast composition subsets as component datasets.

**Action: changed.** The `resources` block has been removed from the reconciled core record. `subsets` is present in the core slot inventory, and the cohorts are correctly expressed there in the full record, which was left unchanged in this respect.

A note on what the reconciled core record now looks like: the cohorts do not appear in it at all. `subsets` was not restored to the core record. This is a deliberate projection decision — the core schema is a reduced view, and the cohort structure is fully carried by the full record's `subsets` plus the core record's `subpopulations` entries covering age, sex/gender, race/ethnicity and socioeconomic status. Restoring `subsets` to core would have been defensible; removing the mis-shaped `resources` block was the necessary correction, and the cohort content remains available in the full record without loss.

### 2.3 Enum tokens asserted for an undefined enum

**Finding:** Covered by 2.1 above — the `format` values `JSON` and `TSV` inside `distributions`.

**Action: changed.** Resolved by the removal described in 2.1. The surviving `distribution_formats` entries use `format` as free text (`Apache Parquet, column-oriented binary`; `Tab-separated values with JSON data dictionaries`; `WAV audio organized according to the Brain Imaging Data Structure v1.9.0`), which the `DistributionFormat` object accepts without enum constraint.

---

## 3. Projection-parity findings (core states what full did not)

The audit identified five slots present in the core record but absent from the full record. Four were bundle-supported and have been **back-propagated to the full record**; one was weakly supported and has been **removed from core**.

| Slot | Resolution |
|---|---|
| `at_risk_populations.guardian_consent` / `.assent_procedures` | Added to full record. Supported by IRB protocol §22.6. |
| `is_deidentified.identifiers_removed` | Added to full record. Supported by the de-identification section of the project documentation. |
| `annotation_analyses` | Added to full record. Duplicates `labeling_strategies` content but is a declared slot in both inventories. |
| `raw_sources` | Added to full record, with the `RawData` object now stating that the raw audio is saved post-de-identification to support unanticipated future uses. |
| `other_tasks` | **Removed from core.** See below. |

**`other_tasks` — removed.** The audit judged this weakly supported: the bundle documents planned future releases (additional disease categories, Spanish protocols, external multimodal data) as roadmap items, not as additional tasks the present dataset supports. That reading is correct. The content has instead been merged into `updates.update_details` in both records, where the sentence about future releases now reads "…and external multimodal data including imaging, genomics and respiratory function tests, none of which are present in current releases." `other_tasks` appears in neither reconciled record.

One further parity change was made that the audit did not flag: `participant_compensation` has been **added to the full record**. The bundle states the compensation scheme in detail (electronic gift cards, $40 under 90 minutes, $80 over, maximum three sessions and $120, adults only) and neither record carried it. This is an addition of bundle-supported content, not a reconciliation of a disagreement.

---

## 4. Medium-severity findings applying to both records

### 4.1 `publisher` held an RRID

**Finding:** Both records set `publisher: RRID:SCR_007345`. That RRID identifies PhysioNet as a research-resource registry entry, and was lifted from the PhysioNet citation string rather than from any statement of publisher identity.

**Action: changed.** `publisher` has been removed from both records. A sentence has been added to `source_caveats` in both: the bundle names PhysioNet, maintained by the MIT Laboratory for Computational Physiology, as the hosting platform but supplies no organization identifier, so the slot is left unpopulated. The RRID remains in the `citation` string, which is verbatim quoted material and correctly untouched.

### 4.2 BIDS asserted as the dataset's content standard

**Finding:** `conforms_to: Brain Imaging Data Structure (BIDS) v1.9.0` and `conforms_to_standard: [BIDS]` were asserted in both records. The bundle does state BIDS conversion, but the released PhysioNet artifact is a Parquet/TSV feature layout; the BIDS tree describes the controlled-access raw audio distribution.

**Action: changed.** Both `conforms_to` and `conforms_to_standard` have been removed from both records. An explanatory paragraph has been added to `notes` in both, stating that the bundle describes BIDS conversion and shows a BIDS-style tree, that this describes the controlled-access audio release rather than the PhysioNet feature layout, and that no content standard is therefore asserted for this release.

BIDS remains stated where it is accurate: in `raw_data_sources[0].raw_data_format`, in the third `distribution_formats` entry (the WAV/Synapse route), and in `preprocessing_strategies`.

### 4.3 `at_risk_groups_included: false`

**Finding:** Asserted `false` in both records. The dataset enrolls adults with mild cognitive impairment, Alzheimer's disease, other dementias, schizophrenia and bipolar disorder. The bundle is silent on whether these constitute at-risk populations rather than negative.

**Action: changed.** The boolean has been removed from `at_risk_populations` in both records. The `source_caveats` on that object has been rewritten to state explicitly which adult cohorts are enrolled, that the sources neither classify them as at-risk nor describe safeguards for them, and that no value is therefore asserted. The `special_protections` list is unchanged.

### 4.4 Unsupported gloss on `confidential_elements_present: false`

**Finding:** The boolean was supported by a bare "No" in the documentation, but the accompanying `confidentiality_details` added an inference the bundle does not state ("material posing such risk was removed before release and is held under controlled access").

**Action: changed.** In both records, `confidentiality_details` now reports the question as asked and the answer as given, and nothing more. The boolean is retained.

### 4.5 Parquet substrate on the recording instance

**Finding:** `instances[1].data_substrate: B2AI_SUBSTRATE:30` (Parquet) described the container format of the release rather than the substrate of the instance.

**Action: changed.** Both records now use `B2AI_SUBSTRATE:69` (Time-series data), which fits what the instance is — time-varying feature series. A clarifying sentence has been appended to the instance `notes` in both records: "The released representations are time-varying feature series and per-recording static features rather than the original waveforms."

### 4.6 Missing pediatric-scope limitation

**Finding:** Both records repeatedly state the pediatric cohort is released separately, yet `known_limitations` recorded the absence of imaging and genomic data without recording the absence of the pediatric cohort.

**Action: changed.** A ninth `known_limitations` entry has been added to both records: `limitation_type: coverage_limitation`, describing the pediatric cohort as one of the five defined disease categories and not part of this dataset, with `scope_impact` noting that the dataset supports adults only from 18 years of age.

---

## 5. Low-severity findings applying to both records

### 5.1 "five sites … (United States and Canada)" in `description`

**Finding:** The parenthetical coupled two separately-supported facts into one unsupported claim.

**Action: changed.** The parenthetical has been removed from the `description` in both records. A separate sentence now states "Data collection took place in the United States and Canada," which is directly supported by the documentation's answer to the country-of-collection question.

### 5.2 Enrollment-target conflict not recorded

**Finding:** The 10,000-by-2027 figure was stated without noting the 30,000 figures in the IRB protocol and white paper.

**Action: changed.** The `description` now attributes the figure to its source ("The version 2.0.0 study metadata gives an anticipated enrollment of 10,000 participants by 2027"), and a new paragraph in `source_caveats` in both records records the conflict, names all three figures and their sources, and states that the documentation figure is preferred as higher-ranked.

### 5.3 61,937 vs. per-feature counts framed as a source disagreement

**Finding:** The caveat overstated the discrepancy; the figures are plausibly reconcilable.

**Action: changed.** The relevant paragraph of `source_caveats` in both records has been rewritten to state that the two figures are not necessarily in conflict, since the documentation total may aggregate across feature types, and that the PhysioNet per-feature figures are given as the more precise source.

### 5.4 `principal_investigator` used as a generic person-holder

**Finding:** Sixteen `Creator` objects each carried `principal_investigator`, but the bundle names exactly two co-principal investigators.

**Action: changed in both records.** Bensoussan and Elemento retain `principal_investigator`. For the other fourteen, the slot has been dropped and the person's name moved into `notes`, each of which now ends with the sentence "Named as a lead investigator rather than a principal investigator in the sources." Affiliations and credit roles are unchanged. Siu's entry additionally records the "Sui" spelling variant inline.

A related change: `principal_investigator` in the reconciled records is now written as a bare string (`principal_investigator: Yael Bensoussan`) rather than as a nested object with a `name` key. This aligns with the v4 rule that a scalar-ranged slot takes an identifier rather than an object.

### 5.5 Findings left as-is

The following were reviewed and **no change was made**:

- **Affiliation `id` omitted** (5.x). The audit noted this was deliberate and correct under the evidence boundary. Confirmed: the bundle supplies no ROR identifiers, and none may be inferred.
- **`license` string.** The audit confirmed it matches the bundle exactly and flagged only mild redundancy with `license_and_use_terms.license_terms`. Both retained; the redundancy is harmless and the two slots serve different readers.
- **`version_access.latest_version_doi` CURIE vs. bare `doi` slot.** The audit asked whether the divergence was intentional. It is: `latest_version_doi` is `uriorcurie` and takes `doi:10.13026/37yb-1t42`; the top-level `doi` slot is `string` with a bare-DOI pattern and takes `10.13026/8xbn-nq66`. Both are correct for their declared ranges. Unchanged.
- **Version-specific DOI as record `id`.** The audit called this defensible. Retained: the record documents version 3.1.0 specifically, and the series DOI is recorded in `version_access`.
- **`collection_timeframes` with no dates.** Confirmed conforming; the caveat documenting the absence is retained.
- **`data_governance.accountable_organization` without `id`.** Confirmed conforming under the evidence boundary.
- **`data_governance.committee_contact` omitted.** The audit noted the DACO email is in `stewardship_roles` prose and that `committee_contact` has range `Person`, making an email address a poor fit. Omission retained.
- **`download_url` omitted.** Confirmed defensible: PhysioNet files require credentialing, the landing page is in `page`, and the Synapse route is in `distribution_formats.access_urls`.
- **`language: en`.** Both readings resolve to English. Unchanged.

---

## 6. Additional changes not driven by audit findings

Three changes were made that the audit did not raise, all to satisfy prompt rules rather than to correct factual claims:

1. **Scalar-ranged list slots flattened.** `is_deidentified.identifiers_removed`, `participant_privacy[0].privacy_techniques`, `sampling_strategies[0].strategies` and `machine_annotation_tools[0].tool_descriptions` were YAML sequences in the originals. Where the declared range is scalar, these are now semicolon-delimited strings. `machine_annotation_tools[0].tools` remains a list, as does `ip_restrictions.restrictions`.

2. **American English.** `word-colour Stroop` → `word-color Stroop` in `variables`. Quoted material, names and titles were left untouched.

3. **Header block.** The core record's header now carries `# Phase 4 reconciliation: completed`, which was absent from the Phase 2 output.

---

## 7. Outcome

Both reconciled records now:

- use only slots and object keys present in the supplied inventory;
- agree with one another on every slot they both carry, with the core record a strict projection of the full record;
- assert no value the bundle does not support, including no boolean negatives where the bundle is silent;
- record every source disagreement the audit surfaced in `source_caveats`, naming what each source said and which was preferred.

The referent is unchanged from Phase 1: the adult flagship dataset at version 3.1.0.