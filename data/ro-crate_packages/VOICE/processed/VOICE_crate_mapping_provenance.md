# Crate → D4D Static Mapping — VOICE

Produced by `d4d rocrate map`. Every field below was placed by this
repo's own mapping table (`data/ro-crate_mapping/d4d_rocrate_interface_mapping.tsv`), not by an upstream
D4D-shaped rendering. No value is inferred: a field is filled only when
its declared path resolves in the crate.

- Crate metadata: `data/ro-crate_packages/VOICE/raw/ro-crate-metadata.json`
- Mapping table: `data/ro-crate_mapping/d4d_rocrate_interface_mapping.tsv` (137 rows applied)
- Validation: **PASS**

## Outcome

| Status | Rows | Meaning |
|--------|------|---------|
| filled | 48 | path resolved; value placed |
| empty | 31 | path valid but the crate has no value there |
| unresolvable | 4 | the table declares no crate path |
| unplaceable | 54 | no route into a `Dataset` record |

## Fidelity of what was filled

| Mapping type | Filled fields |
|---|---|
| closeMatch | 15 |
| exactMatch | 31 |
| narrowMatch | 1 |
| relatedMatch | 1 |

| Information loss | Filled fields |
|---|---|
| minimal | 11 |
| moderate | 6 |
| none | 31 |

Fields marked `moderate` or `high` loss carry a value that the mapping
table itself flags as an imperfect representation of the crate's
content. Treat them as weaker evidence than `none`/`minimal` fields.

## Per-field detail

