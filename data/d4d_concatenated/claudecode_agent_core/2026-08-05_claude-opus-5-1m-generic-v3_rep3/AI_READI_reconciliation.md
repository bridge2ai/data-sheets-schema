# Reconciliation Report — AI_READI

**Version label:** `2026-08-05_claude-opus-5-1m-generic-v3_rep3`
**Arm:** BASELINE (input documents only)
**Records reconciled:** `AI_READI_d4d.yaml` (full, Phase 1), `AI_READI_d4d_core.yaml` (core, Phase 2)
**Audit input:** Phase 3 source/provenance audit — 45 findings (12 high, 20 medium, 13 low)

---

## 1. Referent

`Dataset` admits one referent. The referent is **the v3.0.0 release of "Flagship Dataset of Type 2 Diabetes from the AI-READI Project"** (DOI `10.60775/fairhub.3`, published 2025-11-17, 2,280 participants, 356,343 files, 3.82 TB).

This choice governs every reconciliation decision below. It is not the AI-READI *study* (target n=4,000, anticipated completion 2027-01-01), not the v2.0.0 release the input sheet originally selected, and not FAIRhub record 4 (the 100-participant "Mini Version"). Where the bundle supplies a fact about the study rather than the release, that fact was either relocated to a slot that genuinely concerns study conduct (`human_subject_research`, `collection_consents`, `ethical_reviews`, `sampling_strategies`) or dropped.

Both records now hold this referent consistently. Prior to reconciliation the full record's `description` blurred it, asserting the three-site single-visit protocol as a property of the release.

---

## 2. What the audit found

Four defect clusters, in descending order of consequence:

1. **Structural divergence between the two records.** The core record carried a `distributions` block that the schema digest does not declare, holding per-directory format assignments; the full record carried the same content in `file_collections`. Two records, one bundle, two shapes.
2. **Fabrication in `creators`.** The bundle declares exactly one creator — `{creatorName: "AI-READI Consortium", nameType: "Organizational"}`. Both records substituted twenty individuals harvested from a publication author list and a FAIRhub `overallOfficialList`, assigned each of them CRediT roles that appear nowhere in the bundle, and embedded source commentary inside affiliation strings.
3. **Synthesized structured values.** A collection timeframe assembled from two different sources; minted URI fragments; an invented time component on `issued`; one side of a live date conflict silently selected into a structured field while the conflict stayed in prose.
4. **`variables` without a data dictionary.** Twenty `VariableMetadata` objects with invented snake_case field names and constructed category sets, derived from a clinical protocol table rather than from any description of the released files.

Plus a long tail: slots populated with statements of absence, four slots present in core but not full, and a `has_part` relation the bundle's own curation note explicitly disclaims.

---

## 3. Changes to the full record

### 3.1 `creators` — reduced from 20 objects to 1

**Changed.** The slot now holds a single `Creator` for the AI-READI Consortium, with no `credit_roles` and no `principal_investigator` flag.

Rationale: `Creator` is defined as "individuals or organizations who created the dataset." The only statement in the bundle about who created *this dataset* is the `datasetDescription.creator` array, which has one organizational entry. The twenty individuals came from two other places — the Nature Metabolism consortium author list (authors of a comment article) and `studyDescription.contactsLocationsModule.overallOfficialList` (study officials). Neither source designates a dataset creator.

An intermediate option was considered and rejected: retaining the sixteen individuals whom FAIRhub labels `overallOfficialRole: "Study Principal Investigator"`, using `principal_investigator: true` and the declared ROR-identified affiliations, with no CRediT roles. That would be transcription for the role and affiliation fields, but the step from *study principal investigator* to *dataset creator* is itself the inference, and it is the inference the audit flagged. Under the guard's preference for omission over inference, the conservative reading stands.

Consequence recorded honestly: the record now names no individuals. PI identity survives only where the bundle attaches it to a specific declared function — `ethical_reviews.contact_person`, and the `human_subject_research` block.

The `credit_roles` deletion is the single largest fabrication removal in this reconciliation: twenty objects × three to five invented enum values each.

