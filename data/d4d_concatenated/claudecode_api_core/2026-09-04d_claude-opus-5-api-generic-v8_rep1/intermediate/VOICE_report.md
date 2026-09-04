# VOICE D4D Reconciliation Report

Version label: `2026-09-04d_claude-opus-5-api-generic-v8_rep1`
Records reconciled: full (`Dataset`) and core (`CoreDataset`)
Referent: PhysioNet Bridge2AI-Voice adult release, version 3.1.0 (`doi:10.13026/8xbn-nq66`)

---

## 1. What the audit found

The Phase 3 audit returned 78 findings against the full record. They clustered into eight recurring patterns:

1. **Shape risk on object-ranged slots.** Every `external_resources` entry and every `maintainers` entry used `name` and `description` keys, which the supplied schema digest does not list for `ExternalResource` (declared: `archival`, `external_resources`, `future_guarantees`, `notes`, `restrictions`, `source_caveats`) or for `Maintainer` (declared: `maintainer_details`, `notes`, `role`, `source_caveats`).
2. **Cross-referent contamination.** `at_risk_populations` asserted `at_risk_groups_included: false` while populating `guardian_consent` and `assent_procedures` with pediatric provisions belonging to the separately published pediatric dataset. The third `maintainers` entry named a past host of an earlier release as a current maintainer.
3. **Absence-statements occupying content fields.** Six values whose whole content was that a thing does not exist: `cleaning_strategies[0]`, `errata[3]`, `labeling_strategies[0].inter_annotator_agreement`, `machine_annotation_tools[0].tool_accuracy`, `sampling_strategies[0].representative_verification`, `regulatory_restrictions.regulatory_restrictions`.
4. **Neighbouring-field answers.** `data_governance.appeal_process` gave a contract termination clause; `participant_privacy[0].data_linkage` gave a contact prohibition; `confidential_elements[0]` trailed into the access route; `license_and_use_terms.license_terms` duplicated the whole controlled-access workflow already held in `data_governance.access_review_process`.
5. **Internal inconsistency.** `content_warnings[0]` set `content_warnings_present: false` beside a populated `warnings` list; one person carried two different affiliation strings across `creators` and `ethical_reviews`; `instances[1].data_substrate` was set to `B2AI_SUBSTRATE:30` (Parquet), the distribution container rather than the instance substrate.
6. **Supported omissions.** `file_collections` (chunk c019 enumerates a three-folder tree with named member files and paths) and `subsets` (five named disease cohorts, seventeen per-condition diagnosis tables).
7. **Inferences exceeding the evidence.** `regulatory_restrictions.hipaa_compliant: compliant`, whose own caveat conceded no source uses the word; `conforms_to_standard: [BIDS]`, where the BIDS statement demonstrably describes the audio dataset.
8. **Duplication and roster gaps.** DTUA clauses triplicated across `prohibited_uses`, `ip_restrictions` and `license_and_use_terms`; several `creators` entries carrying role prose no passage supports; `Creator.credit_roles` unused although the feasibility publication's author-contributions block supplies mapped values.

Several findings were confirmations rather than defects: `use_repository`, `data_protection_impacts`, `imputation_protocols`, `annotation_analyses`, `total_file_count`, `total_size_bytes`, `compression`, `is_tabular`, `resources`, `parent_datasets`, `created_on`, `last_updated_on` and `modified_by` were all correctly omitted; `license`, `issued`, `keywords`, `publisher`, `was_derived_from`, `version_access.latest_version_doi` and the three `is_new_version_of` directions were all confirmed correct.

---

## 2. Changes made to the full record

### 2.1 Object shape

**`external_resources`** — all eleven entries were reshaped. `name` and `description` were dropped and the content moved into `notes`, which the digest does list. The bibliographic content is unchanged; the entry that read `name: b2aiprep` / `description: Open-source library at …` now reads `notes: b2aiprep, the open-source library at …`. `archival` was retained on the seven entries that carried it.

**`maintainers`** — `name` was dropped from all entries and the organization named inside `maintainer_details` instead. The first entry now opens "The MIT Laboratory for Computational Physiology maintains PhysioNet…"; the second, "The Bridge2AI-Voice Consortium curates the dataset…". `role: academic_institution` was retained on both.

