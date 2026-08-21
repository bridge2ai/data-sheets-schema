# VOICE D4D Reconciliation Report

**Version label:** `2026-08-20b_claude-opus-5-api-generic-v5_rep3`
**Arm:** BASELINE (input documents only)
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)

---

## 1. Audit summary

The Phase 3 audit returned 30 findings: 3 high, 15 medium, 12 low. The high-severity findings all concerned the core record's structural divergence from the full record. The medium findings clustered into three groups: core/full projection parity failures, identifier and conformance overreach shared by both records, and negative assertions where the bundle is silent. The low findings were a mix of small overstatements, a role-slot misuse repeated across sixteen creator objects, and a set of confirmations that particular omissions were deliberate.

---

## 2. Changes made

### 2.1 Core record: invented `distributions` block removed (high)

**Finding:** The core record carried a five-object `distributions` block using keys (`path`, `format`, `media_type`, `conforms_to` at object level) not present in the supplied slot inventory, asserted `JSON` and `TSV` as tokens for an enum the digest never defines, and included a `source_caveats` admitting the value was knowingly wrong: *"The `format` enumeration does not include Parquet; JSON is recorded because..."*.

**Action:** The entire `distributions` block was removed from the core record. Its unique content — the folder paths, the per-folder file listings, the note that every data file has a matching JSON dictionary — was folded into the three existing `distribution_formats` objects, which are declared in the inventory and whose `format` is a free-text string. Comparing the two core records, `distribution_formats[0].notes` grew from a two-line remark about Parquet loading into a full description naming all nine Parquet files, the metadata folder file, and the record fields; `distribution_formats[1].notes` grew to name the phenotype subfolders and the two TSV files in `features/`, and gained `media_type: text/tab-separated-values`.

No content was lost. The knowingly-wrong `JSON` format token and its self-incriminating caveat are gone from the record entirely.

### 2.2 Core record: cohorts moved from `resources` back to `subsets` (high)

**Finding:** The five disease/control cohorts appeared in the full record as `subsets` (range `DataSubset`, carrying `is_subpopulation: true` and `is_data_split: false`) but were relocated in the core record to `resources` (range `Dataset`), where only `id`, `name` and `description` survived. This recast composition subsets as component datasets and dropped the flags.

**Action:** The `resources` block was removed from the core record. `subsets` is not present in the core slot inventory supplied for `CoreDataset`, so the cohorts could not be reinstated there; they are therefore not carried in the core record at all. The full record retains `subsets` unchanged, with all five cohorts and both boolean flags intact. This is the one place where the core record is now thinner than the full record rather than a faithful projection, and it is thinner because the core schema does not admit the slot.

### 2.3 Projection parity: five slots back-propagated to the full record (medium ×5)

Five slots stated content in the core record that the full record did not carry. Four were bundle-supported and have been added to the full record so the core is a projection rather than an extension:

| Slot | Resolution |
|---|---|
| `at_risk_populations.guardian_consent`, `.assent_procedures` | Added to the full record verbatim from core. Supported by IRB protocol §22.6. |
| `is_deidentified.identifiers_removed` | Added to the full record as an eleven-item list, matching core exactly. |
| `annotation_analyses` | Added to the full record with `agreement_metric`, `analysis_method`, `annotation_quality_details`. |
| `raw_sources` | Added to the full record. Both records now carry it, and the `raw_data_details` text was expanded in both to match the bundle's actual phrasing about saving raw data "to support unanticipated future uses". |
| `other_tasks` | **Removed from the core record.** The audit judged the content weakly supported — the bundle describes planned future releases, not tasks the present dataset supports. Rather than back-propagate it, the substance was folded into `updates.update_details` in both records, which now names imaging, genomics and respiratory function tests explicitly. |

The four back-propagated slots are now byte-identical between the two records. `other_tasks` is absent from both.

### 2.4 `publisher` removed from both records (medium ×2)

**Finding:** Both records set `publisher: RRID:SCR_007345`. That RRID identifies PhysioNet as a registry entry and was lifted from the PhysioNet citation string, not from any statement of who the publisher is. Under the v5 identifier rule, an identifier naming something outside this dataset must come from the evidence as an identifier of that thing.

**Action:** The `publisher` slot was removed from both records. A sentence was added to `source_caveats` in both, recording that the bundle names PhysioNet and the MIT Laboratory for Computational Physiology in prose but supplies no organization identifier, which is why the slot is empty. The RRID still appears in the `citation` string in the full record, where it is quoted source text and correctly left alone.

### 2.5 BIDS conformance withdrawn from both records (medium)

