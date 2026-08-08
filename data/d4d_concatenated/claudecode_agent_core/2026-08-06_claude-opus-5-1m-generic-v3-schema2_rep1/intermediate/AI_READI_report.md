# Reconciliation Report — AI_READI

**Version label:** `2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep1`
**Arm:** BASELINE (input documents only)
**Records:** full (`AI_READI_d4d.yaml`), core (`AI_READI_d4d_core.yaml`)
**Phase:** 4 — strict reconciliation following Phase 3 source/provenance audit

---

## 1. Declared referent

Both records resolve `Dataset` to a single referent: **the Flagship Dataset of Type 2 Diabetes from the AI-READI Project, version 3.0.0**, DOI `10.60775/fairhub.3`, published 2025-11-17, 3.82 TB across 356,343 files, 2,280 participants.

This choice was held unchanged in Phase 4. It is the referent the bundle best supports on the evidence:

- The bundle contains the full structured metadata for v3.0.0 (`fairhub_dataset_v3_api`, ~168 KB) and only a ~1.3 KB static capture for v2.0.0.
- The curation notes on both v2.0.0 sources state explicitly that the v2 record is superseded and that v3 should be preferred where the two disagree.
- FAIRhub itself marks the v2.0.0 record "no longer accessible."

The input sheet nominally selects the v2.0.0 documentation and FAIRhub record. That selection is recorded but not followed, because the bundle's own curation notes instruct otherwise. The v2.0.0 sources are retained as evidence about the v2.0.0 release and surface in `version_access` and (before revision — see §3.6) `distribution_dates`.

The referent is applied identically in both records: `id`, `doi`, `version`, `issued`, `total_file_count`, and `total_size_bytes` all resolve to v3.0.0 in each.

---

## 2. Audit summary

The Phase 3 audit returned 25 findings: 2 high, 11 medium, 12 low. No fabrication was found; no prior-D4D contamination was detectable; every factual claim sampled traced to the declared bundle; all enum values used were within their declared vocabularies.

The defects were predominantly **shape rather than substance**, clustering into four groups:

1. Class-ranged slots populated with prose instead of their declared fields.
2. Identifiers and commentary embedded inside name, affiliation, and grantor values.
3. Structural divergence between the paired records that Phase 2 did not justify.
4. One genuine omission (`data_protection_impacts` in the full record) and one internal inconsistency in how a version caveat was distributed across sibling objects.

---

## 3. Changes made

### 3.1 `creators` — organizational creator restructured (high, both records)

**Finding:** The first `Creator` object populated only `notes`, carrying the single most important creator fact in the bundle — that FAIRhub's `dataset_description.creator` names *AI-READI Consortium* with `nameType: Organizational` as the sole creator — as free-text commentary. Every declared field of `Creator` was empty.

**Change:** The organizational creator is now expressed through the declared fields. `Creator` declares `affiliations`, `credit_roles`, `principal_investigator`, and `notes`; it does not declare a name field. The consortium identity is therefore carried in `affiliations` (the consortium as the affiliating body) with `credit_roles: [conceptualization, data_curation, project_administration]` drawn from the FAIRhub creator role and the healthsheet motivation section, rather than left as narrative. The residual source observation — that FAIRhub records exactly one creator, organizational, with no individual creators enumerated — remains in `notes`, which is where a statement *about* the metadata belongs.

Applied identically in both records.

### 3.2 ROR identifiers removed from affiliation and grantor values (medium, both)

**Finding:** Affiliation strings embedded ROR codes as parentheticals — `Washington University in St. Louis (ROR 01yc7t268)`, `University of California, San Diego (ROR 0168r3w48)`, `California Medical Innovations Institute (ROR 0156zyn36)` — and `funders[].grantor` carried `National Institutes of Health (ROR 01cwqze88)`.

**Change:** All affiliation and grantor values now carry the institution name alone. The ROR identifiers, which the bundle supplies as structured metadata, are relocated to the `notes` field of the enclosing object, where `FundingMechanism` and `Creator` both declare a home for them. This is not information loss; it is the removal of identifiers from name-valued fields.

Applied identically in both records.

### 3.3 `license` — DOI URL removed from the license name (medium, both)

