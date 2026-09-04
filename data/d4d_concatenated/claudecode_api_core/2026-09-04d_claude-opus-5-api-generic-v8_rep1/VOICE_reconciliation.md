# Reconciliation Report — VOICE

Version label: `2026-09-04d_claude-opus-5-api-generic-v8_rep1`
Records reconciled: full (`VOICE_d4d.yaml`) and core (`VOICE_d4d_core.yaml`)

## 1. What the audit found

The Phase 3 audit returned 92 findings against the full record. They fell into recognisable groups:

1. **Absence-statements occupying content fields.** Several slots carried values whose content was that a thing does not exist, plus a pointer to where the negative was documented — `cleaning_strategies[0]`, `errata[3]`, `labeling_strategies[0].inter_annotator_agreement`, `machine_annotation_tools[0].tool_accuracy`, `sampling_strategies[0].representative_verification`, `regulatory_restrictions.regulatory_restrictions`.
2. **Cross-referent contamination.** `at_risk_populations` asserted `at_risk_groups_included: false` while populating `guardian_consent` and `assent_procedures` with pediatric provisions belonging to the separately published pediatric dataset. The third `maintainers` entry recorded a past host of an earlier release as a current maintainer.
3. **Neighbouring-field answers.** `data_governance.appeal_process` gave a contract termination clause; `participant_privacy[0].data_linkage` gave a contact prohibition; `confidential_elements[0].confidentiality_details` trailed into the access route; `license_and_use_terms.license_terms` duplicated the controlled-access workflow already in `data_governance.access_review_process`.
4. **Internal inconsistency.** `content_warnings[0]` set `content_warnings_present: false` while populating `warnings`. One person carried two different affiliation strings across `creators` and `ethical_reviews`. `instances[1].data_substrate` was set to Parquet — the distribution container, not the instance substrate.
5. **Inferences exceeding the evidence.** `regulatory_restrictions.hipaa_compliant: compliant`, whose own caveat admitted no source uses the word; `conforms_to_standard: [BIDS]`, where the BIDS statement demonstrably describes the audio dataset rather than the feature-only release.
6. **Supported omissions.** `file_collections` (the bundle enumerates a three-folder tree with named member files and paths) and `subsets` (five named disease cohorts, seventeen per-condition diagnosis tables).
7. **Shape risk.** The audit flagged that `external_resources` and `maintainers` entries used `name`/`description`, and that three `human_subject_research` fields were list-wrapped, and asked that these be checked against the schema digest.
8. **Quotation fidelity.** The `citation` rendered "Belisle-Pipon" where the source writes "Bélisle-Pipon".
9. **Confirmations.** A substantial number of findings were explicit confirmations that a value or omission was correct.

## 2. What was changed in the full record

**Absence-statements removed.** `cleaning_strategies` went from two entries to one: the entry reading "No data cleaning preprocessing was applied" is gone, and the surviving audit-protocol entry gained a `source_caveats` recording that the healthsheet answers "no" to the cleaning question. `errata` went from four entries to three: the "No formal erratum document is published" entry is gone. `labeling_strategies[0].inter_annotator_agreement` and `machine_annotation_tools[0].tool_accuracy` are both absent from the reconciled record. `sampling_strategies[0].representative_verification` is absent; the substantive part of its content (the intention to improve representativeness) was folded into `why_not_representative`. `regulatory_restrictions.regulatory_restrictions` is absent, and the export-control negative is now noted in that object's `source_caveats` instead.

**Cross-referent contamination cleared.** `at_risk_populations.guardian_consent` and `at_risk_populations.assent_procedures` are absent from the reconciled record; a `source_caveats` now explains that those provisions belong to the pediatric cohort. `special_protections` was rewritten to drop the superseded clause about criteria changing when the pediatric cohort was introduced. `maintainers` went from three entries to two: the T-CAIREM / Health Data Nexus entry is gone, and the record-level `source_caveats` now explains that the Health Data Nexus is recorded under `related_datasets` and in the extension mechanism but not among current maintainers.

