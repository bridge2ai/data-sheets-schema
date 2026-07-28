# Crate → D4D Static Mapping — CHORUS

Produced by `d4d rocrate map`. Every field below was placed by this
repo's own mapping table (`data/ro-crate_mapping/d4d_rocrate_interface_mapping.tsv`), not by an upstream
D4D-shaped rendering. No value is inferred: a field is filled only when
its declared path resolves in the crate.

- Crate metadata: `data/ro-crate_packages/CHORUS/raw/ro-crate-metadata.json`
- Mapping table: `data/ro-crate_mapping/d4d_rocrate_interface_mapping.tsv` (137 rows applied)
- Validation: **PASS**

## Outcome

| Status | Rows | Meaning |
|--------|------|---------|
| filled | 32 | path resolved; value placed |
| empty | 47 | path valid but the crate has no value there |
| unresolvable | 4 | the table declares no crate path |
| unplaceable | 54 | no route into a `Dataset` record |

## Fidelity of what was filled

| Mapping type | Filled fields |
|---|---|
| closeMatch | 6 |
| exactMatch | 22 |
| narrowMatch | 1 |
| relatedMatch | 3 |

| Information loss | Filled fields |
|---|---|
| high | 1 |
| minimal | 6 |
| moderate | 3 |
| none | 22 |

Fields marked `moderate` or `high` loss carry a value that the mapping
table itself flags as an imperfect representation of the crate's
content. Treat them as weaker evidence than `none`/`minimal` fields.

## Per-field detail

