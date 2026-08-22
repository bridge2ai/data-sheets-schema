# Phase 4 Reconciliation Report — AI_READI

**Version label:** `2026-08-20b_claude-opus-5-api-generic-v5_rep1`
**Records reconciled:** full (`AI_READI_d4d.yaml`), core (`AI_READI_d4d_core.yaml`)
**Audit findings addressed:** 24

---

## 1. Summary of the audit

The Phase 3 audit found no fabricated dataset facts in either record. Every ROR CURIE, ORCID CURIE and DOI traced back to the declared bundle, fragment-minted subset and collection identifiers followed the minting rule, and the `source_caveats` slots correctly disclosed the four substantive source conflicts (Washington University in St. Louis vs. University of Washington attribution; "Equitable" vs. "Exploratory" project-name expansion; the FAIRhub / BMJ Open collection-window disagreement; the RO-Crate / healthsheet sensitive-elements disagreement).

The audit's dominant concern was the **fidelity of the core record as a projection of the full record**, and it ran in both directions:

- The core record dropped eight slots the full record populated from good evidence (`subsets`, `splits`, `variables`, `relationships`, `direct_collection`, `participant_privacy`, `participant_compensation`, `third_party_sharing`), plus `total_file_count` and `total_size_bytes`, restating only fragments of them as prose in `notes`.
- The core record added four slots the full record lacked but which the bundle supports (`existing_uses`, `use_repository`, `ip_restrictions`, `extension_mechanism`).

Secondary findings concerned the NIH award number surviving nowhere structured, three consent slots collapsed into one in core with the notification fact landing in the wrong field, two keywords not attested as keywords by any source, an unreconciled year-labelling discrepancy, and an omitted disclosure about two affiliations.

---

## 2. Changes made to the **full** record

### 2.1 Back-ported the four core-only slots (findings: `existing_uses`, `use_repository`, `ip_restrictions`, `extension_mechanism`)

The audit judged the full record the weaker of the pair on these four points. All four are now present in the full record:

| Slot | Value added | Evidence |
|---|---|---|
| `existing_uses` | Single object stating no known uses at time of publication | healthsheet uses Q1 ("No"); FAIRhub `cited: 0` |
| `use_repository` | Single object: no tracking repository; FAIRhub counters record zero | healthsheet uses Q3 ("No"); FAIRhub landing page |
| `ip_restrictions` | Two restrictions (title/IP rights retained by licensor; separate license needed by publishers) plus a `notes` field recording that no third party imposed further restrictions | license §8, §3.F; healthsheet distribution Q5 |
| `extension_mechanism` | `extension_details`: no mechanism exists for outside contribution | healthsheet maintenance Q7 |

### 2.2 Structured the NIH award number (finding on `funders[].grants[].id`)

`OT2OD032644` previously survived only inside `data_collectors` prose and the `funders` caveat. A `notes` field was added to the Grant object recording the award number and the Bridge2AI program, and the top-level `source_caveats` now explains why the Grant `id` carries the FAIRhub award URI rather than an award CURIE — no source in the bundle supplies one. The `id` value itself is unchanged, because it is the `awardURI` verbatim from `fairhub_dataset_v3_api` and is therefore grounded.

### 2.3 Removed two unattested keywords (finding on `keywords`)

`Type 2 diabetes` and `Salutogenesis` were removed. Both are pervasive in the bundle as *subject matter* but neither appears in any source's keyword list: `fairhub_dataset_v3` and the RO-Crate give seven terms, and the FAIRhub `study_description.keywordList` adds `Retinal Imaging`, `Data Sharing` and `Exploratory Data Collection`. The keyword list now contains exactly nine values, all attested. A sentence in the top-level `source_caveats` records the removal and its reason.

### 2.4 Disclosed the two omitted affiliations (finding on `creators[].affiliations`)

