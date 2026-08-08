# Reconciliation Report — AI_READI

**Records reconciled**

- Full: `data/d4d_concatenated/claudecode_agent/2026-08-05_claude-opus-5-1m-generic-v3_rep2/AI_READI_d4d.yaml`
- Core: `data/d4d_concatenated/claudecode_agent_core/2026-08-05_claude-opus-5-1m-generic-v3_rep2/AI_READI_d4d_core.yaml`

**Declared input bundle**: `data/preprocessed/concatenated/AI_READI_preprocessed.txt` (10 sources). No prior D4D record was consulted at any phase.

---

## 1. Declared referent

`Dataset` admits one referent. Both records take the referent to be **the Flagship Dataset of Type 2 Diabetes from the AI-READI Project, version 3.0.0, DOI `10.60775/fairhub.3`, published on FAIRhub 2025-11-17** — the current release the bundle's own version selector and API record describe.

Consequences of that choice, applied identically in both records:

- The v1.0.0 and v2.0.0 releases are represented through `version_access.versions_available` and `related_datasets`, not as the record's subject, even though the input sheet selects the v2 documentation and v2 FAIRhub page. The curation notes on both v3 sources instruct that v3 be preferred where the two disagree.
- The FAIRhub "Mini Version" (100 participants, DOI `10.60775/fairhub.4`) is a distinct dataset and appears only as a `related_datasets` entry typed `is_source_of`, matching `data.child: 4` in the API record.
- The AI-READI biorepository at UAB CCTS is an associated specimen collection, not part of the distributed data, and is therefore out of referent scope.

---

## 2. What the audit found

The audit returned 38 findings: 3 high, 12 medium, 23 low. No fabricated dataset fact was identified in either record; every finding concerns slot placement, schema conformance, structural granularity, or cross-record symmetry.

The three high findings all concern a single block in the core record — a `distributions` list whose slot name and member keys (`path`, `format`, `media_type`, `bytes`) do not appear in the schema inventory, whose per-directory `format` values are inferred rather than stated, and whose byte counts duplicate `resources`.

The medium findings cluster into four groups: source commentary embedded in `creators[].affiliations`; under-structured `creators` and `funders`; a supported negative finding (`data_protection_impacts`) present in one record and absent from the other; and four slots present in the full record and absent from the core.

---

## 3. Changes to the core record

### 3.1 Removed the `distributions` block (high — 3 findings)

The block was deleted in full.

Three independent grounds, any one sufficient:

1. **Not schematized.** `distributions` is not a declared slot of `CoreDataset`, and none of `path`, `format`, `media_type`, `bytes` is declared on any class in the schema. The slots that carry this content are `distribution_formats` (range `DistributionFormat`, which accepts only `access_urls`) and `file_collections` / `resources` (range `FileCollection` / `Dataset`, which accept `path`, `file_count`, `total_bytes`, `collection_type`). An undeclared block populates nothing and fails validation.
2. **Unsupported values.** The per-directory `format` assignments were not in evidence. The bundle states WaveForm DataBase (WFDB) for `cardiac_ecg`, which the block labelled `TXT`; NASA ASCII File Format Guidelines for `environment`, which it labelled `CSV`; and DICOM for `retinal_flio`, `retinal_oct`, `retinal_octa` and `retinal_photography`, which the block omitted entirely. The dataset-level `format` array in the FAIRhub API (`application/dicom`, `text/markdown`, `text/csv`, `application/json`) is declared once for the whole dataset and is not decomposed per directory. Assigning it per directory is inference, and the decision rules prefer omission to inference.
3. **Redundant.** The nine directories, their byte counts and file counts are already carried by `resources`, which conforms to a declared slot.

No information was lost: the directory inventory, sizes, counts and the standards each directory follows survive in `resources`.

### 3.2 Removed source commentary from `creators[].affiliations` (medium)

Two Creator objects — Aaron Y. Lee and Cecilia S. Lee — carried parenthetical source attribution inside the affiliation string:

> `Washington University in St. Louis (affiliation as recorded in the FAIRhub dataset and study metadata)`

The commentary was removed. Both affiliations are now recorded as bare institutional names, and because the bundle genuinely disagrees, **both** are listed rather than one being silently selected:

- `Washington University in St. Louis` — FAIRhub `studyDescription` (`leadSponsor`, `responsibleParty`, `overallOfficial` affiliations, ROR `01yc7t268`)
- `University of Washington` — NIH RePORTER organization for `OT2OD032644`; Nature Metabolism affiliation 4; BMJ Open affiliation 5; the license agreement, which names the University of Washington as Licensor

