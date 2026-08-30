# Reconciliation Report — AI_READI D4D Records

**Version label:** 2026-08-28c_claude-opus-5-api-generic-v7_rep1
**Records reconciled:** full (`AI_READI_d4d.yaml`), core (`AI_READI_d4d_core.yaml`)
**Bundle:** `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (md5 `0f3abb51a333555456bedd63891fcd99`)

---

## 1. Audit summary

The Phase 3 audit returned 45 findings, of which four were raised and withdrawn by the auditor on re-check (`conforms_to_standard` enum membership at the top level and on `file_collections`; the `errata` omission; the `imputation_protocols` borderline). Of the remaining findings, several were confirmations of conformance rather than defects (`data_governance.accountable_organization.id`, `data_collectors[*].role`, `compression`, `machine_annotation_tools`, `annotation_analyses`, `resources`/`parent_datasets`, `total_file_count`).

The substantive defects fell into five groups: an undeclared key on every `VariableMetadata` object; entity collapsing in `external_resources` and `creators`; enum values reasoned to rather than read off (`confidentiality_level`, `hipaa_compliant`); five supported omissions of stated negatives; and internal contradictions between sibling fields.

---

## 2. Changes made

### 2.1 `variables` — undeclared `description` key removed (high)

The audit found that `VariableMetadata` does not declare a `description` field. Checking the schema digest confirms this: the permitted fields are `variable_name`, `categories`, `data_type`, `derivation`, `examples`, `is_identifier`, `is_sensitive`, `maximum_value`, `measurement_technique`, `minimum_value`, `missing_value_code`, `notes`, `precision`, `quality_notes`, `source_caveats`, `unit`.

All eleven `description` keys were removed from the full record. Their content was redistributed into declared fields:

- `cgm_glucose` — description folded into `measurement_technique`.
- `hba1c` — description folded into `measurement_technique`; the laboratory reference range (4.0–6.0%) moved from prose in `notes` into `minimum_value: 4.0` / `maximum_value: 6.0`, with a `notes` clarification that these are the reference range and not the observed range.
- `heart_rate`, `oxygen_saturation`, `moca_total_score` — descriptions folded into `measurement_technique`.
- `best_corrected_visual_acuity_logmar` — description folded into `measurement_technique`; the Snellen-drop note moved from `notes` to `quality_notes`.
- `contrast_sensitivity_logcs` — description folded into `measurement_technique`.
- `diabetes_status_group`, `recommended_split`, `race_ethnicity`, `zip_code_5_digit` — descriptions folded into `notes`.

A `source_caveats` was added to the last variable object recording that the eleven variables are exemplars rather than the complete inventory, addressing the separate coverage finding.

### 2.2 `external_resources` — six-into-one and four-into-one collapses split (high/medium)

The original carried two objects: the first packing six distinct resources into one prose string, the second packing two publications plus a trial registration and a grant record. The reconciled record carries **ten** objects, one per entity: the documentation site, the project website, the Zenodo community, the GitHub organization, the CDS specification, the license record, the Nature Metabolism comment, the BMJ Open protocol paper, the ClinicalTrials.gov registration, and the NIH RePORTER project record. The CC-BY restriction and the self-containment note stayed with the documentation object, where they belong.

### 2.3 `creators` — affiliation corrected (high)

The original placed `name: AI-READI Consortium` in `affiliations[0]`, making the sole organizational creator an affiliation of an unnamed creator. The reconciled record places the affiliation the bundle actually attests — `ROR:01yc7t268`, Washington University in St. Louis, which FAIRhub gives as the affiliation of both Aaron Lee and the responsible party. A `notes` field now records that FAIRhub names "AI-READI Consortium" as the single organizational creator, and the `source_caveats` was rewritten to state that Aaron Lee is named as principal investigator of the study rather than as an individual creator.

### 2.4 `regulatory_restrictions` — two reasoned enum values withdrawn (medium)

Both `confidentiality_level: restricted` and `hipaa_compliant: compliant` were removed. The audit was right that these were argued to rather than transcribed: the only attested confidentiality label in the bundle is the RO-Crate's `HL7:2N (normal)`, which no permitted value carries, and the bundle nowhere makes a HIPAA compliance determination. Both attested facts were moved into `other_compliance`, and a `source_caveats` explains why the two enum slots are unpopulated.

The `regulatory_restrictions` list was also split from one prose entry into four, one per restriction (license reference, NIH GDS security standards, general legal compliance, storage-location constraint).

### 2.5 `ip_restrictions.restrictions` — one entry split into four (low)

The single long paragraph became four entries: title and ownership; derivative data; synthetic data; licensee models.

### 2.6 Five supported omissions of stated negatives recorded (medium)

Each of these is a fact the bundle states explicitly and the original record dropped:

- **`extension_mechanism`** — added, with `extension_details` recording that there is no mechanism for others to extend the dataset outside the project.
- **`existing_uses`** — added, recording the healthsheet's "No" answer.
- **`use_repository`** — added, recording the healthsheet's "No" answer plus the citation requirement.
- **`data_protection_impacts`** — added, recording that no DPIA has been conducted.
- **`labeling_strategies`** — added, recording that no labeling or annotation was performed, that no software was used, and that no guidelines exist for future label creation.

### 2.7 `subpopulations[0]` — boolean/content contradiction resolved (medium)

`subpopulation_elements_present` was changed from `false` to `true`. The object populates `distribution` with race/ethnicity, sex and diabetes-status counts; asserting that no subpopulation elements are present while enumerating them was internally inconsistent. `identification` was rewritten to name the three dimensions and to state that individual-level values are withheld from the public release. `distribution` now reports the overall counts for the release rather than duplicating the per-split table.

### 2.8 `sensitive_elements` — contradictory second object folded into notes (medium)

The original carried two objects with opposing booleans and nothing but free text to distinguish which release tier each described. Since the referent chosen for this record is the public v3.0.0 release, the second object was removed and its content moved into the `notes` field of the remaining object, explicitly labeled as describing a separate controlled-access tier that is not the dataset described here.

### 2.9 `subsets` — per-split counts moved out of `splits` prose (medium)

Three `DataSubset` objects were added (`#split-train`, `#split-validation`, `#split-test`), each with `is_data_split: true` and per-stratum counts. The fragment identifiers are minted on the dataset DOI, as the minting rule directs. `splits[0].split_details` was correspondingly trimmed to the split rationale and mean ages, with a pointer in `notes` to the `subsets` slot.

