# data-sheets-schema

A LinkML schema for Datasheets for Datasets.

URI: https://w3id.org/bridge2ai/data-sheets-schema

Name: data-sheets-schema



## Classes

| Class | Description |
| --- | --- |
| [DatasetProperty](DatasetProperty.md) | Represents a single property of a dataset, or a set of related properties |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[AddressingGap](AddressingGap.md) | Was there a specific gap that needed to be filled by creation of the dataset? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[AnnotationAnalysis](AnnotationAnalysis.md) | Analysis of annotation quality, inter-annotator agreement metrics, and system... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[CleaningStrategy](CleaningStrategy.md) | Was any cleaning of the data done (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[CollectionConsent](CollectionConsent.md) | Did the individuals in question consent to the collection and use of their da... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[CollectionMechanism](CollectionMechanism.md) | What mechanisms or procedures were used to collect the data (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[CollectionNotification](CollectionNotification.md) | Were the individuals in question notified about the data collection? If so, p... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[CollectionTimeframe](CollectionTimeframe.md) | Over what timeframe was the data collected, and does this timeframe match the... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Confidentiality](Confidentiality.md) | Does the dataset contain data that might be confidential (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ConsentRevocation](ConsentRevocation.md) | If consent was obtained, were the consenting individuals provided with a mech... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ContentWarning](ContentWarning.md) | Does the dataset contain any data that might be offensive, insulting, threate... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Creator](Creator.md) | Who created the dataset (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DataAnomaly](DataAnomaly.md) | Are there any errors, sources of noise, or redundancies in the dataset? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DataCollector](DataCollector.md) | Who was involved in the data collection (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DataProtectionImpact](DataProtectionImpact.md) | Has an analysis of the potential impact of the dataset and its use on data su... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DatasetBias](DatasetBias.md) | Documents known biases present in the dataset |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DatasetLimitation](DatasetLimitation.md) | Documents known limitations of the dataset that may affect its use or interpr... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DatasetRelationship](DatasetRelationship.md) | Typed relationship to another dataset, enabling precise specification of how ... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Deidentification](Deidentification.md) | Is it possible to identify individuals in the dataset, either directly or ind... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DirectCollection](DirectCollection.md) | Indicates whether the data was collected directly from the individuals in que... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DiscouragedUse](DiscouragedUse.md) | Are there tasks for which the dataset should not be used? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DistributionDate](DistributionDate.md) | When will the dataset be distributed? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DistributionFormat](DistributionFormat.md) | How will the dataset be distributed (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Erratum](Erratum.md) | Is there an erratum? If so, please provide a link or other access point |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[EthicalReview](EthicalReview.md) | Were any ethical or compliance review processes conducted (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ExistingUse](ExistingUse.md) | Has the dataset been used for any tasks already? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ExportControlRegulatoryRestrictions](ExportControlRegulatoryRestrictions.md) | Do any export controls or other regulatory restrictions apply to the dataset ... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ExtensionMechanism](ExtensionMechanism.md) | If others want to extend/augment/build on/contribute to the dataset, is there... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ExternalResource](ExternalResource.md) | Is the dataset self-contained or does it rely on external resources (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[FundingMechanism](FundingMechanism.md) | Who funded the creation of the dataset? If there is an associated grant, plea... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[FutureUseImpact](FutureUseImpact.md) | Is there anything about the dataset's composition or collection that might im... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[HumanSubjectCompensation](HumanSubjectCompensation.md) | Information about compensation or incentives provided to human research parti... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[HumanSubjectResearch](HumanSubjectResearch.md) | Information about whether the dataset involves human subjects research and wh... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ImputationProtocol](ImputationProtocol.md) | Description of data imputation methodology, including techniques used to hand... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[InformedConsent](InformedConsent.md) | Details about informed consent procedures used in human subjects research |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Instance](Instance.md) | What do the instances that comprise the dataset represent (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[InstanceAcquisition](InstanceAcquisition.md) | Describes how data associated with each instance was acquired (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[IntendedUse](IntendedUse.md) | Explicit statement of intended uses for this dataset |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[IPRestrictions](IPRestrictions.md) | Have any third parties imposed IP-based or other restrictions on the data ass... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[LabelingStrategy](LabelingStrategy.md) | Was any labeling of the data done (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[LicenseAndUseTerms](LicenseAndUseTerms.md) | Will the dataset be distributed under a copyright or other IP license, and/or... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[MachineAnnotationTools](MachineAnnotationTools.md) | Automated or machine-learning-based annotation tools used in dataset creation... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Maintainer](Maintainer.md) | Who will be supporting/hosting/maintaining the dataset? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[MissingDataDocumentation](MissingDataDocumentation.md) | Documentation of missing data in the dataset, including patterns, causes, and... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[MissingInfo](MissingInfo.md) | Is any information missing from individual instances? (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[OtherTask](OtherTask.md) | What other tasks could the dataset be used for? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ParticipantPrivacy](ParticipantPrivacy.md) | Information about privacy protections and anonymization procedures for human ... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[PreprocessingStrategy](PreprocessingStrategy.md) | Was any preprocessing of the data done (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ProhibitedUse](ProhibitedUse.md) | Explicit statement of prohibited or forbidden uses for this dataset |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Purpose](Purpose.md) | For what purpose was the dataset created? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[RawData](RawData.md) | Was the "raw" data saved in addition to the preprocessed/cleaned/labeled data... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[RawDataSource](RawDataSource.md) | Description of raw data sources before preprocessing, cleaning, or labeling |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Relationships](Relationships.md) | Are relationships between individual instances made explicit (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[RetentionLimits](RetentionLimits.md) | If the dataset relates to people, are there applicable limits on the retentio... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[SamplingStrategy](SamplingStrategy.md) | Does the dataset contain all possible instances, or is it a sample (not neces... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[SensitiveElement](SensitiveElement.md) | Does the dataset contain data that might be considered sensitive (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Splits](Splits.md) | Are there recommended data splits (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Subpopulation](Subpopulation.md) | Does the dataset identify any subpopulations (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Task](Task.md) | Was there a specific task in mind for the dataset's application? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ThirdPartySharing](ThirdPartySharing.md) | Will the dataset be distributed to third parties outside of the entity (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[UpdatePlan](UpdatePlan.md) | Will the dataset be updated (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[UseRepository](UseRepository.md) | Is there a repository that links to any or all papers or systems that use the... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[VariableMetadata](VariableMetadata.md) | Metadata describing an individual variable, field, or column in a dataset |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[VersionAccess](VersionAccess.md) | Will older versions of the dataset continue to be supported/hosted/maintained... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[VulnerablePopulations](VulnerablePopulations.md) | Information about protections for vulnerable populations in human subjects re... |
| [FormatDialect](FormatDialect.md) | Additional format information for a file |
| [NamedThing](NamedThing.md) | A generic grouping for any identifiable entity |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Grant](Grant.md) | The name and/or identifier of the specific mechanism providing monetary suppo... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Information](Information.md) | Grouping for datasets and data files |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Dataset](Dataset.md) | A single component of related observations and/or information that can be rea... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DataSubset](DataSubset.md) | A subset of a dataset, likely containing multiple files of multiple potential... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DatasetCollection](DatasetCollection.md) | A collection of related datasets, likely containing multiple files of multipl... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Organization](Organization.md) | Represents a group or organization |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Grantor](Grantor.md) | The name and/or identifier of the organization providing monetary support  or... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Person](Person.md) | An individual human being |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Software](Software.md) | A software program or library |



