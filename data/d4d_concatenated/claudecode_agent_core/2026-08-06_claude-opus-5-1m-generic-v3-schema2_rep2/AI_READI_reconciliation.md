# Reconciliation Report — AI_READI

**Version label:** `2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2`
**Arm:** BASELINE (input documents only)
**Source bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt`
**Records reconciled:**
- Full — `data/d4d_concatenated/claudecode_agent/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2/AI_READI_d4d.yaml`
- Core — `data/d4d_concatenated/claudecode_agent_core/2026-08-06_claude-opus-5-1m-generic-v3-schema2_rep2/AI_READI_d4d_core.yaml`

---

## 1. Referent

Both records describe a single referent: **the Flagship Dataset of Type 2 Diabetes from the AI-READI Project, version 3.0.0**, DOI `10.60775/fairhub.3`, published 2025-11-17, 2,280 participants, 356,343 files, 3.82 TB.

The bundle contains material describing three neighbouring things, and the choice was held consistently across both records:

| Entity | Treatment |
|---|---|
| Dataset v3.0.0 (`10.60775/fairhub.3`) | **The referent.** |
| Dataset v2.0.0 (`10.60775/fairhub.2`) and v1.0.0 (`10.60775/fairhub.1`) | Prior versions. Recorded in the full record via `related_datasets` (`is_new_version_of`) and in `version_access`. Not merged into the referent's counts. |
| "Mini Version" (`10.60775/fairhub.4`, 100 participants) | A distinct derived artifact, not a version of the referent. Recorded in the full record as `related_datasets` with `relationship_type: is_source_of`. |
| The AI-READI *study* (NCT06002048, grant OT2OD032644, 4,000-person target) | Provenance of the referent, not the referent. Study-level facts populate collection, ethics, and motivation slots; the study's 4,000-participant target is not reported as the dataset's instance count. |

The v2.0.0 documentation and FAIRhub record are present in the bundle but are marked by the curator as superseded and no longer accessible. They were used only as evidence about the v2.0.0 release.

---

## 2. What the audit found

The audit returned 38 findings: 2 high, 12 medium, 24 low. They fall into five groups.

### 2.1 Schema-shape defects (2 high)

1. **`distributions` in the core record is undeclared.** Neither the slot nor its member keys (`path`, `bytes`, `format`, `media_type`) appear in the schema. The conforming construct is `file_collections`, which the full record already used correctly.
2. **`at_risk_populations` cardinality mismatch.** Range `AtRiskPopulations` is *not* `[many]`, but the full record emitted a list while the core record emitted a bare mapping. The two paired records disagreed with each other, and the full record disagreed with the schema.

### 2.2 Structural demotion in the core record (13 low, conditional)

Content carried as typed objects in the full record (`subsets`, `splits`, `participant_compensation`, `participant_privacy`, `collection_notifications`, `consent_revocations`, `third_party_sharing`, `direct_collection`, `related_datasets`, `relationships`, `variables`, `total_file_count`, `total_size_bytes`) had been relocated into free-text `notes` in the core record. Whether each instance is a v3-rule violation depends on whether `CoreDataset` declares the slot.

### 2.3 Supported omissions — explicit negatives left unpopulated (5 medium)

The healthsheet answers five questions in the negative, and each negative is representable in a declared field:

| Slot | Bundle text |
|---|---|
| `extension_mechanism` | "No, currently there is no mechanism for others to extend or augment the AI-READI dataset outside of those who are involved in the project." |
| `data_protection_impacts` | "No, a data protection impact analysis has not been conducted." |
| `existing_uses` | "Has the dataset been used for any tasks already?" → "No" |
| `use_repository` | "Is there a repository that links to any or all papers or systems that use the dataset?" → "No" |
| `labeling_strategies` | "N/A - no labels are provided… the dataset is a hypothesis-agnostic dataset" |

### 2.4 Inferential enum choices (3 low)

`hipaa_compliant: compliant`, `confidentiality_level: restricted`, and `data_use_permission: disease_specific_research` are all permitted values and all defensible, but none is stated literally in the bundle.

### 2.5 Correctly-handled disagreements (no action, confirmed)

The audit confirmed that the bundle's internal conflicts were preserved rather than silently resolved.

---

## 3. Changes made to the full record

### 3.1 `at_risk_populations` — list converted to single object *(high)*

The slot inventory lists `at_risk_populations` with range `AtRiskPopulations` and **no** `[many]` marker. A list is not a valid value.

**Before**
```yaml
at_risk_populations:
  - at_risk_groups_included: ...
    special_protections: ...
