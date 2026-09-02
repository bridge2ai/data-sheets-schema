# VOICE D4D Reconciliation Report

**Project:** VOICE (Bridge2AI Precision Public Health Grand Challenge — Voice as a Biomarker of Health)
**Records:** `VOICE_d4d.yaml` (full, class `Dataset`), `VOICE_d4d_core.yaml` (core, class `CoreDataset`)
**Label:** `2026-09-01_claude-opus-5-api-generic-v7_rep3`
**Arm:** BASELINE (declared input bundle only)
**Phase:** 4 — strict reconciliation following the Phase 3 source/provenance audit

---

## 1. Referent

The referent held throughout both records is the **adult Bridge2AI-Voice dataset, PhysioNet version 3.1.0** (`doi:10.13026/8xbn-nq66`, published 1 May 2026). This is the highest-ranked non-superseded source describing a released dataset in the bundle. The pediatric dataset (`doi:10.13026/h995-bt35`) is treated as a separate, related dataset rather than as part of this record; earlier versions (1.0, 1.1, 2.0.0, 2.0.1, 3.0.0) are recorded as prior versions via `related_datasets` and `version_access`. The referent was not changed during reconciliation and is consistent across both records.

---

## 2. Audit findings and dispositions

The Phase 3 audit returned thirteen findings against the full record: two major, three moderate, eight minor. Every finding was acted on. Nine produced changes to the records; four were addressed by adding or adjusting evidence-tracking prose rather than by altering a claim, and one (the `subsets`/`file_collections` pair) produced substantial new structure.

### 2.1 Major — `updates` emitted as a list (shape defect)

**Disposition: changed.**

The schema digest declares `updates` as single-valued, range `UpdatePlan`, with no `[many]` marker. The original full record emitted it as a YAML sequence:

```yaml
updates:
- frequency: Semi-annual, that is twice a year.
```

The reconciled full record emits it as a mapping:

```yaml
updates:
  frequency: Semi-annual, that is twice a year.
```

This was a validation-blocking defect: an array where the schema requires an object. Note that the **core record was not changed here** — the original core record already emitted `updates` as a list and still does in the completed core record. This is a residual inconsistency between the two records and is recorded below in §4.

### 2.2 Major — `creators` omitted despite attested authorship

**Disposition: changed.**

The original full record left `creators` empty and packed authorship into the free-text `created_by` string, which enumerated the two co-PIs and then listed eleven institutions in prose. The reconciled record adds a populated `creators` list with **eighteen entries**: seventeen named individuals each carrying a `principal_investigator` (a `Person` with `id` and `name`) and an `affiliations` list (each an `Organization` with `id` and `name`), plus a final unnamed entry recording that the PhysioNet v3.1.0 author list names 117 further contributors and that the consortium is credited collectively.

CRediT `credit_roles` were populated for six contributors (Bensoussan, Elemento, Sigaras, Rameau, Ghosh, Johnson), drawn from the author-contributions statement in the feasibility publication where that statement supplies them. Johnson's roles carry a `source_caveats` noting they are inferred from described project roles rather than from a CRediT statement.

Person and organization identifiers are minted as fragments on the dataset DOI (`doi:10.13026/8xbn-nq66#person-bensoussan`, `#org-usf`, and so on) — these are labels for entities this record refers to, not claims about registry entries the bundle does not supply. No ORCID or ROR identifiers were invented.

`created_by` was correspondingly shortened from the eleven-institution prose list to the two co-PIs, since the institutional detail now sits in the structured `affiliations` fields.

One creator entry carries a substantive source note: Ravitsky's affiliation is given as the University of Montreal in the feasibility publication and as The Hastings Center in the audiomics white paper and project documentation. Both are recorded in the entry's `notes`, with the more recent form used as the value.

The core record received the same eighteen-entry `creators` list and the same shortened `created_by`.

### 2.3 Moderate — unattested content warning

**Disposition: changed (value removed).**

