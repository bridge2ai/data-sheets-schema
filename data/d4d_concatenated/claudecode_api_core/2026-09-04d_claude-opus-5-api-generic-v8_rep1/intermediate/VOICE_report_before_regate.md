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
9. **Confirmations.** A substantial number of findings were explicit confirmations that a value or omission was correct (`license`, `issued`, `created_on`, `last_updated_on`, `compression`, `total_size_bytes`, `total_file_count`, `use_repository`, `imputation_protocols`, `data_protection_impacts`, `annotation_analyses`, `parent_datasets`, `resources`, `keywords`, `publisher`, `was_derived_from`, `related_datasets[*].relationship_type`, `raw_sources[0].access_url`, `download_url`).

## 2. What was changed in the full record

**Absence-statements removed.** `cleaning_strategies` went from two entries to one: the entry reading "No data cleaning preprocessing was applied" is gone, and the surviving audit-protocol entry gained a `source_caveats` recording that the healthsheet answers "no" to the cleaning question. `errata` went from four entries to three: the "No formal erratum document is published" entry is gone. `labeling_strategies[0].inter_annotator_agreement` and `machine_annotation_tools[0].tool_accuracy` are both absent from the reconciled record. `sampling_strategies[0].representative_verification` is absent; the substantive part of its content (the intention to improve representativeness) was folded into `why_not_representative`. `regulatory_restrictions.regulatory_restrictions` is absent, and the export-control negative is now noted in that object's `source_caveats` instead.

**Cross-referent contamination cleared.** `at_risk_populations.guardian_consent` and `at_risk_populations.assent_procedures` are absent from the reconciled record; a `source_caveats` now explains that those provisions belong to the pediatric cohort. `special_protections` was rewritten to drop the superseded clause about criteria changing when the pediatric cohort was introduced. `maintainers` went from three entries to two: the T-CAIREM / Health Data Nexus entry is gone, and `source_caveats` at record level now explains that the Health Data Nexus is recorded under `related_datasets` and in the extension mechanism but not among current maintainers.

**Neighbouring-field answers relocated or trimmed.** `data_governance.appeal_process` is absent; the termination clause is now described in `data_governance.source_caveats` as not being an appeal process. `participant_privacy[0].data_linkage` is absent; the contact prohibition now appears in `license_and_use_terms.license_terms`, which is where the use restriction belongs. `confidential_elements[0].confidentiality_details` lost its trailing sentence about the controlled-access mechanism. `license_and_use_terms.license_terms` lost the enumerated DARF/DUA/DACO/DTUA workflow, which remains in `data_governance.access_review_process`, and now says only that raw audio is governed by a separate controlled-access agreement.

**Internal inconsistencies resolved.** `content_warnings[0].content_warnings_present` changed from `false` to `true`, with the `source_caveats` rewritten to explain the resolution. `creators[0].affiliations[0].name` changed from "University of South Florida" to "USF Health Morsani College of Medicine, University of South Florida", matching the nested `principal_investigator.affiliation`. `ethical_reviews[0].contact_person` is absent; the person and their departmental affiliation are now stated in `review_details` prose, removing the second affiliation string and the inference that the PI is the ethics contact. `instances[1].data_substrate` is absent, replaced by `data_topic: B2AI_TOPIC:37` (Waveform).

**Inferences withdrawn.** `regulatory_restrictions.hipaa_compliant` is absent; the de-identification fact is retained in `other_compliance` and the reason for omission stated in `source_caveats`. `conforms_to_standard` is absent from the full record; `conforms_to` was rewritten from the bare string "Brain Imaging Data Structure (BIDS) v1.9.0" to a sentence attributing the claim to the project documentation and to the audio dataset it describes, and the record-level `source_caveats` explains the change.

**Supported omissions filled.** `file_collections` was added with three entries (`#collection-features`, `#collection-metadata`, `#collection-phenotype`), each with `id`, `name`, `path`, `collection_type` and a description enumerating member files. `subsets` was added with five entries, one per adult disease cohort plus controls, each with a minted fragment id, `is_subpopulation: true` and cohort inclusion criteria; a `source_caveats` on the last explains why the pediatric cohort is not among them.

**Shape corrections.** `external_resources` entries no longer use `name`/`description`; each entry now carries its content in `notes`, with `archival` retained where the evidence supports it. `maintainers` entries no longer use `name`; the organisation is named inside `maintainer_details`. `human_subject_research.regulatory_compliance` was split so that the data-monitoring-committee and drug/device negatives are gone, leaving the three positive compliance facts. `instances[0].missing_information[*].missing` changed from scalar strings to single-item lists.

