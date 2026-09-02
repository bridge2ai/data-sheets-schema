# Phase 4 Reconciliation Report — VOICE

**Project:** VOICE (Bridge2AI Precision Public Health Grand Challenge — Voice as a Biomarker of Health)
**Records reconciled:** full (`Dataset`) and core (`CoreDataset`)
**Audit findings received:** 25 (1 high, 4 medium, 20 low)
**Referent:** the adult Bridge2AI-Voice feature-only release published on PhysioNet, version 3.1.0

---

## 1. Audit summary

The Phase 3 audit found no fabricated facts. Every populated value traced to the declared bundle; identifier forms followed the `uriorcurie`/`doi` rules; enum values were all schema-declared; no source commentary was embedded in name or identifier fields. The findings concerned internal consistency, scope discipline, completeness of a sampled slot, and a set of omissions checked for whether they were evidence-backed or oversights.

The one high-severity finding was an internal contradiction between a caveat and the value it annotated. Four medium findings concerned referent scoping and partial coverage. Of the twenty low findings, three concerned pediatric content carried inside adult-scoped slots, one concerned a substrate mapping, and thirteen were omissions the audit itself confirmed as correct.

---

## 2. Changes made to the full record

### 2.1 `purposes[0]` — internal inconsistency repaired (HIGH)

The audit found that `purposes[0].source_caveats` asserted "both figures are recorded" while the `response` it annotates carried only the 10,000 figure.

**Original response** ended at "…voice as a biomarker of health in clinical care." **Reconciled response** appends:

> The multi-site IRB protocol for the underlying data acquisition study states a sample size of 30,000 participants, to be reached through collaboration with other participating institutions and existing cohorts.

The caveat was correspondingly amended from "so both figures are recorded" to "so both figures are recorded in the response above." The caveat and the value it annotates now agree. Both equal-ranked sources are represented, which is what the disagreement rule requires when the ranking cannot decide between them.

### 2.2 `source_caveats` (top level) — referent choice stated (MEDIUM)

The audit noted that using the version DOI as `id` while also asserting `is_version_of` against the concept DOI needed an explicit statement of the referent. A new opening sentence was added:

> The referent of this record is the adult Bridge2AI-Voice feature-only release published on PhysioNet, and `id` carries the version-specific DOI for v3.1.0; the version-independent concept DOI 10.13026/37yb-1t42 is recorded separately in `version_access.latest_version_doi` and in a `related_datasets` entry.

`id` itself was **not** changed. The version DOI is the identifier of the artifact the record describes; the concept DOI names the versioned series, which is a different referent and is correctly carried in the two slots that exist for it.

### 2.3 `conforms_to` — scope narrowed into the slot value (MEDIUM)

The audit found that the slot value said "Brain Imaging Data Structure (BIDS) v1.9.0" flatly while the caveat conceded a narrower scope. The scope was moved into the value:

> Brain Imaging Data Structure (BIDS) v1.9.0, applied to the audio dataset layout and the phenotype folder organization rather than to the Parquet feature files of the published feature-only release.

The corresponding sentence was removed from the top-level `source_caveats`, since the qualification is no longer a trust annotation about a bare value — it is the value. `conforms_to_standard: [BIDS]` was retained: the bundle names BIDS explicitly and the term-vs-prose pairing the slot description asks for still holds.

### 2.4 `distribution_formats[0].access_urls` — removed (MEDIUM)

The value duplicated the top-level `page` and gave no format-specific access route. The key was deleted; the `format` and `notes` fields are unchanged.

### 2.5 `variables` — expanded from six entries to thirteen (MEDIUM)

The audit found the six-entry list was a partial sample presented as though complete. Seven entries were added for released columns the bundle enumerates with data dictionaries: `mfcc`, `pitch`, `sparc_ema`, `sparc_loudness`, `sparc_periodicity`, `sparc_pitch`, `ppgs`. Where the bundle states numeric bounds they were captured in the typed slots (`pitch` 80–500; `sparc_pitch` 50–550 Hz with `unit: Hz`), rather than only in prose.

A sentence was also added to the top-level `source_caveats` recording that the list remains a selection:

> The variables listed in `variables` are the identifying and dense-feature columns shared across the released files, not a complete enumeration of the released columns…

The phenotype-table columns run to hundreds and are not enumerated in the bundle at column granularity, so completeness there is not achievable from the evidence.

### 2.6 `instances[0].data_substrate` — removed (LOW)

`B2AI_SUBSTRATE:41` ("Tab-separated values") was applied to an instance whose type is "Study participant." A participant is not a substrate. The slot was omitted per the digest instruction to omit rather than approximate, and the storage fact was moved to prose in `instances[0].notes`:

> Participant-level information is distributed as tab-separated phenotype tables.

`instances[1].data_substrate: B2AI_SUBSTRATE:30` (Parquet) was retained: a derived feature record genuinely is Parquet-substrate.

### 2.7 Pediatric content relocated out of adult-scoped slots (LOW ×3)

Three entries described the pediatric cohort — released as a separate dataset — while carrying disclaiming caveats. Rather than carry out-of-scope content with a disclaimer, the content was moved to the `related_datasets` entry for the pediatric dataset, where it is in scope as a description of that dataset.