```

**After**
```yaml
at_risk_populations:
  at_risk_groups_included: ...
  special_protections: ...
```

Content unchanged; only the shape. This also brought the full record into agreement with the core record, which had the correct form.

### 3.2 `extension_mechanism` added *(medium)*

Range `ExtensionMechanism` (not `[many]`), declared key `extension_details`. The bundle answers the question directly.

```yaml
extension_mechanism:
  extension_details: No mechanism exists for parties outside the AI-READI project
    to extend or augment the dataset. Contributions are limited to those involved
    in the project.
```

### 3.3 `data_protection_impacts` added *(medium)*

```yaml
data_protection_impacts:
  - impact_details: No data protection impact analysis (DPIA) has been conducted
      for this dataset.
```

### 3.4 `existing_uses` added *(medium)*

Recording the negative, with the corroborating citation count from the FAIRhub API payload.

```yaml
existing_uses:
  - notes: At the time of the v3.0.0 release the dataset had not been used for any
      tasks. The FAIRhub record reports a citation count of zero.
```

### 3.5 `use_repository` added *(medium)*

```yaml
use_repository:
  - notes: No repository or registry tracks papers or systems that use this dataset
      beyond general citation indices such as Google Scholar.
```

### 3.6 `labeling_strategies` added *(medium)*

The negative was previously reachable only through `instances[0].label_description`. `LabelingStrategy` is the slot the schema designates for it, so it now appears in both places — the instance-level field describing the instances, and the dataset-level field describing the procedure (or its absence).

```yaml
labeling_strategies:
  - labeling_details: No labeling or annotation was performed. The dataset is
      hypothesis-agnostic and is intended to support multiple downstream AI/ML
      applications rather than a predefined labeled task.
```

### 3.7 `discouraged_uses` added *(medium)*

The healthsheet's motivation section asks about *discouraged* usage; the license imposes *prohibited* usage. The full record had routed everything to `prohibited_uses`. The clinical-decision-making restriction is framed in the license as a statement about the resource's intended scope ("as it is intended solely as a research resource"), which reads as guidance more than as an enforcement clause, so it now appears in both slots with distinct framing.

```yaml
discouraged_uses:
  - discouragement_details: Use of the data to make clinical treatment decisions
      is discouraged; the dataset is intended solely as a research resource.
    notes: The healthsheet frames license restrictions as answering the question
      of discouraged applications.
```

### 3.8 `variables` — `measurement_technique` added to four lipid entries *(low)*

Total cholesterol, triglycerides, HDL-C and LDL-C omitted the field while neighbouring serum analytes populated it. Table 3 of the protocol lists "lipids" among the UW NORC serum tests, so the omission was an internal inconsistency, not an evidence gap. All four now carry:

```yaml
measurement_technique: Serum assay performed by the University of Washington
  Nutrition and Obesity Research Center (NORC) laboratory
```

### 3.9 `acquisition_methods[3]` — over-reach trimmed *(low)*

"Blood urea nitrogen/creatinine ratio" was listed among derived variables. Table 2 marks `Globulin, total (calculated)`, `A/G ratio (calculated)` and `Low-density lipoprotein cholesterol (calculated)` explicitly; the BUN/creatinine ratio carries no such annotation. The inference is sound but not stated, so the item was removed from the enumerated list and the residual reasoning moved to `notes`:

```yaml
notes: Table 2 of the protocol marks total globulin, the A/G ratio and LDL
  cholesterol as calculated. Other ratio measures appear in the table without a
  calculation annotation.