The original records carried two warnings under `content_warnings[0].warnings`. The first asserted that phenotype tables cover "depression, suicidal ideation, anxiety, post-traumatic stress, substance use and psychiatric history, which some users may find distressing." The bundle's healthsheet answers the offensive/safety-risk question solely by reference to free-speech transcription and nowhere characterizes questionnaire content as a content warning; "suicidal ideation" in particular required outside knowledge of PHQ-9 item content, which the bundle never enumerates.

That warning was **removed** from both records. The surviving warning — about open-response free speech — is retained, and the accompanying `source_caveats` was rewritten to say the residual exposure in the released files "is limited to static features" rather than "to questionnaire content and static features," so the caveat no longer implies the removed claim.

### 2.4 Moderate — grant identifiers in `notes` rather than `grants`

**Disposition: changed.**

`FundingMechanism` declares `grants` with range `Grant[]`. The original record placed every award identifier into free-text `notes`. The reconciled record populates `grants` with four `Grant` objects, each with a minted fragment `id`, a `name` carrying the award number, and a `description` recording what that identifier is and where it appears:

- `#grant-ot2od032720` — core project number, with PI, organization and 2022-09-01 to 2026-11-30 project period
- `#grant-3ot2od032720-01s1` — the number in the PhysioNet acknowledgements
- `#grant-1ot2od032720-01` — the number in the feasibility publication
- `#grant-3ot2od032720-01s3` — the NIH RePORTER application, with application ID 11376382 and the 4,660,942 USD FY2025 amount

`grantor` was shortened to name the funder without the identifiers. A `notes` field now records the two apparently corrupted award strings in the documentation acknowledgement text, and a `source_caveats` records that identifiers differ across sources and are given as each source states them rather than normalized. The core record received the identical structure.

### 2.5 Moderate — `file_collections` omitted

**Disposition: changed.**

The bundle supplies explicit named directory trees for v3.1.0. The reconciled full record adds four `FileCollection` entries with `id`, `name`, `path`, `collection_type` and `description`:

- `#files-features` (`features`, `processed_data`) — the nine named Parquet files plus `static_features.tsv` and `audio_quality_metrics.tsv`, with `conforms_to` noting Parquet and TSV-with-JSON-dictionaries
- `#files-metadata` (`metadata`, `metadata`) — the per-recording Parquet and its dictionary
- `#files-phenotype` (`phenotype`, `processed_data`) — every named subfolder and table
- `#files-audio` (`b2ai-voice-audio`, `raw_data`) — the BIDS tree, with `conforms_to` and `conforms_to_standard: [BIDS]`

The core schema does not declare `file_collections`; the core record carries the equivalent content under its `distributions` slot, with the same four entries and the same minted identifiers.

### 2.6 Minor — inferred instance count

**Disposition: changed (value removed).**

`instances[1].counts` originally held `32522`, which the bundle states as the record count for `torchaudio_pitch.parquet` specifically, not as a recording total. The `counts` key was **removed** from that instance in both records. The per-feature counts are retained in `notes`, now prefixed with "The v3.1.0 release does not state a single recording total," and a new `source_caveats` records that the project documentation gives approximately 61,937 voice-derived recordings for v3.0 while the preferred PhysioNet v3.1.0 source gives only per-feature counts, so no aggregate value is recorded.

`instances[0].counts: 833` is directly attested in the v3.1.0 abstract and is unchanged.

### 2.7 Minor — non-resource entry in `external_resources`

**Disposition: changed.**

The seventh `ExternalResource` entry stated that the dataset "is self-contained and does not rely on external resources," with `archival: false`. This was a negative statement occupying a slot meant to name a resource. It was **replaced** with a genuine external resource: the Bridge2AI Voice Scholars training program at `https://www.b2aivoicescholars.org/`.

That URL was previously carried as a second example under `existing_uses[0].examples`, where it described a training offering rather than a use of the dataset. It was removed from `existing_uses`, which now carries only the Summer School and hackathon example. Both records reflect this move.