The disagreement is recorded here rather than in the record, because `Creator` declares `affiliations`, `credit_roles` and `principal_investigator` and no field for provenance annotation. Listing both values represents the evidence; annotating one value editorialises inside a field that is not for editorial content.

### 3.3 Added the organizational creator (medium)

`AI-READI Consortium` was added as a Creator. The FAIRhub dataset description declares it explicitly as the sole `creator`, with `nameType: Organizational`, and the FAIRhub landing page bylines the dataset to it. Its absence from `creators` — while sixteen individual PIs were listed — omitted the one creator the dataset's own metadata asserts. It previously appeared only in `created_by`, which answers a different question.

### 3.4 Restructured `funders` (medium)

Applied identically in both records; see §4.3.

### 3.5 Restored cross-record symmetry (medium)

`subsets` and `variables` were added to the core record, mirroring the full record's content from the same evidence (the README split table; the BMJ Open clinical-laboratory tables and the healthsheet device section). Their prior absence from the core dropped directly supported content for no stated reason.

`splits` and `relationships` are not in the `CoreDataset` slot inventory. Their asymmetry is therefore schema-driven, not a defect, and the full record carries them alone.

`data_protection_impacts` was retained in the core; the corresponding gap was closed in the full record instead (§4.4).

---

## 4. Changes to the full record

### 4.1 Removed source commentary from `creators[].affiliations` (medium)

Same two Creator objects, same remedy and same rationale as §3.2. Both records now carry identical Creator objects.

### 4.2 Added the organizational creator (medium)

Same addition and rationale as §3.3.

### 4.3 Restructured `funders` (medium)

The prior record grouped three distinct NIH awards under a single `FundingMechanism` with grantor `Bridge2AI Program`, and packed award number, title, amount, project period, core project number and application ID into one free-text `grants` string.

Two problems, both fixed:

- **Over-attribution.** Only `OT2OD032644` is a Bridge2AI award. `P30DK035816` and `UL1TR003096` are named in BMJ Open and Nature Metabolism as NIH grants supporting the work, with no Bridge2AI attribution anywhere in the bundle. The grantor is now recorded as `National Institutes of Health` — the attribution the bundle actually makes — with the Bridge2AI program association stated only against `OT2OD032644`, which the NIH RePORTER record and the FAIRhub `fundingReference.awardTitle` both support.
- **Distinct entities collapsed.** `Research to Prevent Blindness` is a separate funder named in the BMJ Open funding statement and is now a separate `FundingMechanism` object, per the v2 rule on multivalued ranges.

`FundingMechanism` declares only `grantor` and `grants`, so award number, title and identifiers remain packed within each `grants` string. That is a class limitation, not a placement error; the alternative is discarding the award metadata.

### 4.4 Added `data_protection_impacts` (medium)

The healthsheet, collection section Q12, asks whether a data protection impact analysis has been conducted and answers: *"No, a data protection impact analysis has not been conducted."* This is the exact question the slot asks, answered directly and negatively. The core record carried it; the full record did not. A `DataProtectionImpact` object with `impact_details` recording the negative finding was added to the full record. Both records now agree.

### 4.5 Removed the biorepository item from `known_limitations` (low, referent scope)

The BMJ Open protocol lists, under "Strengths and limitations of this study": *"A limitation of our biorepository is that there are a finite number of samples to share with scientists."*

This was typed `scope_limitation` in the prior record. It was removed. The biorepository is an associated specimen collection held at UAB CCTS; no specimens and no biorepository-derived data are part of the FAIRhub v3 release, which is the declared referent. The constraint limits the study, not the dataset. Retaining it would extend the record past the referent boundary declared in §1.

The remaining `known_limitations` entries — all concerning the released data — were left intact.

---

## 5. Left as-is, with reasons

### 5.1 `creators[].credit_roles` left unpopulated (medium)

`credit_roles` is declared with a controlled vocabulary and the bundle contains role language, but the language attributes roles to **authorship of publications about the dataset**, not to creation of the dataset:

- BMJ Open: *"CO is the guarantor. All authors are submitting authors. They meet the four criteria of the ICMJE Recommendations"* — generic ICMJE boilerplate applied uniformly to every author of the protocol paper.
- Nature Metabolism: *"The Writing Committee members created the first draft, which was reviewed, edited and approved by all the authors."*

Mapping paper-authorship credit onto dataset-creation credit is inference. The bundle also structures its personnel into Writing Committee, Principal Investigators, Research/Technical/Clinical Staff, Project Managers, Interns and NIH Program Scientists — a taxonomy that does not align with the CRediT enum. Populating `credit_roles` would require choosing a mapping the evidence does not supply, so the field stays empty.