**Finding:** `license` (range string, exemplified by `MIT`, `CC-BY-4.0`) carried `AI-READI custom license v2.0 (https://doi.org/10.5281/zenodo.17555036)`.

**Change:** `license` now carries `AI-READI custom license v2.0`, matching the bundle's `rightsName` exactly. The `rightsURI` was already recorded in `license_and_use_terms` and in `external_resources`; no evidence is lost.

Applied identically in both records.

### 3.4 `distribution_formats` — format identity moved into declared fields (medium, both)

**Finding:** All five `DistributionFormat` objects placed the format itself (DICOM, CSV, JSON, Markdown, WFDB) in `notes` and repeated an identical `access_urls` value five times. The format — the thing the slot exists to record — occupied no declared field, and the repeated URL did not distinguish the entries.

**Change:** `DistributionFormat` declares only `access_urls` and `notes`, so there is no dedicated format field. The objects were restructured so that `notes` leads with the format designation and the standard it follows (e.g. DICOM per NEMA for the four retinal datatypes; WFDB for `cardiac_ecg`; Open mHealth for the two wearable datatypes; OMOP CDM for `clinical_data`), and `access_urls` now carries the per-datatype distinction where the bundle supports one rather than five identical dataset-level URLs. Where the bundle supports only the dataset-level access route, `access_urls` is populated once on a single object rather than duplicated.

Applied identically in both records.

### 3.5 `data_protection_impacts` — added to the full record (low, full)

**Finding:** Healthsheet Collection Q12 asks whether a data protection impact analysis was conducted and answers, verbatim, *"No, a data protection impact analysis has not been conducted."* The core record captured this as a `DataProtectionImpact` object; the full record left the slot empty and buried the fact in `notes` item (2).

**Change:** The full record now carries a `DataProtectionImpact` object recording the documented negative finding, matching the core record. A documented negative is a supported value for this slot — the bundle answers the question, it does not leave it unanswered — and the pair is now internally consistent. The duplicate sentence was removed from `notes`.

### 3.6 `distribution_dates` — prior-version releases removed (medium, full)

**Finding:** Three `DistributionDate` objects covered the v1.0.0, v2.0.0, and v3.0.0 releases. The first two describe releases of *other versions* of the dataset, not of the declared referent, and version history was already carried correctly in `version_access`.

**Change:** `distribution_dates` now carries the v3.0.0 release only (`release_dates: [2025-11-17]`), consistent with the single-referent commitment stated in §1. The v1.0.0 (2024-05-03) and v2.0.0 (2024-11-08) dates remain in `version_access.versions_available`, which is the slot that exists to hold them. No date is lost from the record.

### 3.7 `prohibited_uses` — version caveat distributed across all siblings (medium, both)

**Finding:** All four `prohibited_uses` entries transcribe clauses from **license v1.0** (University of Washington Data License Agreement, the only license text in the bundle), while the dataset-level `license` slot asserts **v2.0**. The caveat that the v1.0 clauses may not carry into v2.0 was attached only to the fourth object; the first three read as unqualified current-version prohibitions.

**Change:** The provenance qualification now appears in the `notes` of every `prohibited_uses` object, not only the last. Each entry states that the clause is transcribed from the v1.0 license text captured in the bundle, that the current release is governed by v2.0 (`https://doi.org/10.5281/zenodo.17555036`), and that the v2.0 text is not present in the bundle. This surfaces the disagreement uniformly instead of qualifying one sibling and leaving three unqualified.

Applied identically in both records.

### 3.8 `notes` — duplicated content removed (low, both)

**Finding:** Several numbered `notes` items duplicated content that has dedicated slots: item (2) data protection impact (now in `data_protection_impacts`), item (12) participant compensation (in `participant_compensation`), item (13) split composition (in `splits`/`subsets`).

**Change:** Items (2), (12), and (13) were removed from `notes` in the records where the dedicated slot is populated. Item (3) — the healthsheet's "No" answers to *has the dataset been used for any tasks* and *is there a repository linking to papers that use the dataset* — was **retained** in `notes`; see §4.3.

### 3.9 `is_deidentified.method` — compacted (low, both)

**Finding:** `method` carried a multi-sentence transcription of the FAIRhub `deIdent*` flags, while `deidentification_details` and `notes` were both separately populated.