### 3.2 `variables` — removed entirely (20 objects → slot omitted)

**Changed.** The bundle contains no data dictionary, no column list, and no field-name inventory for the released files. It contains a *clinical laboratory table* in the BMJ Open protocol (test names, units, reference ranges) and a *directory inventory* in the FAIRhub structure description. Neither is a variable-level description of the dataset.

The removed objects had invented identifiers (`hemoglobin_a1c`, `visual_acuity_logmar`, `particulate_matter_pm2_5`) where the bundle says "HbA1c", and constructed category sets (`[sensate, insensate]`) where the bundle says participants answer "yes" or are "considered to be insensate". Reference ranges from the protocol table had been mapped onto `quality_notes` as though they were dataset quality metadata.

The `participants.tsv` and `participants.json` metadata files are named in the bundle, but their contents are not, so nothing survives.

### 3.3 `collection_timeframes` — 3 objects → 2, one synthesized span deleted

**Changed.** The object spanning `2022-09-01` to `2027-01-01` is deleted. Its start was the NIH RePORTER project start date; its end was the FAIRhub anticipated study completion. No source asserts that span. Combining a start from one document with an end from another manufactures a fact.

The remaining two objects:

- **Release collection window.** `start_date: 2023-07-19`, `end_date: 2025-05-01`, taken verbatim from `datasetDescription.date` where `dateType: Collected`. This is the release's own statement about itself and is the correct structured value for the chosen referent.
- **Study enrolment period.** `start_date: 2023-07-18`, `end_date: 2026-11-30`, from the BMJ Open protocol ("Enrolment began on 18 July 2023 and will continue until 30 November 2026"). `timeframe_details` records that this is the study-level enrolment window, not the release window, and that the protocol's 18 July start disagrees by one day with the release metadata's 19 July.

This resolves the audit's objection that one side of a live conflict had been selected silently: the two dates now appear in two separate objects attributed to their two sources, rather than one being chosen and the disagreement demoted to prose.

### 3.4 `file_collections` — retained, formats corrected, ids documented

**Changed in part.** The nine collections are retained (they are directly evidenced: directory name, description, `size`, `numberOfFiles`, and declared standard, all from `datasetStructureDescription`). Corrections:

- `conforms_to` values verified against the bundle. `cardiac_ecg` → WaveForm DataBase (WFDB). `clinical_data` → OMOP CDM. `environment` → NASA ASCII File Format Guidelines for Earth Science Data. `retinal_flio`, `retinal_oct`, `retinal_octa`, `retinal_photography` → DICOM. `wearable_activity_monitor`, `wearable_blood_glucose` → Open mHealth. All nine additionally conform to CDS v0.1.1 for their organization; this is recorded once at dataset level via `conforms_to` rather than repeated.
- `file_count` and `total_bytes` transcribed from `numberOfFiles` and `size`. These sum to 356,343 and 3,815,969,779,678, matching the dataset-level totals — verified, not asserted.
- `collection_type` set to `raw_data` only where the bundle supports it; otherwise omitted. Most collections hold processed, standard-mapped output, and the bundle states the true raw data "is not anticipated to be shared outside the project team right now." No collection is typed `processed_data` by inference.

**`id` is minted, and this is a structural necessity, not a claim.** `FileCollection` requires `id`; the bundle supplies no identifier for any directory. Ids are formed deterministically as `<dataset DOI URL>#<directoryName>`, where the directory name is the bundle's own verbatim value. The same applies to `DataSubset.id`. These fragments assert nothing about the dataset; they exist because the schema will not accept the object without them. No other slot was populated by minting.

### 3.5 `distribution_formats` — repopulated

**Changed.** Previously the object held only `access_urls`, restating the landing page already in `page` — answering the access question in the format field.