### 5.2 `creators` restricted to Principal Investigators plus the Consortium (medium)

Beyond the sixteen PIs and the organizational Consortium creator, the bundle names roughly fifty further individuals across four staff categories. They are contributors to the project; the bundle nowhere asserts that they are creators of the dataset, and `Creator` provides no field to distinguish contributor grades. The PI list is what the FAIRhub `studyDescription` designates as `Principal Investigators`, and `principal_investigator` is a declared Creator field, so this population is directly supported.

### 5.3 `distribution_formats` retains only `access_urls` (medium)

`DistributionFormat` accepts exactly one field, `access_urls`. The bundle's explicit format evidence — `application/dicom`, `text/markdown`, `text/csv`, `application/json`, plus the per-directory standards WFDB, OMOP CDM, DICOM, Open mHealth and NASA ASCII — has no declared field on this class to occupy. The per-directory standards are carried on `resources` via `conforms_to`; the dataset-level MIME list has no home and is not represented. This is a schema limitation, recorded here rather than worked around by inventing a field (the error §3.1 corrects).

### 5.4 `download_url` omitted (medium)

The FAIRhub v3 page offers "Access this dataset", and the v3 documentation adds an Azure Storage access route. Neither is a URL that points directly at the data: the API's `accessType` is `PublicDownloadSelfAttestationRequired` and `accessDetails` requires verified-ID login, a research-scope attestation and license agreement before any download. The slot's description distinguishes the download URL from the landing page; what the bundle supplies is a landing page, and it is recorded in `page`.

### 5.5 `citation` omitted (medium)

The bundle supplies only a pointer: *"please follow the citation instructions provided at https://docs.aireadi.org/docs/3/citation"*. The citation string itself is not in evidence. The v2 rule forbids populating a slot with a pointer to where the information lives, so the slot is omitted. The pointer survives in `external_resources`, where documentation URLs belong.

### 5.6 `existing_uses` and `use_repository` omitted (low)

The healthsheet answers both questions with a bare "No" (uses Q1, Q3). `ExistingUse` accepts only `examples` and `UseRepository` only `repository_details` / `repository_url`; neither class has a field whose purpose is to record absence. Under prefer-omission, an unpopulated slot is the correct representation of "none". The same handling was applied to `errata`, whose healthsheet response is empty.

### 5.7 `labeling_strategies`, `annotation_analyses`, `machine_annotation_tools`, `imputation_protocols` omitted (low)

The healthsheet labeling section answers "N/A — no labels are provided" to every question, including the explicit *"no specific labeling was performed in the dataset, as the dataset is a hypothesis-agnostic dataset."* For imputation, the cleaning narrative mentions filling *"missing data that can be directly filed from other portions of an individual's record"*, but names no method, no affected variables and no validation. Omission is supported in all four cases.

### 5.8 `subpopulations[].subpopulation_elements_present: false` alongside a populated `distribution` (low)

The flag is `false` because the public release strips sex, race and ethnicity — stated in the Nature Metabolism comment, the v3 documentation and the dataset description. The counts in `distribution` come from the README split table, which reports the strata used to construct the balanced splits without shipping the labels. The `identification` field states this reconciliation explicitly. Left as-is: both halves are accurate and the apparent tension is a real property of the release.

### 5.9 `human_subject_research.special_populations` retains the 85-year upper limit (low)

The FAIRhub eligibility metadata lists `maximumAge: 85 Years` and an exclusion of *"Adults older than 85 years of age"*; the BMJ Open protocol and the healthsheet inclusion criteria state only "aged 40 and older". The record reports the 85-year figure and attributes it to the eligibility metadata, representing the disagreement rather than resolving it. Left as-is under the rule on disagreeing sources.

### 5.10 Third `collection_timeframes` entry carries no dates (low)

The object exists to record that the bundle disagrees on the enrolment window: BMJ Open gives 18 July 2023 to 30 November 2026 as the enrolment period, while the FAIRhub `date` field gives the v3 collection period as 2023-07-19 to 2025-05-01 and the `statusModule` gives an anticipated completion of 2027-01-01. The first two `CollectionTimeframe` objects carry the dated periods; the third carries the discrepancy in `timeframe_details`, which is a declared field. Using it this way is a mild stretch of the class's intent, but the alternative is dropping a real disagreement.

### 5.11 String-packing in `external_resources`, `version_access.versions_available`, `funders[].grants` (low)