### 2.10 `instances[0]` — `data_substrate` added (medium)

`data_substrate: B2AI_SUBSTRATE:11` (DICOM) was added, DICOM being the substrate of the largest share of the release by both file count and volume. Because the slot is single-valued, the remaining substrates the bundle names are enumerated in `notes`, and a `source_caveats` records why only one term appears.

### 2.11 `collection_timeframes[0]` — end date semantics clarified (medium)

The date value is unchanged, but `timeframe_details` now states explicitly that the end date is the release cut-off rather than the end of study collection, which is ongoing. The `source_caveats` was extended to note the anticipated completion date of 1 January 2027.

### 2.12 `related_datasets[1]` — relationship type corrected (medium)

`is_new_version_of` → `is_version_of` for v1.0.0. v3.0.0 is the new version of v2.0.0; v1.0.0 precedes both, and the chained relation is now stated in the `description`.

### 2.13 `ethical_reviews[1]` — invented organization replaced with a person (medium)

`reviewing_organization: AI-READI ethics team` was removed. The RO-Crate's `ethicalReview` field names four individuals, not an organization. The object now carries `contact_person: {name: Camille Nebeker}` as the first-named reviewer, with the other three named in `review_details` and a `source_caveats` explaining that the class carries a single contact person.

### 2.14 `notes` — participant-facing content moved to `description` (medium)

The return-of-results procedures and the incidental-findings referral pathway were moved from `notes` into `description`, where they describe the dataset's collection context. The biorepository statement stayed in `notes` but was extended to say the biospecimens are to be made available separately under policies still in development. The "under review" banner and the FAIRhub beta status remained in `notes` as genuine residue.

### 2.15 Smaller changes

- **`license_and_use_terms.source_caveats`** — added, recording that FAIRhub gives `rightsName: "AI-READI custom license v2.0"` while the license document itself is titled "AI-READI DATA LICENSE AGREEMENT (Version 2.0)".
- **`acquisition_methods[0].source_caveats`** — added, explaining why `was_inferred_derived` is left unset.
- **`participant_compensation[0].compensation_amount`** — `USD 200` → `200`, with the currency moved into `compensation_type`; the IRB's note that the amount may change was added to `compensation_rationale`.
- **`at_risk_populations.special_protections`** — split from one entry into two (eligibility exclusions; transportation assistance), with the accessibility statement moved to `notes`.
- **`human_subject_research.irb_approval`** — the reliance-agreement sentence was folded in from `ethics_review_board`, which no longer duplicates it.
- **`data_governance`** — `committee_contact` added (`ORCID:0000-0002-7452-1648`, Aaron Lee), attested as central contact in the FAIRhub study metadata; `notes` rewritten accordingly.
- **`maintainers[0]`** — contact information moved from `maintainer_details` prose into `notes`.
- **`is_deidentified`** — `deidentification_details` now quotes the FAIRhub detail field that resolves the `deIdentDirect: true` flag, and `source_caveats` was rewritten to explain the flag rather than merely note it.
- **`source_caveats`** (top level) — item (3) extended to state that `errata` is omitted for the blank-answer reason; item (4) extended to say neither acronym expansion is used in the record's prose, resolving the orphaned-caveat finding; item (6) added, recording the file-size and file-count arithmetic inconsistencies present in the tier-1 source.