`DistributionFormat` declares only `access_urls` beyond the common slots, so the four declared media types (`application/dicom`, `text/markdown`, `text/csv`, `application/json`, from `datasetDescription.format`) are recorded in the object's `description`, with `access_urls` retained pointing at the FAIRhub dataset page. This is a schema limitation, not a modelling choice: there is no dataset-level format slot, and `compression` (the only adjacent slot) is inapplicable — no compression is declared anywhere in the bundle, so `compression` remains omitted.

The access *route* — verified-ID login, agreement to type-2-diabetes-only research use, agreement to licence terms, plus Azure Storage access mentioned in the v3 documentation — is recorded in `license_and_use_terms` and `regulatory_restrictions`, where it belongs.

### 3.6 `distribution_dates` — 1 object → 3

**Changed.** One object holding three dates in a single `release_dates` list could not associate a date with a version. Now three objects: v1.0.0 / 2024-05-03, v2.0.0 / 2024-11-08, v3.0.0 / 2025-11-17. Each `description` names the version. All three dates appear in both the FAIRhub HTML version list and the API `versions` array; the healthsheet's "May 2024 / November 2024 / November 2025" phrasing corroborates at month granularity.

### 3.7 `external_resources` — 1 object → 9

**Changed.** Ten heterogeneous URLs had been collapsed into a single object. Split into distinct objects: dataset documentation, project website, FAIRhub platform, Zenodo community, GitHub organization, CDS specification, Bridge2AI programme page, ClinicalTrials.gov registration (NCT06002048), NIH RePORTER project. The licence DOI moved out of this slot into `license_and_use_terms`, where it is the governing instrument rather than a related resource.

`archival` and `future_guarantees` populated only for the documentation, where the bundle addresses persistence and licensing (CC-BY 4.0, "no restrictions associated with its use"). Left empty elsewhere — the bundle makes no persistence guarantee for GitHub, Zenodo, or the project site.

### 3.8 `related_datasets` — `has_part` to fairhub.4 removed; declared relations added

**Changed.** The `has_part` relation to `10.60775/fairhub.4` is deleted. The bundle's curation note states directly: *"FAIRhub record 4 is a distinct 'Mini Version' (100 participants, DOI 10.60775/fairhub.4) for pipeline development, not a version of this dataset."* The API field `data.child: 4` is a platform link; it does not establish a part–whole relation, and the record had contradicted an explicit disclaimer in its own source.

Added, from `datasetDescription.relatedIdentifier`, which the previous record had ignored: `is_documented_by` → `https://docs.aireadi.org/`, `is_documented_by` → `https://aireadi.org/`.

Retained: `is_new_version_of` → `10.60775/fairhub.2`; `is_version_of` chain to `10.60775/fairhub.1`.

Retained but re-typed: the two publications were carried as `is_described_by`. The BMJ Open protocol describes the study design and the Nature Metabolism comment describes the project; neither is declared as a relation of the dataset record. They are now `is_documented_by`, and the reader is told in each object's description which document is which. This is a weaker, more defensible claim than `is_described_by`.

### 3.9 `subsets` — structure moved out of prose

**Changed.** The three splits (train 1,576 / validation 352 / test 352) previously carried their entire composition — race counts, sex counts, diabetes-status counts, mean age — inside free-text `description`. Under the v3 rule, content that answers a declared field belongs in that field. Each `DataSubset` now nests `subpopulations` objects carrying the race/ethnicity, sex, and diabetes-status distributions from the README table, with `is_data_split: true` and `is_subpopulation: false` set explicitly.

The split rationale (70/15/15, validation and test balanced as well as possible for sex, race/ethnicity, and diabetes status, because sex and race are withheld from the public release) is retained in `splits.split_details` — that is genuinely rationale, not composition.

### 3.10 `subpopulations` — flag semantics corrected

**Changed.** Two objects had set `subpopulation_elements_present: false` while reporting a full distribution — the flag denying what the object supplied. Set to `true` where a distribution is given. The fourth object (data collection site) is deleted: the bundle gives no per-site participant counts for v3.0.0, so neither `true` nor `false` is supportable and the object carried no distribution.

### 3.11 `is_deidentified` — boolean removed, declared fields populated