**Neighbouring-field answers relocated or trimmed.** `data_governance.appeal_process` is absent; the termination clause is now described in `data_governance.source_caveats` as not being an appeal process. `participant_privacy[0].data_linkage` is absent; the contact prohibition now appears in `license_and_use_terms.license_terms`, which is where the use restriction belongs. `confidential_elements[0].confidentiality_details` lost its trailing sentence about the controlled-access mechanism. `license_and_use_terms.license_terms` lost the enumerated DARF/DUA/DACO/DTUA workflow, which remains in `data_governance.access_review_process`, and now says only that raw audio is governed by a separate controlled-access agreement.

**Internal inconsistencies resolved.** `content_warnings[0].content_warnings_present` changed from `false` to `true`, with the `source_caveats` rewritten to explain the resolution. `creators[0].affiliations[0].name` changed from "University of South Florida" to "USF Health Morsani College of Medicine, University of South Florida", matching the nested `principal_investigator.affiliation`. `ethical_reviews[0].contact_person` is absent; the person and their departmental affiliation are now stated in `review_details` prose, removing the second affiliation string and the inference that the PI is the ethics contact. `instances[1].data_substrate` is absent, replaced by `data_topic: B2AI_TOPIC:37`.

**Inferences withdrawn.** `regulatory_restrictions.hipaa_compliant` is absent; the de-identification fact is retained in `other_compliance` and the reason for omission stated in `source_caveats`. `conforms_to_standard` is absent from both records; `conforms_to` was rewritten from the bare string "Brain Imaging Data Structure (BIDS) v1.9.0" to a sentence attributing the claim to the project documentation and to the audio dataset it describes, and the record-level `source_caveats` explains the change.

**Supported omissions filled.** `file_collections` was added to the full record with three entries (`#collection-features`, `#collection-metadata`, `#collection-phenotype`), each with `id`, `name`, `path`, `collection_type` and a description enumerating member files. `subsets` was added to the full record with five entries, one per adult disease cohort plus controls, each with a minted fragment id, `is_subpopulation: true` and cohort inclusion criteria; a `source_caveats` on the last explains why the pediatric cohort is not among them.

**Shape corrections.** `external_resources` entries no longer use `name`/`description`; each entry now carries its content in `notes`, with `archival` retained where the evidence supports it. `maintainers` entries no longer use `name`; the organisation is named inside `maintainer_details`. `human_subject_research.regulatory_compliance` was rewritten so that the data-monitoring-committee and drug/device negatives are gone, leaving the three positive compliance facts. `instances[0].missing_information[*].missing` changed from scalar strings to single-item lists.

**List-shape corrections elsewhere.** `distribution_dates[0].release_dates` changed from a scalar string to a single-item list. `ip_restrictions.restrictions[0]` lost its trailing third-party negative and no-guarantee clause; the no-warranty statement moved to `ip_restrictions.notes`.

**Duplication reduced.** `purposes` went from four entries to three: the entry built around "50 multidisciplinary experts from 12 North American institutions" is gone, and the team-composition fact now appears in the `creators` entry for the consortium. `prohibited_uses[2]` lost its trailing "Sale of all or part of the data on any media is not permitted", which remains in `license_and_use_terms.license_terms`. `machine_annotation_tools[0].tools` entries are now bare names, with the repository URLs left to `external_resources` and a pointer added to `tool_descriptions`.

**Creator entries reworked.** `creators[0].credit_roles` and `creators[1].credit_roles` were added from the feasibility publication's author-contributions statement, each with a `source_caveats` noting that the roles describe that article. Authorship-position commentary ("first-listed author", "last-listed author") is gone from both descriptions. The unsupported bare "Lead investigator" descriptions for Bolser, Payne, Dorr, Bélisle-Pipon and Ravitsky are gone; those entries now carry `name` and `affiliations` only. `creators[10].name` changed from "Jean-Christophe Belisle-Pipon" to "Jean-Christophe Bélisle-Pipon", matching the source.