### 2.2 Cross-referent contamination

**`at_risk_populations`** — `guardian_consent` and `assent_procedures` were removed. `special_protections` was rewritten to drop the clause about criteria that "would change when the pediatric cohort was introduced" and now reads "…so no minors are included." A `source_caveats` was added recording that the IRB protocol's guardian-consent and assent provisions apply to the separately published pediatric cohort.

**`maintainers`** — the third entry (T-CAIREM / Health Data Nexus) was removed. The Health Data Nexus is still recorded in `related_datasets` and in `extension_mechanism`, which the documentation ties to that platform. A note was added to `source_caveats` explaining this placement.

### 2.3 Absence-statements

- `cleaning_strategies` — the first entry ("No data cleaning preprocessing was applied…") was removed. The surviving audit-protocol entry gained a `source_caveats` recording that the healthsheet answers "no" to the cleaning question, so the audit is quality assessment rather than correction.
- `errata` — the fourth entry ("No formal erratum document is published…") was removed. Three substantive corrections remain.
- `labeling_strategies[0].inter_annotator_agreement` — removed. `annotations_per_item: 1` and `annotator_demographics` already carry the fact.
- `machine_annotation_tools[0].tool_accuracy` — removed. The identical statement survives as a `methodological_limitation` in `known_limitations`.
- `sampling_strategies[0].representative_verification` — removed. The forward-looking clause was folded into `why_not_representative`, which now ends "The project states an intention to improve representativeness by moving to remote collection…".
- `regulatory_restrictions.regulatory_restrictions` — removed. The no-export-controls negative is now recorded in that object's `source_caveats`.

### 2.4 Neighbouring-field answers

- `data_governance.appeal_process` — removed; a `source_caveats` on `data_governance` explains that the DTUA clause is a termination provision rather than an appeal route.
- `participant_privacy[0].data_linkage` — removed; the contact prohibition was moved into `license_and_use_terms.license_terms`, where it is a use restriction.
- `confidential_elements[0].confidentiality_details` — the trailing access-route sentence was dropped.
- `license_and_use_terms.license_terms` — the controlled-access workflow enumeration (DARF, DUA, DACO review, DTUA) was replaced with "Raw audio is governed by a separate controlled-access agreement." The workflow remains in full in `data_governance.access_review_process`.
- `labeling_strategies[0].data_annotation_protocol` — the sentence about downstream researchers describing new labels was removed and relocated to `intended_uses[0].usage_notes`.
- `ip_restrictions` — the third-party negative and the no-guarantee disclaimer were removed from `restrictions` and the disclaimer placed in a new `notes`.

### 2.5 Internal inconsistency

- `content_warnings[0].content_warnings_present` — changed `false` → `true`, with `warnings` retained and the `source_caveats` extended to explain why present was chosen.
- `creators[0].affiliations[0].name` — changed from "University of South Florida" to "USF Health Morsani College of Medicine, University of South Florida", matching the nested `principal_investigator.affiliation`.
- `ethical_reviews[0].contact_person` — removed. The audit noted the PI was inferred into an ethics-contact role and that the affiliation string diverged. The PI and her department are now named inside `review_details`.
- `instances[1].data_substrate` — removed and replaced with `data_topic: B2AI_TOPIC:37` (Waveform).
- `instances[0].label_description` — shortened to describe the label rather than restate the whole clinical-validation paragraph, which remains in `labeling_strategies`.
- `subpopulations[0].distribution` — removed; the cohort-composition statement it carried does not answer the demographic-subpopulation question. A `source_caveats` explains the omission.

### 2.6 Supported omissions filled

**`file_collections`** — added, with three entries carrying `id`, `name`, `path`, `collection_type` and `description`:

| id fragment | path | collection_type |
|---|---|---|
| `#collection-features` | `features` | `processed_data` |
| `#collection-metadata` | `metadata` | `metadata` |
| `#collection-phenotype` | `phenotype` | `processed_data` |