**Changed.** `identifiable_elements_present: false` contradicted the bundle's own `datasetDeIdentLevel`, which records `deIdentDirect: true` alongside `deIdentType: NoDeIdentification`. The two fields read against each other in the source, and the record had picked an interpretation.

The boolean is removed. In its place:

- `identifiers_removed`: PHI as defined by HIPAA; sex; race/ethnicity; medications — all four named explicitly in the README and the Nature Metabolism comment.
- `method`: HIPAA Safe Harbor, per the Nature Metabolism statement that the public set "is stripped of Protected Health Information (PHI) … via the 'Safe Harbor' method."
- `deidentification_details`: the verbatim `deIdentDetails` — no identifiers were collected, so no active de-identification was necessary, but the data were checked for HIPAA-identifiable content.

Note the tension retained rather than resolved: the healthsheet's de-identification question (composition #13) has an **empty response** in the bundle, and the preprocessing de-identification question (#1) is likewise empty. The record does not fill those silences.

### 3.12 `human_subject_research.irb_approval` — added

**Changed.** `STUDY00016228` had appeared only inside `ethics_review_board` prose in the full record while sitting in the declared `irb_approval` field in core. Now in the declared field in both. Initial UW IRB approval date 2022-12-20 recorded in `ethical_reviews`.

### 3.13 `known_biases` — enum values corrected

**Changed.** Three of six objects had used `selection_bias` for distinct phenomena. Retyped:

- Volunteer bias (protocol: "there is selection bias known as volunteer bias") → `selection_bias`, unchanged and directly quoted.
- English-language eligibility requirement → `representation_bias`.
- Documented difficulty recruiting Black men → `representation_bias`.

`affected_subsets` populated where the bundle names the affected group (Hispanic and Asian participants for the language requirement; Black men for the recruitment difficulty), omitted otherwise. Previously populated on one object of six.

### 3.14 Smaller corrections

| Slot | Change |
|---|---|
| `keywords` | Dropped "Type 2 Diabetes" (a `resourceTypeValue` and `conditionName`, not a keyword) and "Salutogenesis" (appears nowhere as a keyword). Seven FAIRhub `subject` values retained verbatim. |
| `issued` | `2025-11-17T00:00:00Z` → `2025-11-17`. The Z-offset was invented precision. |
| `status` | Removed. "published" is not in the bundle; FAIRhub's `overallStatus` is "Enrolling by invitation" and describes the *study*. |
| `is_tabular` | Removed. The bundle makes no such declaration, and the release is genuinely mixed — `clinical_data` is entirely tabular OMOP CSV, everything else is not. The boolean forced a judgement the evidence declines to make. |
| `conforms_to_schema` | Removed. It held the v0.1.0 metadata-file schema URL while `conforms_to` held CDS v0.1.1, producing an internal version conflict. `conforms_to` retained as the dataset-level statement. |
| `acquisition_methods` | `was_validated_verified: true` removed from the directly-observed object. The bundle evidences verification for participant-reported data (medication cross-referencing against physically brought or photographed medications) and says nothing about validating device measurements. Retained on the subject-reported object. |
| `sampling_strategies` | Second object (census framing, `is_sample: false`) deleted — the healthsheet answers the sampling-strategy question "N/A", so that framing was the record's own construction. First object retained: wave-based recruitment, EHR ICD-10 screening, triple balancing, `is_representative: false` with `why_not_representative` quoting the protocol on urban hospital-based recruitment and absent Pacific Islander and Native American representation. |
| `third_party_sharing` | `description` added from the healthsheet distribution answer ("The dataset will be distributed and be available for public use"). Previously `is_shared: true` with nothing else. |
| `funders` | Grant string reduced from a narrative blob to the identifier `OT2OD032644`. Award title, amount ($5,026,499), and project period had been packed into one string; `FundingMechanism` accepts only `grantor` and `grants`, so those three facts have no home and are dropped rather than smuggled. Second grantor entry retained for P30DK035816 and UL1TR003096, and Research to Prevent Blindness. |
| `publisher` | Retained as `https://fairhub.io`. The declared value is the *name* "FAIRhub"; the slot range is `uriorcurie` and will not accept a bare name. Flagged here as a range-forced construction. The separately declared `managingOrganization` (Washington University in St. Louis, ROR `01yc7t268`) is **not** used here — it is a different role. |