| D4D path | Status | Mapping | Loss | Source path | Value / note |
|---|---|---|---|---|---|
| Dataset.acquisition_methods | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollection'] | [{"description": "Data are derived from routine clinical care at participating hospitals … |
| Dataset.citation | filled | exactMatch | none | @graph[?@type='Dataset']['citation'] | The CHoRUS for Clinical Care AI Network. The Bridge2AI CHoRUS for Clinical Care AI Datase… |
| Dataset.collection_mechanisms | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollection'] | [{"description": "Data are derived from routine clinical care at participating hospitals … |
| Dataset.confidential_elements | filled | exactMatch | none | @graph[?@type='Dataset']['rai:personalSensitiveInformation'] | [{"name": "CHoRUS operates within a secure enclave environment aligned with NIST 800-53 c… |
| Dataset.created_by | filled | closeMatch | minimal | @graph[?@type='Dataset']['author'] | Eric S. Rosenthal(1), Rishikesan Kamaleswaran(2), Yulia Levites Strekalova(3), Andrew E. … |
| Dataset.creators | filled | closeMatch | minimal | @graph[?@type='Dataset']['author'] | [{"description": "Eric S. Rosenthal(1), Rishikesan Kamaleswaran(2), Yulia Levites Strekal… |
| Dataset.description | filled | exactMatch | none | @graph[?@type='Dataset']['description'] | The Collaborative Hospital Repository Uniting Standards (CHoRUS) for Clinical Care AI is … |
| Dataset.doi | filled | exactMatch | none | @graph[?@type='Dataset']['identifier'] | https://doi.org/10.18130/V3/XNBOPG |
| Dataset.download_url | filled | exactMatch | none | @graph[?@type='Dataset']['contentUrl'] | http://chorus4ai.org/dataset |
| Dataset.ethical_reviews | filled | exactMatch | none | @graph[?@type='Dataset']['ethicalReview'] | [{"description": "Eric S. Rosenthal, Michael J. Young, Ishan Williams, Ashley Cordes, and… |
| Dataset.extension_mechanism | filled | closeMatch | moderate | @graph[?@type='Dataset']['license'] | {"name": "Data Use Agreement available at 'https://chorus4ai.org/dataset/'"} |
| Dataset.funders | filled | exactMatch | none | @graph[?@type='Dataset']['funder'] | [{"name": "NIH Common Fund OT2OD032701"}] |
| Dataset.id | filled | exactMatch | none | crate root identifier/@id | https://doi.org/10.18130/V3/XNBOPG |
| Dataset.ip_restrictions | filled | closeMatch | minimal | @graph[?@type='Dataset']['conditionsOfAccess'] | {"name": "https://chorus4ai.org/wp-content/uploads/2025/10/Data-Agreement-9.30.2025.docx"} |
| Dataset.issued | filled | exactMatch | none | @graph[?@type='Dataset']['datePublished'] | 2026-04-03T00:00:00Z |
| Dataset.keywords | filled | exactMatch | none | @graph[?@type='Dataset']['keywords'] | ["Bridge2AI", "CHoRUS", "Electronic health records", "physiological data", "medical image… |
| Dataset.known_biases | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataBiases'] | [{"description": "•\tReferral bias from tertiary/quaternary academic centers\n•\tSocioeco… |
| Dataset.known_limitations | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataLimitations'] | [{"description": "•\tObservational data; and not randomized; collected as real-world clin… |
| Dataset.license | filled | exactMatch | none | @graph[?@type='Dataset']['license'] | Data Use Agreement available at 'https://chorus4ai.org/dataset/' |
| Dataset.license_and_use_terms | filled | closeMatch | moderate | @graph[?@type='Dataset']['license'] | {"name": "Data Use Agreement available at 'https://chorus4ai.org/dataset/'"} |
| Dataset.missing_data_documentation | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollectionMissingData'] | [{"name": "Variable sampling rates across real-world data from hospital waveform systems … |
| Dataset.name | filled | exactMatch | none | @graph[?@type='Dataset']['name'] | CHoRUS RO-Crate Package |
| Dataset.publisher | filled | exactMatch | none | @graph[?@type='Dataset']['publisher'] | B2AI CHoRUS |
| Dataset.regulatory_restrictions | filled | closeMatch | minimal | @graph[?@type='Dataset']['conditionsOfAccess'] | {"name": "https://chorus4ai.org/wp-content/uploads/2025/10/Data-Agreement-9.30.2025.docx"} |
| Dataset.resources | filled | relatedMatch | moderate | @graph[?@type='Dataset']['hasPart'] | [{"id": "08cf7419-b94d-4508-8f64-c99c557351d7", "name": "CHoRUS RO-Crate EHR SubRoCrate"}… |
| Dataset.retention_limit | filled | narrowMatch | minimal | @graph[?@type='Dataset']['conditionsOfAccess'] | {"name": "https://chorus4ai.org/wp-content/uploads/2025/10/Data-Agreement-9.30.2025.docx"} |
| Dataset.sensitive_elements | filled | exactMatch | none | @graph[?@type='Dataset']['rai:personalSensitiveInformation'] | [{"name": "CHoRUS operates within a secure enclave environment aligned with NIST 800-53 c… |
| Dataset.subsets | filled | relatedMatch | high | @graph[?@type='Dataset']['hasPart'] | [{"id": "08cf7419-b94d-4508-8f64-c99c557351d7", "name": "CHoRUS RO-Crate EHR SubRoCrate"}… |
| Dataset.title | filled | exactMatch | none | @graph[?@type='Dataset']['name'] | CHoRUS RO-Crate Package |
| Dataset.updates | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataReleaseMaintenancePlan'] | {"description": "\n•\tVersioned dataset releases e.g., CHoRUS vX.Y)\n•\tRelease notes doc… |
| Dataset.version | filled | exactMatch | none | @graph[?@type='Dataset']['version'] | 1.0 Beta |
| Dataset.version_access | filled | relatedMatch | minimal | @graph[?@type='Dataset']['version'] | {"name": "1.0 Beta"} |
| AnnotationAnalysis.description | empty | closeMatch | moderate | rai:dataAnnotationAnalysis | 'rai:dataAnnotationAnalysis' not present on crate root |
| CleaningStrategy.description | empty | closeMatch | moderate | rai:dataManipulationProtocol | 'rai:dataManipulationProtocol' not present on crate root |
| CleaningStrategy.pipeline_step | unplaceable | closeMatch | high | rai:dataManipulationProtocol | 'pipeline_step' is not a slot on CleaningStrategy |
| CleaningStrategy.step_type | unplaceable | closeMatch | high | rai:dataManipulationProtocol | 'step_type' is not a slot on CleaningStrategy |
| Dataset.addressing_gaps | empty | exactMatch | none | @graph[?@type='Dataset']['d4d:addressingGaps'] | @type=Dataset present but 'd4d:addressingGaps' empty or absent |
| Dataset.annotation_analyses | empty | closeMatch | minimal | @graph[?@type='Dataset']['rai:dataAnnotationAnalysis'] | @type=Dataset present but 'rai:dataAnnotationAnalysis' empty or absent |
| Dataset.anomalies | empty | exactMatch | none | @graph[?@type='Dataset']['d4d:anomalies'] | @type=Dataset present but 'd4d:anomalies' empty or absent |
| Dataset.bytes | unplaceable | exactMatch | none | @graph[?@type='Dataset']['contentSize'] | 'bytes' is not a slot on Dataset |
| Dataset.cleaning_strategies | empty | closeMatch | minimal | @graph[?@type='Dataset']['rai:dataManipulationProtocol'] | @type=Dataset present but 'rai:dataManipulationProtocol' empty or absent |
| Dataset.collection_timeframes | empty | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollectionTimeframe'] | @type=Dataset present but 'rai:dataCollectionTimeframe' empty or absent |
| Dataset.compression | empty | closeMatch | minimal | @graph[?@type='Dataset']['evi:formats'] | @type=Dataset present but 'evi:formats' empty or absent |
| Dataset.conforms_to | empty | exactMatch | none | @graph[?@type='Dataset']['conformsTo'] | @type=Dataset present but 'conformsTo' empty or absent |
| Dataset.content_warnings | empty | exactMatch | none | @graph[?@type='Dataset']['d4d:contentWarnings'] | @type=Dataset present but 'd4d:contentWarnings' empty or absent |
| Dataset.created_on | empty | exactMatch | none | @graph[?@type='Dataset']['dateCreated'] | @type=Dataset present but 'dateCreated' empty or absent |
| Dataset.data_collectors | empty | relatedMatch | moderate | @graph[?@type='Dataset']['contributor'] | @type=Dataset present but 'contributor' empty or absent |
| Dataset.data_protection_impacts | empty | exactMatch | none | @graph[?@type='Dataset']['rai:dataSocialImpact'] | @type=Dataset present but 'rai:dataSocialImpact' empty or absent |
| Dataset.dialect | unplaceable | closeMatch | minimal | @graph[?@type='Dataset']['encodingFormat'] | 'dialect' is not a slot on Dataset |
| Dataset.discouraged_uses | empty | exactMatch | none | @graph[?@type='Dataset']['prohibitedUses'] | @type=Dataset present but 'prohibitedUses' empty or absent |
| Dataset.distribution_dates | empty | exactMatch | none | @graph[?@type='Dataset']['dateCreated'] | @type=Dataset present but 'dateCreated' empty or absent |
| Dataset.distribution_formats | empty | exactMatch | none | @graph[?@type='Dataset']['evi:formats'] | @type=Dataset present but 'evi:formats' empty or absent |
| Dataset.encoding | unplaceable | closeMatch | minimal | @graph[?@type='Dataset']['evi:formats'] | 'encoding' is not a slot on Dataset |
| Dataset.errata | empty | exactMatch | none | @graph[?@type='Dataset']['correction'] | @type=Dataset present but 'correction' empty or absent |
| Dataset.existing_uses | empty | exactMatch | none | @graph[?@type='Dataset']['rai:dataUseCases'] | @type=Dataset present but 'rai:dataUseCases' empty or absent |
| Dataset.external_resource | unplaceable | closeMatch | minimal | @graph[?@type='Dataset']['relatedLink'] | 'external_resource' is not a slot on Dataset |
| Dataset.future_use_impacts | empty | exactMatch | none | @graph[?@type='Dataset']['rai:dataSocialImpact'] | @type=Dataset present but 'rai:dataSocialImpact' empty or absent |
| Dataset.hash | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:md5'] | 'hash' is not a slot on Dataset |
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
| Dataset.machine_annotation_analyses | unplaceable | closeMatch | minimal | @graph[?@type='Dataset']['rai:machineAnnotationTools'] | 'machine_annotation_analyses' is not a slot on Dataset |
| Dataset.maintainers | empty | relatedMatch | minimal | @graph[?@type='Dataset']['maintainer'] | @type=Dataset present but 'maintainer' empty or absent |
| Dataset.md5 | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:md5'] | 'md5' is not a slot on Dataset |
| Dataset.media_type | unplaceable | closeMatch | minimal | @graph[?@type='Dataset']['encodingFormat'] | 'media_type' is not a slot on Dataset |
| Dataset.modified_by | empty | closeMatch | minimal | @graph[?@type='Dataset']['contributor'] | @type=Dataset present but 'contributor' empty or absent |
| Dataset.other_tasks | empty | exactMatch | none | @graph[?@type='Dataset']['rai:dataUseCases'] | @type=Dataset present but 'rai:dataUseCases' empty or absent |
| Dataset.page | empty | exactMatch | none | @graph[?@type='Dataset']['url'] | @type=Dataset present but 'url' empty or absent |
| Dataset.path | unplaceable | narrowMatch | minimal | @graph[?@type='Dataset']['contentUrl'] | 'path' is not a slot on Dataset |
| Dataset.preprocessing_strategies | empty | closeMatch | minimal | @graph[?@type='Dataset']['rai:dataPreprocessingProtocol'] | @type=Dataset present but 'rai:dataPreprocessingProtocol' empty or absent |
| Dataset.prohibited_uses | empty | exactMatch | none | @graph[?@type='Dataset']['prohibitedUses'] | @type=Dataset present but 'prohibitedUses' empty or absent |
| Dataset.purposes | empty | closeMatch | minimal | @graph[?@type='Dataset']['rai:dataUseCases'] | @type=Dataset present but 'rai:dataUseCases' empty or absent |
| Dataset.raw_data_sources | empty | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollectionRawData'] | @type=Dataset present but 'rai:dataCollectionRawData' empty or absent |
| Dataset.raw_sources | empty | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollectionRawData'] | @type=Dataset present but 'rai:dataCollectionRawData' empty or absent |
| Dataset.sampling_strategies | empty | relatedMatch | moderate | @graph[?@type='Dataset']['d4d:samplingStrategy'] | @type=Dataset present but 'd4d:samplingStrategy' empty or absent |
| Dataset.sha256 | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:sha256'] | 'sha256' is not a slot on Dataset |
| Dataset.status | empty | exactMatch | none | @graph[?@type='Dataset']['creativeWorkStatus'] | @type=Dataset present but 'creativeWorkStatus' empty or absent |
| Dataset.subpopulations | empty | relatedMatch | moderate | @graph[?@type='Dataset']['variableMeasured'] | @type=Dataset present but 'variableMeasured' empty or absent |
| Dataset.tasks | empty | exactMatch | none | @graph[?@type='Dataset']['rai:dataUseCases'] | @type=Dataset present but 'rai:dataUseCases' empty or absent |
| Dataset.total_size_bytes | empty | exactMatch | none | @graph[?@type='Dataset']['evi:totalContentSizeBytes'] | @type=Dataset present but 'evi:totalContentSizeBytes' empty or absent |
| Dataset.use_repository | empty | relatedMatch | minimal | @graph[?@type='Dataset']['relatedLink'] | @type=Dataset present but 'relatedLink' empty or absent |
| Dataset.variables | unresolvable | unmapped | high | N/A | not a crate path |
| Dataset.vulnerable_populations | unplaceable | exactMatch | none | @graph[?@type='Dataset']['rai:atRiskPopulations'] | 'vulnerable_populations' is not a slot on Dataset |
| Dataset.was_derived_from | empty | exactMatch | none | @graph[?@type='Dataset']['isBasedOn'] | @type=Dataset present but 'isBasedOn' empty or absent |
| DatasetCollection.completeness | unplaceable | exactMatch | none | @graph[?@type='Dataset']['additionalProperty'][?name='Completeness']['value'] | no Dataset slot ranges over DatasetCollection |
| DatasetCollection.contact_email | unplaceable | exactMatch | none | @graph[?@type='Dataset']['contactEmail'] | no Dataset slot ranges over DatasetCollection |
| DatasetCollection.data_governance_committee | unplaceable | exactMatch | none | @graph[?@type='Dataset']['dataGovernanceCommittee'] | no Dataset slot ranges over DatasetCollection |
| DatasetCollection.data_sharing_agreement | unplaceable | exactMatch | none | @graph[?@type='Dataset']['dataSharingAgreement'] | no Dataset slot ranges over DatasetCollection |
| DatasetCollection.funding_and_acknowledgements | unplaceable | closeMatch | minimal | @graph[?@type='Dataset']['funder'] | no Dataset slot ranges over DatasetCollection |
| DatasetCollection.parent_datasets | unplaceable | relatedMatch | minimal | @graph[?@type='Dataset']['isPartOf'] | no Dataset slot ranges over DatasetCollection |
| DatasetCollection.principal_investigator | unplaceable | exactMatch | none | @graph[?@type='Dataset']['principalInvestigator'] | no Dataset slot ranges over DatasetCollection |
| DatasetCollection.provenance_and_lineage | unplaceable | closeMatch | minimal | @graph[?@type='Dataset']['generatedBy'] | no Dataset slot ranges over DatasetCollection |
| DatasetCollection.quality_control | unplaceable | exactMatch | none | @graph[?@type='Dataset']['additionalProperty'][?name='Quality Control']['value'] | no Dataset slot ranges over DatasetCollection |
| DatasetCollection.related_datasets | unplaceable | relatedMatch | minimal | @graph[?@type='Dataset']['relatedLink'] | no Dataset slot ranges over DatasetCollection |
| DatasetCollection.summary_statistics | unplaceable | exactMatch | none | @graph[?@type='Dataset']['hasSummaryStatistics'] | no Dataset slot ranges over DatasetCollection |
| EthicalReview.irb_id | unplaceable | closeMatch | moderate | rai:ethicalReview | 'irb_id' is not a slot on EthicalReview |
| EvidenceMetadata.computation_count | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:computationCount'] | no Dataset slot ranges over EvidenceMetadata |
| EvidenceMetadata.dataset_count | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:datasetCount'] | no Dataset slot ranges over EvidenceMetadata |
| EvidenceMetadata.entities_with_checksums | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:entitiesWithChecksums'] | no Dataset slot ranges over EvidenceMetadata |
| EvidenceMetadata.entities_with_summary_stats | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:entitiesWithSummaryStats'] | no Dataset slot ranges over EvidenceMetadata |
| EvidenceMetadata.formats | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:formats'] | no Dataset slot ranges over EvidenceMetadata |
| EvidenceMetadata.schema_count | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:schemaCount'] | no Dataset slot ranges over EvidenceMetadata |
| EvidenceMetadata.software_count | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:softwareCount'] | no Dataset slot ranges over EvidenceMetadata |
| EvidenceMetadata.total_content_size_bytes | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:totalContentSizeBytes'] | no Dataset slot ranges over EvidenceMetadata |
| EvidenceMetadata.total_entities | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:totalEntities'] | no Dataset slot ranges over EvidenceMetadata |
| FormatDialect.delimiter | unplaceable | closeMatch | moderate | encodingFormat MIME parameter | no Dataset slot ranges over FormatDialect |
| FormatDialect.header | unplaceable | closeMatch | moderate | encodingFormat MIME parameter | no Dataset slot ranges over FormatDialect |
| HumanSubjectResearch.exemption | unplaceable | closeMatch | moderate | d4d:humanSubject | 'exemption' is not a slot on HumanSubjectResearch |
| Instance.counts | unresolvable | unmapped | high | N/A | not a crate path |
| Instance.data_topic | unresolvable | unmapped | high | N/A | not a crate path |
| Instance.instance_type | unresolvable | unmapped | high | N/A | not a crate path |
| LabelingStrategy.annotator_type | unplaceable | closeMatch | high | rai:dataAnnotationProtocol | 'annotator_type' is not a slot on LabelingStrategy |
| LabelingStrategy.description | empty | closeMatch | moderate | rai:dataAnnotationProtocol | 'rai:dataAnnotationProtocol' not present on crate root |
| LabelingStrategy.evidence_type | unplaceable | closeMatch | high | rai:dataAnnotationProtocol | 'evidence_type' is not a slot on LabelingStrategy |
| MachineAnnotation.tool_name | unplaceable | closeMatch | moderate | rai:machineAnnotationTools | no Dataset slot ranges over MachineAnnotation |
| Maintenance.frequency | unplaceable | closeMatch | moderate | rai:dataReleaseMaintenancePlan | no Dataset slot ranges over Maintenance |
| Maintenance.versioning_strategy | unplaceable | closeMatch | moderate | rai:dataReleaseMaintenancePlan | no Dataset slot ranges over Maintenance |
| PreprocessingStrategy.description | empty | closeMatch | moderate | rai:dataPreprocessingProtocol | 'rai:dataPreprocessingProtocol' not present on crate root |
| PreprocessingStrategy.pipeline_step | unplaceable | closeMatch | high | rai:dataPreprocessingProtocol | 'pipeline_step' is not a slot on PreprocessingStrategy |
| PreprocessingStrategy.step_type | unplaceable | closeMatch | high | rai:dataPreprocessingProtocol | 'step_type' is not a slot on PreprocessingStrategy |
| QualityControl.accuracy | unplaceable | exactMatch | none | @graph[?@type='Dataset']['additionalProperty'][?name='Accuracy']['value'] | no Dataset slot ranges over QualityControl |
| QualityControl.data_quality_report | unplaceable | exactMatch | none | @graph[?@type='Dataset']['additionalProperty'][?name='Data Quality Report']['value'] | no Dataset slot ranges over QualityControl |
| QualityControl.fda_compliant | unplaceable | exactMatch | none | @graph[?@type='Dataset']['fdaRegulated'] | no Dataset slot ranges over QualityControl |
| SamplingStrategy.details | unplaceable | relatedMatch | moderate | d4d:samplingStrategy | 'details' is not a slot on SamplingStrategy |
| SamplingStrategy.strategy_type | unplaceable | relatedMatch | moderate | d4d:samplingStrategy | 'strategy_type' is not a slot on SamplingStrategy |
| Subset.is_data_split | unplaceable | unmapped | high | N/A | no Dataset slot ranges over Subset |
| Subset.is_sub_population | unplaceable | unmapped | high | N/A | no Dataset slot ranges over Subset |
| ValidationMetrics.validation_method | unplaceable | exactMatch | none | @graph[?@type='Dataset']['additionalProperty'][?name='Validation Method']['value'] | no Dataset slot ranges over ValidationMetrics |
| Variable.name | unplaceable | unmapped | high | N/A | no Dataset slot ranges over Variable |
| Variable.type | unplaceable | unmapped | high | N/A | no Dataset slot ranges over Variable |