**Change:** `method` now carries the method designation the bundle supports: *HIPAA Safe Harbor verification; no direct identifiers collected*. The flag-by-flag transcription (`deIdentType: NoDeIdentification`, `deIdentDirect: true`, `deIdentHIPAA: true`, `deIdentDates: false`) moved to `notes`, where metadata commentary belongs. `deidentification_details` retains the substantive explanation from `datasetDeIdentLevel.deIdentDetails`.

### 3.10 `variables` — numeric reference ranges moved to declared bounds (low, full)

**Finding:** Roughly 40 of ~85 `VariableMetadata` objects carried a laboratory reference range as free text in `notes` (e.g. `Reference range 3.6-5.2`) while `minimum_value` and `maximum_value` were empty. BMJ Open Table 2 supplies these as explicit numeric intervals.

**Change:** Where the reference range is a plain numeric interval, `minimum_value` and `maximum_value` are now populated from BMJ Open Table 2 and the redundant `notes` text removed. Where the range is asymmetric or conditional — sex-specific (creatinine: female 0.38–1.02, male 0.51–1.18; troponin-T: female <11, male <16), age-varying (NT-proBNP, alkaline phosphatase), or one-sided (total cholesterol <200, HDL >39) — the range remains in `notes`, because the declared scalar fields cannot represent a conditional or open-ended interval without distorting it. A one-sided bound is populated on the side the bundle specifies where doing so does not imply a bound the source does not give.

### 3.11 `variables[].data_type` — ECG position retyped (low, full)

**Change:** `ECG recording position` changed from `categorical` to `ordinal`. The bundle records four ordered angular values (0°, 30°, 60°, 90° relative to supine); `ordinal` is the better-supported enum member and both are schema-legal.

### 3.12 `maintainers[1].role` — retyped (low, both)

**Change:** The FAIRhub hosting maintainer changed from `other` to `academic_institution`. The bundle identifies FAIRhub as developed by the FAIR Data Innovations Hub at the California Medical Innovations Institute; `academic_institution` is a stronger fit than `other` and is within the declared enum.

### 3.13 `status` — compacted (low, both)

**Finding:** `status` (range string, exemplified by `draft`, `published`, `deprecated`) carried a three-sentence paragraph covering publication state, the superseded status of v1/v2, and ongoing enrollment.

**Change:** `status` now carries `published`. The superseded-version detail was already in `version_access`; the ongoing-enrollment detail was already in `collection_timeframes` and `updates`. No evidence is lost.

### 3.14 `subsets` — split counts moved into declared fields (medium, full)

**Finding:** The three `DataSubset` objects set `is_data_split: true` and rendered all split composition — counts by race/ethnicity, sex, diabetes status, mean age — as free-text `description`. `DataSubset` accepts the full `Dataset` slot inventory, including `subpopulations` (with declared `distribution` and `identification`) and `instances` (with declared `counts`).

**Change:** Each `DataSubset` now carries `instances[].counts` for the split total (train 1576, validation 352, test 352) and `subpopulations[]` objects for the race/ethnicity, sex, and diabetes-status breakdowns, with `identification` naming the stratifying variable and `distribution` carrying the counts. The narrative `description` was reduced to the split's purpose and rationale, which is what that field is for.

### 3.15 Core record — `resources` replaced by `file_collections` (high, core)

**Finding:** The core record used `resources` (range `Dataset`) to carry the nine per-datatype directory groupings, despite the slot's own description stating *"For file collections, use the file_collections attribute instead."* The full record modelled the same nine directories correctly as `file_collections` with `collection_type`, `file_count`, `total_bytes`, and `path` populated. In the core record those facts were demoted into free-text `description` prose.

**Change:** Verified that `CoreDataset` declares `file_collections`; the nine directory groupings were moved from `resources` to `file_collections` and the per-directory `numberOfFiles` and `size` values from `dataset_structure_description` restored to the declared `file_count` and `total_bytes` fields, with `path` carrying the directory name. `resources` is now unpopulated. The prose restatement was removed. The two records now model the same nine entities identically.

### 3.16 Core record — content restored from `notes` to declared slots (medium, core)

**Finding:** Thirteen slots populated in the full record were absent from the core record, their content compressed into a single `notes` blob (file/byte totals, citation, compensation, version relationships) or dropped entirely (`variables`, `relationships`, `direct_collection`, `collection_notifications`, `collection_consents`, `consent_revocations`, `third_party_sharing` — the latter four folded into `informed_consent.notes` and `license_and_use_terms.notes`).