The Interspeech protocol publication entry also changed here — see §2.9.

### 2.8 Minor — inferred inter-annotator agreement

**Disposition: changed (wording).**

`labeling_strategies[0].inter_annotator_agreement` originally read "Not assessed; a single labeler provides one label per instance," asserting a fact about assessment the bundle does not state. It now reads "A single labeler provides one label per instance, so no inter-annotator agreement is reported" — which states the attested fact and the consequence that follows from it, without claiming an assessment decision.

### 2.9 Minor — inferred archival status

**Disposition: changed.**

`external_resources[5].archival: true` was asserted for the Interspeech publication on the strength of its ISCA archive URL, but the healthsheet answers the external-resource permanence questions with "NA". The `archival` key was **removed** from that entry and replaced with a `future_guarantees` field recording exactly what the healthsheet says.

The `archival: true` values on the two Zenodo-archived entries (`bridge2ai-redcap`, `bridge2ai-docs`) were retained: the bundle states a Zenodo DOI for each, which is a direct statement of archiving.

### 2.10 Minor — `accountable_organization` unpopulated

**Disposition: changed.**

`data_governance.accountable_organization` (range `Organization`) is now populated with the University of South Florida Board of Trustees, named in the Data Transfer and Use Agreement as the provider institution, carrying a minted fragment `id`. The `stewardship_roles` list, which previously ran as one long prose block, was split into four separate entries so that each distinct role occupies its own item. A `notes` field records NIH support and hosting-platform infrastructure. Both records received this.

### 2.11 Minor — tension between `errata` and `updates`

**Disposition: changed (wording, both slots).**

`updates.update_details` originally said "There is no separate erratum document," which read as contradicting a populated `errata` slot. It now says corrections "are communicated through a changelog published online with the dataset metadata for each version rather than through a separate erratum document" — the same fact, stated so it does not read as a denial of the errata content.

Each of the three `errata` entries gained a `source_caveats` recording that the entry is drawn from PhysioNet release notes rather than from a separate erratum document. Both records received these changes.

### 2.12 Minor — v1.0 release date missing

**Disposition: changed.**

`distribution_dates[0].release_dates` now opens with "End of November 2024 (version 1.0, on the Health Data Nexus)" before the five PhysioNet dates, and a `source_caveats` records that this date comes from the project documentation while the PhysioNet version list begins at v1.1. Both records received this.

### 2.13 Minor — `subsets` omitted despite defined cohorts

**Disposition: changed.**

The full record now carries eight `DataSubset` entries. Five describe the disease cohorts (`#subset-voice-disorders`, `#subset-respiratory`, `#subset-neurological`, `#subset-mood`, `#subset-controls`), each with `is_subpopulation: true`, `is_data_split: false`, and a `description` reproducing the Table 1 inclusion criteria, exclusion criteria and gold-standard validation methods. Three describe the release components (`#subset-features`, `#subset-phenotype`, `#subset-metadata`) with both flags false.

The core schema does not declare `subsets`; the core record does not carry these entries. The release-component information reaches the core record through the `distributions` entries described in §2.5. The cohort structure is present in the core record via `subpopulations` and the disease-cohort content already carried in `description`.

---

## 3. What was left as-is