---

## 4. Changes to the core record

### 4.1 `distributions` — removed entirely

**Changed.** This was the most serious defect in either record, on two counts.

*Schema:* `distributions` is not in the `CoreDataset` slot inventory, and its member keys (`path`, `format`, `media_type`, `bytes`) are declared nowhere. The block would either fail validation or pass only by the schema being more permissive than the digest.

*Fact:* the format assignments contradicted the bundle. `cardiac_ecg` was given `format: JSON` where the bundle declares WaveForm DataBase (WFDB). `environment` was given `format: CSV` where the bundle declares the NASA ASCII File Format Guidelines. The four DICOM collections had no format at all. The dataset-level `format` array (`application/dicom`, `text/markdown`, `text/csv`, `application/json`) is a set covering the whole release; distributing its members across directories by guesswork produced two false statements and seven unsupported ones.

The content is now carried in `file_collections`, identically to the full record, with formats taken from each directory's declared `relatedStandard` rather than inferred.

### 4.2 Absence-statements removed (4 slots)

**Changed.** Four slots recorded that something does not exist. Under the v2 rule, a value stating absence has not answered the field; omission is the answer.

| Slot | Value removed | Bundle basis |
|---|---|---|
| `data_protection_impacts` | "No DPIA has been conducted" | Healthsheet collection #12: "No, a data protection impact analysis has not been conducted." |
| `existing_uses` | `examples: ["None. …had not yet been used for any tasks."]` | Healthsheet uses #1: "No" |
| `use_repository` | "no such repository exists" + `repository_url` pointing at the dataset landing page | Healthsheet uses #3: "No" |
| `extension_mechanism` | "no mechanism exists" | Healthsheet maintenance #7: "No, currently there is no mechanism…" |

`use_repository` was doubly wrong: it recorded an absence *and* supplied a URL for the wrong kind of resource (the FAIRhub dataset page is not a use-tracking registry), with view and citation counts attached.

These four removals also close four of the five full/core divergences, since none was present in the full record.

### 4.3 `at_risk_populations.at_risk_groups_included: false` — removed

**Changed.** Present in core, absent from full, and unsupported in either. The bundle lists exclusion criteria (pregnancy, gestational diabetes, type 1 diabetes) and a minimum age of 40; it makes no global determination about at-risk group inclusion. The remaining `at_risk_populations` content — no minors (age ≥40), pregnancy excluded, no prisoner population identified — is retained where the bundle states it.

### 4.4 `human_subject_research.irb_approval` — retained

**Not changed in core.** Core had this right; the full record was brought into line with it (§3.12).

### 4.5 Aggregate totals — added

**Changed.** `total_file_count: 356343` and `total_size_bytes: 3815969779678` added to core, matching full. Both are declared directly in the API response and verified against the sum of the nine per-collection values. Their previous absence from core alone was an unexplained divergence.

---

## 5. Cross-record alignment after reconciliation

| Divergence found in audit | Resolution |
|---|---|
| `distributions` (core) vs `file_collections` (full) | Core rebuilt on `file_collections`; both records now identical in shape and content for this material |
| `irb_approval` in core only | Added to full |
| `at_risk_groups_included` in core only | Removed from core |
| `data_protection_impacts`, `existing_uses`, `use_repository`, `extension_mechanism` in core only | Removed from core |
| `total_file_count` / `total_size_bytes` in full only | Added to core |

No factual claim now appears in one record and contradicts, or is absent from, the other where both records carry the relevant slot. Where core omits a slot the full record carries, the omission is a consequence of the core schema's narrower inventory, not a divergence in reading.

---

## 6. Left as-is, and why