**`subsets`** — added, with five entries (`#subset-voice-disorders`, `#subset-respiratory`, `#subset-neurological`, `#subset-mood-psychiatric`, `#subset-controls`), each with `is_subpopulation: true` and inclusion criteria and gold-standard validation drawn from the documentation's Table 1. A `source_caveats` on the last entry records why the fifth programme cohort (pediatric) is not a subset here.

### 2.7 Inferences withdrawn

- `regulatory_restrictions.hipaa_compliant` — removed. The de-identification fact remains in `is_deidentified` and in `other_compliance`; the caveat now states that no source makes a compliance determination.
- `conforms_to_standard` — removed. `conforms_to` was rewritten from the bare string "Brain Imaging Data Structure (BIDS) v1.9.0" to prose attributing the claim to the project documentation and to the audio dataset it illustrates. The `source_caveats` paragraph on `conforms_to` was extended accordingly.

### 2.8 Rosters, duplication and prose

- `creators` — `credit_roles` added to the two co-PI entries from the feasibility publication's author-contributions block, each with a `source_caveats` noting the roles describe that article. Unsupported role prose was removed from six entries (`Philip Payne`, `David Dorr`, `Jean-Christophe Bélisle-Pipon`, `Vardit Ravitsky`, `Donald Bolser` lost `description` entirely; `Maria Powell` changed from "Lead investigator, voice disorders cohort" to "Investigator, voice disorders", matching the Annex C table). Authorship-position commentary ("first-listed author", "last-listed author of version 3.1.0") was removed. `Jean-Christophe Belisle-Pipon` was corrected to `Bélisle-Pipon`.
- `citation` — `Belisle-Pipon` corrected to `Bélisle-Pipon`, restoring the accent the quoted PhysioNet citation uses.
- `funders[0]` — `source_caveats` added recording the two corrupted award-number renderings and flagging that awardee, amount and period rest on the tier-4 source alone; each `Grant` gained a `notes` distinguishing core, release and application numbers.
- `purposes` — the fourth entry (50 experts, 12 institutions) was removed as a team fact rather than a purpose; the team-size figure survives in `creators[2].description`.
- `prohibited_uses[2]` — the no-sale sentence was dropped, leaving the IP clause; the no-sale term remains in `license_and_use_terms`.
- `acquisition_methods` — the second entry (`was_inferred_derived: true`) was removed as the record's own characterization rather than a source's answer; the derivation is fully described in `preprocessing_strategies`.
- `collection_mechanisms[2]` — the trailing clause about the initial release was removed.
- `collection_timeframes[0]` — the award period and the four-year phased plan were removed; only the 12-month statement and an explicit note of the missing dates remain.
- `distribution_formats` — `format` values normalized to `Parquet`, `TSV`, `JSON`; the three repeated `access_urls` (the landing page, already in `page`) were removed.
- `variables` — the `static_features` and `audio_quality_metrics` entries were removed from `variables`; both files are described in `file_collections[0].description`. The exclusion note was applied consistently across the five affected feature families.
- `informed_consent[0].consent_type` — "Prospective written informed consent" → "Prospective informed consent", since paper, electronic and video modalities are all documented.
- `consent_revocations[0]` — the longitudinal re-consent sentence was removed as a protocol provision not attested for this release.
- `participant_compensation[0]` — a `source_caveats` was added noting the IRB revision history shows two changes to the amount.
- `retention_limit` — `retention_period` reduced to the archive term; the DTUA and institutional regimes moved into `retention_details` and labelled as applying to copies.
- `updates.update_details` — re-tensed to the source's own future tense ("will be released", "will be notified").
- `extension_mechanism.extension_details` — "the hosting platform" restored to "the Health Data Nexus", the platform the source names.
- `machine_annotation_tools[0].tools` — URLs stripped for consistent formatting; a pointer to `external_resources` added to `tool_descriptions`.
- `human_subject_research.regulatory_compliance` — the DMC and drug/device negatives removed; the three substantive facts retained. `special_populations` gained the maximum age and healthy-volunteer facts.
- `related_datasets[4]` — a `source_caveats` added recording the two Zenodo artefacts the sources name.
- `raw_data_sources[0].access_details` — extended to reconcile with `raw_sources.access_url` by naming the Synapse route as controlled rather than public.
- `data_governance` — a `notes` added recording DACO@b2ai-voice.org as the access contact and stating that no individual is named as committee contact.

