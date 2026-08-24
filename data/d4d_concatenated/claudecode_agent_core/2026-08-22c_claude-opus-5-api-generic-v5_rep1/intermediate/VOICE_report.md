# VOICE — Phase 4 Reconciliation Report

**Version label:** `2026-08-22c_claude-opus-5-api-generic-v5_rep1`
**Arm:** BASELINE (input documents only)
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)

---

## 1. Audit summary

The Phase 3 audit returned 29 findings: 2 high, 8 medium, 19 low. Two of the high findings were structural defects confined to the core record. One medium finding was a factual defect present in both records. Eleven medium/low findings were supported omissions in the core record — content the full record carried on plain bundle evidence that the core record simply dropped. The remainder concerned vocabulary fit, list-shape questions, an internally inconsistent boolean, and several correct-by-omission slots flagged only for completeness.

No unsupported factual claim was found. Identifiers, counts, dates, agreements and processing parameters all trace to the declared bundle, and the tier-1 PhysioNet v3.1.0 release is preferred throughout over the superseded v3.0.0 and over lower-tier sources.

---

## 2. Changes made

### 2.1 Core record: `distributions` removed (high)

The core record carried a top-level `distributions` slot holding three objects with keys `format`, `media_type`, `path`, `notes`, `source_caveats`. The schema digest for `Dataset`/`CoreDataset` lists no such slot. Two of the three entries additionally declared `format: JSON` / `media_type: application/json` for folders whose payload is Parquet — a mismatch the record's own `source_caveats` conceded rather than resolved.

**Action:** the `distributions` block is gone from the reconciled core record. Its content was folded into `distribution_formats`, which the core record already carried and which is a declared slot.

### 2.2 Core record: file-collection content recovered (high)

The full record's three `FileCollection` objects (`features/`, `phenotype/`, `metadata/`, with per-file record counts and tensor dimensions) had no counterpart in the core record; that content had been diverted into the removed `distributions` block.

**Action:** rather than reintroduce a `file_collections` block into the core record, the per-folder detail was merged into the corresponding `distribution_formats` entries. The Apache Parquet entry now enumerates all nine feature Parquet files with record counts and dimensions plus the `metadata/` Parquet file; the tab-separated-values entry now enumerates `static_features.tsv`, `audio_quality_metrics.tsv` and the full phenotype subfolder inventory; the JSON entry now explains the data-dictionary convention. Full and core now represent the same evidence in slots each schema declares.

### 2.3 Both records: cohort enumeration corrected (medium)

The core record's second `Subpopulation` object asserted that the five cohort categories are "voice disorders, respiratory disorders, neurological and neurodegenerative disorders, mood and psychiatric disorders, and controls." The project documentation names the fifth category as pediatric voice and speech disorders; controls are a separately recruited comparison group. The full record's `subsets` block carried the same substitution implicitly by presenting five entries, one of which was Controls, without flagging the pediatric category's absence.

**Action, core:** the `Subpopulation` `identification` field now names all five consortium categories including pediatric, and states that the pediatric category is published separately so that this release covers four adult disease cohorts plus separately recruited controls.

**Action, full:** each of the four disease `DataSubset` descriptions now ends "One of the consortium's five disease cohort categories." The Controls subset description now states explicitly that controls are a separately recruited comparison group rather than one of the five categories, and that the fifth category is published as a separate dataset. The `related_datasets` entry for the pediatric dataset now notes that it covers the fifth category. A sentence was added to the top-level `source_caveats` of both records explaining the arrangement.

### 2.4 Core record: eleven supported omissions repaired (medium/low)

The audit identified content the full record carried and the core record did not. Because the core schema is narrower, the repairs took two forms.

**Content placed in the slot the core schema declares:**

| Full-record slot | Core-record destination |
|---|---|
| `direct_collection` | folded into `acquisition_methods[0].acquisition_details` and `[2]` |
| `collection_consents` (consent scope) | folded into `informed_consent[0].consent_scope` |
| `collection_notifications` | folded into `informed_consent[0].notes` |
| `consent_revocations` (longitudinal case) | folded into `informed_consent[0].withdrawal_mechanism` |
| `participant_privacy` | folded into `is_deidentified.deidentification_details` |
| `participant_compensation` | folded into `informed_consent[0].notes` |
| `third_party_sharing` | folded into `distribution_dates[0].notes` |
| `splits` | folded into top-level `notes` |
| `relationships` + `variables` | folded into top-level `notes` |
| `subsets` (cohort detail) | folded into top-level `notes` |