- **Referent selection, version and DOI handling.** Unchanged in both records. `doi` carries the bare `10.13026/8xbn-nq66` per the slot's string range and pattern; `id` and `related_datasets` targets carry `doi:` CURIEs; `access_urls` (range `uri[]`) carry URLs.
- **Enum usage.** `DatasetBias.bias_type`, `DatasetLimitation.limitation_type`, `DatasetRelationship.relationship_type`, `LicenseAndUseTerms.data_use_permission`, `ExportControlRegulatoryRestrictions.confidentiality_level` and `hipaa_compliant`, `Maintainer.role`, `FileCollection.collection_type`, `conforms_to_standard`, and `Creator.credit_roles` all draw from their declared enumerations. No changes.
- **Required keys.** `RawDataSource.source_description` and `DatasetRelationship.relationship_type`/`target_dataset` were satisfied in the original and remain so. Every newly added `DataSubset`, `FileCollection`, `Grant`, `Person` and `Organization` object carries the required `id`.
- **Source-conflict handling.** The top-level `source_caveats` (v3.1.0 over v3.0.0; documentation and IRB co-ranked on enrollment target; hosting-platform discrepancy; redacted email addresses) is unchanged in both records. Per-slot caveats on `maintainers`, `preprocessing_strategies`, `data_protection_impacts` and `collection_timeframes` are unchanged.
- **All remaining slot content.** `purposes`, `tasks`, `addressing_gaps`, `anomalies`, `known_biases`, `known_limitations`, `missing_data_documentation`, `cleaning_strategies`, `preprocessing_strategies`, `machine_annotation_tools`, `raw_data_sources`, `acquisition_methods`, `collection_mechanisms`, `collection_notifications`, `collection_consents`, `consent_revocations`, `data_collectors`, `direct_collection`, `sampling_strategies`, `relationships`, `related_datasets`, `distribution_formats`, `third_party_sharing`, `intended_uses`, `discouraged_uses`, `prohibited_uses`, `future_use_impacts`, `maintainers`, `retention_limit`, `version_access`, `extension_mechanism`, `license_and_use_terms`, `ip_restrictions`, `regulatory_restrictions`, `is_deidentified`, `participant_privacy`, `informed_consent`, `human_subject_research`, `at_risk_populations`, `participant_compensation`, `ethical_reviews`, `data_protection_impacts`, `splits`, `subpopulations`, `sensitive_elements`, `confidential_elements`, and the header/identity block are all unchanged apart from the specific edits itemized above.

---

## 4. Residual inconsistency between the two records

One difference between the full and core records survives reconciliation and should be recorded plainly:

- **`updates` shape.** The reconciled full record emits `updates` as a mapping (§2.1). The completed core record still emits it as a list. The two records therefore disagree on the shape of this slot. The `update_details` and `source_caveats` text is identical in both.

All other Phase 3 changes were applied to both records, subject to the two slots the core schema does not declare (`file_collections` → carried as `distributions`; `subsets` → not carried).

---

## 5. Summary of edits

| Finding | Severity | Disposition | Full | Core |
|---|---|---|---|---|
| `updates` as list | major | shape corrected | changed | unchanged |
| `creators` omitted | major | 18 entries added; `created_by` shortened | changed | changed |
| Unattested content warning | moderate | warning removed; caveat rewritten | changed | changed |
| Grant IDs in `notes` | moderate | 4 `Grant` objects added | changed | changed |
| `file_collections` omitted | moderate | 4 collections added | changed | via `distributions` |
| Inferred instance count | minor | `counts` removed; caveat added | changed | changed |
| Non-resource external entry | minor | replaced with Voice Scholars resource | changed | changed |
| Inferred IAA | minor | rewording | changed | changed |
| Inferred archival status | minor | `archival` → `future_guarantees` | changed | changed |
| `accountable_organization` empty | minor | populated; roles split | changed | changed |
| `errata`/`updates` tension | minor | rewording + 3 caveats | changed | changed |
| v1.0 release date missing | minor | date + caveat added | changed | changed |
| `subsets` omitted | minor | 8 subsets added | changed | not declared in core schema |

**Outcome:** all thirteen findings addressed. Six values that the bundle does not support were removed or replaced (the suicidal-ideation warning, the 32,522 instance count, the "not assessed" IAA claim, the archival assertion, the self-contained non-resource, the Voice Scholars entry relocated out of `existing_uses`). Four structured slots that the bundle supports were populated for the first time (`creators`, `grants`, `file_collections`/`distributions`, `subsets`), plus `accountable_organization`. One shape defect was corrected in the full record and remains in the core record.