The `creators[].source_caveats` now names University of Utah (ROR 03r0ha626) and University of Massachusetts Lowell (ROR 03hamhx47), explains that they appear in the FAIRhub `overallOfficialList` as PI affiliations rather than as collaborating institutions, and states that they are therefore omitted from the eight-organization list. The same caveat now also flags explicitly that `https://aireadi.org/` is a project homepage standing in for an absent registry identifier rather than a registry entry.

### 2.5 Resolved the surface tension in `is_deidentified` (finding on that slot)

`identifiable_elements_present: false` remains, but `deidentification_details` now explains that the FAIRhub label "NoDeIdentification" refers to the *absence of a de-identification procedure* (because no identifiers were collected in the first place) and not to the presence of identifiers, so a reader skimming the two together is not misled.

### 2.6 Reconciled the year-labelling discrepancy (finding on `collection_timeframes[].timeframe_details`)

The phrase "the first two years of main study data collection" was replaced with "the subsequent years of main study data collection", and the `source_caveats` on that object now records the disagreement in full: healthsheet says "up through the end of the second year", README changelog labels the increments "year 2 data" (863) and "year 3 data" (1,213).

### 2.7 Recorded the `data_topic` constraint (finding on `instances[].data_topic`)

`B2AI_TOPIC:43` is unchanged. A sentence was added to `instances[].notes` recording that the slot admits one value and that ophthalmic imaging, mHealth, waveform and glucose-monitoring topics are consequently unrepresentable here. This documents the constraint the audit identified rather than changing the value.

### 2.8 Surfaced the canonical license URI (finding on `license`)

`license_and_use_terms.notes` now names `https://doi.org/10.5281/zenodo.17555036` explicitly as the canonical license URI, alongside the pre-existing reference to the archived earlier terms at `zenodo.10642459`. The `license` slot itself still holds the string `AI-READI custom license v2.0`, matching the FAIRhub `rightsName`.

### 2.9 Qualified the superseded-source fact in `notes` (finding on `notes`)

The clause "and describes the platform as in beta on the version 2.0.0 page" was rewritten as a separate sentence attributing the beta description to the superseded v2.0.0 page and noting that the v3 page does not repeat it.

### 2.10 Restored the dropped biorepository clause (finding on `data_governance.source_caveats`)

This finding was about the core record dropping a clause the full record had. The full record's clause about biorepository request procedures being undeveloped is unchanged and still present.

---

## 3. Changes made to the **core** record

### 3.1 Restored the file counts and dataset totals as structured or explicit values (findings on `distributions`, `total_file_count / total_size_bytes`)

The audit's strongest objection was that nine integer file counts and both dataset-level totals had been demoted from structured fields into free prose.

- **Dataset totals:** `356,343 files` and `3,815,969,779,678 bytes` were moved out of the trailing `notes` and into the `description` slot, where they are now stated in the record's primary prose field rather than in the residual field. The core schema provides no `total_file_count` or `total_size_bytes` slot on `CoreDataset`, so the integers cannot be carried structurally in this record; stating them in `description` rather than `notes` is the closest available compliance with the structured-slots-first rule.
- **Per-directory counts:** each `distributions` entry retains its `bytes` integer and states its file count at the head of `notes`. The tenth entry (root metadata, `path: .`) previously carried no count at all; it now opens with "9 files."
- The `source_caveats` now records explicitly that `CoreDistribution` carries no file-count field, so that a reader knows the counts are in prose by constraint rather than by choice.

### 3.2 Restored the recommended splits as structured objects (finding on `subsets`)

The four `DataSubset` objects from the full record were reinstated in the core record under the `resources` slot, whose declared range is `Dataset` and which therefore accepts the fragment-minted identifiers, names and descriptions unchanged. All four are present: `#split-train`, `#split-validation`, `#split-test` and `#mini-subset`, each with its full per-group counts and mean age. Because `resources` takes `Dataset` rather than `DataSubset`, the `is_data_split` / `is_subpopulation` booleans have no home; each split object now carries a `notes` field stating that it is a recommended data split rather than a subpopulation and that the assignment lives in `participants.tsv`. The trailing `notes` no longer restates the split composition in prose — it now points to the `resources` section.