The `notes` slot description directs residual content there only after every fitting slot is used; each of the four items routed to `notes` was checked against the core slot inventory first and has no declared home there.

**Content deliberately not carried across:** `citation`. The core schema digest supplied does not list `citation`. The full record retains it verbatim from the PhysioNet release.

### 2.5 Both records: `sensitive_elements` fourth object removed (low)

The fourth `SensitiveElement` object set `sensitive_elements_present: false` and then described what had been removed — an object flagged absent, inside a list of present elements, describing content the release does not contain.

**Action:** the object was deleted from both records. Its substance (removal of raw voice recordings as biometric identifiers, removal of REDCap-flagged sensitive fields) moved into `is_deidentified.deidentification_details` and `identifiers_removed`, where it describes de-identification rather than posing as a sensitive element.

### 2.6 Both records: `at_risk_populations.at_risk_groups_included` flipped to `true` (low)

The flag read `false` while `human_subject_research.special_populations` named cognitively impaired participants — MCI, Alzheimer's disease, other dementias — who are in scope for this adult dataset.

**Action:** the value is now `true` in both records. Two additional `special_protections` entries were added recording the neurological cohort's diagnosis and age constraints and the surgical-intervention exclusion, and the English-consent capacity requirement. The `source_caveats` now explains that the pediatric provisions are inherited from the consortium protocol while the `true` value rests on the MCI and dementia cohorts.

### 2.7 Both records: two B2AI substrate terms withdrawn (low)

`data_substrate: B2AI_SUBSTRATE:49` (Waveform Data) sat on an instance whose own prose says the release contains derived tensors, not waveforms. `data_substrate: B2AI_SUBSTRATE:80` (Questionnaire response data) sat on an instance spanning questionnaires, enrollment records and clinician-supplied diagnosis tables.

**Action:** both `data_substrate` assignments were removed from both records, following the instruction to omit rather than approximate. Each instance's `notes` now states why no term was asserted. The third instance was also renamed from "questionnaire and clinical record" to "participant questionnaire and clinical record" in both records. `data_topic` values were left in place; they fit.

### 2.8 Both records: `known_biases.affected_subsets` removed (low)

The `measurement_bias` object carried `affected_subsets: ['Disease cohorts recruited predominantly at a single site']`. The bundle states that participants were screened for different disorders based on site and that distinct devices were used per site; it does not state that any cohort was predominantly single-site.

**Action:** the `affected_subsets` key was deleted from both records. The `bias_description` is unchanged and still records what the bundle does state.

### 2.9 Both records: `collection_timeframes` decomposed (low)

The `timeframe_details` combined a twelve-month healthsheet figure with the NIH RePORTER award period, reading as one timeframe though the two describe different things.

**Action:** `timeframe_details` now carries only the healthsheet's twelve-month statement. The award period moved into `source_caveats`, labelled as the award period rather than a collection window. No `start_date` or `end_date` was added; the bundle supports neither.

### 2.10 Both records: `human_subject_research` list elements consolidated (low)

`regulatory_compliance` and `special_populations` held paragraph-length strings, and `special_populations` held three separate elements whose content the audit noted was better read together.

**Action:** `regulatory_compliance` now names HIPAA, the Common Rule and the Certificate of Confidentiality with a short gloss on the Certificate. `special_populations` was consolidated from three elements into one covering adult eligibility, the pediatric separation and the cognitively-impaired cohorts. Same in both records. `at_risk_populations.guardian_consent` was left as a single-element list; the digest does not settle whether it is multivalued, and the content is one coherent provision.

### 2.11 Both records: `data_governance` contact recorded (low)

`committee_contact` (range `Person`) was unpopulated while `DACO@b2ai-voice.org` appeared only inside `access_review_process` prose.

**Action:** `committee_contact` remains unpopulated — the bundle names no individual, and an email address is not a `Person`. A new `stewardship_roles` element now names the address explicitly, `access_decision_timeframe` was added recording that no timeframe is published, and a `source_caveats` was added to the object explaining why `committee_contact` and `committee_members` are empty.