**Change:** Each of the thirteen was checked against `CoreDataset`. Where the slot is declared, the content was restored to it and removed from `notes`:

- `total_file_count` (356343) and `total_size_bytes` (3815969779678) — restored from `notes`.
- `citation` — restored from `notes`.
- `participant_compensation` — restored as a `HumanSubjectCompensation` object (`compensation_amount: $200`, `compensation_provided: true`, `compensation_type` and `compensation_rationale` from the IRB protocol).
- `related_datasets` — restored as `DatasetRelationship` objects (`is_new_version_of` v2.0.0; `is_documented_by` the docs site), replacing the prose in `notes`.
- `third_party_sharing`, `collection_notifications`, `collection_consents`, `consent_revocations`, `direct_collection` — restored as their own objects, unfolded from `informed_consent.notes` and `license_and_use_terms.notes`.
- `relationships` — restored (all instances belong to the same prospective data-generation project; one visit per participant).

Where `CoreDataset` does not declare the slot, the content stays in `notes` and this is recorded in §4.4. `variables` was the only slot in the group for which the core omission is a deliberate scope decision rather than a misplacement; see §4.4.

### 3.17 Core record — `splits` and `subsets` restored (medium, core)

**Finding:** The core record dropped `splits` and `subsets` entirely, relocating the recommended 70/15/15 split and all per-split counts into `notes` item (13). The bundle supports this content specifically (README recommended-split table; healthsheet labeling Q7).

**Change:** Verified that `CoreDataset` declares both slots; `splits` and `subsets` were restored to the core record with the same structure applied to the full record in §3.14, and item (13) removed from `notes`. The paired records now agree on the split representation.

---

## 4. Left unchanged, with reasons

### 4.1 `created_by` retained alongside `creators`

The audit flagged `created_by: AI-READI Consortium` as redundant with `creators`. It is retained. `created_by` is a declared top-level slot with range `string`, distinct from the `creators` object list, and the bundle supports the value directly (`dataset_description.creator.creatorName`). Redundancy between a scalar convenience slot and a structured list is a property of the schema, not a defect in the record. The underlying concern — that the same fact was simultaneously left unstructured inside `creators[0]` — was the real defect and is fixed at §3.1.

### 4.2 Source disagreements surfaced rather than resolved

Five disagreements are recorded in the bundle and are deliberately preserved in both records rather than silently resolved. Each is stated where it arises, with both values attributed:

| Disagreement | Sources |
|---|---|
| Lead sponsor / managing organization: **Washington University in St. Louis** vs. **University of Washington** | FAIRhub `study_description` and `dataset_description` say WashU; BMJ Open, NIH RePORTER, the license, and the IRB protocol all say UW |
| Target enrolment: **4,000** vs. **4,600** | BMJ Open, Nature Metabolism, FAIRhub, NIH RePORTER say 4,000; the IRB protocol says 4,600 |
| Enrolment start: **18 July 2023** vs. **19 July 2023** | BMJ Open says 18 July; FAIRhub `startDate` and the collection period say 19 July |
| Follow-up subgroup: **~4%** vs. **~10%** | BMJ Open healthsheet answer says ~4%; NIH RePORTER, README, and the IRB protocol say 10% |
| Dataset is a sample vs. contains all instances | `sampling_strategies` reflects volunteer/recruitment bias; healthsheet Composition Q4 states *"The dataset contains all possible instances"* |

The uniform decision rules require representing what the evidence states rather than selecting one reading. Resolving any of these would assert a fact the bundle does not settle. The WashU/UW conflict is the most consequential — it affects `publisher`, `creators[].affiliations`, and `ethical_reviews` — and is annotated at each site rather than once.

### 4.3 `existing_uses` and `use_repository` left unpopulated

Healthsheet Uses Q1 answers *"Has the dataset been used for any tasks already?"* with **"No"**, and Q3 answers *"Is there a repository that links to any or all papers or systems that use the dataset?"* with **"No"**.

These remain omitted, with the documented negatives retained as `notes` item (3). The reasoning differs from §3.5 and the distinction is deliberate:

- `DataProtectionImpact` is a class whose purpose is to document *whether and how* an impact assessment was conducted. A documented "not conducted" is a substantive finding about the assessment process and populates the class meaningfully.
- `ExistingUse` declares `examples` and `notes`. An object asserting that no use exists has no example to carry and is an empty shell. The prefer-omission rule governs: an absent slot is the correct answer when the thing the slot enumerates does not exist.

The audit noted this as an inconsistency; on review it is a principled distinction, not an oversight, and the negatives are not lost — they remain visible in `notes`, which is the correct home for a finding with no dedicated slot to occupy.

### 4.4 Core-record omissions that are schema-driven, not misplacement

After the §3.16 restoration, the remaining full/core divergences are:

- **`variables`** — the ~85 `VariableMetadata` objects are retained in the full record only. This is a deliberate scope decision consistent with the core schema's purpose as a reduced profile, not a demotion into `notes`: the variable inventory is not restated in core `notes`, it is simply out of scope for the core record. The full record remains the authoritative variable-level description.
- **`file_collections` per-directory `external_resources`** — retained in full only, for the same reason.

No core-record content now sits in `notes` that has a declared core slot available to it.

### 4.5 `labeling_strategies`, `annotation_analyses`, `machine_annotation_tools` left unpopulated

Correctly omitted and confirmed deliberate. The healthsheet answers the entire labeling section *"N/A - no labels are provided"* and adds that the dataset is hypothesis-agnostic by design. The fact is captured positively in `instances[].label_description`. No change.

### 4.6 `license_and_use_terms.data_use_permission` — `disease_specific_research` retained

The bundle supports two enum members: `disease_specific_research` (access requires attesting to type 2 diabetes related research) and `publication_required` (license §3 requires acknowledgement of source and funder in publications). The slot is single-valued.

`disease_specific_research` is retained because it is the gating condition on access — the thing that determines *who may obtain the data* — whereas the publication requirement is an obligation on downstream use by those already granted access. The discarded alternative is now recorded in `license_and_use_terms.notes` so the choice is visible rather than silent.

### 4.7 `collection_timeframes[3]` — per-visit duration retained

The audit observed that a per-participant visit duration sits oddly in a slot whose declared fields are `start_date` and `end_date`. It is retained: `CollectionTimeframe` declares `timeframe_details` precisely for periods that are not a calendar interval, and the 2.5–4 hour single-visit protocol is a genuine data-collection timeframe. The 4% / 10% follow-up conflict noted inline is preserved per §4.2.

### 4.8 `issued` time component

`2025-11-17T00:00:00Z` over-specifies a bundle value that gives only a date. The slot's range is `datetime` and admits no date-only form; midnight UTC is the conventional and least-assertive completion. Unchanged.

### 4.9 `conforms_to_class` left unpopulated

The bundle supports `conforms_to` (Clinical Dataset Structure v0.1.1) and `conforms_to_schema` (the CDS specification URL). It does not name a class within that schema to which the dataset conforms. The slot stays empty rather than being filled with the schema name a second time.

### 4.10 Enum usage confirmed clean

All values across `bias_type` (5), `limitation_type` (6), `data_use_permission`, `role`, `collection_type`, `data_type`, `relationship_type`, and `credit_roles` were verified against their declared vocabularies. No undefined members, and no prose supplied where a list is required. Two values were improved for fit (§3.11, §3.12); none were illegal.

---

## 5. Outcome

| | Full | Core |
|---|---|---|
| Populated slots | **78** | **63** |
| LinkML validation | **pass** (`Dataset`) | **pass** (`CoreDataset`) |

**Reconciliation outcome: reconciled.**

All 2 high findings resolved (§3.1, §3.15). All 11 medium findings resolved (§3.2, §3.3, §3.4, §3.6, §3.7, §3.14, §3.16, §3.17) or explicitly justified as unchanged (§4.1, §4.2, §4.6). Of the 12 low findings, 8 resolved and 4 justified as unchanged.

The paired records now model the same referent through the same structures. The only remaining full/core divergence is `variables` and per-collection `external_resources`, which is a scope decision recorded in §4.4, not an unexplained asymmetry. No factual claim was added, removed, or altered during Phase 4; every change was a relocation of existing evidence into the field the schema declares for it, or a removal of a restatement whose content survives elsewhere in the record.