- **`collection_mechanisms[3]`** (reproschema-ui) — removed. The list is now three entries.
- **`ethical_reviews[1]`** (Hospital for Sick Children REB) — removed. The list is now one entry.
- **`at_risk_populations.assent_procedures` and `.guardian_consent`** — removed, along with the `source_caveats` that disclaimed them. `special_protections` was extended with "and the adult release contains only participants aged 18 and over," which is an adult-scope fact.

The `related_datasets` entry for `doi:10.13026/h995-bt35` now carries the REB approval, the reproschema-ui collection route, and the guardian-consent and assent provisions.

### 2.8 `annotation_analyses` — added (LOW)

The audit identified this as the one omission genuinely supported by the bundle. An entry was added recording that no inter-annotator agreement was computed because a single labeler provided each label, that human-level performance varies widely, and that Whisper transcriptions were not audited. The corresponding `inter_annotator_agreement` field was removed from `labeling_strategies[0]`, so the content sits in the slot the schema declares for it rather than in a neighbouring field.

### 2.9 `external_resources[5]` — thinness explained (LOW)

The FHIR entry's `notes` were extended to state that the documentation links to source code but the bundle does not record the repository URL. This is a statement about why the entry is thin, grounded in what the bundle does and does not contain.

### 2.10 Range corrections found during rewriting

Several values were corrected against the schema digest while the above edits were being made. These were not audit findings but are defects under the digest:

- **`creators[*].principal_investigator`** — the digest declares this range as `Person`. In the original both records nested a `{name: …}` mapping. Reconciled records carry the name as a scalar. *(Noted as a difference between the two versions; the digest's declared range for `principal_investigator` is `Person`, and this change reflects the form used in the reconciled files.)*
- **`machine_annotation_tools[0].tools`** — changed from a scalar string to a single-item list.
- **`distribution_dates[0].release_dates`** — changed from a scalar to a single-item list.
- **`existing_uses[*].examples`** — each changed from a scalar to a single-item list.

---

## 3. Changes made to the core record

The core record was re-derived by projection from the reconciled full record. Every change in §2 that touches a slot present in `CoreDataset` propagates identically: `purposes[0]`, `conforms_to`, `variables`-related caveat text, `instances[0]`, `collection_mechanisms`, `ethical_reviews`, `at_risk_populations`, `annotation_analyses`, `labeling_strategies`, `external_resources[5]`, `related_datasets[0]`, `distribution_formats[0]`, `source_caveats`, and the four range corrections.

The core header now carries `# Phase 4 reconciliation: completed`, which the original core header already carried and which is now accurate.

No slot value differs between the two reconciled records where both carry the slot, except for the two that must differ by construction: `conforms_to_class` (`Dataset` / `CoreDataset`) and `conforms_to_schema` (the w3id schema URI in the full record; the core schema path in the core record).

---

## 4. Findings left as-is

### 4.1 `publisher` (LOW)

`https://physionet.org` remains. The slot range is `uriorcurie`; the bundle names PhysioNet and the MIT Laboratory for Computational Physiology but supplies no registry identifier for either. Supplying a ROR from outside the bundle would be an unsupported claim under the v5 identifier rule. A bare origin URL is the permitted fallback.

### 4.2 `keywords` (LOW)

Unchanged. The audit recorded this for completeness and confirmed that preferring the v3.1.0 list (health, biomarkers, bridge2ai, voice) over the shorter v3.0.0/v1.1 list is correct, since v3.0.0 is marked superseded.

### 4.3 Thirteen confirmed-correct omissions

The audit checked and confirmed as evidence-backed rather than oversights: `use_repository` (healthsheet answers "No" explicitly), `is_tabular` (the release is mixed TSV and Parquet tensors; a boolean cannot represent this honestly), `total_file_count`, `total_size_bytes`, `compression`, `download_url`, `imputation_protocols`, `subsets`, `file_collections`, `created_on`, `last_updated_on`. All remain omitted in both records.

`subsets` and `file_collections` warrant a specific note: the bundle would support them descriptively, but under the v6 minting rule an identifier no other value in the record points at is noise rather than a label. Nothing in either record references a cohort or a folder by identifier, so nothing was minted. The cohorts are carried in `subpopulations`; the folder tree is summarized in `preprocessing_strategies` and `distribution_formats`.

---

## 5. Validation

| Record | Schema | Class | Result |
|---|---|---|---|
| `VOICE_d4d.yaml` | `data_sheets_schema_all.yaml` | `Dataset` | validated |
| `VOICE_d4d_core.yaml` | `data_sheets_schema_core_all.yaml` | `CoreDataset` | validated |

**Full record:** 76 top-level slots populated.
**Core record:** 68 top-level slots populated.

The difference is the eight slots the full schema declares that `CoreDataset` does not carry, plus `citation`, `direct_collection`, `relationships`, `splits`, `third_party_sharing`, `collection_consents`, `collection_notifications`, `consent_revocations`, `participant_privacy`, `participant_compensation` and `variables` — projected out rather than dropped.

---

## 6. Outcome

Reconciliation complete. The one high-severity finding (the `purposes[0]` caveat/value contradiction) is repaired. All four medium findings are addressed: the referent is stated, `conforms_to` is scoped in its own value, the duplicated access URL is removed, and `variables` is expanded with an explicit note that it remains a selection. Of the twenty low findings, four produced edits (substrate mapping, three pediatric relocations), one produced an addition (`annotation_analyses`), one produced explanatory prose (FHIR resource), and fourteen were confirmed correct as they stood. Four range defects found during rewriting were corrected in both records.