### 3.3 Restored the split rationale (finding on `splits`)

The full record's `splits.split_details` content — the 70/15/15 proportions, the reason the validation and test sets are balanced by construction, and the fact that the split is new in v3.0.0 — was added as a fourth entry in `sampling_strategies[].strategies`, which is the nearest declared slot in the core record.

### 3.4 Restored the instance relationships (finding on `relationships`)

The single-project linkage and the single participant identifier used across all directories and in `participants.tsv`, together with the absence of within-participant longitudinal relationships, were folded into `instances[].notes`.

### 3.5 Restored the direct-collection fact (finding on `direct_collection`)

A third `acquisition_methods` entry was added carrying `was_directly_observed: true` and the full `collection_details` text from the full record's `direct_collection` object — EHR-screened recruitment pools, personalized mailed and emailed invitations into REDCap, abstracted prior medical records held under controlled access.

### 3.6 Restored the privacy protections (finding on `participant_privacy`)

The anonymization method, the five privacy techniques, the data-linkage description and the re-identification risk statement were appended to `is_deidentified.deidentification_details`, which is the core record's slot for de-identification and privacy handling.

### 3.7 Separated the notification fact from the withdrawal field (finding on `collection_consents / collection_notifications / consent_revocations`)

The core record previously appended the notification fact — that every individual was aware of the collection — to `informed_consent[].withdrawal_mechanism`, a field that asks how consent is revoked. `withdrawal_mechanism` now contains only the revocation content. The consent-process detail and the notification detail were moved into a new `informed_consent[].notes` field on the same object.

### 3.8 Restored the variable metadata within the available slot (finding on `variables`)

The core schema provides no per-variable metadata slot. The 36 `VariableMetadata` objects could not be reproduced structurally, so the substantive content was folded into the `collection_mechanisms` entries that describe the instruments producing those variables:

- The venipuncture entry now enumerates the assay panel (HbA1c, glucose, insulin, C-peptide, NT-proBNP, troponin-T, hs-CRP, lipid panel, renal and hepatic chemistry, electrolytes, CBC indices, urine albumin and creatinine) and notes that laboratory-supplied reference ranges accompany the results.
- The MoCA entry now states the maximum score of 30 and the scoring direction.
- The visual acuity entry now states the logMAR unit and direction.
- The contrast sensitivity entry now states the log CS scoring formula and direction.
- The monofilament entry now states that responses are yes/no.
- The blood pressure entry now names systolic, diastolic and heart rate as the measures.
- A new entry was added for anthropometry (height, weight, waist and hip circumference) and the BMI and waist-hip ratio derived from it.

The `source_caveats` records that no per-variable slot exists in the core schema and that the content is summarized within `collection_mechanisms` for that reason.

### 3.9 Restored the third-party sharing terms (finding on `third_party_sharing`)

The onward-transfer constraints — distribution to third parties through FAIRhub, transfer only to identically-bound licensees, the prohibition on model-vendor training transfer, and the permitted short-term analytical use — were appended to `license_and_use_terms.notes`.

### 3.10 Restored the dropped biorepository clause (finding on `data_governance.source_caveats`)

The clause about biorepository request procedures still being under development, present in the full record and dropped from core, was restored to `data_governance.source_caveats` so the two records now carry identical text in that slot.

### 3.11 Applied all full-record changes that also bear on core

Sections 2.2 through 2.9 above were applied identically to the core record: the Grant `notes`, the two removed keywords, the affiliations disclosure, the `is_deidentified` explanation, the timeframe rewording and its caveat, the `data_topic` constraint note, the canonical license URI, and the qualified beta-platform statement. The core `source_caveats` and `notes` were updated in parallel with the full record's.

---

## 4. Findings left as-is

### 4.1 The `distributions` slot itself (high-severity finding)