## Slots

| Slot | Description |
| --- | --- |
| [access_details](access_details.md) | Information on how to access or retrieve the raw source data |
| [access_url](access_url.md) | URL or access point for the raw data |
| [access_urls](access_urls.md) | Details of the distribution channel(s) or format(s) |
| [acquisition_details](acquisition_details.md) | Details on how data was acquired for each instance |
| [acquisition_methods](acquisition_methods.md) |  |
| [addressing_gaps](addressing_gaps.md) |  |
| [affected_subsets](affected_subsets.md) | Specific subsets or features of the dataset affected by this bias |
| [affiliation](affiliation.md) | The organization(s) to which the person belongs in the context of this datase... |
| [affiliations](affiliations.md) | Organizations with which the creator or team is affiliated |
| [agreement_metric](agreement_metric.md) | Type of agreement metric used (Cohen's kappa, Fleiss' kappa, Krippendorff's a... |
| [analysis_method](analysis_method.md) | Methodology used to assess annotation quality and resolve disagreements |
| [annotation_analyses](annotation_analyses.md) | Analysis of annotation quality and inter-annotator agreement |
| [annotation_quality_details](annotation_quality_details.md) | Additional details on annotation quality assessment and findings |
| [annotations_per_item](annotations_per_item.md) | Number of annotations collected per data item |
| [annotator_demographics](annotator_demographics.md) | Demographic information about annotators, if available and relevant (e |
| [anomalies](anomalies.md) |  |
| [anomaly_details](anomaly_details.md) | Details on errors, noise sources, or redundancies in the dataset |
| [anonymization_method](anonymization_method.md) | What methods were used to anonymize or de-identify participant data? Include ... |
| [archival](archival.md) | Indication whether official archival versions of external resources are inclu... |
| [assent_procedures](assent_procedures.md) | For research involving minors, what assent procedures were used? How was deve... |
| [bias_description](bias_description.md) | Detailed description of how this bias manifests in the dataset, including aff... |
| [bias_type](bias_type.md) | The type of bias identified, using standardized categories from the Artificia... |
| [bytes](bytes.md) | Size of the data in bytes |
| [categories](categories.md) | The permitted categories or values for a categorical variable |
| [citation](citation.md) | Recommended citation for this dataset in DataCite or BibTeX format |
| [cleaning_details](cleaning_details.md) | Details on data cleaning procedures applied |
| [cleaning_strategies](cleaning_strategies.md) |  |
| [collection_details](collection_details.md) | Details on direct vs |
| [collection_mechanisms](collection_mechanisms.md) |  |
| [collection_timeframes](collection_timeframes.md) |  |
| [collector_details](collector_details.md) | Details on who collected the data and their compensation |
| [comment_prefix](comment_prefix.md) |  |
| [compensation_amount](compensation_amount.md) | What was the amount or value of compensation provided? Include currency or eq... |
| [compensation_provided](compensation_provided.md) | Were participants compensated for their participation? |
| [compensation_rationale](compensation_rationale.md) | What was the rationale for the compensation structure? How was the amount det... |
| [compensation_type](compensation_type.md) | What type of compensation was provided (e |
| [compression](compression.md) | compression format used, if any |
| [confidential_elements](confidential_elements.md) |  |
| [confidential_elements_present](confidential_elements_present.md) | Indicates whether any confidential data elements are present |
| [confidentiality_details](confidentiality_details.md) | Details on confidential data elements and handling procedures |
| [confidentiality_level](confidentiality_level.md) | Confidentiality classification of the dataset indicating level of access rest... |
| [conforms_to](conforms_to.md) |  |
| [conforms_to_class](conforms_to_class.md) |  |
| [conforms_to_schema](conforms_to_schema.md) |  |
| [consent_details](consent_details.md) | Details on how consent was requested, provided, and documented |
| [consent_documentation](consent_documentation.md) | How is consent documented? Include references to consent forms or procedures ... |
| [consent_obtained](consent_obtained.md) | Was informed consent obtained from all participants? |
| [consent_scope](consent_scope.md) | What specific uses did participants consent to? Are there limitations on data... |
| [consent_type](consent_type.md) | What type of consent was obtained (e |
| [contact_person](contact_person.md) | Contact person for questions about ethical review |
| [content_warnings](content_warnings.md) |  |
| [content_warnings_present](content_warnings_present.md) | Indicates whether any content warnings are needed |
| [contribution_url](contribution_url.md) | URL for contribution guidelines or process |
| [counts](counts.md) | How many instances are there in total (of each type, if appropriate)? |
| [created_by](created_by.md) |  |
| [created_on](created_on.md) |  |
| [creators](creators.md) |  |
| [credit_roles](credit_roles.md) | Contributor roles using the CRediT (Contributor Roles Taxonomy) for the princ... |
| [data_annotation_platform](data_annotation_platform.md) | Platform or tool used for annotation (e |
| [data_annotation_protocol](data_annotation_protocol.md) | Annotation methodology, tasks, and protocols followed during labeling |
| [data_collectors](data_collectors.md) |  |
| [data_linkage](data_linkage.md) | Can this dataset be linked to other datasets in ways that might compromise pa... |
| [data_protection_impacts](data_protection_impacts.md) |  |
| [data_substrate](data_substrate.md) | Type of data (e |
| [data_topic](data_topic.md) | General topic of each instance (e |
| [data_type](data_type.md) | The data type of the variable (e |
| [data_use_permission](data_use_permission.md) | Structured data use permissions using the Data Use Ontology (DUO) |
| [deidentification_details](deidentification_details.md) | Details on de-identification procedures and residual risks |
| [delimiter](delimiter.md) |  |
| [derivation](derivation.md) | Description of how this variable was derived or calculated from other variabl... |
| [description](description.md) | A human-readable description for a thing |
| [dialect](dialect.md) |  |
| [disagreement_patterns](disagreement_patterns.md) | Systematic patterns in annotator disagreements (e |
| [discouraged_uses](discouraged_uses.md) |  |
| [discouragement_details](discouragement_details.md) | Details on tasks for which the dataset should not be used |
| [distribution](distribution.md) |  |
| [distribution_dates](distribution_dates.md) |  |
| [distribution_formats](distribution_formats.md) |  |
| [doi](doi.md) | digital object identifier |
| [double_quote](double_quote.md) |  |
| [download_url](download_url.md) | URL from which the data can be downloaded |
| [email](email.md) | The email address of the person |
| [encoding](encoding.md) | the character encoding of the data |
| [end_date](end_date.md) | End date of data collection |
| [errata](errata.md) |  |
| [erratum_details](erratum_details.md) | Details on any errata or corrections to the dataset |
| [erratum_url](erratum_url.md) | URL or access point for the erratum |
| [ethical_reviews](ethical_reviews.md) |  |
| [ethics_review_board](ethics_review_board.md) | What ethics review board(s) reviewed this research? Include institution names... |
| [examples](examples.md) | List of examples of known/previous uses of the dataset |
| [existing_uses](existing_uses.md) |  |
| [extension_details](extension_details.md) | Details on extension mechanisms, contribution validation, and communication |
| [extension_mechanism](extension_mechanism.md) |  |
| [external_resources](external_resources.md) | Links or identifiers for external resources |
| [format](format.md) | The file format, physical medium, or dimensions of a resource |
| [frequency](frequency.md) | How often updates are planned (e |
| [funders](funders.md) |  |
| [future_guarantees](future_guarantees.md) | Explanation of any commitments that external resources will remain available ... |
| [future_use_impacts](future_use_impacts.md) |  |
| [governance_committee_contact](governance_committee_contact.md) | Contact person for data governance committee |
| [grant_number](grant_number.md) | The alphanumeric identifier for the grant |
| [grantor](grantor.md) | Name/identifier of the organization providing monetary or resource support |
| [grants](grants.md) | Grant mechanisms supporting dataset creation |
| [guardian_consent](guardian_consent.md) | For participants unable to provide their own consent, how was guardian or sur... |
| [handling_strategy](handling_strategy.md) | Strategy used to handle missing data (e |
| [hash](hash.md) | hash of the data |
| [header](header.md) |  |
| [hipaa_compliant](hipaa_compliant.md) | Indicates compliance with the Health Insurance Portability and Accountability... |
| [human_subject_research](human_subject_research.md) | Information about whether dataset involves human subjects research, including... |
| [id](id.md) | A unique identifier for a thing |
| [identifiable_elements_present](identifiable_elements_present.md) | Indicates whether data subjects can be identified |
| [identification](identification.md) |  |
| [identifiers_removed](identifiers_removed.md) | List of identifier types removed during de-identification |
| [impact_details](impact_details.md) | Details on potential impacts, risks, and mitigation strategies |
| [imputation_method](imputation_method.md) | Specific imputation technique used (mean, median, mode, forward fill, backwar... |
| [imputation_protocols](imputation_protocols.md) | Data imputation methodology and techniques |
| [imputation_rationale](imputation_rationale.md) | Justification for the imputation approach chosen, including assumptions made ... |
| [imputation_validation](imputation_validation.md) | Methods used to validate imputation quality (if any) |
| [imputed_fields](imputed_fields.md) | Fields or columns where imputation was applied |
| [informed_consent](informed_consent.md) | Details about informed consent procedures, including consent type, documentat... |
| [instance_type](instance_type.md) | Multiple types of instances? (e |
| [instances](instances.md) |  |
| [intended_uses](intended_uses.md) | Explicit intended and recommended uses for this dataset |
| [inter_annotator_agreement](inter_annotator_agreement.md) | Measure of agreement between annotators (e |
| [inter_annotator_agreement_score](inter_annotator_agreement_score.md) | Measured agreement between annotators (e |
| [involves_human_subjects](involves_human_subjects.md) | Does this dataset involve human subjects research? |
| [ip_restrictions](ip_restrictions.md) |  |
| [irb_approval](irb_approval.md) | Was Institutional Review Board (IRB) approval obtained? Include approval numb... |
| [is_data_split](is_data_split.md) | Is this subset a split of the larger dataset, e |
| [is_deidentified](is_deidentified.md) |  |
| [is_direct](is_direct.md) | Whether collection was direct from individuals |
| [is_identifier](is_identifier.md) | Indicates whether this variable serves as a unique identifier or key for reco... |
| [is_random](is_random.md) | Indicates whether the sample is random |
| [is_representative](is_representative.md) | Indicates whether the sample is representative of the larger set |
| [is_sample](is_sample.md) | Indicates whether it is a sample of a larger set |
| [is_sensitive](is_sensitive.md) | Indicates whether this variable contains sensitive information (e |
| [is_shared](is_shared.md) | Boolean indicating whether the dataset is distributed to parties external to ... |
| [is_subpopulation](is_subpopulation.md) | Is this subset a subpopulation of the larger dataset, e |
| [is_tabular](is_tabular.md) |  |
| [issued](issued.md) |  |
| [keywords](keywords.md) |  |
| [known_biases](known_biases.md) | Known biases present in the dataset that may affect fairness, representativen... |
| [known_limitations](known_limitations.md) | Known limitations of the dataset that may affect its use or interpretation |
| [label](label.md) | Is there a label or target associated with each instance? |
| [label_description](label_description.md) | If labeled, what pattern or format do labels follow? |
| [labeling_details](labeling_details.md) | Details on labeling/annotation procedures and quality metrics |
| [labeling_strategies](labeling_strategies.md) |  |
| [language](language.md) | language in which the information is expressed |
| [last_updated_on](last_updated_on.md) |  |
| [latest_version_doi](latest_version_doi.md) | DOI or URL of the latest dataset version |
| [license](license.md) |  |
| [license_and_use_terms](license_and_use_terms.md) |  |
| [license_terms](license_terms.md) | Description of the dataset's license and terms of use (including links, costs... |
| [limitation_description](limitation_description.md) | Detailed description of the limitation and its implications |
| [limitation_type](limitation_type.md) | Category of limitation (e |
| [machine_annotation_tools](machine_annotation_tools.md) | Automated annotation tools used in dataset creation |
| [maintainer_details](maintainer_details.md) | Details on who will support, host, or maintain the dataset |
| [maintainers](maintainers.md) |  |
| [maximum_value](maximum_value.md) | The maximum value that the variable can take |
| [md5](md5.md) | md5 hash of the data |
| [measurement_technique](measurement_technique.md) | The technique or method used to measure this variable |
| [mechanism_details](mechanism_details.md) | Details on mechanisms or procedures used to collect the data |
| [media_type](media_type.md) | The media type of the data |
| [method](method.md) | Method used for de-identification (e |
| [minimum_value](minimum_value.md) | The minimum value that the variable can take |
| [missing](missing.md) | Description of the missing data fields or elements |
| [missing_data_causes](missing_data_causes.md) | Known or suspected causes of missing data (e |
| [missing_data_documentation](missing_data_documentation.md) | Documentation of missing data patterns and handling strategies |
| [missing_data_patterns](missing_data_patterns.md) | Description of patterns in missing data (e |
| [missing_information](missing_information.md) | References to one or more MissingInfo objects describing missing data |
| [missing_value_code](missing_value_code.md) | Code(s) used to represent missing values for this variable |
| [mitigation_strategy](mitigation_strategy.md) | Steps taken or recommended to mitigate this bias |
| [modified_by](modified_by.md) |  |
| [name](name.md) | A human-readable name for a thing |
| [notification_details](notification_details.md) | Details on how individuals were notified about data collection |
| [orcid](orcid.md) | ORCID (Open Researcher and Contributor ID) - a persistent digital identifier ... |
| [other_compliance](other_compliance.md) | Other regulatory compliance frameworks applicable to this dataset (e |
| [other_tasks](other_tasks.md) |  |
| [page](page.md) |  |
| [parent_datasets](parent_datasets.md) | Parent datasets that this dataset is part of or derived from |
| [participant_compensation](participant_compensation.md) | Compensation or incentives provided to human research participants |
| [participant_privacy](participant_privacy.md) | Privacy protections and anonymization procedures for human research participa... |
| [path](path.md) |  |
| [precision](precision.md) | The precision or number of decimal places for numeric variables |
| [preprocessing_details](preprocessing_details.md) | Details on preprocessing steps applied to the data |
| [preprocessing_strategies](preprocessing_strategies.md) |  |
| [principal_investigator](principal_investigator.md) | A key individual (Principal Investigator) responsible for or overseeing datas... |
| [privacy_techniques](privacy_techniques.md) | What privacy-preserving techniques were applied (e |
| [prohibited_uses](prohibited_uses.md) | Explicitly prohibited or forbidden uses for this dataset |
| [prohibition_reason](prohibition_reason.md) | Reason why this use is prohibited (e |
| [publisher](publisher.md) |  |
| [purposes](purposes.md) |  |
| [quality_notes](quality_notes.md) | Notes about data quality, reliability, or known issues specific to this varia... |
| [quote_char](quote_char.md) |  |
| [raw_data_details](raw_data_details.md) | Details on raw data availability and access procedures |
| [raw_data_format](raw_data_format.md) | Format of the raw data before any preprocessing |
| [raw_data_sources](raw_data_sources.md) | Description of raw data sources before preprocessing |
| [raw_sources](raw_sources.md) |  |
| [recommended_mitigation](recommended_mitigation.md) | Recommended approaches for users to address this limitation |
| [regulatory_compliance](regulatory_compliance.md) | What regulatory frameworks govern this human subjects research (e |
| [regulatory_restrictions](regulatory_restrictions.md) |  |
| [reidentification_risk](reidentification_risk.md) | What is the assessed risk of re-identification? What measures were taken to m... |
| [related_datasets](related_datasets.md) | Related datasets with typed relationships (e |
| [relationship_details](relationship_details.md) | Details on relationships between instances (e |
| [relationship_type](relationship_type.md) | The type of relationship (e |
| [release_dates](release_dates.md) | Dates or timeframe for dataset release |
| [repository_details](repository_details.md) | Details on the repository of known dataset uses |
| [repository_url](repository_url.md) | URL to a repository of known dataset uses |
| [representative_verification](representative_verification.md) | Explanation of how representativeness was validated or verified |
| [resources](resources.md) | Sub-resources or component datasets |
| [response](response.md) | Short explanation describing the primary purpose of creating the dataset |
| [restrictions](restrictions.md) | Description of any restrictions or fees associated with external resources |
| [retention_details](retention_details.md) | Details on data retention limits and enforcement procedures |
| [retention_limit](retention_limit.md) |  |
| [retention_period](retention_period.md) | Time period for data retention |
| [review_details](review_details.md) | Details on ethical review processes, outcomes, and supporting documentation |
| [reviewing_organization](reviewing_organization.md) | Organization that conducted the ethical review (e |
| [revocation_details](revocation_details.md) | Details on consent revocation mechanisms and procedures |
| [role](role.md) | Role of the data collector (e |
| [same_as](same_as.md) | URL of a reference web resource that is the same as this dataset |
| [sampling_strategies](sampling_strategies.md) |  |
| [scope_impact](scope_impact.md) | How this limitation affects the scope or applicability of the dataset |
| [sensitive_elements](sensitive_elements.md) |  |
| [sensitive_elements_present](sensitive_elements_present.md) | Indicates whether sensitive data elements are present |
| [sensitivity_details](sensitivity_details.md) | Details on sensitive data elements present and handling procedures |
| [sha256](sha256.md) | sha256 hash of the data |
| [source_data](source_data.md) | Description of the larger set from which the sample was drawn, if any |
| [source_description](source_description.md) | Detailed description of where raw data comes from (e |
| [source_type](source_type.md) | Type of raw source (sensor, database, user input, web scraping, etc |
| [special_populations](special_populations.md) | Does the research involve any special populations that require additional pro... |
| [special_protections](special_protections.md) | What additional protections were implemented for vulnerable populations? Incl... |
| [split_details](split_details.md) | Details on recommended data splits and their rationale |
| [start_date](start_date.md) | Start date of data collection |
| [status](status.md) |  |
| [strategies](strategies.md) | Description of the sampling strategy (deterministic, probabilistic, etc |
| [subpopulation_elements_present](subpopulation_elements_present.md) | Indicates whether any subpopulations are explicitly identified |
| [subpopulations](subpopulations.md) |  |
| [subsets](subsets.md) |  |
| [target_dataset](target_dataset.md) | The dataset that this relationship points to |
| [task_details](task_details.md) | Details on other potential tasks the dataset could be used for |
| [tasks](tasks.md) |  |
| [themes](themes.md) | Themes associated with the data |
| [timeframe_details](timeframe_details.md) | Details on the collection timeframe and relationship to data creation dates |
| [title](title.md) | the official title of the element |
| [tool_accuracy](tool_accuracy.md) | Known accuracy or performance metrics for the automated tools (if available) |
| [tool_descriptions](tool_descriptions.md) | Descriptions of what each tool does in the annotation process and what types ... |
| [tools](tools.md) | List of automated annotation tools with their versions |
| [unit](unit.md) | The unit of measurement for the variable, preferably using QUDT units (http:/... |
| [update_details](update_details.md) | Details on update plans, responsible parties, and communication methods |
| [updates](updates.md) |  |
| [url](url.md) |  |
| [usage_notes](usage_notes.md) | Notes or caveats about using the dataset for intended purposes |
| [use_category](use_category.md) | Category of intended use (e |
| [use_repository](use_repository.md) |  |
| [used_software](used_software.md) | What software was used as part of this dataset property? |
| [variable_name](variable_name.md) | The name or identifier of the variable as it appears in the data files |
| [variables](variables.md) | Metadata describing individual variables, fields, or columns in the dataset |
| [version](version.md) |  |
| [version_access](version_access.md) |  |
| [version_details](version_details.md) | Details on version support policies and obsolescence communication |
| [versions_available](versions_available.md) | List of available versions with metadata |
| [vulnerable_groups_included](vulnerable_groups_included.md) | Are any vulnerable populations included (e |
| [vulnerable_populations](vulnerable_populations.md) | Information about protections for vulnerable populations (e |
| [warnings](warnings.md) |  |
| [was_derived_from](was_derived_from.md) |  |
| [was_directly_observed](was_directly_observed.md) | Whether the data was directly observed |
| [was_inferred_derived](was_inferred_derived.md) | Whether the data was inferred or derived from other data |
| [was_reported_by_subjects](was_reported_by_subjects.md) | Whether the data was reported directly by the subjects themselves |
| [was_validated_verified](was_validated_verified.md) | Whether the data was validated or verified in any way |
| [why_missing](why_missing.md) | Explanation of why each piece of data is missing |
| [why_not_representative](why_not_representative.md) | Explanation of why the sample is not representative, if applicable |
| [withdrawal_mechanism](withdrawal_mechanism.md) | How can participants withdraw their consent? What procedures are in place for... |


## Enumerations

| Enumeration | Description |
| --- | --- |
| [BiasTypeEnum](BiasTypeEnum.md) | Types of bias that may be present in datasets |
| [Boolean](Boolean.md) |  |
| [ComplianceStatusEnum](ComplianceStatusEnum.md) | Compliance status for regulatory frameworks |
| [CompressionEnum](CompressionEnum.md) |  |
| [ConfidentialityLevelEnum](ConfidentialityLevelEnum.md) | Confidentiality classification levels for datasets indicating the degree of a... |
| [CreatorOrMaintainerEnum](CreatorOrMaintainerEnum.md) | Types of agents (persons or organizations) involved in dataset creation or ma... |
| [CRediTRoleEnum](CRediTRoleEnum.md) | Contributor roles based on the CRediT (Contributor Roles Taxonomy) |
| [DatasetRelationshipTypeEnum](DatasetRelationshipTypeEnum.md) | Standardized types of relationships between datasets, based on DataCite Metad... |
| [DataUsePermissionEnum](DataUsePermissionEnum.md) | Data use permissions and restrictions based on the Data Use Ontology (DUO) |
| [EncodingEnum](EncodingEnum.md) |  |
| [FormatEnum](FormatEnum.md) |  |
| [LimitationTypeEnum](LimitationTypeEnum.md) | Types of limitations that may affect dataset use or interpretation |
| [MediaTypeEnum](MediaTypeEnum.md) |  |
| [VariableTypeEnum](VariableTypeEnum.md) | Common data types for variables |
| [VersionTypeEnum](VersionTypeEnum.md) | Type of version change using semantic versioning principles |


## Types

| Type | Description |
| --- | --- |
| [Boolean](Boolean.md) | A binary (true or false) value |
| [Curie](Curie.md) | a compact URI |
| [Date](Date.md) | a date (year, month and day) in an idealized calendar |
| [DateOrDatetime](DateOrDatetime.md) | Either a date or a datetime |
| [Datetime](Datetime.md) | The combination of a date and time |
| [Decimal](Decimal.md) | A real number with arbitrary precision that conforms to the xsd:decimal speci... |
| [Double](Double.md) | A real number that conforms to the xsd:double specification |
| [Float](Float.md) | A real number that conforms to the xsd:float specification |
| [Integer](Integer.md) | An integer |
| [Jsonpath](Jsonpath.md) | A string encoding a JSON Path |
| [Jsonpointer](Jsonpointer.md) | A string encoding a JSON Pointer |
| [Ncname](Ncname.md) | Prefix part of CURIE |
| [Nodeidentifier](Nodeidentifier.md) | A URI, CURIE or BNODE that represents a node in a model |
| [Objectidentifier](Objectidentifier.md) | A URI or CURIE that represents an object in the model |
| [Sparqlpath](Sparqlpath.md) | A string encoding a SPARQL Property Path |
| [String](String.md) | A character string |
| [Time](Time.md) | A time object represents a (local) time of day, independent of any particular... |
| [Uri](Uri.md) | a complete URI |
| [Uriorcurie](Uriorcurie.md) | a URI or a CURIE |


## Subsets

| Subset | Description |
| --- | --- |
| [Collection](Collection.md) | The questions in this section are designed to elicit information that may hel... |
| [Composition](Composition.md) | The questions in this section are intended to provide dataset consumers with ... |
| [DataGovernance](DataGovernance.md) | The questions in this section relate to how the dataset is governed: how it i... |
| [Distribution](Distribution.md) | The questions in this section pertain to dataset distribution |
| [Ethics](Ethics.md) | The questions in this section address ethical and data-protection concerns, i... |
| [Maintenance](Maintenance.md) | The questions in this section are intended to encourage dataset creators to p... |
| [Motivation](Motivation.md) | The questions in this section are primarily intended to encourage dataset cre... |
| [Preprocessing-Cleaning-Labeling](Preprocessing-Cleaning-Labeling.md) | The questions in this section are intended to provide dataset consumers with ... |
| [Uses](Uses.md) | The questions in this section are intended to encourage dataset creators to r... |