All slot list order and the `id`, `name`, `title`, `version`, `description`, `doi`, `page`, `publisher`, `issued`, `license`, `status`, `language`, `keywords`, `created_by`, `was_derived_from`, `notes` and header values are unchanged.

---

## 3. Changes made to the core record

The core record was re-projected from the reconciled full record. Every change in §2 that touches a slot the core schema carries is reflected there identically: reshaped `external_resources` and `maintainers`; removed `at_risk_populations.guardian_consent` and `.assent_procedures`; removed `cleaning_strategies[0]`, `errata[3]`, `labeling_strategies[0].inter_annotator_agreement`, `machine_annotation_tools[0].tool_accuracy`, `sampling_strategies[0].representative_verification`, `regulatory_restrictions.regulatory_restrictions`, `regulatory_restrictions.hipaa_compliant`, `data_governance.appeal_process`, `participant_privacy` (the whole slot, its only remaining fields being duplicated in `is_deidentified`), `ethical_reviews[0].contact_person`, `instances[1].data_substrate`, `subpopulations[0].distribution`, `acquisition_methods[1]`, `purposes[3]`, `conforms_to_standard`; `content_warnings[0].content_warnings_present` changed to `true`; `creators` corrected and `credit_roles` added; `conforms_to` rewritten as attributed prose.

One structural difference: the core schema exposes `distributions` where the full schema exposes `file_collections`. The three collections added to the full record appear in the core record under `distributions`, with `id`, `name`, `path`, `description` and, for the phenotype collection, `notes`. The core record carries no `variables`, `subsets`, `relationships`, `splits`, `collection_consents`, `collection_notifications` or `consent_revocations` slot, so those additions and edits have no core counterpart.

The core header block retains all fifteen declared lines including `# Sources:` and `# Phase 4 reconciliation: completed`.

---

## 4. Findings left as-is

- **`id` and person fragments.** The audit reviewed and confirmed these: no ORCID appears anywhere in chunks c002–c022 for any individual, so minting fragments on the record's own id is the correct handling under the v8 rule. Unchanged.
- **`related_datasets` `is_new_version_of` directions.** The audit checked and confirmed the three uses are directionally correct. Unchanged.
- **`raw_sources[0].access_url`.** A URL in a `uri`-ranged slot, correct per the v5 exemption. Unchanged.
- **`version_access.latest_version_doi`.** A `doi:` CURIE in a `uriorcurie` slot, correct. Unchanged.
- **`notes` (AI-readiness table).** The audit judged `notes` the right residual home, no structured slot existing. Unchanged in both records.
- **`existing_uses`, `use_repository`, `data_protection_impacts`, `imputation_protocols`, `annotation_analyses`, `total_file_count`, `total_size_bytes`, `compression`, `is_tabular`, `download_url`, `resources`, `parent_datasets`, `created_on`, `last_updated_on`, `modified_by`.** All confirmations. Unchanged.
- **`collection_consents[0]`.** The five consent-scope negatives were judged substantive, defining the permission granted rather than stating absence. Unchanged.
- **`is_deidentified.deidentification_details`** (k-anonymization negative). Judged substantive, characterizing the de-identification's limits. Unchanged.
- **`third_party_sharing`, `distribution_dates`, `intended_uses.use_category`, `discouraged_uses`, `sampling_strategies[0].strategies` scope.** Judged correct; `strategies` gained a cross-reference to the new subsets rather than being expanded inline.
- **`funders` NIH RePORTER content in `notes`.** Retained, with the tier-4 provenance now flagged in `source_caveats` rather than the content removed.