| D4D path | Status | Mapping | Loss | Source path | Value / note |
|---|---|---|---|---|---|
| AnnotationAnalysis.description | filled | closeMatch | moderate | rai:dataAnnotationAnalysis | Questionnaire-based labels are generated using the standard scoring rules for each valida… |
| CleaningStrategy.description | filled | closeMatch | moderate | rai:dataManipulationProtocol | Prior to release, data are transformed to reduce re-identification risk and align with re… |
| Dataset.acquisition_methods | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollection'] | [{"description": "Prospective observational study conducted at multiple specialty clinics… |
| Dataset.annotation_analyses | filled | closeMatch | minimal | @graph[?@type='Dataset']['rai:dataAnnotationAnalysis'] | [{"description": "Questionnaire-based labels are generated using the standard scoring rul… |
| Dataset.citation | filled | exactMatch | none | @graph[?@type='Dataset']['citation'] | Bensoussan, Y., Sigaras, A., Rameau, A., Elemento, O., Powell, M., Dorr, D., Payne, P., R… |
| Dataset.cleaning_strategies | filled | closeMatch | minimal | @graph[?@type='Dataset']['rai:dataManipulationProtocol'] | [{"description": "Prior to release, data are transformed to reduce re-identification risk… |
| Dataset.collection_mechanisms | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollection'] | [{"description": "Prospective observational study conducted at multiple specialty clinics… |
| Dataset.collection_timeframes | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollectionTimeframe'] | [{"description": "Data collection for the adult flagship cohort began after project launc… |
| Dataset.confidential_elements | filled | exactMatch | none | @graph[?@type='Dataset']['rai:personalSensitiveInformation'] | [{"description": "The dataset encodes health-related information including diagnostic cat… |
| Dataset.created_by | filled | closeMatch | minimal | @graph[?@type='Dataset']['author'] | Yael Bensoussan; Alexandros Sigaras; Anais Rameau; Olivier Elemento; Maria Powell; David … |
| Dataset.creators | filled | closeMatch | minimal | @graph[?@type='Dataset']['author'] | [{"name": "Yael Bensoussan"}, {"name": "Alexandros Sigaras"}, {"name": "Anais Rameau"}, {… |
| Dataset.data_protection_impacts | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataSocialImpact'] | [{"description": "The project aims to create an ethically sourced, diverse voice dataset … |
| Dataset.description | filled | exactMatch | none | @graph[?@type='Dataset']['description'] | The human voice contains complex acoustic markers which have been linked to important hea… |
| Dataset.doi | filled | exactMatch | none | @graph[?@type='Dataset']['identifier'] | https://doi.org/10.13026/k81f-qr68 |
| Dataset.download_url | filled | exactMatch | none | @graph[?@type='Dataset']['contentUrl'] | file:///features/ppgs.parquet |
| Dataset.ethical_reviews | filled | exactMatch | none | @graph[?@type='Dataset']['ethicalReview'] | [{"name": "Ethical Review by Vardit Ravitsky at the Hastings Center for Bioethics"}] |
| Dataset.existing_uses | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataUseCases'] | [{"description": "Development, training and fine-tuning of machine-learning models that a… |
| Dataset.extension_mechanism | filled | closeMatch | moderate | @graph[?@type='Dataset']['license'] | {"name": "https://physionet.org/content/b2ai-voice/view-license/3.0.0/"} |
| Dataset.funders | filled | exactMatch | none | @graph[?@type='Dataset']['funder'] | [{"name": "Funded by the NIH Common Fund. Award #3Tf-OTOD03272001S2"}] |
| Dataset.future_use_impacts | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataSocialImpact'] | [{"description": "The project aims to create an ethically sourced, diverse voice dataset … |
| Dataset.id | filled | exactMatch | none | crate root identifier/@id | https://doi.org/10.13026/k81f-qr68 |
| Dataset.intended_uses | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataUseCases'] | [{"description": "Development, training and fine-tuning of machine-learning models that a… |
| Dataset.ip_restrictions | filled | closeMatch | minimal | @graph[?@type='Dataset']['conditionsOfAccess'] | {"name": "https://physionet.org/content/b2ai-voice/view-dua/3.0.0/"} |
| Dataset.issued | filled | exactMatch | none | @graph[?@type='Dataset']['datePublished'] | 2025-12-16T00:00:00Z |
| Dataset.keywords | filled | exactMatch | none | @graph[?@type='Dataset']['keywords'] | ["voice", "Voice as a biomarker", "Voice dataset", "Acoustic biomarker", "Speech analysis… |
| Dataset.known_biases | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataBiases'] | [{"description": "Sampling bias: participants are recruited from specialty clinics and as… |
| Dataset.known_limitations | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataLimitations'] | [{"description": "The feature-only release does not include raw audio waveforms or free-s… |
| Dataset.labeling_strategies | filled | closeMatch | minimal | @graph[?@type='Dataset']['rai:dataAnnotationProtocol'] | [{"description": "Annotations for this dataset consist primarily of clinical labels and q… |
| Dataset.license | filled | exactMatch | none | @graph[?@type='Dataset']['license'] | https://physionet.org/content/b2ai-voice/view-license/3.0.0/ |
| Dataset.license_and_use_terms | filled | closeMatch | moderate | @graph[?@type='Dataset']['license'] | {"name": "https://physionet.org/content/b2ai-voice/view-license/3.0.0/"} |
| Dataset.missing_data_documentation | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollectionMissingData'] | [{"description": "Phenotype tables include a row for a participant only when at least one… |
| Dataset.name | filled | exactMatch | none | @graph[?@type='Dataset']['name'] | B2AI Voice: An ethically-sourced, diverse voice dataset linked to health information |
| Dataset.other_tasks | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataUseCases'] | [{"description": "Development, training and fine-tuning of machine-learning models that a… |
| Dataset.preprocessing_strategies | filled | closeMatch | minimal | @graph[?@type='Dataset']['rai:dataPreprocessingProtocol'] | [{"description": "Raw audio waveforms are converted to mono and resampled to 16 kHz using… |
| Dataset.publisher | filled | exactMatch | none | @graph[?@type='Dataset']['publisher'] | PhysioNet |
| Dataset.purposes | filled | closeMatch | minimal | @graph[?@type='Dataset']['rai:dataUseCases'] | [{"description": "Development, training and fine-tuning of machine-learning models that a… |
| Dataset.raw_data_sources | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollectionRawData'] | [{"source_description": "The original raw data consist of high-quality voice, speech and … |
| Dataset.raw_sources | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataCollectionRawData'] | [{"description": "The original raw data consist of high-quality voice, speech and respira… |
| Dataset.regulatory_restrictions | filled | closeMatch | minimal | @graph[?@type='Dataset']['conditionsOfAccess'] | {"name": "https://physionet.org/content/b2ai-voice/view-dua/3.0.0/"} |
| Dataset.retention_limit | filled | narrowMatch | minimal | @graph[?@type='Dataset']['conditionsOfAccess'] | {"name": "https://physionet.org/content/b2ai-voice/view-dua/3.0.0/"} |
| Dataset.sensitive_elements | filled | exactMatch | none | @graph[?@type='Dataset']['rai:personalSensitiveInformation'] | [{"description": "The dataset encodes health-related information including diagnostic cat… |
| Dataset.tasks | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataUseCases'] | [{"description": "Development, training and fine-tuning of machine-learning models that a… |
| Dataset.title | filled | exactMatch | none | @graph[?@type='Dataset']['name'] | B2AI Voice: An ethically-sourced, diverse voice dataset linked to health information |
| Dataset.updates | filled | exactMatch | none | @graph[?@type='Dataset']['rai:dataReleaseMaintenancePlan'] | {"description": "Dataset releases follow a static versioning scheme managed through Physi… |
| Dataset.version | filled | exactMatch | none | @graph[?@type='Dataset']['version'] | 3.0.0 |
| Dataset.version_access | filled | relatedMatch | minimal | @graph[?@type='Dataset']['version'] | {"name": "3.0.0"} |
| LabelingStrategy.description | filled | closeMatch | moderate | rai:dataAnnotationProtocol | Annotations for this dataset consist primarily of clinical labels and questionnaire-deriv… |
| PreprocessingStrategy.description | filled | closeMatch | moderate | rai:dataPreprocessingProtocol | Raw audio waveforms are converted to mono and resampled to 16 kHz using anti-aliasing fil… |
| CleaningStrategy.pipeline_step | unplaceable | closeMatch | high | rai:dataManipulationProtocol | 'pipeline_step' is not a slot on CleaningStrategy |
| CleaningStrategy.step_type | unplaceable | closeMatch | high | rai:dataManipulationProtocol | 'step_type' is not a slot on CleaningStrategy |
| Dataset.addressing_gaps | empty | exactMatch | none | @graph[?@type='Dataset']['d4d:addressingGaps'] | @type=Dataset present but 'd4d:addressingGaps' empty or absent |
| Dataset.anomalies | empty | exactMatch | none | @graph[?@type='Dataset']['d4d:anomalies'] | @type=Dataset present but 'd4d:anomalies' empty or absent |
| Dataset.bytes | unplaceable | exactMatch | none | @graph[?@type='Dataset']['contentSize'] | 'bytes' is not a slot on Dataset |
| Dataset.compression | empty | closeMatch | minimal | @graph[?@type='Dataset']['evi:formats'] | @type=Dataset present but 'evi:formats' empty or absent |
| Dataset.conforms_to | empty | exactMatch | none | @graph[?@type='Dataset']['conformsTo'] | @type=Dataset present but 'conformsTo' empty or absent |
| Dataset.content_warnings | empty | exactMatch | none | @graph[?@type='Dataset']['d4d:contentWarnings'] | @type=Dataset present but 'd4d:contentWarnings' empty or absent |
| Dataset.created_on | empty | exactMatch | none | @graph[?@type='Dataset']['dateCreated'] | @type=Dataset present but 'dateCreated' empty or absent |
| Dataset.data_collectors | empty | relatedMatch | moderate | @graph[?@type='Dataset']['contributor'] | @type=Dataset present but 'contributor' empty or absent |
| Dataset.dialect | unplaceable | closeMatch | minimal | @graph[?@type='Dataset']['encodingFormat'] | 'dialect' is not a slot on Dataset |
| Dataset.discouraged_uses | empty | exactMatch | none | @graph[?@type='Dataset']['prohibitedUses'] | @type=Dataset present but 'prohibitedUses' empty or absent |
| Dataset.distribution_dates | empty | exactMatch | none | @graph[?@type='Dataset']['dateCreated'] | @type=Dataset present but 'dateCreated' empty or absent |
| Dataset.distribution_formats | empty | exactMatch | none | @graph[?@type='Dataset']['evi:formats'] | @type=Dataset present but 'evi:formats' empty or absent |
| Dataset.encoding | unplaceable | closeMatch | minimal | @graph[?@type='Dataset']['evi:formats'] | 'encoding' is not a slot on Dataset |
| Dataset.errata | empty | exactMatch | none | @graph[?@type='Dataset']['correction'] | @type=Dataset present but 'correction' empty or absent |
| Dataset.external_resource | unplaceable | closeMatch | minimal | @graph[?@type='Dataset']['relatedLink'] | 'external_resource' is not a slot on Dataset |
| Dataset.hash | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:md5'] | 'hash' is not a slot on Dataset |
| Dataset.human_subject_research | empty | exactMatch | none | @graph[?@type='Dataset']['d4d:humanSubject'] | @type=Dataset present but 'd4d:humanSubject' empty or absent |
| Dataset.imputation_protocols | empty | exactMatch | none | @graph[?@type='Dataset']['rai:imputationProtocol'] | @type=Dataset present but 'rai:imputationProtocol' empty or absent |
| Dataset.informed_consent | empty | exactMatch | none | @graph[?@type='Dataset']['d4d:informedConsent'] | @type=Dataset present but 'd4d:informedConsent' empty or absent |
| Dataset.instances | empty | relatedMatch | high | @graph[?@type='Dataset']['variableMeasured'] | @type=Dataset present but 'variableMeasured' empty or absent |
| Dataset.is_deidentified | empty | narrowMatch | minimal | @graph[?@type='Dataset']['rai:confidentialityLevel'] | @type=Dataset present but 'rai:confidentialityLevel' empty or absent |
| Dataset.is_tabular | empty | narrowMatch | minimal | @graph[?@type='Dataset']['encodingFormat'] | @type=Dataset present but 'encodingFormat' empty or absent |
| Dataset.language | empty | exactMatch | none | @graph[?@type='Dataset']['inLanguage'] | @type=Dataset present but 'inLanguage' empty or absent |
| Dataset.last_updated_on | empty | exactMatch | none | @graph[?@type='Dataset']['dateModified'] | @type=Dataset present but 'dateModified' empty or absent |
| Dataset.machine_annotation_analyses | unplaceable | closeMatch | minimal | @graph[?@type='Dataset']['rai:machineAnnotationTools'] | 'machine_annotation_analyses' is not a slot on Dataset |
| Dataset.maintainers | empty | relatedMatch | minimal | @graph[?@type='Dataset']['maintainer'] | @type=Dataset present but 'maintainer' empty or absent |
| Dataset.md5 | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:md5'] | 'md5' is not a slot on Dataset |
| Dataset.media_type | unplaceable | closeMatch | minimal | @graph[?@type='Dataset']['encodingFormat'] | 'media_type' is not a slot on Dataset |
| Dataset.modified_by | empty | closeMatch | minimal | @graph[?@type='Dataset']['contributor'] | @type=Dataset present but 'contributor' empty or absent |
| Dataset.page | empty | exactMatch | none | @graph[?@type='Dataset']['url'] | @type=Dataset present but 'url' empty or absent |
| Dataset.path | unplaceable | narrowMatch | minimal | @graph[?@type='Dataset']['contentUrl'] | 'path' is not a slot on Dataset |
| Dataset.prohibited_uses | empty | exactMatch | none | @graph[?@type='Dataset']['prohibitedUses'] | @type=Dataset present but 'prohibitedUses' empty or absent |
| Dataset.resources | empty | relatedMatch | moderate | @graph[?@type='Dataset']['hasPart'] | @type=Dataset present but 'hasPart' empty or absent |
| Dataset.sampling_strategies | empty | relatedMatch | moderate | @graph[?@type='Dataset']['d4d:samplingStrategy'] | @type=Dataset present but 'd4d:samplingStrategy' empty or absent |
| Dataset.sha256 | unplaceable | exactMatch | none | @graph[?@type='Dataset']['evi:sha256'] | 'sha256' is not a slot on Dataset |
| Dataset.status | empty | exactMatch | none | @graph[?@type='Dataset']['creativeWorkStatus'] | @type=Dataset present but 'creativeWorkStatus' empty or absent |
| Dataset.subpopulations | empty | relatedMatch | moderate | @graph[?@type='Dataset']['variableMeasured'] | @type=Dataset present but 'variableMeasured' empty or absent |
| Dataset.subsets | empty | relatedMatch | high | @graph[?@type='Dataset']['hasPart'] | @type=Dataset present but 'hasPart' empty or absent |
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
| LabelingStrategy.evidence_type | unplaceable | closeMatch | high | rai:dataAnnotationProtocol | 'evidence_type' is not a slot on LabelingStrategy |
| MachineAnnotation.tool_name | unplaceable | closeMatch | moderate | rai:machineAnnotationTools | no Dataset slot ranges over MachineAnnotation |
| Maintenance.frequency | unplaceable | closeMatch | moderate | rai:dataReleaseMaintenancePlan | no Dataset slot ranges over Maintenance |
| Maintenance.versioning_strategy | unplaceable | closeMatch | moderate | rai:dataReleaseMaintenancePlan | no Dataset slot ranges over Maintenance |
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