**Other changes.** `funders[0]` gained per-grant `notes` distinguishing what each number is, and a `source_caveats` recording the two corrupted award-number renderings and the tier-4 provenance of the award amount. `subpopulations[0].distribution` is absent, replaced by a `source_caveats` explaining that the unequal-distribution statement concerns disease cohorts rather than demographic subpopulations. `instances[0].label_description` was shortened from the full clinical-validation paragraph to a description of the label itself. `variables[*].quality_notes` now apply the exclusion note consistently across the five affected feature families, and the two table-level entries (`static_features`, `audio_quality_metrics`) are gone from `variables`, their content now carried in the `#collection-features` file collection. `distribution_formats[*].format` normalised to "Parquet", "TSV", "JSON", and the repeated landing-page `access_urls` are gone. `acquisition_methods` went from two entries to one: the `was_inferred_derived` entry is gone. `collection_mechanisms[2]` lost its trailing clause about the initial release. `collection_timeframes[0].timeframe_details` lost the award period and the four-year phased programme. `updates.update_details` was retensed to the source's own future tense. `extension_mechanism.extension_details` restored "Health Data Nexus" in place of the generalised "the hosting platform". `retention_limit` was restructured so `retention_period` covers the archive and `retention_details` separates the DTUA and institutional regimes. `informed_consent[0].consent_type` changed from "Prospective written informed consent" to "Prospective informed consent". `related_datasets[4]` gained a `source_caveats` about the two Zenodo artefacts, and `related_datasets[0].notes` gained the separate Synapse route for pediatric raw audio. `human_subject_research.special_populations` gained the maximum-age and healthy-volunteer facts. `raw_data_sources[0].access_details` now names the Synapse route, reconciling it with `raw_sources`. `intended_uses[0].usage_notes` absorbed the new-labels guidance formerly in `labeling_strategies`. `data_governance.notes` was added, carrying the DACO contact address the bundle repeatedly gives.

## 3. What was changed in the core record

The core record was re-derived by projection from the reconciled full record, so every change above propagates to whichever core slots exist. In addition:

- `distributions` was added, projecting the three new `file_collections` entries.
- `conforms_to_standard` is absent from the core record, matching the full record.
- The `subsets` and `variables` lists have no counterpart in the core schema and do not appear there.

Header block: `# Phase 4 reconciliation: completed` is present, as is `# Sources:` naming the full record.

## 4. What was left as-is, and why

**Confirmed values.** Where the audit confirmed a populated value as correct — `license`, `issued`, `created_by`, `page`, `publisher`, `keywords`, `was_derived_from`, `existing_uses`, `third_party_sharing` (present with `is_shared: true` and its note), `is_deidentified`, `collection_consents`, `license_and_use_terms.data_use_permission`, `data_governance.accountable_organization`, `version_access.latest_version_doi`, `raw_sources[0].access_url`, `related_datasets[*].relationship_type`, `intended_uses[0].use_category` — nothing was altered.

**Confirmed omissions.** The audit confirmed as correct the omission of `created_on`, `last_updated_on`, `modified_by`, `compression`, `is_tabular`, `total_file_count`, `total_size_bytes`, `download_url`, `use_repository`, `imputation_protocols`, `data_protection_impacts`, `annotation_analyses`, `parent_datasets` and `resources`. These slots remain absent from both records and are not listed in the disposition table, which covers only slots present in a record after reconciliation.

**`citation`.** The audit flagged the missing acute accent in "Belisle-Pipon". Comparing the two full records, the `citation` slot is unchanged between them: it still reads "Belisle-Pipon". The finding was **left as-is**. The accent was restored in `creators[10].name`, which is a separate slot; the citation itself was not amended.

**`consent_revocations[0].revocation_details`.** The audit flagged the trailing longitudinal-consent sentence as a protocol provision rather than a property of the release. Comparing the two records, this value is unchanged: the sentence about electronic consent before each subsequent collection session is still present. The finding was **left as-is**.