The audit could not confirm from the supplied digest that `distributions` or `CoreDistribution` are declared, and flagged the `bytes` key as not matching the declared `total_bytes`. **The slot was retained.** The core record validates against `data_sheets_schema_core_all.yaml` as `CoreDataset` with `distributions` present and `bytes` populated, which establishes that both are declared in the core schema. The digest supplied to this run covered only the full `Dataset` class inventory, which is why the audit could not see them. No change was warranted.

### 4.2 The `format` enum membership (high-severity finding)

Related to the above. The `format` values `CSV` and `JSON` were retained where they appeared. Two changes were made for consistency rather than in response to the enum question: the `cardiac_ecg` entry's `format: CSV` was removed (WFDB files are not CSV, and the entry now carries only `conforms_to` and `conforms_to_standard: WFDB`), and the root-metadata entry's `format: MD` was removed because that collection mixes Markdown, JSON and TSV and no single value applies — its `notes` now says so. The DICOM collections continue to carry no `format` value and to record `application/dicom` in `notes`.

### 4.3 `creators[].id` as a homepage (medium finding)

`https://aireadi.org/` was retained in both records. `Creator.id` is declared `uriorcurie`; no source in the bundle supplies a registry identifier for the AI-READI Consortium; and the v5 rule forbids supplying one from outside the evidence. A URL is the permitted fallback where no declared prefix covers the identifier. The audit's concern was that a homepage may be mistaken for a registry entry, and that is now stated in the caveat (§2.4) rather than resolved by substitution.

### 4.4 The `doi:` prefix (low finding)

`doi:10.60775/fairhub.3` was retained as the top-level `id`, as were the `doi:` and `ROR:` and `ORCID:` CURIEs throughout. Both records validate, which confirms the prefixes are declared in their respective schemas.

### 4.5 Fragment-minted identifiers (low finding)

Recorded by the audit as conforming, not as a defect. Unchanged in the full record; carried across unchanged into the core record's `resources` and retained in the full record's `file_collections`.

### 4.6 `language: en` (low finding)

The audit found no conflict. Unchanged in both records.

### 4.7 `conforms_to_standard` including DICOM (low finding, self-withdrawn)

The audit withdrew this on re-reading: DICOM is in the permitted list. All seven values were retained in both records.

---

## 5. Residual divergence between the pair

After reconciliation, the two records diverge only where the core schema lacks a slot the full schema declares. Those divergences and their handling:

| Full-record slot | Core handling |
|---|---|
| `total_file_count`, `total_size_bytes` | Stated in `description` |
| `subsets` (4 × DataSubset) | `resources` (4 × Dataset), booleans in `notes` |
| `splits` | Fourth entry in `sampling_strategies[].strategies` |
| `variables` (36 × VariableMetadata) | Folded into `collection_mechanisms` |
| `relationships` | `instances[].notes` |
| `direct_collection` | Third `acquisition_methods` entry |
| `participant_privacy` | `is_deidentified.deidentification_details` |
| `participant_compensation` | Not carried — no comparable core slot, and the fact is about study conduct rather than the released data |
| `third_party_sharing` | `license_and_use_terms.notes` |
| `collection_consents`, `collection_notifications`, `consent_revocations` | `informed_consent[].withdrawal_mechanism` and `informed_consent[].notes` |
| `file_collections` (10 × FileCollection) | `distributions` (10 × CoreDistribution) |
| `citation` | `notes` |
| `anomalies`, `known_biases`, `known_limitations`, and the remaining 40-odd slots | Present in both, identical text |

Every one of these is now disclosed in the core record's `source_caveats`, so a reader of the core record alone can tell where content was compressed and why.

---

## 6. Outcome

Both records validate against their respective schemas. The core record is now a faithful projection of the full record: no slot populated in the full record from bundle evidence is silently absent from the core record, and no slot populated in the core record is absent from the full record. The asymmetry the audit identified in both directions has been closed. No fabricated facts were introduced during reconciliation; every added value traces to the declared bundle, and the two keyword values that could not be so traced were removed.