**`citation` — omitted in both, deliberately.** The bundle supplies only a pointer: "please follow the citation instructions provided at `https://docs.aireadi.org/docs/3/citation`." Per the v2 rule, a value recording where information lives has not answered the field. The URL is captured in `external_resources` as the documentation resource; it is not laundered into `citation`.

**`download_url` — omitted in both.** No direct download URL exists. Access requires verified-ID login and self-attestation (`accessType: PublicDownloadSelfAttestationRequired`). The landing page is in `page`.

**`errata` — omitted in both.** The healthsheet question "Is there an erratum?" has an **empty response** in the bundle. Empty is not "no"; it is unanswered. Omission is correct on either reading.

**`annotation_analyses`, `labeling_strategies`, `machine_annotation_tools`, `imputation_protocols` — omitted in both.** The healthsheet answers the entire labeling section "N/A — no labels are provided… the dataset is a hypothesis-agnostic dataset aimed at facilitating multiple potential downstream AI/ML applications." No imputation is described anywhere. Verified-correct omissions.

**`compression` — omitted.** No compression is declared for any file or collection.

**`id` as the DOI URL — retained.** The audit noted `id` duplicates `doi`. This is intentional and correct: `id` requires a `uriorcurie` and the DOI URL is the dataset's genuine persistent identifier, present verbatim in the bundle. The alternative (`dataset_id: d894862f-0795-4ba6-b40b-fae14eb77813`) is an internal FAIRhub UUID with no resolution semantics. Duplication between `id` and `doi` is a schema artefact.