---

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `id` | retained | both | Fragment base correct; no ORCID stated anywhere in the bundle. |
| `citation` | changed | full | Accent restored to `Bélisle-Pipon` in quoted PhysioNet citation. |
| `conforms_to` | changed | both | Rewritten as attributed prose naming the source and the audio dataset it describes. |
| `conforms_to_standard` | removed | both | The BIDS claim attaches to the audio dataset, not this feature-only release. |
| `creators[0].credit_roles` | added | both | Mapped from the feasibility publication's author-contributions block. |
| `creators[0].affiliations` | changed | both | Aligned with the nested `principal_investigator.affiliation` form. |
| `creators[0].source_caveats` | changed | both | Extended to record that credit roles describe the article, not the release. |
| `creators[1].credit_roles` | added | both | Mapped from the author-contributions block. |
| `creators[1].source_caveats` | added | both | Records that credit roles describe the article. |
| `creators[5].description` | changed | both | "Lead investigator, voice disorders cohort" → "Investigator, voice disorders", per Annex C. |
| `creators[8]` | changed | both | Unsupported `description` removed from Philip Payne entry. |
| `creators[9]` | changed | both | Unsupported `description` removed from David Dorr entry. |
| `creators[10]` | changed | both | Name corrected to `Bélisle-Pipon`; unsupported `description` removed. |
| `creators[11]` | changed | both | Unsupported `description` removed from Vardit Ravitsky entry. |
| `creators[15]` | changed | both | Unsupported "Lead investigator" removed from Donald Bolser entry. |
| `funders[0].source_caveats` | added | both | Records corrupted award renderings and tier-4 dependence. |
| `funders[0].grants` | changed | both | Each grant gained a `notes` distinguishing core, release and application numbers. |
| `purposes[3]` | removed | both | Team composition is not a purpose; figure survives in `creators`. |
| `intended_uses[0].usage_notes` | changed | both | Gained the downstream-labelling guidance relocated from `labeling_strategies`. |
| `prohibited_uses[2].prohibition_reason` | changed | both | No-sale clause removed; retained in `license_and_use_terms`. |
| `instances[0].label_description` | changed | both | Shortened to describe the label rather than restate the validation paragraph. |
| `instances[1].data_substrate` | removed | both | Parquet is the distribution container, not the instance substrate. |
| `instances[1].data_topic` | added | both | `B2AI_TOPIC:37` (Waveform), which the vocabulary does fit. |
| `subpopulations[0].distribution` | removed | both | Carried cohort composition, not demographic subpopulation distribution. |
| `subpopulations[0].source_caveats` | added | both | Explains the omission. |
| `subsets` | added | full | Five disease cohorts attested with inclusion criteria and validation methods. |
| `content_warnings[0].content_warnings_present` | changed | both | `false` → `true`, resolving inconsistency with the populated `warnings`. |
| `content_warnings[0].source_caveats` | changed | both | Extended to explain the choice of `true`. |
| `confidential_elements[0].confidentiality_details` | changed | both | Trailing access-route sentence removed. |
| `variables` | changed | full | `static_features` and `audio_quality_metrics` removed; exclusion notes applied consistently. |
| `file_collections` | added | full | Three collections enumerated with paths in chunk c019. |
| `distributions` | added | core | Core-schema counterpart of the added `file_collections`. |
| `collection_mechanisms[2].mechanism_details` | changed | both | Clause about the initial release removed. |
| `collection_timeframes[0].timeframe_details` | changed | both | Award period and phased plan removed; missing dates noted. |
| `acquisition_methods[1]` | removed | both | The record's own characterization, not a source's answer. |
| `sampling_strategies[0].representative_verification` | removed | both | Absence-statement plus plan; substance moved to `why_not_representative`. |
| `sampling_strategies[0].why_not_representative` | changed | both | Gained the forward-looking clause. |
| `sampling_strategies[0].strategies` | changed | both | Cross-reference to the new subset entries added. |
| `raw_data_sources[0].access_details` | changed | both | Reconciled with the Synapse route named in `raw_sources`. |
| `cleaning_strategies[0]` | removed | both | Absence-statement ("No data cleaning preprocessing was applied"). |
| `cleaning_strategies[0].source_caveats` | added | both | Records the healthsheet negative against the surviving audit entry. |
| `labeling_strategies[0].inter_annotator_agreement` | removed | both | Absence-statement; fact held by `annotations_per_item`. |
| `labeling_strategies[0].data_annotation_protocol` | changed | both | Downstream-labelling guidance relocated to `intended_uses`. |
| `machine_annotation_tools[0].tool_accuracy` | removed | both | Absence-statement; duplicated in `known_limitations`. |
| `machine_annotation_tools[0].tools` | changed | both | URLs stripped for consistent formatting. |
| `machine_annotation_tools[0].tool_descriptions` | changed | both | Pointer to `external_resources` added. |
| `participant_privacy` | removed | core | Remaining content duplicated in `is_deidentified`. |
| `participant_privacy[0].data_linkage` | removed | full | Contact prohibition relocated to `license_and_use_terms`. |
| `is_deidentified.deidentification_details` | retained | both | K-anonymization negative judged substantive. |
| `human_subject_research.regulatory_compliance` | changed | both | DMC and drug/device negatives removed. |
| `human_subject_research.special_populations` | changed | both | Maximum age and healthy-volunteer facts added. |
| `at_risk_populations.guardian_consent` | removed | both | Pediatric provision belonging to the separate pediatric dataset. |
| `at_risk_populations.assent_procedures` | removed | both | Pediatric provision belonging to the separate pediatric dataset. |
| `at_risk_populations.special_protections` | changed | both | Superseded plan clause removed. |
| `at_risk_populations.source_caveats` | added | both | Records why the pediatric provisions are excluded. |
| `ethical_reviews[0].contact_person` | removed | both | PI inferred into an ethics-contact role; affiliation string diverged. |
| `ethical_reviews[0].review_details` | changed | both | PI and department named inline instead. |
| `informed_consent[0].consent_type` | changed | both | "written" dropped; three consent modalities are documented. |
| `consent_revocations[0].revocation_details` | changed | full | Longitudinal re-consent sentence removed as unattested for this release. |
| `collection_consents[0].consent_details` | retained | full | Consent-scope negatives judged substantive. |
| `participant_compensation[0].source_caveats` | added | full | Records that the amount changed twice in the IRB revision history. |
| `license_and_use_terms.license_terms` | changed | both | Access workflow replaced by a pointer; contact prohibition added. |
| `data_governance.appeal_process` | removed | both | A termination clause, not an appeal route. |
| `data_governance.notes` | added | both | Records DACO@b2ai-voice.org and that no individual is named. |
| `data_governance.source_caveats` | added | both | Explains the appeal omission. |
| `ip_restrictions.restrictions` | changed | both | Third-party negative and no-guarantee disclaimer removed. |
| `ip_restrictions.notes` | added | both | Holds the as-is / no-warranty disclaimer. |
| `regulatory_restrictions.hipaa_compliant` | removed | both | No source makes a compliance determination. |
| `regulatory_restrictions.regulatory_restrictions` | removed | both | Absence-statement about export controls. |
| `regulatory_restrictions.other_compliance` | changed | both | Gained the HIPAA de-identification fact and the OMB M-07-16 classification. |
| `regulatory_restrictions.source_caveats` | changed | both | Rewritten to record both withdrawn values. |
| `distribution_formats` | changed | both | `format` normalized to Parquet/TSV/JSON; landing-page `access_urls` removed. |
| `maintainers` | changed | both | `name` dropped from all entries; organization named in `maintainer_details`; T-CAIREM entry removed. |
| `updates.update_details` | changed | both | Re-tensed to the source's own future tense. |
| `retention_limit.retention_period` | changed | both | Reduced to the archive term. |
| `retention_limit.retention_details` | changed | both | DTUA and institutional regimes separated and labelled. |
| `errata[3]` | removed | both | Absence-statement ("No formal erratum document is published"). |
| `extension_mechanism.extension_details` | changed | both | "the hosting platform" restored to "the Health Data Nexus". |
| `related_datasets[0].notes` | changed | both | Pediatric Synapse route noted. |
| `related_datasets[4].source_caveats` | added | both | Records the two Zenodo artefacts the sources name. |
| `external_resources` | changed | both | All eleven entries reshaped from `name`/`description` to `notes`. |
| `source_caveats` | changed | both | Extended for hosting placement and the `conforms_to` decision. |
| `use_repository` | retained | both | Correctly omitted; explicit negative in the bundle. |
| `data_protection_impacts` | retained | both | Correctly omitted; explicit negative in the bundle. |
| `notes` | retained | both | AI-readiness table judged correct residual content. |