**List-shape corrections elsewhere.** `distribution_dates[0].release_dates` changed from a scalar string to a single-item list. `ip_restrictions.restrictions[0]` lost its trailing third-party negative and no-guarantee clause; the no-warranty statement moved to `ip_restrictions.notes`.

**Duplication reduced.** `purposes` went from four entries to three: the entry built around "50 multidisciplinary experts from 12 North American institutions" is gone, and the team-composition fact now appears in the `creators` entry for the consortium. `prohibited_uses[2]` lost its trailing "Sale of all or part of the data on any media is not permitted", which remains in `license_and_use_terms.license_terms`. `machine_annotation_tools[0].tools` entries are now bare names, with the repository URLs left to `external_resources` and a pointer added to `tool_descriptions`.

**Creator entries reworked.** `creators[0].credit_roles` and `creators[1].credit_roles` were added from the feasibility publication's author-contributions statement, each with a `source_caveats` noting that the roles describe that article. Authorship-position commentary ("first-listed author", "last-listed author") is gone from both descriptions. The unsupported bare "Lead investigator" descriptions for Bolser, Payne, Dorr, Bélisle-Pipon and Ravitsky are gone; those entries now carry `name` and `affiliations` only. `creators[10].name` changed from "Jean-Christophe Belisle-Pipon" to "Jean-Christophe Bélisle-Pipon", matching the source.

**Other changes.** `citation` now reads "Bélisle-Pipon" with the acute accent, as the source writes it. `funders[0]` gained per-grant `notes` distinguishing what each number is, and a `source_caveats` recording the two corrupted award-number renderings and the tier-4 provenance of the award amount. `subpopulations[0].distribution` is absent, replaced by a `source_caveats` explaining that the unequal-distribution statement concerns disease cohorts rather than demographic subpopulations. `instances[0].label_description` was shortened from the full clinical-validation paragraph to a description of the label itself. `variables[*].quality_notes` now apply the exclusion note consistently across the five affected feature families, and the two table-level entries (`static_features`, `audio_quality_metrics`) are gone from `variables`, their content now carried in the `#collection-features` file collection. `distribution_formats[*].format` normalised to "Parquet", "TSV", "JSON", and the repeated landing-page `access_urls` are gone. `acquisition_methods` went from two entries to one: the `was_inferred_derived` entry is gone. `collection_mechanisms[2]` lost its trailing clause about the initial release. `collection_timeframes[0].timeframe_details` lost the award period and the four-year phased programme. `updates.update_details` was retensed to the source's own future tense. `extension_mechanism.extension_details` restored "Health Data Nexus" in place of the generalised "the hosting platform". `retention_limit` was restructured so `retention_period` covers the archive and `retention_details` separates the DTUA and institutional regimes. `informed_consent[0].consent_type` changed from "Prospective written informed consent" to "Prospective informed consent". `consent_revocations[0]` lost its longitudinal-collection sentence. `participant_compensation[0]` gained a `source_caveats` about the two compensation amendments. `related_datasets[4]` gained a `source_caveats` about the two Zenodo artefacts. `human_subject_research.special_populations` gained the maximum-age and healthy-volunteer facts. `raw_data_sources[0].access_details` now names the Synapse route, reconciling it with `raw_sources`. `intended_uses[0].usage_notes` absorbed the new-labels guidance formerly in `labeling_strategies`.

## 3. What was changed in the core record

The core record was re-derived by projection from the reconciled full record, so every change above propagates to whichever core slots exist. In addition:

- `distributions` was added, projecting the three new `file_collections` entries.
- `conforms_to_standard` is absent from the core record, matching the full record.
- The three `subsets` and the `variables` list have no counterpart in the core schema and do not appear.

Header block: `# Phase 4 reconciliation: completed` is present, as is `# Sources:` naming the full record.

## 4. What was left as-is, and why

**All confirmations.** Where the audit confirmed a value or omission as correct — `license`, `issued`, `created_on`, `last_updated_on`, `created_by`, `modified_by`, `compression`, `is_tabular`, `total_file_count`, `total_size_bytes`, `download_url`, `page`, `publisher`, `keywords`, `was_derived_from`, `use_repository`, `imputation_protocols`, `data_protection_impacts`, `annotation_analyses`, `parent_datasets`, `resources`, `existing_uses`, `third_party_sharing`, `raw_sources[0].access_url`, `version_access`, `related_datasets[*].relationship_type`, `intended_uses[0].use_category`, `discouraged_uses`, `prohibited_uses` shape, `is_deidentified`, `collection_consents`, `license_and_use_terms.data_use_permission`, `data_governance.accountable_organization`, `data_governance.committee_members` — nothing was altered.