### 2.16 Core record

All of the above were projected into the core record, which carries every change: the `variables` slot is not in the core schema so no projection was needed there, but `creators`, `external_resources`, `regulatory_restrictions`, `ip_restrictions`, `subpopulations`, `sensitive_elements`, `instances`, `collection_timeframes`, `related_datasets`, `ethical_reviews`, `at_risk_populations`, `human_subject_research`, `data_governance`, `is_deidentified`, `maintainers`, `license_and_use_terms`, `acquisition_methods`, `description`, `notes` and `source_caveats` all match the reconciled full record. The five newly recorded negatives (`extension_mechanism`, `existing_uses`, `use_repository`, `data_protection_impacts`, `labeling_strategies`) were added to the core record. The `# Phase 4 reconciliation: completed` line was retained in the core header.

---

## 3. Findings left as-is

**Withdrawn by the auditor, no action taken:** the two `conforms_to_standard` enum findings (both re-checked as conforming — `CDS`, `WFDB`, `OMOP_CDM`, `DICOM`, `OPEN_MHEALTH`, `ESDS`, `RO_CRATE` are all permitted values), the `errata` finding, and the `imputation_protocols` finding.

**Confirmations of conformance, no change needed:** `data_governance.accountable_organization.id` (CURIE form, attested in FAIRhub); `data_collectors[*].role` (not enum-constrained per the digest); `compression` (correctly omitted); `machine_annotation_tools` and `annotation_analyses` (correctly omitted — no annotation was performed); `resources` and `parent_datasets` (correctly empty); `created_on`/`last_updated_on`/`modified_by`/`was_derived_from` (no independent timestamps attested); `description` (well-formed and grounded).

**`publisher`** — left as `https://fairhub.io/`. The finding is fair that a trailing-slash root URL is a weak identifier, but the bundle supplies only `publisherName: "FAIRhub"` with no registry entry, and no declared prefix covers it. Under the identifier rule, supplying a ROR for FAIRhub from outside the bundle would be an unsupported claim; the `uri` half of `uriorcurie` is the correct fallback.

**`file_collections[*].id`** — the ARK identifiers were retained. They are attested in the RO-Crate rather than minted, so the minting rule does not reach them, and the audit itself concluded they are "acceptable but inert."

**`instances[0].data_topic` single-valued flattening** — the audit noted that one Instance cannot carry multiple topics. The slot is single-valued and `B2AI_TOPIC:43` (Diabetes) is the correct primary term; splitting one participant-instance into several objects to carry more topics would misrepresent what an instance is.

**`human_subject_research` list-valued prose fields** and **`at_risk_populations.special_protections`** — the audit flagged these for range verification. The schema digest does not state their ranges, so no defect can be established from it; the list form was retained, and where the audit's concurrent point about entity collapsing applied (`special_protections`, `ip_restrictions.restrictions`, `regulatory_restrictions`), the lists were split into one entry per restriction, which is correct under either range.

**`maintainers[0].role: academic_institution`** — retained; the value is permitted by the `Maintainer.role` enum. The audit's separate point about the missing contact was addressed by moving that content into `notes`.

**`ethical_reviews[2].reviewing_organization`** — retained unchanged; the audit rated this low concern and the name is a reasonable rendering of what the BMJ and IRB sources state.

**`total_file_count` / `total_size_bytes` arithmetic** — the declared totals were retained. Both figures and the per-directory figures come from the same tier-1 source; the inconsistency is in the bundle, not the record, and is now disclosed in the top-level `source_caveats`.

**`variables` coverage gap** — the eleven variables were retained rather than expanded. The bundle names a full variable list only by reference to external documentation not included in the bundle; the gap is now disclosed in `source_caveats` instead of being silently presented as complete.