**`participant_compensation[0]`.** The audit noted that the IRB revision history shows the compensation amount changed twice, and that this was not recorded. No `source_caveats` was added to this object; the four original fields are unchanged. The finding was **left as-is**.

**`data_governance.committee_contact` and `license_and_use_terms.contact_person`.** Both remain absent from both records. Because they are absent, they are not listed in the disposition table.

**`notes`.** The audit judged the AI-readiness table acceptable as residual content. Unchanged.

**`source_caveats` (record level).** The audit judged the handling correct. The text was extended to cover the hosting and `conforms_to` decisions made in this phase, but the six original conflict paragraphs are intact.

**`instances[1]` count omission.** The audit confirmed the deliberate omission of a total. No total was computed.

**`prohibited_uses` / `discouraged_uses` placement.** The audit confirmed the split is right. Unchanged.

**`related_datasets` direction.** The audit confirmed `is_new_version_of` is directionally correct for all three earlier versions. Unchanged.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `id` | retained | both | Audit review found no ORCID anywhere in the bundle for either person; the DOI-based fragment base stands. |
| `creators[0].credit_roles` | added | both | Author-contributions statement in the feasibility publication maps to closed-enum values; roles narrated in prose belong in the declared field. |
| `creators[1].credit_roles` | added | both | As above for the second co-principal investigator. |
| `creators[0].description` | changed | both | Authorship-position commentary ("first-listed author") removed: a fact about the source document, not the creator. |
| `creators[12].description` | changed | both | Removed "last-listed author of version 3.1.0" for the same reason. |
| `creators[0].affiliations` | changed | both | Aligned with the nested `principal_investigator.affiliation` so one person carries one affiliation string. |
| `creators[10].name` | changed | both | Restored the acute accent the source uses. |
| `creators[2].description` | changed | both | Absorbed the team-composition figures displaced from `purposes`. |
| `creators[0].source_caveats` | changed | both | Extended to note that the credit roles describe the feasibility article, not the dataset release. |
| `creators[1].source_caveats` | added | both | Same caveat for the second co-principal investigator. |
| `funders[0].grants[0].notes` | added | both | Distinguishes the core project number from the other two. |
| `funders[0].grants[1].notes` | added | both | Identifies the number named in the PhysioNet acknowledgements. |
| `funders[0].grants[2].notes` | added | both | Identifies the NIH RePORTER application number. |
| `funders[0].source_caveats` | added | both | Records the two corrupted award-number renderings in the documentation and the tier-4 provenance of the award amount. |
| `funders[0].notes` | retained | both | The award amount and period remain, now flagged as tier-4-only in the caveat. |
| `purposes` | changed | both | Fourth entry removed: team composition is not a purpose and duplicated purpose 2. |
| `instances[0].label_description` | changed | both | Shortened to describe the label rather than restate the validation narrative already in `labeling_strategies`. |
| `instances[0].missing_information[0].missing` | changed | both | Corrected from a scalar string to a list. |
| `instances[0].missing_information[1].missing` | changed | both | Corrected from a scalar string to a list. |
| `instances[0].missing_information[2].missing` | changed | both | Corrected from a scalar string to a list. |
| `instances[1].data_topic` | added | both | B2AI_TOPIC:37 (Waveform) is attested by the subject of the instance; replaces the withdrawn substrate value. |
| `instances[1].notes` | retained | both | Explains why per-feature counts differ; unchanged. |
| `subpopulations[0].source_caveats` | added | both | Explains why `distribution` is left unpopulated: the unequal-distribution statement concerns disease cohorts. |
| `subsets` | added | full | Five adult disease cohorts with named per-condition diagnosis tables are attested; a supported omission the audit flagged. |
| `file_collections` | added | full | The bundle enumerates a three-folder tree with named member files and paths; a supported omission the audit flagged. |
| `distributions` | added | core | Projection of the new `file_collections`. |
| `content_warnings[0].content_warnings_present` | changed | both | Changed to `true` to resolve the contradiction with a populated `warnings` list. |
| `content_warnings[0].source_caveats` | changed | both | Rewritten to explain the resolution rather than assert two states. |
| `confidential_elements[0].confidentiality_details` | changed | both | Trailing access-route sentence removed; that content answers `data_governance`. |
| `collection_timeframes[0].timeframe_details` | changed | both | Award period and four-year phased plan removed; neither is a collection timeframe for the released cohort. |
| `variables` | changed | full | Exclusion note applied consistently across the five affected feature families; the two table-level entries moved to `file_collections`. |
| `acquisition_methods` | changed | both | The `was_inferred_derived` entry removed: no source answers the acquisition question that way for the derived features. |
| `collection_mechanisms[2].mechanism_details` | changed | both | Trailing clause about the initial release removed; it describes v1.0, not the referent. |
| `sampling_strategies[0].why_not_representative` | changed | both | Absorbed the mitigation intention, in the source's own tense, from the removed verification field. |
| `sampling_strategies[0].strategies` | changed | both | Points to the per-cohort criteria now carried on the subset entries. |
| `raw_data_sources[0].access_details` | changed | both | Names the Synapse controlled-access route, reconciling it with `raw_sources`. |
| `cleaning_strategies` | changed | both | Reduced from two entries to one: "No data cleaning preprocessing was applied" is an absence-statement. |
| `cleaning_strategies[0].source_caveats` | added | both | The healthsheet negative recorded as a caveat on the surviving audit-protocol entry. |
| `labeling_strategies[0].data_annotation_protocol` | changed | both | Guidance to future users moved to `intended_uses[0].usage_notes`. |
| `machine_annotation_tools[0].tools` | changed | both | Normalised to bare names; URLs left to `external_resources`. |
| `machine_annotation_tools[0].tool_descriptions` | changed | both | Gained a pointer to `external_resources` for the repository URLs. |
| `human_subject_research.regulatory_compliance` | changed | both | Data-monitoring-committee and drug/device negatives removed; three positive compliance facts retained. |
| `human_subject_research.special_populations` | changed | both | Added the maximum age and healthy-volunteer inclusion. |
| `at_risk_populations.special_protections` | changed | both | Superseded plan about pediatric criteria removed. |
| `at_risk_populations.source_caveats` | added | both | Explains why the pediatric guardian-consent and assent provisions are excluded. |
| `ethical_reviews[0].review_details` | changed | both | The PI and their department are stated in prose, replacing the removed `contact_person` object. |
| `informed_consent[0].consent_type` | changed | both | "written" narrowed the source, which describes paper, electronic and video modalities. |
| `consent_revocations[0].revocation_details` | retained | both | Audit flagged the longitudinal-consent sentence; comparing the records, the value is unchanged and the finding was not acted on. |
| `participant_compensation[0].compensation_amount` | retained | both | Audit noted the amount was amended twice; no caveat was added and the value is unchanged. |
| `license_and_use_terms.license_terms` | changed | both | Controlled-access workflow removed as duplicative of `data_governance`; the contact prohibition relocated here from `participant_privacy`. |
| `data_governance.notes` | added | both | Carries the DACO contact address the bundle repeatedly gives. |
| `data_governance.source_caveats` | added | both | Explains why `appeal_process` is left unpopulated: the DTUA gives a termination clause, not an appeal route. |
| `ip_restrictions.restrictions` | changed | both | Third-party negative and no-guarantee disclaimer removed from the restrictions list. |
| `ip_restrictions.notes` | added | both | The no-warranty statement recorded as context. |
| `regulatory_restrictions.other_compliance` | changed | both | Absorbed the HIPAA de-identification fact and the PII classification. |
| `regulatory_restrictions.source_caveats` | changed | both | Rewritten to explain both the `hipaa_compliant` and export-control omissions. |
| `distribution_formats[0].format` | changed | both | Normalised to "Parquet"; landing-page `access_urls` removed. |
| `distribution_formats[1].format` | changed | both | Normalised to "TSV"; landing-page `access_urls` removed. |
| `distribution_formats[2].format` | changed | both | Normalised to "JSON"; "JSON data dictionaries" described a role, not a format. |
| `distribution_dates[0].release_dates` | changed | both | Corrected from a scalar string to a list. |
| `maintainers` | changed | both | Reduced from three entries to two: the T-CAIREM entry recorded a past host of an earlier release. |
| `maintainers[0].maintainer_details` | changed | both | Now names MIT LCP, whose name was formerly in an undeclared `name` key. |
| `maintainers[1].maintainer_details` | changed | both | Now names the consortium and the DACO address, replacing the undeclared `name` key. |
| `updates.update_details` | changed | both | Retensed to the source's own future tense; the plan is no longer stated as current practice. |
| `retention_limit.retention_period` | changed | both | Narrowed to the archive; the DTUA and institutional regimes separated into `retention_details`. |
| `retention_limit.retention_details` | changed | both | Now distinguishes the three regimes explicitly. |
| `errata` | changed | both | Reduced from four entries to three: "No formal erratum document is published" is an absence-statement plus a pointer. |
| `extension_mechanism.extension_details` | changed | both | Restored "Health Data Nexus", which the source names, in place of a generalisation that read as current. |
| `external_resources` | changed | both | Content moved from `name`/`description` into `notes`, the field the digest declares for this class. |
| `related_datasets[0].notes` | changed | both | Added the separate Synapse route for pediatric raw audio. |
| `related_datasets[4].source_caveats` | added | both | Records the two Zenodo artefacts named by different sources. |
| `conforms_to` | changed | both | Rewritten to attribute the BIDS claim to the documentation and to the audio dataset it describes. |
| `citation` | retained | both | Audit flagged the missing acute accent; comparing the records, the citation is unchanged and still reads "Belisle-Pipon". |
| `intended_uses[0].usage_notes` | changed | both | Absorbed the new-labels guidance displaced from `labeling_strategies`. |
| `prohibited_uses[2].prohibition_reason` | changed | both | No-sale clause removed as triplicated; it remains in `license_and_use_terms`. |
| `source_caveats` | changed | both | Extended to cover the hosting and `conforms_to` decisions taken in this phase. |
| `notes` | retained | both | Audit judged the AI-readiness table acceptable as residual content. |
| `existing_uses` | retained | both | Audit downgraded its own finding to a confirmation. |
| `license` | retained | both | Supported verbatim by four tier-1 sources. |
| `issued` | retained | both | Matches the tier-1 publication date, with UTC offset. |
| `keywords` | retained | both | Taken verbatim from the v3.1.0 topics list. |
| `publisher` | retained | both | No declared prefix covers PhysioNet; a URL is the correct fallback in a `uriorcurie` slot. |
| `page` | retained | both | The version-3.1.0 landing page, consistent with the record's version DOI. |
| `was_derived_from` | retained | both | Supported by the tier-1 methods section. |
| `created_by` | retained | both | Supported; no distinct modifier is named by any source. |
| `raw_sources[0].access_url` | retained | both | Declared range is `uri`; a URL is correct there. |
| `version_access.latest_version_doi` | retained | both | Correctly given as a `doi:` CURIE in a `uriorcurie` slot. |
| `third_party_sharing[0].is_shared` | retained | both | Audit confirmed the tense reading is acceptable. |
| `discouraged_uses` | retained | both | Audit confirmed placement is right. |
| `is_deidentified.deidentification_details` | retained | both | Audit found the k-anonymisation statement substantive rather than an absence-statement. |
| `collection_consents[0].consent_details` | retained | both | Audit found the five consent-scope negatives substantive: they define the permission granted. |
| `related_datasets[1].relationship_type` | retained | both | Audit confirmed `is_new_version_of` is directionally correct. |
| `related_datasets[2].relationship_type` | retained | both | Audit confirmed direction. |
| `related_datasets[3].relationship_type` | retained | both | Audit confirmed direction. |