**`language: en` — retained.** Taken from `datasetDescription.language`, which describes the metadata and dataset language. The separate fact that participant communication was conducted in English (healthsheet inclusion #1) is recorded in `known_limitations` and `known_biases`, where it functions as an eligibility constraint, not a metadata property.

**`license: "AI-READI custom license v2.0"` — retained.** See §7 for the unresolved conflict with the FAIRhub HTML capture.

**`purposes`, `addressing_gaps`, `tasks`, `anomalies`, `known_limitations`, `cleaning_strategies`, `collection_consents`, `consent_revocations`, `ethical_reviews`, `participant_compensation`, `collection_notifications`, `preprocessing_strategies`, `raw_sources`, `instances`, `relationships`, `maintainers`, `updates`, `retention_limit`, `version_access`, `discouraged_uses`, `prohibited_uses`, `future_use_impacts`, `confidential_elements`, `sensitive_elements`, `content_warnings`** — all retained substantially as generated. The audit found no fabrication in these. They draw on healthsheet answers and protocol text that state the relevant facts directly, and the generated values transcribe rather than infer. Minor edits only: quoted phrasing tightened to match source wording where paraphrase had drifted.

---

## 7. Conflicts held, not resolved

These are genuine disagreements between sources in the declared bundle. The records represent the disagreement rather than selecting a side.

**Managing institution.** FAIRhub `datasetDescription.managingOrganization`, `studyDescription.leadSponsor`, and every `overallOfficialAffiliation` for the two Lees give **Washington University in St. Louis** (ROR `01yc7t268`). Every publication in the bundle, the NIH RePORTER record, the IRB protocol, and the FAIRhub `locationList` give **University of Washington** (ROR `00cvxb145`), Seattle. The BMJ Open protocol names UW as the IRB of record; NIH RePORTER lists UNIVERSITY OF WASHINGTON as the awardee organization; the licence agreement names "UNIVERSITY OF WASHINGTON ('Licensor')". This is almost certainly a data-entry error in the FAIRhub study metadata, but "almost certainly" is inference. Recorded in `description` and in this report; not silently corrected, and no longer embedded as commentary inside `creators.affiliations` (§3.1).

**Licence name.** `datasetDescription.rights.rightsName` gives **"AI-READI custom license v2.0"** (`https://doi.org/10.5281/zenodo.17555036`). The FAIRhub HTML capture gives **"Health Data License"**. The bundle also contains the full text of **AI-READI-LICENSE-v1.0** (Zenodo `10.5281/zenodo.10642459`), which the v3 healthsheet supersedes with the v2.0 DOI. `license` carries the v3.0.0 `rightsName`; `license_and_use_terms.license_terms` records all three strings and their sources.

**Collection start date.** 2023-07-18 (BMJ Open protocol, enrolment start) vs 2023-07-19 (FAIRhub `dateType: Collected`). Both retained in separate `collection_timeframes` objects (§3.3).

**Target enrolment.** 4,000 (BMJ Open, Nature Metabolism, FAIRhub `enrollmentCount`, README) vs 4,600 (IRB protocol, in two places: the objectives narrative and the per-group table of 4 × 1,000 which itself sums to 4,000). The IRB document is internally inconsistent. Recorded in `known_limitations`; the release's actual n=2,280 is the only figure used in `instances`.

**Study completion.** 2025-08-31 (NIH RePORTER project end) vs 2026-11-30 (BMJ Open, enrolment end) vs 2027-01-01 (FAIRhub, anticipated completion). None is used as a structured date on the release.

**Documentation version.** The input sheet selects the v2.0.0 documentation and the v2.0.0 FAIRhub record; the bundle's curation notes instruct that v3.0.0 supersedes both and that the v2.0.0 record is marked "no longer accessible." The referent decision (§1) follows the curation instruction. v2.0.0 evidence is used only where it speaks to the v2.0.0 release, and is cited as such.

---

## 8. Residual limitations

- **No individual is named as a creator.** A conservative reading of `Creator` costs the record all twenty personal names, including the PI. This is a real information loss accepted in exchange for not asserting authorship the bundle does not assert.
- **No variable-level description survives.** The dataset is documented at directory and standard granularity only. Anyone needing field names must go to `docs.aireadi.org`.
- **`FileCollection.id` and `DataSubset.id` are minted.** Schema-required, bundle-unsupported. Flagged in §3.4 rather than presented as identifiers.
- **`publisher` is a constructed URI** for a declared name, forced by the slot's range (§3.14).
- **The healthsheet is itself a datasheet-style artefact.** The bundle's own curation note observes that material drawn from it "is closer to transcription than extraction." A substantial fraction of both records — most of `purposes`, `anomalies`, `collection_consents`, `preprocessing_strategies`, `updates`, `retention_limit` — originates there. This is not a defect, but it should temper any reading of these records as independent extraction.
- **Two healthsheet answers are empty** (composition #13 and preprocessing #1, both on de-identification). Neither silence is filled.

---

## 9. Outcome

| | Full | Core |
|---|---|---|
| Slots populated, Phase 1/2 | 74 | 46 |
| Slots removed in Phase 4 | 6 | 7 |
| Slots added in Phase 4 | 1 | 3 |
| Slots populated, final | 69 | 42 |
| Objects removed (fabrication) | 20 `variables`, 19 `creators`, 1 `collection_timeframes`, 1 `subpopulations`, 1 `sampling_strategies`, 1 `related_datasets` | 9 `distributions`, 19 `creators`, 20 `variables`, + as full |
| Objects added (splitting) | 2 `distribution_dates`, 8 `external_resources`, 1 `collection_timeframes` | as full |
| Enum values corrected | 2 (`known_biases.bias_type`) | 2 |
| Fabricated enum values removed | ~70 (`creators.credit_roles`) | ~70 |

**Validation:** both records re-validated after reconciliation.

```
linkml-validate -s data_sheets_schema_all.yaml -C Dataset      …/AI_READI_d4d.yaml       → PASS
linkml-validate -s data_sheets_schema_core_all.yaml -C CoreDataset …/AI_READI_d4d_core.yaml → PASS
```

**Reconciliation outcome: RECONCILED.** All 12 high-severity findings addressed by change. Of the 20 medium findings, 17 addressed by change and 3 addressed by explicit retention with stated reasons (§6, §7). Of the 13 low findings, 6 addressed by change and 7 retained as verified-correct omissions or range-forced constructions. No finding was dismissed without a recorded reason. The two records now hold the same referent, the same structure over the same evidence, and no claim in either that the declared bundle does not support.