**`data_governance.committee_contact`.** The audit flagged this for decision, noting that DACO is an office rather than a person and that `Person` requires an `id`. It remains omitted; the email address is recorded in `data_governance.notes` instead.

**`notes`.** The audit judged the AI-readiness table acceptable as residual content. Unchanged.

**`source_caveats` (record level).** The audit judged the handling correct. The text was extended to cover the hosting and `conforms_to` decisions made in this phase, but the six original conflict paragraphs are intact.

**`instances[1]` count omission.** The audit confirmed the deliberate omission of a total. Unchanged, and no total was computed.

**`prohibited_uses` / `discouraged_uses` placement.** The audit confirmed the split is right. Unchanged.

**`related_datasets` direction.** The audit confirmed `is_new_version_of` is directionally correct for all three earlier versions. Unchanged.

## Dispositions

| slot | disposition | record | reason |
|---|---|---|---|
| `id` | retained | both | Audit review found no ORCID anywhere in the bundle for either person; the DOI-based fragment base stands. |
| `creators[0].credit_roles` | added | both | Author-contributions statement in the feasibility publication maps to closed-enum values; roles narrated in prose belong in the declared field. |
| `creators[1].credit_roles` | added | both | As above for the second co-principal investigator. |
| `creators[0].description` | changed | both | Authorship-position commentary ("first-listed author") is a fact about the source document, not the creator. |
| `creators[12].description` | changed | both | Removed "last-listed author of version 3.1.0" for the same reason. |
| `creators[0].affiliations` | changed | both | Aligned with the nested `principal_investigator.affiliation` so one person carries one affiliation string. |
| `creators[15].description` | removed | both | "Lead investigator" for Bolser is unsupported: the documentation lists him with no role and Annex C does not include him. |
| `creators[8].description` | removed | both | Same unsupported bare role for Payne. |
| `creators[9].description` | removed | both | Same unsupported bare role for Dorr. |
| `creators[10].name` | changed | both | Restored the acute accent the source uses. |
| `creators[10].description` | removed | both | Unsupported bare role. |
| `creators[11].description` | removed | both | Unsupported bare role. |
| `creators[2].description` | changed | both | Absorbed the team-composition figures displaced from `purposes`. |
| `funders[0].grants[*].notes` | added | both | Distinguishes what each of the three award numbers is and which source states it. |
| `funders[0].source_caveats` | added | both | Records the two corrupted award-number renderings in the documentation and the tier-4 provenance of the award amount. |
| `funders[0].notes` | retained | both | The award amount and period remain, now flagged as tier-4-only in the caveat. |
| `purposes` | changed | both | Fourth entry removed: team composition is not a purpose and duplicated purpose 2. |
| `instances[0].label_description` | changed | both | Shortened to describe the label rather than restate the whole validation narrative already in `labeling_strategies`. |
| `instances[0].missing_information[*].missing` | changed | both | Corrected from scalar strings to lists. |
| `instances[1].data_substrate` | removed | both | Parquet is the distribution container, not the instance substrate; the digest directs omission where no term fits. |
| `instances[1].data_topic` | added | both | B2AI_TOPIC:37 (Waveform) is attested by the subject of the instance. |
| `subpopulations[0].distribution` | removed | both | The unequal-distribution statement concerns disease cohorts, not the demographic subpopulations named in `identification`. |
| `subpopulations[0].source_caveats` | added | both | Explains the omission. |
| `subsets` | added | full | Five adult disease cohorts with named per-condition diagnosis tables are attested; a supported omission the audit flagged. |
| `file_collections` | added | full | The bundle enumerates a three-folder tree with named member files and paths; a supported omission the audit flagged. |
| `distributions` | added | core | Projection of the new `file_collections`. |
| `content_warnings[0].content_warnings_present` | changed | both | Changed to `true` to resolve the contradiction with a populated `warnings` list. |
| `content_warnings[0].source_caveats` | changed | both | Rewritten to explain the resolution rather than assert two states. |
| `confidential_elements[0].confidentiality_details` | changed | both | Trailing access-route sentence removed; that content answers `data_governance`. |
| `collection_timeframes[0].timeframe_details` | changed | both | Award period and four-year phased plan removed; neither is a collection timeframe for the released cohort. |
| `variables` | changed | full | Exclusion note applied consistently across the five affected feature families; the two table-level entries moved to `file_collections`. |
| `acquisition_methods` | changed | both | The `was_inferred_derived` entry removed: no source answers the acquisition question that way for the derived features. |
| `collection_mechanisms[2]` | changed | both | Trailing clause about the initial release removed; it describes v1.0, not the referent. |
| `sampling_strategies[0].representative_verification` | removed | both | An absence-statement plus a plan; the substantive content moved to `why_not_representative`. |
| `sampling_strategies[0].why_not_representative` | changed | both | Absorbed the mitigation intention, in the source's own tense. |
| `sampling_strategies[0].strategies` | changed | both | Points to the per-cohort criteria now carried on the subset entries. |
| `raw_data_sources[0].access_details` | changed | both | Names the Synapse controlled-access route, reconciling it with `raw_sources`. |
| `cleaning_strategies[0]` | removed | both | "No data cleaning preprocessing was applied" is an absence-statement. |
| `cleaning_strategies[0].source_caveats` | added | both | The healthsheet negative is recorded as a caveat on the surviving audit-protocol entry. |
| `labeling_strategies[0].inter_annotator_agreement` | removed | both | "Not applicable" is an absence-statement; the fact is already in `annotations_per_item`. |
| `labeling_strategies[0].data_annotation_protocol` | changed | both | Guidance to future users moved to `intended_uses[0].usage_notes`. |
| `machine_annotation_tools[0].tool_accuracy` | removed | both | States the absence of an accuracy assessment; the same fact is already a `known_limitations` entry. |
| `machine_annotation_tools[0].tools` | changed | both | Normalised to bare names; URLs left to `external_resources`. |
| `participant_privacy[0].data_linkage` | removed | both | A contact prohibition, not a description of data linkage; relocated to `license_and_use_terms`. |
| `human_subject_research.regulatory_compliance` | changed | both | The data-monitoring-committee and drug/device negatives removed; three positive compliance facts retained. |
| `human_subject_research.special_populations` | changed | both | Added the maximum age and healthy-volunteer inclusion. |
| `at_risk_populations.guardian_consent` | removed | both | Pediatric provisions belonging to a separately published dataset. |
| `at_risk_populations.assent_procedures` | removed | both | As above. |
| `at_risk_populations.special_protections` | changed | both | Superseded plan about pediatric criteria removed. |
| `at_risk_populations.source_caveats` | added | both | Explains why the pediatric provisions are excluded. |
| `ethical_reviews[0].contact_person` | removed | both | Assigning the protocol PI as ethics-review contact is an inference, and the object carried a second affiliation string for one person. |
| `ethical_reviews[0].review_details` | changed | both | The PI and their department are stated in prose instead. |
| `informed_consent[0].consent_type` | changed | both | "written" narrowed the source, which describes paper, electronic and video modalities. |
| `consent_revocations[0].revocation_details` | changed | both | Longitudinal-consent sentence removed: a protocol provision, not a property of the release. |
| `participant_compensation[0].source_caveats` | added | both | Records that the amount was amended twice, so earlier participants may have received a different sum. |
| `license_and_use_terms.license_terms` | changed | both | Controlled-access workflow removed as duplicative of `data_governance`; the contact prohibition relocated here from `participant_privacy`. |
| `license_and_use_terms.contact_person` | retained | both | Still omitted: DACO is an office, and `Person` is the declared range. |
| `data_governance.appeal_process` | removed | both | A contract termination clause, not an appeal route for access decisions. |
| `data_governance.notes` | added | both | Carries the DACO contact address the bundle repeatedly gives. |
| `data_governance.source_caveats` | added | both | Explains the appeal-process omission. |
| `data_governance.committee_contact` | retained | both | Left omitted; the office is not a person and the schema declares `Person`. |
| `ip_restrictions.restrictions` | changed | both | Third-party negative and no-guarantee disclaimer removed from the restrictions list. |
| `ip_restrictions.notes` | added | both | The no-warranty statement recorded as context. |
| `regulatory_restrictions.hipaa_compliant` | removed | both | No source makes a compliance determination; the caveat admitted as much. |
| `regulatory_restrictions.regulatory_restrictions` | removed | both | "No export controls apply" is an absence-statement. |
| `regulatory_restrictions.other_compliance` | changed | both | Absorbed the HIPAA de-identification fact and the PII classification. |
| `regulatory_restrictions.source_caveats` | changed | both | Rewritten to explain both omissions. |
| `distribution_formats[*].format` | changed | both | Normalised to Parquet / TSV / JSON. |
| `distribution_formats[*].access_urls` | removed | both | Repeated the landing page already in `page`; the slot description distinguishes the two. |
| `distribution_dates[0].release_dates` | changed | both | Corrected from a scalar string to a list. |
| `maintainers` | changed | both | T-CAIREM entry removed: a past host of an earlier release, not a current maintainer. |
| `maintainers[*].name` | removed | both | Organisation names moved into `maintainer_details`, which the digest declares. |
| `updates.update_details` | changed | both | Retensed to the source's own future tense; the plan is no longer stated as current practice. |
| `retention_limit.retention_period` | changed | both | Narrowed to the archive; the DTUA and institutional regimes separated into `retention_details`. |
| `retention_limit.retention_details` | changed | both | Now distinguishes the three regimes explicitly. |
| `errata[3]` | removed | both | "No formal erratum document is published" is an absence-statement plus a pointer. |
| `extension_mechanism.extension_details` | changed | both | Restored "Health Data Nexus", which the source names, in place of a generalisation that read as current. |
| `external_resources[*]` | changed | both | Content moved from `name`/`description` into `notes`, the field the digest declares. |
| `related_datasets[4].source_caveats` | added | both | Records the two Zenodo artefacts named by different sources. |
| `related_datasets[0].notes` | changed | both | Added the separate Synapse route for pediatric raw audio. |
| `conforms_to` | changed | both | Rewritten to attribute the BIDS claim to the documentation and to the audio dataset it describes. |
| `conforms_to_standard` | removed | both | The evidence attaches the BIDS claim to the audio dataset, not this feature-only release. |
| `citation` | changed | both | Restored the acute accent in "Bélisle-Pipon" as the source writes it. |
| `intended_uses[0].usage_notes` | changed | both | Absorbed the new-labels guidance displaced from `labeling_strategies`. |
| `prohibited_uses[2].prohibition_reason` | changed | both | No-sale clause removed as triplicated; it remains in `license_and_use_terms`. |
| `source_caveats` | changed | both | Extended to cover the hosting and `conforms_to` decisions taken in this phase. |
| `notes` | retained | both | Audit judged the AI-readiness table acceptable as residual content. |
| `existing_uses` | retained | both | Audit downgraded its own finding to a confirmation. |
| `use_repository` | retained | both | Omission confirmed correct: the bundle answers the question in the negative. |
| `imputation_protocols` | retained | both | Omission confirmed correct. |
| `data_protection_impacts` | retained | both | Omission confirmed correct. |
| `annotation_analyses` | retained | both | Omission confirmed correct. |
| `total_file_count` | retained | both | No source states one; not computed. |
| `total_size_bytes` | retained | both | No source states one. |
| `is_tabular` | retained | both | No source characterises the dataset either way. |
| `compression` | retained | both | No source states a compression format. |
| `download_url` | retained | both | Correctly omitted; files are restricted. |
| `license` | retained | both | Supported verbatim by four tier-1 sources. |
| `issued` | retained | both | Matches the tier-1 publication date, with UTC offset. |
| `keywords` | retained | both | Taken verbatim from the v3.1.0 topics list. |
| `publisher` | retained | both | No declared prefix covers PhysioNet; URL is the correct fallback. |
| `was_derived_from` | retained | both | Supported by the tier-1 methods section. |
| `parent_datasets` | retained | both | Version relationships belong in `related_datasets`. |
| `resources` | retained | both | No component sub-datasets beyond the file collections. |
| `raw_sources[0].access_url` | retained | both | Declared range is `uri`; a URL is correct there. |
| `version_access.latest_version_doi` | retained | both | Correctly given as a `doi:` CURIE in a `uriorcurie` slot. |
| `discouraged_uses` | retained | both | Audit confirmed placement is right. |
| `third_party_sharing` | retained | both | Audit confirmed the tense reading is acceptable. |
| `is_deidentified` | retained | both | Audit found the k-anonymisation statement substantive rather than an absence-statement. |
| `collection_consents[0].consent_details` | retained | both | Audit found the five consent-scope negatives substantive: they define the permission granted. |
| `related_datasets[*].relationship_type` | retained | both | Audit confirmed direction is correct for all three earlier versions. |