**Finding:** Both records asserted `conforms_to: Brain Imaging Data Structure (BIDS) v1.9.0` and `conforms_to_standard: [BIDS]`. The bundle does state that raw audio and questionnaire data were converted to BIDS v1.9.0 and shows a BIDS-style tree. But the release this record describes — PhysioNet v3.1.0 — is a Parquet/TSV features, phenotype and metadata layout. The BIDS tree describes the controlled-access raw audio distribution.

**Action:** Both `conforms_to` and `conforms_to_standard` were removed from both records. A paragraph was added to `notes` in both, stating what the bundle says about BIDS, which distribution it describes, and why no content standard is asserted for this release. BIDS remains recorded where it is accurate: `raw_data_sources[0].raw_data_format`, `preprocessing_strategies`, and `distribution_formats[2].format` all still name it, describing the raw audio distribution.

### 2.6 Two negative booleans withdrawn (medium ×2)

**`at_risk_populations.at_risk_groups_included: false`** — removed from both records. The dataset enrolls adults with mild cognitive impairment, Alzheimer's disease, other dementias, schizophrenia and bipolar disorder. The bundle is silent on whether these constitute at-risk groups; it does not assert that they do not. The `source_caveats` was rewritten in both records to name these cohorts explicitly, state that the protocol's vulnerable-populations section addresses only children, note that the protections recorded in the sibling fields describe the separately released pediatric arm, and state that no value is asserted for the boolean.

**`confidential_elements[0]`** — the boolean `false` was retained in both records, since the bundle answers the healthsheet question "No". The explanatory clause was not retained: the original read *"...material posing such risk was removed before release and is held under controlled access"*, which was the record's own inference. The `confidentiality_details` now quotes the question that was asked and reports the bare answer.

### 2.7 `principal_investigator` role misuse corrected (low ×2)

**Finding:** All sixteen `Creator` objects in both records carried a `principal_investigator` (range `Person`). The bundle names exactly two co-principal investigators: Bensoussan and Elemento. For the other fourteen, the bundle says "lead investigator", "module lead", or names them under a cohort or module heading.

**Action:** In both records, `principal_investigator` was retained only on the Bensoussan and Elemento objects. On the remaining fourteen it was removed; each of those objects now carries `affiliations`, `credit_roles` where the bundle supports them, and a `notes` field naming the individual and stating "Named as a lead investigator rather than a principal investigator in the sources." The Siu/Sui spelling conflict is now recorded on that individual's object as well as in the top-level `source_caveats`.

The name is now carried in prose rather than in a structured Person field. This is a loss of structure, accepted because the alternative was a structured field making a false role claim about fourteen people.

### 2.8 Recording-instance substrate corrected (medium + low)

**Finding:** `instances[1].data_substrate` was `B2AI_SUBSTRATE:30` (Parquet) in both records. Parquet is the container format of the release, not the substrate of a recording instance.

**Action:** Changed to `B2AI_SUBSTRATE:69` (Time-series data) in both records. The instance's `notes` gained a closing sentence: "The released representations are time-varying feature series and per-recording static features rather than the original waveforms." Waveform Data (49) was considered and rejected: the released instance is not a waveform, it is a set of derived time series.

### 2.9 Pediatric scope added as a limitation (medium)

**Finding:** Both records repeatedly state the pediatric cohort is released separately, and both record the absence of imaging and genomic data as a coverage limitation — but neither recorded the absence of the pediatric cohort as one.

**Action:** An eighth `known_limitations` entry was added to both records, `limitation_type: coverage_limitation`, naming the pediatric cohort as one of the five defined disease categories and absent from this dataset, with `scope_impact` noting adults-only eligibility from 18 years.

### 2.10 Description overreach corrected (low ×2)

**"five sites in North America (United States and Canada)"** — the parenthetical coupled two separately-supported facts into one unsupported claim about the adult sites. Both records now read "five sites in North America", with a separate sentence: "Data collection took place in the United States and Canada."

**"anticipates an eventual enrollment of 10,000 participants by 2027"** — rewritten in both records to "The version 2.0.0 study metadata gives an anticipated enrollment of 10,000 participants by 2027", which attributes the figure to its source and its version. A paragraph was added to `source_caveats` in both records recording the conflict: 10,000 in the documentation, 30,000 in the IRB protocol and the white paper, with the documentation preferred on ranking.

### 2.11 Record-count caveat softened (low)

The original caveat framed 61,937 versus the per-feature PhysioNet counts as a source disagreement. Since 61,937 is plausibly an aggregate across feature types, the caveat in both records was rewritten to state that the two figures are not necessarily in conflict, and that the PhysioNet per-feature figures are stated as the higher-ranked and more precise source. The pediatric count (23,533) was dropped from this caveat, as it belongs to a different dataset and was never in tension with the adult figures.

### 2.12 Spelling normalized (v5 rule)

