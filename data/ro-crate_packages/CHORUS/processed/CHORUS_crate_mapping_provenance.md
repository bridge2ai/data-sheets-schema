# Crate → D4D Static Mapping — CHORUS

Produced by `d4d rocrate map`. Every field below was placed by this
repo's own mapping table (`data/ro-crate_mapping/d4d_rocrate_interface_mapping.tsv`), not by an upstream
D4D-shaped rendering. No value is inferred: a field is filled only when
its declared path resolves in the crate.

- Crate metadata: `data/ro-crate_packages/CHORUS/raw/ro-crate-metadata.json`
- Mapping table: `data/ro-crate_mapping/d4d_rocrate_interface_mapping.tsv` (136 table rows applied, plus the record's `id`, taken from the crate root)
- Validation: **PASS** — schema 3.0.0 / sha256 eb543e1597b29599952359818bc741b0f23eaa3a30e7aa8c63e60212c7bbb92f / 2026-10-05 (`src/data_sheets_schema/schema/data_sheets_schema_all.yaml`)
- Distinct top-level `Dataset` slots filled: 33 (from 33 filled rows, the `id` among them)

## Outcome

| Status | Rows | Meaning |
|--------|------|---------|
| filled | 33 | path resolved; value placed (includes the record's `id`, which no table row supplies) |
| subsumed | 1 | path resolved, but a `Dataset` row already placed the same crate value in the host slot |
| empty | 51 | path valid but the crate has no value there |
| unresolvable | 10 | the table declares no crate path |
| unplaceable | 42 | no route into a `Dataset` record; the mapping table says why for 42 of them: 11 out of scope, 31 awaiting an owner's decision |

## Fidelity of what was filled

| Mapping type | Filled fields |
|---|---|
| closeMatch | 6 |
| exactMatch | 23 |
| narrowMatch | 1 |
| relatedMatch | 3 |

| Information loss | Filled fields |
|---|---|
| high | 1 |
| minimal | 6 |
| moderate | 3 |
| none | 23 |

Fields marked `moderate` or `high` loss carry a value that the mapping
table itself flags as an imperfect representation of the crate's
content. Treat them as weaker evidence than `none`/`minimal` fields.

## Per-field detail

| D4D path | Status | Mapping | Loss | Source path | Value / note |
|---|---|---|---|---|---|
| DataGovernance.committee_name | filled | exactMatch | none | @graph[?@type='Dataset']['dataGovernanceCommittee'] | Eric Rosenthal, EROSENTHAL@mgh.harvard.edu |
| Dataset.acquisition_methods | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollection'] | [{"description": "Data are derived from routine clinical care at participating hospitals … — string -> InstanceAcquisition.description; wrapped scalar into a list |
| Dataset.citation | filled | exactMatch | none | @graph[?@type='Dataset']['citation'] | The CHoRUS for Clinical Care AI Network. The Bridge2AI CHoRUS for Clinical Care AI Datase… |
| Dataset.collection_mechanisms | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollection'] | [{"description": "Data are derived from routine clinical care at participating hospitals … — string -> CollectionMechanism.description; wrapped scalar into a list |
| Dataset.confidential_elements | filled | exactMatch | none | @graph[?@type='Dataset']['rai:personalSensitiveInformation'] | [{"name": "CHoRUS operates within a secure enclave environment aligned with NIST 800-53 c… — string -> Confidentiality.name |
| Dataset.created_by | filled | closeMatch | minimal | @graph[?@type='Dataset']['author'] | Eric S. Rosenthal(1), Rishikesan Kamaleswaran(2), Yulia Levites Strekalova(3), Andrew E. … |
| Dataset.creators | filled | closeMatch | minimal | @graph[?@type='Dataset']['author'] | [{"description": "Eric S. Rosenthal(1), Rishikesan Kamaleswaran(2), Yulia Levites Strekal… — string -> Creator.description; wrapped scalar into a list |
| Dataset.description | filled | exactMatch | none | @graph[?@type='Dataset']['description'] | The Collaborative Hospital Repository Uniting Standards (CHoRUS) for Clinical Care AI is … |
| Dataset.doi | filled | exactMatch | none | @graph[?@type='Dataset']['identifier'] | 10.18130/V3/XNBOPG — rewritten from the crate's https://doi.org/10.18130/V3/XNBOPG: resolver or `doi:` prefix removed, case kept |
| Dataset.download_url | filled | exactMatch | none | @graph[?@type='Dataset']['contentUrl'] | http://chorus4ai.org/dataset |
| Dataset.ethical_reviews | filled | exactMatch | none | @graph[?@type='Dataset']['ethicalReview'] | [{"description": "Eric S. Rosenthal, Michael J. Young, Ishan Williams, Ashley Cordes, and… — string -> EthicalReview.description; wrapped scalar into a list |
| Dataset.extension_mechanism | filled | closeMatch | moderate | @graph[?@type='Dataset']['license'] | {"name": "Data Use Agreement available at 'https://chorus4ai.org/dataset/'"} — string -> ExtensionMechanism.name |
| Dataset.funders | filled | exactMatch | none | @graph[?@type='Dataset']['funder'] | [{"name": "NIH Common Fund OT2OD032701"}] — string -> FundingMechanism.name; wrapped scalar into a list |
| Dataset.id | filled | exactMatch | none | crate root identifier/@id | doi:10.18130/V3/XNBOPG — rewritten from the crate's https://doi.org/10.18130/V3/XNBOPG: required by the schema; taken from the crate itself; a DOI is written as the doi: CURIE (#974) |
| Dataset.ip_restrictions | filled | closeMatch | minimal | @graph[?@type='Dataset']['conditionsOfAccess'] | {"name": "https://chorus4ai.org/wp-content/uploads/2025/10/Data-Agreement-9.30.2025.docx"} — string -> IPRestrictions.name |
| Dataset.issued | filled | exactMatch | none | @graph[?@type='Dataset']['datePublished'] | 2026-04-03T00:00:00Z — date -> date-time |
| Dataset.keywords | filled | exactMatch | none | @graph[?@type='Dataset']['keywords'] | ["Bridge2AI", "CHoRUS", "Electronic health records", "physiological data", "medical image… |
| Dataset.known_biases | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataBiases'] | [{"description": "•\tReferral bias from tertiary/quaternary academic centers\n•\tSocioeco… — string -> DatasetBias.description; wrapped scalar into a list |
| Dataset.known_limitations | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataLimitations'] | [{"description": "•\tObservational data; and not randomized; collected as real-world clin… — string -> DatasetLimitation.description; wrapped scalar into a list |
| Dataset.license | filled | exactMatch | none | @graph[?@type='Dataset']['license'] | Data Use Agreement available at 'https://chorus4ai.org/dataset/' |
| Dataset.license_and_use_terms | filled | closeMatch | moderate | @graph[?@type='Dataset']['license'] | {"name": "Data Use Agreement available at 'https://chorus4ai.org/dataset/'"} — string -> LicenseAndUseTerms.name |
| Dataset.missing_data_documentation | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollectionMissingData'] | [{"name": "Variable sampling rates across real-world data from hospital waveform systems … — string -> MissingDataDocumentation.name; wrapped scalar into a list |
| Dataset.name | filled | exactMatch | none | @graph[?@type='Dataset']['name'] | CHoRUS RO-Crate Package |
| Dataset.publisher | filled | exactMatch | none | @graph[?@type='Dataset']['publisher'] | B2AI CHoRUS |
| Dataset.regulatory_restrictions | filled | closeMatch | minimal | @graph[?@type='Dataset']['conditionsOfAccess'] | {"name": "https://chorus4ai.org/wp-content/uploads/2025/10/Data-Agreement-9.30.2025.docx"} — string -> ExportControlRegulatoryRestrictions.name |
| Dataset.resources | filled | relatedMatch | moderate | @graph[?@type='Dataset']['hasPart'] | [{"id": "08cf7419-b94d-4508-8f64-c99c557351d7", "name": "CHoRUS RO-Crate EHR SubRoCrate"}… — crate reference -> Dataset |
| Dataset.retention_limit | filled | narrowMatch | minimal | @graph[?@type='Dataset']['conditionsOfAccess'] | {"name": "https://chorus4ai.org/wp-content/uploads/2025/10/Data-Agreement-9.30.2025.docx"} — string -> RetentionLimits.name |
| Dataset.sensitive_elements | filled | exactMatch | none | @graph[?@type='Dataset']['rai:personalSensitiveInformation'] | [{"name": "CHoRUS operates within a secure enclave environment aligned with NIST 800-53 c… — string -> SensitiveElement.name |
| Dataset.subsets | filled | relatedMatch | high | @graph[?@type='Dataset']['hasPart'] | [{"id": "08cf7419-b94d-4508-8f64-c99c557351d7", "name": "CHoRUS RO-Crate EHR SubRoCrate"}… — crate reference -> DataSubset |
| Dataset.title | filled | exactMatch | none | @graph[?@type='Dataset']['name'] | CHoRUS RO-Crate Package |
| Dataset.updates | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataReleaseMaintenancePlan'] | {"description": "\n•\tVersioned dataset releases e.g., CHoRUS vX.Y)\n•\tRelease notes doc… — string -> UpdatePlan.description |
| Dataset.version | filled | exactMatch | none | @graph[?@type='Dataset']['version'] | 1.0 Beta |
| Dataset.version_access | filled | relatedMatch | minimal | @graph[?@type='Dataset']['version'] | {"name": "1.0 Beta"} — string -> VersionAccess.name |
| AnnotationAnalysis.description | empty | closeMatch | moderate | rai:dataAnnotationAnalysis | 'rai:dataAnnotationAnalysis' not present on crate root |
| CleaningStrategy.description | empty | closeMatch | moderate | rai:dataManipulationProtocol | 'rai:dataManipulationProtocol' not present on crate root |
| CleaningStrategy.pipeline_step | unplaceable | closeMatch | high | rai:dataManipulationProtocol | 'pipeline_step' is not a slot on CleaningStrategy; awaiting an owner's decision, as the table declares: No slot for a step's place in a pipeline on `CleaningStrategy` at schema 3.0.0, and the schema never had one (`git log -S pipeline_step`). |
| CleaningStrategy.step_type | unplaceable | closeMatch | high | rai:dataManipulationProtocol | 'step_type' is not a slot on CleaningStrategy; awaiting an owner's decision, as the table declares: No slot for a step type on `CleaningStrategy` at schema 3.0.0, and the schema never had one (`git log -S step_type`). |
| DataSubset.is_data_split | unresolvable | unmapped | high | N/A | not a crate path |
| DataSubset.is_subpopulation | unresolvable | unmapped | high | N/A | not a crate path |
| Dataset.addressing_gaps | empty | exactMatch | none | @graph[?@type='Dataset']['d4d:addressingGaps'] | @type=Dataset present but 'd4d:addressingGaps' empty or absent |
| Dataset.annotation_analyses | empty | closeMatch | minimal | @graph[?@type='Dataset']['rai:dataAnnotationAnalysis'] | @type=Dataset present but 'rai:dataAnnotationAnalysis' empty or absent |
| Dataset.anomalies | empty | exactMatch | none | @graph[?@type='Dataset']['d4d:anomalies'] | @type=Dataset present but 'd4d:anomalies' empty or absent |
| Dataset.at_risk_populations | empty | exactMatch | none | @graph[?@type='Dataset']['d4d:atRiskPopulations'] | @type=Dataset present but 'd4d:atRiskPopulations' empty or absent |
| Dataset.bytes | unplaceable | exactMatch | none | @graph[?@type='Dataset']['contentSize'] | 'bytes' is not a slot on Dataset; out of scope, as the table declares: `bytes` is a `File` slot, and `contentSize` is a rounded human string ('1.2 tb', '12.9 GB'), not a byte count. The record's size is `Dataset.total_size_bytes`, which its own row reads from the exact `evi:totalContentSizeBytes`. |
| Dataset.cleaning_strategies | empty | closeMatch | minimal | @graph[?@type='Dataset']['rai:dataManipulationProtocol'] | @type=Dataset present but 'rai:dataManipulationProtocol' empty or absent |
| Dataset.collection_timeframes | empty | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollectionTimeframe'] | @type=Dataset present but 'rai:dataCollectionTimeframe' empty or absent |
| Dataset.compression | empty | closeMatch | minimal | @graph[?@type='Dataset']['evi:formats'] | @type=Dataset present but 'evi:formats' empty or absent |
| Dataset.conforms_to | empty | exactMatch | none | @graph[?@type='Dataset']['conformsTo'] | @type=Dataset present but 'conformsTo' empty or absent |
| Dataset.content_warnings | empty | exactMatch | none | @graph[?@type='Dataset']['d4d:contentWarnings'] | @type=Dataset present but 'd4d:contentWarnings' empty or absent |
| Dataset.created_on | empty | exactMatch | none | @graph[?@type='Dataset']['dateCreated'] | @type=Dataset present but 'dateCreated' empty or absent |
| Dataset.data_collectors | empty | relatedMatch | moderate | @graph[?@type='Dataset']['contributor'] | @type=Dataset present but 'contributor' empty or absent |
| Dataset.data_protection_impacts | empty | exactMatch | none | @graph[?@type='Dataset']['rai:dataSocialImpact'] | @type=Dataset present but 'rai:dataSocialImpact' empty or absent |
| Dataset.dialect | unplaceable | closeMatch | minimal | @graph[?@type='Dataset']['encodingFormat'] | 'dialect' is not a slot on Dataset; out of scope, as the table declares: `dialect` is a `File` slot; `File` sits two levels below `Dataset` (`file_collections`, then `FileCollection.resources`), and a row places one level deep. |
| Dataset.discouraged_uses | empty | exactMatch | none | @graph[?@type='Dataset']['prohibitedUses'] | @type=Dataset present but 'prohibitedUses' empty or absent |
| Dataset.distribution_dates | empty | exactMatch | none | @graph[?@type='Dataset']['dateCreated'] | @type=Dataset present but 'dateCreated' empty or absent |
| Dataset.distribution_formats | empty | exactMatch | none | @graph[?@type='Dataset']['evi:formats'] | @type=Dataset present but 'evi:formats' empty or absent |
| Dataset.encoding | unplaceable | closeMatch | minimal | @graph[?@type='Dataset']['evi:formats'] | 'encoding' is not a slot on Dataset; out of scope, as the table declares: `encoding` is a `File` slot, one file's character encoding; `File` sits two levels below `Dataset` (`file_collections`, then `FileCollection.resources`), and a row places one level deep. `evi:formats` lists file formats, which the `Dataset.distribution_formats` row already reads. |
| Dataset.errata | empty | exactMatch | none | @graph[?@type='Dataset']['correction'] | @type=Dataset present but 'correction' empty or absent |
| Dataset.existing_uses | empty | exactMatch | none | @graph[?@type='Dataset']['rai:dataUseCases'] | @type=Dataset present but 'rai:dataUseCases' empty or absent |
| Dataset.external_resources | empty | closeMatch | minimal | @graph[?@type='Dataset']['relatedLink'] | @type=Dataset present but 'relatedLink' empty or absent |
| Dataset.future_use_impacts | empty | exactMatch | none | @graph[?@type='Dataset']['rai:dataSocialImpact'] | @type=Dataset present but 'rai:dataSocialImpact' empty or absent |
| Dataset.hash | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:md5'] | 'hash' is not a slot on Dataset; out of scope, as the table declares: `hash` is a `File` slot, the checksum of one file; `File` sits two levels below `Dataset` (`file_collections`, then `FileCollection.resources`), and a row places one level deep. |
| Dataset.human_subject_research | empty | exactMatch | none | @graph[?@type='Dataset']['d4d:humanSubject'] | @type=Dataset present but 'd4d:humanSubject' empty or absent |
| Dataset.imputation_protocols | empty | exactMatch | none | @graph[?@type='Dataset']['rai:imputationProtocol'] | @type=Dataset present but 'rai:imputationProtocol' empty or absent |
| Dataset.informed_consent | empty | exactMatch | none | @graph[?@type='Dataset']['d4d:informedConsent'] | @type=Dataset present but 'd4d:informedConsent' empty or absent |
| Dataset.instances | empty | relatedMatch | high | @graph[?@type='Dataset']['variableMeasured'] | @type=Dataset present but 'variableMeasured' empty or absent |
| Dataset.intended_uses | empty | exactMatch | none | @graph[?@type='Dataset']['rai:dataUseCases'] | @type=Dataset present but 'rai:dataUseCases' empty or absent |
| Dataset.is_deidentified | empty | narrowMatch | minimal | @graph[?@type='Dataset']['rai:confidentialityLevel'] | @type=Dataset present but 'rai:confidentialityLevel' empty or absent |
| Dataset.is_tabular | empty | narrowMatch | minimal | @graph[?@type='Dataset']['encodingFormat'] | @type=Dataset present but 'encodingFormat' empty or absent |
| Dataset.labeling_strategies | empty | closeMatch | minimal | @graph[?@type='Dataset']['rai:dataAnnotationProtocol'] | @type=Dataset present but 'rai:dataAnnotationProtocol' empty or absent |
| Dataset.language | empty | exactMatch | none | @graph[?@type='Dataset']['inLanguage'] | @type=Dataset present but 'inLanguage' empty or absent |
| Dataset.last_updated_on | empty | exactMatch | none | @graph[?@type='Dataset']['dateModified'] | @type=Dataset present but 'dateModified' empty or absent |
| Dataset.machine_annotation_tools | empty | closeMatch | minimal | @graph[?@type='Dataset']['rai:machineAnnotationTools'] | @type=Dataset present but 'rai:machineAnnotationTools' empty or absent |
| Dataset.maintainers | empty | relatedMatch | minimal | @graph[?@type='Dataset']['maintainer'] | @type=Dataset present but 'maintainer' empty or absent |
| Dataset.md5 | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:md5'] | 'md5' is not a slot on Dataset; out of scope, as the table declares: `md5` is a `File` slot, the checksum of one file; `File` sits two levels below `Dataset` (`file_collections`, then `FileCollection.resources`), and a row places one level deep. |
| Dataset.media_type | unplaceable | closeMatch | minimal | @graph[?@type='Dataset']['encodingFormat'] | 'media_type' is not a slot on Dataset; out of scope, as the table declares: `media_type` is a `File` slot; `File` sits two levels below `Dataset` (`file_collections`, then `FileCollection.resources`), and a row places one level deep. |
| Dataset.modified_by | empty | closeMatch | minimal | @graph[?@type='Dataset']['contributor'] | @type=Dataset present but 'contributor' empty or absent |
| Dataset.other_tasks | empty | exactMatch | none | @graph[?@type='Dataset']['rai:dataUseCases'] | @type=Dataset present but 'rai:dataUseCases' empty or absent |
| Dataset.page | empty | exactMatch | none | @graph[?@type='Dataset']['url'] | @type=Dataset present but 'url' empty or absent |
| Dataset.path | unplaceable | narrowMatch | minimal | @graph[?@type='Dataset']['contentUrl'] | 'path' is not a slot on Dataset; out of scope, as the table declares: `path` locates one file or one file collection (`File.path`, `FileCollection.path`), not the dataset. The root's `contentUrl` already fills `Dataset.download_url`. |
| Dataset.preprocessing_strategies | empty | closeMatch | minimal | @graph[?@type='Dataset']['rai:dataPreprocessingProtocol'] | @type=Dataset present but 'rai:dataPreprocessingProtocol' empty or absent |
| Dataset.prohibited_uses | empty | exactMatch | none | @graph[?@type='Dataset']['prohibitedUses'] | @type=Dataset present but 'prohibitedUses' empty or absent |
| Dataset.purposes | empty | closeMatch | minimal | @graph[?@type='Dataset']['rai:dataUseCases'] | @type=Dataset present but 'rai:dataUseCases' empty or absent |
| Dataset.raw_data_sources | empty | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollectionRawData'] | @type=Dataset present but 'rai:dataCollectionRawData' empty or absent |
| Dataset.raw_sources | empty | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollectionRawData'] | @type=Dataset present but 'rai:dataCollectionRawData' empty or absent |
| Dataset.sampling_strategies | empty | relatedMatch | moderate | @graph[?@type='Dataset']['d4d:samplingStrategy'] | @type=Dataset present but 'd4d:samplingStrategy' empty or absent |
| Dataset.sha256 | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:sha256'] | 'sha256' is not a slot on Dataset; out of scope, as the table declares: `sha256` is a `File` slot, the checksum of one file; `File` sits two levels below `Dataset` (`file_collections`, then `FileCollection.resources`), and a row places one level deep. |
| Dataset.status | empty | exactMatch | none | @graph[?@type='Dataset']['creativeWorkStatus'] | @type=Dataset present but 'creativeWorkStatus' empty or absent |
| Dataset.subpopulations | empty | relatedMatch | moderate | @graph[?@type='Dataset']['variableMeasured'] | @type=Dataset present but 'variableMeasured' empty or absent |
| Dataset.tasks | empty | exactMatch | none | @graph[?@type='Dataset']['rai:dataUseCases'] | @type=Dataset present but 'rai:dataUseCases' empty or absent |
| Dataset.total_size_bytes | empty | exactMatch | none | @graph[?@type='Dataset']['evi:totalContentSizeBytes'] | @type=Dataset present but 'evi:totalContentSizeBytes' empty or absent |
| Dataset.use_repository | empty | relatedMatch | minimal | @graph[?@type='Dataset']['relatedLink'] | @type=Dataset present but 'relatedLink' empty or absent |
| Dataset.variables | unresolvable | unmapped | high | N/A | not a crate path |
| Dataset.was_derived_from | empty | exactMatch | none | @graph[?@type='Dataset']['isBasedOn'] | @type=Dataset present but 'isBasedOn' empty or absent |
| DatasetCollection.completeness | unplaceable | exactMatch | none | @graph[?@type='Dataset']['additionalProperty'][?name='Completeness']['value'] | no Dataset slot ranges over DatasetCollection; awaiting an owner's decision, as the table declares: No completeness slot at schema 3.0.0; adding one is a schema decision. The crate roots also carry an unprefixed `completeness`, which this path does not read. |
| DatasetCollection.contact_email | unplaceable | exactMatch | none | @graph[?@type='Dataset']['contactEmail'] | no Dataset slot ranges over DatasetCollection; awaiting an owner's decision, as the table declares: No dataset-level contact slot at schema 3.0.0. An address fits `Person.email`, two levels down, under a `Person`-ranged slot such as `DataGovernance.committee_contact`; which one is a judgement. |
| DatasetCollection.data_sharing_agreement | unplaceable | exactMatch | none | @graph[?@type='Dataset']['dataSharingAgreement'] | no Dataset slot ranges over DatasetCollection; awaiting an owner's decision, as the table declares: No data-sharing-agreement slot at schema 3.0.0; whether `license_and_use_terms` or `ip_restrictions` should carry it is a judgement. No crate carries `dataSharingAgreement`. |
| DatasetCollection.funding_and_acknowledgements | unplaceable | closeMatch | minimal | @graph[?@type='Dataset']['funder'] | no Dataset slot ranges over DatasetCollection; awaiting an owner's decision, as the table declares: The successor, `Dataset.funders`, is already that row's target from the same `funder`. Remove the row, or retarget it to a `FundingMechanism` slot, where it would be reported subsumed. |
| DatasetCollection.parent_datasets | unplaceable | relatedMatch | minimal | @graph[?@type='Dataset']['isPartOf'] | no Dataset slot ranges over DatasetCollection; awaiting an owner's decision, as the table declares: The successor is `Dataset.parent_datasets` (slot_uri `schema:isPartOf`), but CHORUS's and CM4AI's `isPartOf` name an organization and a project, not datasets. Whether to place them is #4047's open question. |
| DatasetCollection.principal_investigator | unplaceable | exactMatch | none | @graph[?@type='Dataset']['principalInvestigator'] | no Dataset slot ranges over DatasetCollection; out of scope, as the table declares: `principal_investigator` is a slot only on `Creator` (range `Person`), under `Dataset.creators`, which its own row fills from `author`. The crate value is free text naming a person; making a Creator or Person of it is a structural decision, not a rename. |
| DatasetCollection.provenance_and_lineage | unplaceable | closeMatch | minimal | @graph[?@type='Dataset']['generatedBy'] | no Dataset slot ranges over DatasetCollection; awaiting an owner's decision, as the table declares: No provenance or lineage slot at schema 3.0.0. `generatedBy` names the computation that made the data; `Dataset.was_derived_from`, read from `isBasedOn`, names a source, not that. |
| DatasetCollection.quality_control | unplaceable | exactMatch | none | @graph[?@type='Dataset']['additionalProperty'][?name='Quality Control']['value'] | no Dataset slot ranges over DatasetCollection; awaiting an owner's decision, as the table declares: No quality-control slot at schema 3.0.0. No crate carries this `additionalProperty`. |
| DatasetCollection.related_datasets | unplaceable | relatedMatch | minimal | @graph[?@type='Dataset']['relatedLink'] | no Dataset slot ranges over DatasetCollection; awaiting an owner's decision, as the table declares: The successor `Dataset.related_datasets` ranges over `DatasetRelationship`, which requires a `relationship_type`; `relatedLink` states none, so a placed value would fail the schema. The `Dataset.external_resources` and `Dataset.use_repository` rows already read `relatedLink`. |
| DatasetCollection.summary_statistics | unplaceable | exactMatch | none | @graph[?@type='Dataset']['hasSummaryStatistics'] | no Dataset slot ranges over DatasetCollection; awaiting an owner's decision, as the table declares: No summary-statistics slot at schema 3.0.0. No crate carries `hasSummaryStatistics`. |
| EthicalReview.irb_id | unplaceable | closeMatch | moderate | rai:ethicalReview | 'irb_id' is not a slot on EthicalReview; awaiting an owner's decision, as the table declares: Left as it is pending #4043, which asks the owner to rule on this row's crate side (`rai:ethicalReview`). `irb_id` is not a slot on `EthicalReview`; `HumanSubjectResearch.irb_approval` is the nearest. |
| EvidenceMetadata.computation_count | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:computationCount'] | no Dataset slot ranges over EvidenceMetadata; awaiting an owner's decision, as the table declares: No `EvidenceMetadata` class and no slot for FAIRSCAPE evidence-graph counts at schema 3.0.0; adding one is a schema decision. |
| EvidenceMetadata.dataset_count | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:datasetCount'] | no Dataset slot ranges over EvidenceMetadata; awaiting an owner's decision, as the table declares: No `EvidenceMetadata` class and no slot for FAIRSCAPE evidence-graph counts at schema 3.0.0; adding one is a schema decision. |
| EvidenceMetadata.entities_with_checksums | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:entitiesWithChecksums'] | no Dataset slot ranges over EvidenceMetadata; awaiting an owner's decision, as the table declares: No `EvidenceMetadata` class and no slot for FAIRSCAPE evidence-graph counts at schema 3.0.0; adding one is a schema decision. |
| EvidenceMetadata.entities_with_summary_stats | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:entitiesWithSummaryStats'] | no Dataset slot ranges over EvidenceMetadata; awaiting an owner's decision, as the table declares: No `EvidenceMetadata` class and no slot for FAIRSCAPE evidence-graph counts at schema 3.0.0; adding one is a schema decision. |
| EvidenceMetadata.formats | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:formats'] | no Dataset slot ranges over EvidenceMetadata; awaiting an owner's decision, as the table declares: The successor, `Dataset.distribution_formats`, is already that row's target from the same `evi:formats`, so a retarget would place the value twice. Remove the row, or keep it as a documented duplicate. |
| EvidenceMetadata.schema_count | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:schemaCount'] | no Dataset slot ranges over EvidenceMetadata; awaiting an owner's decision, as the table declares: No `EvidenceMetadata` class and no slot for FAIRSCAPE evidence-graph counts at schema 3.0.0; adding one is a schema decision. |
| EvidenceMetadata.software_count | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:softwareCount'] | no Dataset slot ranges over EvidenceMetadata; awaiting an owner's decision, as the table declares: No `EvidenceMetadata` class and no slot for FAIRSCAPE evidence-graph counts at schema 3.0.0; adding one is a schema decision. |
| EvidenceMetadata.total_content_size_bytes | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:totalContentSizeBytes'] | no Dataset slot ranges over EvidenceMetadata; awaiting an owner's decision, as the table declares: The successor, `Dataset.total_size_bytes`, is already that row's target from the same `evi:totalContentSizeBytes`, so a retarget would place the value twice. Remove the row, or keep it as a documented duplicate. |
| EvidenceMetadata.total_entities | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:totalEntities'] | no Dataset slot ranges over EvidenceMetadata; awaiting an owner's decision, as the table declares: No `EvidenceMetadata` class and no slot for FAIRSCAPE evidence-graph counts at schema 3.0.0; adding one is a schema decision. |
| FormatDialect.delimiter | unplaceable | closeMatch | moderate | encodingFormat MIME parameter | no Dataset slot ranges over FormatDialect; out of scope, as the table declares: `FormatDialect` describes one file's CSV dialect, and no `Dataset` slot ranges over it. The source is prose, not a crate path. |
| FormatDialect.header | unplaceable | closeMatch | moderate | encodingFormat MIME parameter | no Dataset slot ranges over FormatDialect; out of scope, as the table declares: `FormatDialect` describes one file's CSV dialect, and no `Dataset` slot ranges over it. The source is prose, not a crate path. |
| HumanSubjectResearch.exemption | unplaceable | closeMatch | moderate | d4d:humanSubject | 'exemption' is not a slot on HumanSubjectResearch; awaiting an owner's decision, as the table declares: No `exemption` slot on `HumanSubjectResearch` at schema 3.0.0; `regulatory_compliance` names frameworks, not an exemption. The crates carry `humanSubjectExemption`, not the `d4d:humanSubject` this row names. |
| Instance.counts | unresolvable | unmapped | high | N/A | not a crate path |
| Instance.data_topic | unresolvable | unmapped | high | N/A | not a crate path |
| Instance.instance_type | unresolvable | unmapped | high | N/A | not a crate path |
| LabelingStrategy.annotator_type | unplaceable | closeMatch | high | rai:dataAnnotationProtocol | 'annotator_type' is not a slot on LabelingStrategy; awaiting an owner's decision, as the table declares: No slot for an annotator type on `LabelingStrategy` at schema 3.0.0, and the schema never had one (`git log -S annotator_type`); `annotator_demographics` describes annotators, not their type. |
| LabelingStrategy.description | empty | closeMatch | moderate | rai:dataAnnotationProtocol | 'rai:dataAnnotationProtocol' not present on crate root |
| LabelingStrategy.evidence_type | unplaceable | closeMatch | high | rai:dataAnnotationProtocol | 'evidence_type' is not a slot on LabelingStrategy; awaiting an owner's decision, as the table declares: No slot for an ECO evidence type on `LabelingStrategy` at schema 3.0.0, and the schema never had one (`git log -S evidence_type`). |
| MachineAnnotationTools.tools | empty | closeMatch | moderate | rai:machineAnnotationTools | 'rai:machineAnnotationTools' not present on crate root |
| Maintenance.versioning_strategy | unplaceable | closeMatch | moderate | rai:dataReleaseMaintenancePlan | no Dataset slot ranges over Maintenance; awaiting an owner's decision, as the table declares: The schema has no `Maintenance` class. A versioning strategy fits neither `UpdatePlan.update_details` (planned update types) nor `VersionAccess.version_details` without a judgement. |
| PreprocessingStrategy.description | empty | closeMatch | moderate | rai:dataPreprocessingProtocol | 'rai:dataPreprocessingProtocol' not present on crate root |
| PreprocessingStrategy.pipeline_step | unplaceable | closeMatch | high | rai:dataPreprocessingProtocol | 'pipeline_step' is not a slot on PreprocessingStrategy; awaiting an owner's decision, as the table declares: No slot for a step's place in a pipeline on `PreprocessingStrategy` at schema 3.0.0, and the schema never had one (`git log -S pipeline_step`). |
| PreprocessingStrategy.step_type | unplaceable | closeMatch | high | rai:dataPreprocessingProtocol | 'step_type' is not a slot on PreprocessingStrategy; awaiting an owner's decision, as the table declares: No slot for a step type on `PreprocessingStrategy` at schema 3.0.0, and the schema never had one (`git log -S step_type`). |
| QualityControl.accuracy | unplaceable | exactMatch | none | @graph[?@type='Dataset']['additionalProperty'][?name='Accuracy']['value'] | no Dataset slot ranges over QualityControl; awaiting an owner's decision, as the table declares: No `QualityControl` class and no accuracy slot at schema 3.0.0. No crate carries this `additionalProperty`. |
| QualityControl.data_quality_report | unplaceable | exactMatch | none | @graph[?@type='Dataset']['additionalProperty'][?name='Data Quality Report']['value'] | no Dataset slot ranges over QualityControl; awaiting an owner's decision, as the table declares: No `QualityControl` class and no data-quality-report slot at schema 3.0.0. No crate carries this `additionalProperty`. |
| QualityControl.fda_compliant | unplaceable | exactMatch | none | @graph[?@type='Dataset']['fdaRegulated'] | no Dataset slot ranges over QualityControl; awaiting an owner's decision, as the table declares: No `QualityControl` class and no FDA slot at schema 3.0.0. `fdaRegulated` is a boolean (CHORUS true, VOICE false); whether `HumanSubjectResearch.regulatory_compliance` or `ExportControlRegulatoryRestrictions.other_compliance` should carry it is a judgement. |
| SamplingStrategy.description | unresolvable | relatedMatch | moderate | d4d:samplingStrategy | not a crate path |
| SamplingStrategy.strategies | unresolvable | relatedMatch | moderate | d4d:samplingStrategy | not a crate path |
| UpdatePlan.frequency | subsumed | closeMatch | moderate | rai:dataReleaseMaintenancePlan | Dataset.updates already carries this crate value (rai:dataReleaseMaintenancePlan); not placed a second time (#2915) |
| ValidationMetrics.validation_method | unplaceable | exactMatch | none | @graph[?@type='Dataset']['additionalProperty'][?name='Validation Method']['value'] | no Dataset slot ranges over ValidationMetrics; awaiting an owner's decision, as the table declares: No `ValidationMetrics` class and no validation-method slot at schema 3.0.0. No crate carries this `additionalProperty`. |
| VariableMetadata.data_type | unresolvable | unmapped | high | N/A | not a crate path |
| VariableMetadata.variable_name | unresolvable | unmapped | high | N/A | not a crate path |