Each of these classes declares a flat list of strings and no per-item structure — `ExternalResource` has no per-URL description field, `VersionAccess` no per-version type. Where an item has several attributes (a version's number, DOI, date, participant count and size), they are packed into one string. Forced by the classes; left as-is.

### 5.12 `publisher`, `id`/`doi`, `license` string forms (low)

- `publisher` is `https://fairhub.io`, coerced from `publisherName: "FAIRhub"` to satisfy the `uriorcurie` range. The `managingOrganization` (Washington University in St. Louis, ROR `01yc7t268`) has no corresponding slot and is not represented.
- `id` is `https://doi.org/10.60775/fairhub.3` and `doi` is the bare `10.60775/fairhub.3`; both satisfy their declared ranges. Subset and file-collection identifiers are minted as fragments on the `id` URI — a locally invented but stable convention, documented here.
- `license` embeds the rights URI parenthetically in the name string because `license` is typed as a plain string. `license_and_use_terms.license_terms` carries the URI separately.

### 5.13 `created_on`, `last_updated_on`, `modified_by`, `compression`, `conforms_to_class`, `parent_datasets`, `was_derived_from` omitted (low)

- The documentation footer's *"Last updated on Jun 4, 2026 by Eamon Dysinger"* pertains to the documentation site, not the dataset; recording it as a dataset modification would misattribute.
- The FAIRhub `created_at` timestamp (2025-11-17) is already carried by `issued`.
- No compression format is stated for the distributed data.
- `resourceTypeValue: "Type 2 Diabetes"` is weak support for `conforms_to_class` and was not used.
- `data.parent: null` in the API supports the absence of a parent dataset; the child is recorded in `related_datasets`.

### 5.14 Acronym expansion (low)

`description` renders the acronym as "Equitable/Exploratory" because the bundle disagrees irreconcilably: BMJ Open gives *"Artificial Intelligence Ready and Equitable Atlas for Diabetes Insights"*, while NIH RePORTER, the FAIRhub README and the healthsheet all give *"Exploratory Atlas"*. The slashed form is awkward but represents both readings rather than silently selecting one. Left as-is.

---

## 6. Cross-record consistency after reconciliation

| Item | Full | Core | Status |
|---|---|---|---|
| Referent (v3.0.0, DOI `10.60775/fairhub.3`) | ✓ | ✓ | Aligned |
| `creators` (16 PIs + AI-READI Consortium, no embedded commentary) | ✓ | ✓ | Aligned |
| `funders` (NIH with three awards; Research to Prevent Blindness) | ✓ | ✓ | Aligned |
| `data_protection_impacts` (negative finding) | ✓ | ✓ | Aligned |
| `subsets`, `variables` | ✓ | ✓ | Aligned |
| `splits`, `relationships` | ✓ | — | Slot absent from `CoreDataset` |
| `distributions` | — | — | Removed; undeclared slot |
| Totals (`356,343` files / `3,815,969,779,678` bytes) | ✓ | ✓ | Aligned; consistent with per-directory sums plus 9 root metadata files |

No fact appears in one record and contradicts the other.

---

## 7. Validation

Both files validated after reconciliation:

```
poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset data/d4d_concatenated/claudecode_agent/2026-08-05_claude-opus-5-1m-generic-v3_rep2/AI_READI_d4d.yaml
→ PASS

poetry run linkml-validate -s src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml \
  -C CoreDataset data/d4d_concatenated/claudecode_agent_core/2026-08-05_claude-opus-5-1m-generic-v3_rep2/AI_READI_d4d_core.yaml
→ PASS
```

The core record failed validation prior to §3.1; the `distributions` removal is what cleared it.

---

## 8. Final state

| Metric | Value |
|---|---|
| Full record — top-level slots populated | 63 |
| Core record — top-level slots populated | 34 |
| Full record — validation | PASS |
| Core record — validation | PASS |
| Audit findings: high | 3 — all resolved |
| Audit findings: medium | 12 — 7 resolved, 5 left as-is with reasons |
| Audit findings: low | 23 — 1 resolved, 22 left as-is with reasons |
| Fabricated facts identified | 0 |
| Prior D4D records consulted | 0 |

**Outcome: reconciled.** The one schema-conformance failure and the one unsupported-value cluster were both in the core `distributions` block and were removed together. Placement and structure defects in `creators` and `funders` were corrected in both records. The one substantive cross-record gap (`data_protection_impacts`) was closed by populating the full record from evidence the core already carried. Remaining findings are class-imposed limitations, judgment calls under prefer-omission, or genuine source disagreements represented rather than resolved — each recorded above with its reason.