```

### 3.10 `license` and `conforms_to` — embedded URLs removed *(low)*

The declared range is a plain string, and the schema's examples (`MIT`, `CC-BY-4.0`) indicate a name, not a name-plus-URL composite. Both URLs were already carried in the appropriate structured locations.

| Slot | Before | After |
|---|---|---|
| `license` | `AI-READI custom license v2.0 (https://doi.org/10.5281/zenodo.17555036)` | `AI-READI custom license v2.0` |
| `conforms_to` | `Clinical Dataset Structure (CDS) v0.1.1 (https://cds-specification.readthedocs.io/en/v0.1.1/)` | `Clinical Dataset Structure (CDS) v0.1.1` |

The license DOI remains in `license_and_use_terms.notes`; the CDS specification URL remains in `external_resources`.

### 3.11 `regulatory_restrictions.hipaa_compliant` — value changed *(low)*

`compliant` asserts a compliance determination the bundle does not make. What the bundle states is that PHI was removed by the HIPAA Safe Harbor method and that results are returned to participants by HIPAA-compliant encrypted email — statements about a de-identification method and a communications channel, not about the dataset's regulatory status. Changed to `not_applicable`, with the reasoning preserved:

```yaml
hipaa_compliant: not_applicable
notes: The public dataset was stripped of Protected Health Information using the
  HIPAA Privacy Rule Safe Harbor method, so HIPAA obligations do not attach to
  the released artifact. The bundle does not state a compliance determination
  for the dataset itself.
```

### 3.12 `regulatory_restrictions.confidentiality_level` — value removed *(low)*

`restricted` was inferred from the verified-ID login and self-attestation gate. The bundle assigns no confidentiality level, and the inference sits in tension with `confidential_elements[0].confidential_elements_present: false`, which reports the healthsheet's explicit statement that the dataset contains nothing confidential. The enum was dropped; the access conditions it was standing in for are already recorded in `license_and_use_terms` and `distribution_formats`.

---

## 4. Changes made to the core record

### 4.1 `distributions` replaced by `file_collections` *(high)*

`distributions` is undeclared, as are its member keys. The content was remapped onto `FileCollection`, whose declared keys (`id`, `path`, `file_count`, `total_bytes`, `collection_type`, `conforms_to`) accommodate it directly.

**Before**
```yaml
distributions:
  - path: retinal_oct
    bytes: 1317625293027
    format: DICOM
    media_type: application/dicom
```

**After**
```yaml
file_collections:
  - id: https://doi.org/10.60775/fairhub.3#retinal_oct
    path: retinal_oct
    file_count: 56478
    total_bytes: 1317625293027
    collection_type: processed_data
    conforms_to: Digital Imaging and Communications in Medicine (DICOM)
```

Applied to all nine data-type directories. This also aligned the core record with the full record, which already used `file_collections`.

### 4.2 Structural demotions reversed where `CoreDataset` declares the slot *(low ×13)*

The core schema was consulted slot by slot, as the audit recommended. Where `CoreDataset` declares the slot, the content was lifted back out of `notes` into the declared structure; where it does not, the prose fallback was retained as correct.

**Restored to structured form:**

- `total_file_count: 356343` and `total_size_bytes: 3815969779678` — previously stated in prose inside `notes` as "356,343 files totalling 3,815,969,779,678 bytes (3.82 TB)". Both are declared integer slots. The prose sentence was removed from `notes`.
- `participant_compensation` — restored as a `HumanSubjectCompensation` object with `compensation_provided: true`, `compensation_amount: $200 USD`, `compensation_type`. Removed from `human_subject_research.notes`.
- `participant_privacy` — restored as a `ParticipantPrivacy` object with `anonymization_method`, the seven-item `privacy_techniques` list, `reidentification_risk` and `data_linkage`. The compressed paraphrase was removed from `is_deidentified.notes`.
- `third_party_sharing` — restored with `is_shared: true`. Removed from `license_and_use_terms.notes`.
- `collection_notifications` — restored with `notification_details` carrying the mailed-invitation and email text. The withdrawal content stayed in `informed_consent.withdrawal_mechanism`, where it was already correctly placed.
- `subsets` and `splits` — the three train/validation/test `DataSubset` objects (each with `id`, `is_data_split: true`, instance counts) and the `Splits` object were restored. The split table remains summarised in `notes` only insofar as it records the per-stratum balancing counts, which have no declared home.

**Prose fallback retained** (slot not declared in `CoreDataset`): `relationships`, `direct_collection`, `related_datasets`, `consent_revocations`, `variables`.

For `variables` in particular: the full record's 57 `VariableMetadata` objects are absent from the core record by schema design, not by omission. This is the largest single difference in content between the two records and is intentional.

### 4.3 Five negatives added, mirroring the full record *(medium)*

`extension_mechanism`, `data_protection_impacts`, `existing_uses`, `use_repository` and `labeling_strategies` were added with text identical to §3.2–3.6.

### 4.4 `license`, `conforms_to`, `hipaa_compliant`, `confidentiality_level` *(low)*

The same four edits described in §3.10–3.12 were applied, keeping the paired records in agreement.

---

## 5. What was left as-is, and why

### 5.1 Preserved source disagreements

The bundle contains six internal conflicts. Each is retained with both readings and an explicit note, rather than silently resolved:

| Conflict | Treatment |
|---|---|
| Acronym: "Artificial Intelligence Ready and **Equitable** Atlas" (BMJ, Nature Metabolism) vs. "**Exploratory** Atlas" (NIH RePORTER, FAIRhub study description, IRB) | Both forms recorded in dataset-level `notes`. `title` uses the FAIRhub official title. |
| Target enrolment: 4,000 (BMJ, Nature Metabolism, NIH RePORTER, FAIRhub) vs. 4,600 (IRB protocol) | Both recorded in `notes`; bears on `sampling_strategies`. |
| Follow-up fraction: 10% (NIH RePORTER, README) vs. ~4% (healthsheet collection Q5) | Recorded in `notes` and again in `known_limitations[1].notes`. **The duplication was retained deliberately** — the `notes` entry is part of the enumerated conflict list, the limitation entry is where a reader assessing longitudinal coverage will look. |
| `STUDY00016228` described as a "Clinicaltrials.org approval number" in the BMJ abstract but as the UW IRB approval number elsewhere in the same paper | The IRB reading is used; the abstract's mislabelling is noted. |
| Collection start: 2023-07-18 (BMJ, "Enrolment began on 18 July 2023") vs. 2023-07-19 (FAIRhub metadata) | Both retained across `collection_timeframes[0]`–`[2]`, flagged in `timeframe_details`. |
| De-identification: `deIdentType: NoDeIdentification` and `deIdentHIPAA: true` in the same FAIRhub block; healthsheet Q13 blank | Both retained in `is_deidentified.method`; reconciled in `deidentification_details` by the bundle's own explanation that no identifiers were collected. |

### 5.2 `errata` left unpopulated

Healthsheet maintenance Q3 ("Is there an erratum?") has an **empty response string** — the question was left unanswered, not answered in the negative. This is materially different from the five negatives added in §3.2–3.6, each of which carries an explicit "No". Populating `errata` here would convert silence into a claim.

The same reasoning applies to healthsheet composition Q13 (de-identification measures) and preprocessing Q1, both blank in the source.

### 5.3 `citation` left unpopulated

Both the FAIRhub record and the license point to `docs.aireadi.org/docs/3/citation` rather than supplying citation text. Under the v2 rule — *a value recording that documentation exists elsewhere has not answered the field* — a pointer is not a citation. The `docs.aireadi.org` URL is recorded in `external_resources`, where a pointer is the appropriate content.

### 5.4 `annotation_analyses`, `machine_annotation_tools`, `imputation_protocols` left unpopulated

- `annotation_analyses` — no annotation was performed, so there is nothing to analyse. The audit confirmed omission is correct.
- `machine_annotation_tools` — the OMOP Data Quality Dashboard is a quality-check tool, not an annotation tool. It remains under `cleaning_strategies`.
- `imputation_protocols` — the bundle supports only the negative "No imputation is applied", already carried in `missing_data_documentation[0].handling_strategy`, which is the field that asks for it.

### 5.5 `subpopulations[].subpopulation_elements_present: false` alongside populated `distribution`

The audit flagged this as a potential reader trap. It was retained: the flag correctly describes the **released artifact** (sex and race/ethnicity are withheld from the public release and held under controlled access), while `distribution` correctly reports counts the README publishes in its split-balancing summary. The `notes` on each entry explain the provenance of the counts. Changing the flag to `true` would misdescribe the release; dropping `distribution` would discard published counts.

### 5.6 `data_use_permission: disease_specific_research`

Retained. The audit correctly observed that a single enum cannot express both the T2DM-only access condition and the license's grant of "research and commercial purposes" (with `consentNoncommercial: false`). The more restrictive value was kept because it describes the binding access gate, and `notes` records the commercial grant that the enum cannot carry. No permitted value expresses the conjunction.

### 5.7 `publisher: https://fairhub.io/`

Retained. `publisherName: FAIRhub` is what the FAIRhub metadata's `publisher` field states. The ROR-identified `managingOrganization` (Washington University in St. Louis, `https://ror.org/01yc7t268`) is a different field describing a different role, and is recorded in `creators[0].notes`. Substituting the managing organisation for the publisher would conflate two distinct source assertions.

### 5.8 `issued: 2025-11-17T00:00:00Z`

Retained. The declared range is `datetime`, which requires a time component; the bundle supplies only the date `2025-11-17` (corroborated by the epoch `1763366400`). The synthesised midnight-UTC component is a type-conformance artifact, not an evidence claim.

### 5.9 `id` and derived subset fragment URIs

Retained. `https://doi.org/10.60775/fairhub.3` is the dataset DOI. The `#split-train` / `#split-val` / `#split-test` fragments (and the `#retinal_oct`-style fragments now used in core `file_collections`) are minted by the generator to give required `id` values to `DataSubset` and `FileCollection` objects. They satisfy the `uriorcurie` range but do not resolve, and should not be treated as citable identifiers.

### 5.10 `keywords` — ten terms retained

Seven come from the FAIRhub dataset-level `subject` list, three from the study-level `keywordList`. The audit flagged the merge of two vocabularies as a minor conflation. All ten are bundle-supported and the slot is a flat string list with no provenance sub-structure, so no distinction is expressible. Deduplication of the repeated "Retinal imaging" was retained.

### 5.11 `created_by: AI-READI Consortium`

Retained despite duplicating `creators[0].principal_investigator`. Both are directly supported by the FAIRhub creator block (`creatorName: AI-READI Consortium`, `nameType: Organizational`), and the two slots answer different questions.

---

## 6. Cross-record consistency after reconciliation

| Property | Full | Core | Agree |
|---|---|---|---|
| Referent | v3.0.0, `10.60775/fairhub.3` | same | ✓ |
| `id` | `https://doi.org/10.60775/fairhub.3` | same | ✓ |
| Participant count | 2,280 | 2,280 | ✓ |
| File count | 356,343 | 356,343 | ✓ |
| Total bytes | 3,815,969,779,678 | 3,815,969,779,678 | ✓ |
| Collection window | 2023-07-19 → 2025-05-01 (with 07-18 variant noted) | same | ✓ |
| `license` | `AI-READI custom license v2.0` | same | ✓ |
| `at_risk_populations` shape | single object | single object | ✓ |
| File-group construct | `file_collections` | `file_collections` | ✓ |
| `hipaa_compliant` | `not_applicable` | `not_applicable` | ✓ |
| `confidentiality_level` | omitted | omitted | ✓ |
| Five added negatives | present | present | ✓ |
| `variables` | 57 objects | absent (not declared in `CoreDataset`) | by design |
| `relationships`, `direct_collection`, `related_datasets`, `consent_revocations` | present | prose in `notes` (not declared) | by design |

No remaining factual disagreement between the paired records. The differences that persist are attributable to `CoreDataset` declaring a narrower slot set than `Dataset`.

---

## 7. Outcome

| Metric | Value |
|---|---|
| Full record — populated slots | **74** |
| Core record — populated slots | **51** |
| Full record — validates against `Dataset` | ✅ |
| Core record — validates against `CoreDataset` | ✅ |
| Audit findings | 38 (2 high, 12 medium, 24 low) |
| Findings acted on | 21 |
| Findings reviewed and left as-is with stated reason | 17 |
| Prior-D4D factual reuse | none — no previously generated record was read or consulted |
| Reconciliation | **complete; records consistent** |