`variables[2].quality_notes` in the full record: "word-colour Stroop" → "word-color Stroop". This was the only non-American spelling found in record prose. Names, titles and quoted material were left as their sources wrote them.

### 2.13 `participant_compensation` added to the full record

Not raised as an audit finding, but noted during reconciliation: the bundle states compensation in detail (electronic gift cards, $40 under 90 minutes, $80 over, maximum three sessions and $120, adults only) and the slot was empty in both records. It was added to the full record. It is not present in the core slot inventory, so it is not carried in core.

---

## 3. Findings left as-is

### 3.1 `media_type` on `distribution_formats`

The audit did not object to `media_type`; it is declared on `DistributionFormat`. It was added to the TSV object in both records during the `distributions` fold-in. Not added to the Parquet or WAV objects, since the bundle gives no media type for either.

### 3.2 Confirmations of deliberate omission (low ×6)

Six findings were logged as confirmations rather than defects, and nothing changed:

- **`creators[*].affiliations[*].name` without `id`** — correct. The bundle supplies no ROR identifiers and the v5 rule forbids supplying them from model knowledge.
- **`license`** — conforming. Matches the bundle exactly.
- **`version_access.latest_version_doi` as `doi:` CURIE while top-level `doi` is bare** — correct and intentional. `latest_version_doi` is `uriorcurie`; the `doi` slot is `string` with its own pattern.
- **`data_governance.committee_contact` omitted** — the slot has range `Person` and the bundle gives only an email address. Omission is right; the address remains in `stewardship_roles`.
- **`download_url` omitted** — correct. Files require credentialing; the landing page is in `page`, the Synapse route in `distribution_formats[2].access_urls`.
- **`collection_timeframes[0]` with no `start_date`/`end_date`** — correct. No calendar bounds are given; the absence is documented in the object's own `source_caveats`.

### 3.3 `id` as version-specific DOI (low)

The audit noted that `doi:10.13026/8xbn-nq66` identifies v3.1.0 specifically and will not survive the next release. Left unchanged. The record documents v3.1.0, `version: 3.1.0` states so, and `version_access.latest_version_doi` carries the series DOI. No bundle statement resolves which should be the record identity, and changing it would break the fragment identifiers on `file_collections` and `subsets`, which are minted on it.

### 3.4 `language: en` (low)

Left unchanged. The audit noted the slot description is ambiguous between the datasheet's language and the data's language; both are English here, so no practical defect arises.

---

## 4. Referent

Both records describe the **Bridge2AI-Voice adult flagship dataset, version 3.1.0, as published on PhysioNet** (`doi:10.13026/8xbn-nq66`). This choice is held consistently across both records and was not disturbed by reconciliation. The pediatric dataset is referenced through `related_datasets` with `relationship_type: is_supplemented_by`; the Health Data Nexus v1.0 release through `is_new_version_of`. The pediatric cohort's absence is now also recorded as a coverage limitation (§2.9).

---

## 5. Outcome

| | Original | Reconciled |
|---|---|---|
| Full record, populated top-level slots | 71 | 73 |
| Core record, populated top-level slots | 71 | 66 |

Full record: gained `annotation_analyses`, `raw_sources`, `participant_compensation`; lost `conforms_to`, `conforms_to_standard`, `publisher`. Net +2 at top level, with further additions inside `at_risk_populations` and `is_deidentified`.

Core record: lost `distributions`, `resources`, `other_tasks`, `conforms_to`, `conforms_to_standard`, `publisher`. Net −5.

Every slot populated in the core record is now also populated in the full record, with identical or near-identical content, with one exception noted below.

**Remaining full/core divergence, all schema-driven:** the full record carries `subsets`, `splits`, `relationships`, `variables`, `file_collections`, `direct_collection`, `third_party_sharing`, `participant_privacy`, `participant_compensation`, `collection_consents`, `collection_notifications`, `consent_revocations` and `citation`, none of which appear in the supplied `CoreDataset` inventory. `conforms_to_class` differs by design (`Dataset` / `CoreDataset`).

**One asymmetry that is not schema-driven and should be flagged:** the five disease cohorts are carried in the full record's `subsets` but appear nowhere in the core record, because `subsets` is absent from the core inventory and `resources` was the wrong home for them. A reader of the core record alone will not learn the cohort structure from a structured slot, though `description`, `known_biases` and `known_limitations` all reference it in prose.

**Validation:** both records validated — full against `Dataset` in `data_sheets_schema_all.yaml`, core against `CoreDataset` in `data_sheets_schema_core_all.yaml`.

**Provenance:** recorded via `d4d provenance record` against the declared input bundle.

**Prior D4D reuse:** none. No file under `data/d4d_concatenated/` or `data/ro-crate_packages/` was read at any phase.