### 2.12 Both records: `data_protection_impacts` annotated (low)

**Action:** a `notes` field was added to the second object recording the healthsheet's separate answer that no analysis of the dataset's potential impact on data subjects has been conducted — a statement that sits in tension with the DPIA-like activity the two objects describe, and which readers should see.

### 2.13 Both records: `description` cohort framing adjusted

**Action:** the `description` in both records no longer lists "controls" as one of five cohort categories. It now reads "spanning voice disorders, respiratory disorders, neurological and neurodegenerative disorders, and mood and psychiatric disorders, together with control participants who do not have the conditions of interest."

---

## 3. Findings left as-is

**`id` pinned to the version DOI (low).** `id` remains `doi:10.13026/8xbn-nq66` and `version_access.latest_version_doi` remains `doi:10.13026/37yb-1t42` in both records. Both are attested; the record describes version 3.1.0 specifically, and `version` is set to `3.1.0`. A sentence was added to `source_caveats` in both records noting the arrangement, but the values were not changed.

**`publisher` as a bare URL (low).** `publisher: https://physionet.org` is unchanged in both records. The slot range is `uriorcurie` and the v5 rule directs a CURIE where a declared prefix fits; no declared prefix covers PhysioNet as an organization, and the bundle contains no organization-registry identifier for it. Supplying one from outside the bundle would be an unsupported claim. The URL fallback stands.

**`download_url` unpopulated (low).** Unchanged in both. PhysioNet requires credentialing before files are exposed, and the Synapse location is a controlled-access landing point. Neither is a direct data URL.

**`total_file_count` and `total_size_bytes` unpopulated (low).** Unchanged in both. The bundle gives per-feature record counts but no file total and no byte total.

**`use_repository` unpopulated (low).** Unchanged in both. The healthsheet answers the corresponding question "No."

---

## 4. Referent

Both records describe the **adult flagship Bridge2AI-Voice dataset** as published on PhysioNet at version 3.1.0, DOI `10.13026/8xbn-nq66`. The Bridge2AI-Voice Pediatric Dataset (DOI `10.13026/h995-bt35`) is a distinct release with its own participant population and its own ethics approval; it is recorded under `related_datasets` in both records and is not merged. This choice is stated in the `source_caveats` of both records and is held consistently across them.

---

## 5. Source-conflict handling

| Conflict | Resolution | Recorded at |
|---|---|---|
| Recording count: ~61,937 (docs, tier 2) vs. 28,640–32,522 per feature (PhysioNet v3.1.0, tier 1) | tier 1 preferred; docs figure read as aggregating across feature types | top-level `source_caveats` |
| "Jennifer Sui" / "Frank Rudzizc" (docs) vs. "Jennifer Siu" / "Frank Rudzicz" (PhysioNet) | tier 1 spellings used | top-level `source_caveats`; object-level `source_caveats` on the Siu creator |
| Award number cited four ways across sources | core project number `OT2OD032720` used as grant identifier; the PhysioNet acknowledgement number recorded in `funders[0].notes` | top-level `source_caveats` |
| v3.0.0 vs. v3.1.0 | v3.0.0 is SUPERSEDED per the manifest; used only where 3.1.0 is silent | top-level `source_caveats` |
| Twelve-month collection window (healthsheet, tier 2) vs. 2022-09-01–2026-11-30 (RePORTER, tier 4) | not a conflict — different things; healthsheet figure kept as the collection window, award period recorded as such | `collection_timeframes[0].source_caveats` |
| Five cohort categories: pediatric (docs) vs. controls (as previously written) | docs preferred; controls recorded as a separate comparison group | top-level `source_caveats`, `subsets`, `subpopulations` |

---

## 6. Validation and provenance

| Item | Result |
|---|---|
| Full record populated slots | 68 |
| Core record populated slots | 62 |
| `linkml-validate` — full, class `Dataset` | pass |
| `linkml-validate` — core, class `CoreDataset` | pass |
| Provenance record written | yes |
| Prior D4D factual reuse | none — declared bundle and schema files only |

The core header now carries `# Phase 4 reconciliation: completed`.