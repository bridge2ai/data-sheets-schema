# data-sheets-schema

A LinkML schema for Datasheets for Datasets.

URI: https://w3id.org/bridge2ai/data-sheets-schema

Name: data-sheets-schema



## Classes

| Class | Description |
| --- | --- |
| [FormatDialect](FormatDialect.md) | Additional format information for a file |
| [NamedThing](NamedThing.md) | A generic grouping for any identifiable entity |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DatasetProperty](DatasetProperty.md) | Represents a single property of a dataset, or a set of related properties |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[AddressingGap](AddressingGap.md) | Was there a specific gap that needed to be filled by creation of the dataset? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[CleaningStrategy](CleaningStrategy.md) | Was any cleaning of the data done (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[CollectionConsent](CollectionConsent.md) | Did the individuals in question consent to the collection and use of their da... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[CollectionMechanism](CollectionMechanism.md) | What mechanisms or procedures were used to collect the data (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[CollectionNotification](CollectionNotification.md) | Were the individuals in question notified about the data collection? If so, p... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[CollectionTimeframe](CollectionTimeframe.md) | Over what timeframe was the data collected, and does this timeframe match the... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Confidentiality](Confidentiality.md) | Does the dataset contain data that might be confidential (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ConsentRevocation](ConsentRevocation.md) | If consent was obtained, were the consenting individuals provided with a mech... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ContentWarning](ContentWarning.md) | Does the dataset contain any data that might be offensive, insulting, threate... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Creator](Creator.md) | Who created the dataset (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DataAnomaly](DataAnomaly.md) | Are there any errors, sources of noise, or redundancies in the dataset? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DataCollector](DataCollector.md) | Who was involved in the data collection (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DataProtectionImpact](DataProtectionImpact.md) | Has an analysis of the potential impact of the dataset and its use on data su... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Deidentification](Deidentification.md) | Is it possible to identify individuals in the dataset, either directly or ind... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DirectCollection](DirectCollection.md) | Indicates whether the data was collected directly from the individuals in que... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DiscouragedUse](DiscouragedUse.md) | Are there tasks for which the dataset should not be used? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DistributionDate](DistributionDate.md) | When will the dataset be distributed? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DistributionFormat](DistributionFormat.md) | How will the dataset be distributed (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Erratum](Erratum.md) | Is there an erratum? If so, please provide a link or other access point |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[EthicalReview](EthicalReview.md) | Were any ethical or compliance review processes conducted (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ExistingUse](ExistingUse.md) | Has the dataset been used for any tasks already? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ExportControlRegulatoryRestrictions](ExportControlRegulatoryRestrictions.md) | Do any export controls or other regulatory restrictions apply to the dataset ... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ExtensionMechanism](ExtensionMechanism.md) | If others want to extend/augment/build on/contribute to the dataset, is there... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ExternalResource](ExternalResource.md) | Is the dataset self-contained or does it rely on external resources (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[FundingMechanism](FundingMechanism.md) | Who funded the creation of the dataset? If there is an associated grant, plea... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[FutureUseImpact](FutureUseImpact.md) | Is there anything about the dataset's composition or collection that might im... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[HumanSubjectCompensation](HumanSubjectCompensation.md) | Information about compensation or incentives provided to human research parti... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[HumanSubjectResearch](HumanSubjectResearch.md) | Information about whether the dataset involves human subjects research and wh... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[InformedConsent](InformedConsent.md) | Details about informed consent procedures used in human subjects research |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Instance](Instance.md) | What do the instances that comprise the dataset represent (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[InstanceAcquisition](InstanceAcquisition.md) | Describes how data associated with each instance was acquired  (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[IPRestrictions](IPRestrictions.md) | Have any third parties imposed IP-based or other restrictions on the data ass... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[LabelingStrategy](LabelingStrategy.md) | Was any labeling of the data done (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[LicenseAndUseTerms](LicenseAndUseTerms.md) | Will the dataset be distributed under a copyright or other IP license, and/or... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Maintainer](Maintainer.md) | Who will be supporting/hosting/maintaining the dataset? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[MissingInfo](MissingInfo.md) | Is any information missing from individual instances? (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[OtherTask](OtherTask.md) | What other tasks could the dataset be used for? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ParticipantPrivacy](ParticipantPrivacy.md) | Information about privacy protections and anonymization procedures for human ... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[PreprocessingStrategy](PreprocessingStrategy.md) | Was any preprocessing of the data done (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Purpose](Purpose.md) | For what purpose was the dataset created? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[RawData](RawData.md) | Was the “raw” data saved in addition to the preprocessed/cleaned/labeled data... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Relationships](Relationships.md) | Are relationships between individual instances made explicit (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[RetentionLimits](RetentionLimits.md) | If the dataset relates to people, are there applicable limits on the retentio... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[SamplingStrategy](SamplingStrategy.md) | Does the dataset contain all possible instances, or is it a sample (not neces... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[SensitiveElement](SensitiveElement.md) | Does the dataset contain data that might be considered sensitive (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Splits](Splits.md) | Are there recommended data splits (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Subpopulation](Subpopulation.md) | Does the dataset identify any subpopulations (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Task](Task.md) | Was there a specific task in mind for the dataset's application? |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[ThirdPartySharing](ThirdPartySharing.md) | Will the dataset be distributed to third parties outside of the entity (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[UpdatePlan](UpdatePlan.md) | Will the dataset be updated (e |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[UseRepository](UseRepository.md) | Is there a repository that links to any or all papers or systems that use the... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[VersionAccess](VersionAccess.md) | Will older versions of the dataset continue to be supported/hosted/maintained... |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[VulnerablePopulations](VulnerablePopulations.md) | Information about protections for vulnerable populations in human subjects re... |
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
| [acquisition_methods](acquisition_methods.md) |  |
| [addressing_gaps](addressing_gaps.md) |  |
| [affiliation](affiliation.md) | The organization(s) to which the person belongs |
| [anomalies](anomalies.md) |  |
| [anonymization_method](anonymization_method.md) | What methods were used to anonymize or de-identify participant data? Include ... |
| [archival](archival.md) | Indication whether official archival versions of external resources are inclu... |
| [assent_procedures](assent_procedures.md) | For research involving minors, what assent procedures were used? How was deve... |
| [bytes](bytes.md) | Size of the data in bytes |
| [cleaning_strategies](cleaning_strategies.md) |  |
| [collection_mechanisms](collection_mechanisms.md) |  |
| [collection_timeframes](collection_timeframes.md) |  |
| [comment_prefix](comment_prefix.md) |  |
| [compensation_amount](compensation_amount.md) | What was the amount or value of compensation provided? Include currency or eq... |
| [compensation_provided](compensation_provided.md) | Were participants compensated for their participation? |
| [compensation_rationale](compensation_rationale.md) | What was the rationale for the compensation structure? How was the amount det... |
| [compensation_type](compensation_type.md) | What type of compensation was provided (e |
| [compression](compression.md) | compression format used, if any |
| [confidential_elements](confidential_elements.md) |  |
| [confidential_elements_present](confidential_elements_present.md) | Indicates whether any confidential data elements are present |
| [conforms_to](conforms_to.md) |  |
| [conforms_to_class](conforms_to_class.md) |  |
| [conforms_to_schema](conforms_to_schema.md) |  |
| [consent_documentation](consent_documentation.md) | How is consent documented? Include references to consent forms or procedures ... |
| [consent_obtained](consent_obtained.md) | Was informed consent obtained from all participants? |
| [consent_scope](consent_scope.md) | What specific uses did participants consent to? Are there limitations on data... |
| [consent_type](consent_type.md) | What type of consent was obtained (e |
| [content_warnings](content_warnings.md) |  |
| [content_warnings_present](content_warnings_present.md) | Indicates whether any content warnings are needed |
| [counts](counts.md) | How many instances are there in total (of each type, if appropriate)? |
| [created_by](created_by.md) |  |
| [created_on](created_on.md) |  |
| [creators](creators.md) |  |
| [data_collectors](data_collectors.md) |  |
| [data_linkage](data_linkage.md) | Can this dataset be linked to other datasets in ways that might compromise pa... |
| [data_protection_impacts](data_protection_impacts.md) |  |
| [data_substrate](data_substrate.md) | Type of data (e |
| [data_topic](data_topic.md) | General topic of each instance (e |
| [delimiter](delimiter.md) |  |
| [description](description.md) | A human-readable description for a thing |
| [dialect](dialect.md) |  |
| [discouraged_uses](discouraged_uses.md) |  |
| [distribution](distribution.md) |  |
| [distribution_dates](distribution_dates.md) |  |
| [distribution_formats](distribution_formats.md) |  |
| [doi](doi.md) | digital object identifier |
| [double_quote](double_quote.md) |  |
| [download_url](download_url.md) | URL from which the data can be downloaded |
| [email](email.md) | The email address of the person |
| [encoding](encoding.md) | the character encoding of the data |
| [errata](errata.md) |  |
| [ethical_reviews](ethical_reviews.md) |  |
| [ethics_review_board](ethics_review_board.md) | What ethics review board(s) reviewed this research? Include institution names... |
| [existing_uses](existing_uses.md) |  |
| [extension_mechanism](extension_mechanism.md) |  |
| [external_resources](external_resources.md) |  |
| [format](format.md) | The file format, physical medium, or dimensions of a resource |
| [funders](funders.md) |  |
| [future_guarantees](future_guarantees.md) | Explanation of any commitments that external resources will remain available ... |
| [future_use_impacts](future_use_impacts.md) |  |
| [grant](grant.md) | Name/identifier of the specific grant mechanism supporting dataset creation |
| [grant_number](grant_number.md) | The alphanumeric identifier for the grant |
| [grantor](grantor.md) | Name/identifier of the organization providing monetary or resource support |
| [guardian_consent](guardian_consent.md) | For participants unable to provide their own consent, how was guardian or sur... |
| [hash](hash.md) | hash of the data |
| [header](header.md) |  |
| [id](id.md) | A unique identifier for a thing |
| [identifiable_elements_present](identifiable_elements_present.md) | Indicates whether data subjects can be identified |
| [identification](identification.md) |  |
| [instance_type](instance_type.md) | Multiple types of instances? (e |
| [instances](instances.md) |  |
| [involves_human_subjects](involves_human_subjects.md) | Does this dataset involve human subjects research? |
| [ip_restrictions](ip_restrictions.md) |  |
| [irb_approval](irb_approval.md) | Was Institutional Review Board (IRB) approval obtained? Include approval numb... |
| [is_data_split](is_data_split.md) | Is this subset a split of the larger dataset, e |
| [is_deidentified](is_deidentified.md) |  |
| [is_random](is_random.md) | Indicates whether the sample is random |
| [is_representative](is_representative.md) | Indicates whether the sample is representative of the larger set |
| [is_sample](is_sample.md) | Indicates whether it is a sample of a larger set |
| [is_subpopulation](is_subpopulation.md) | Is this subset a subpopulation of the larger dataset, e |
| [is_tabular](is_tabular.md) |  |
| [issued](issued.md) |  |
| [keywords](keywords.md) |  |
| [label](label.md) | Is there a label or target associated with each instance? |
| [label_description](label_description.md) | If labeled, what pattern or format do labels follow? |
| [labeling_strategies](labeling_strategies.md) |  |
| [language](language.md) | language in which the information is expressed |
| [last_updated_on](last_updated_on.md) |  |
| [license](license.md) |  |
| [license_and_use_terms](license_and_use_terms.md) |  |
| [maintainers](maintainers.md) |  |
| [md5](md5.md) | md5 hash of the data |
| [media_type](media_type.md) | The media type of the data |
| [missing](missing.md) | Description of the missing data fields or elements |
| [missing_information](missing_information.md) | References to one or more MissingInfo objects describing missing data |
| [modified_by](modified_by.md) |  |
| [name](name.md) | A human-readable name for a thing |
| [other_tasks](other_tasks.md) |  |
| [page](page.md) |  |
| [path](path.md) |  |
| [preprocessing_strategies](preprocessing_strategies.md) |  |
| [principal_investigator](principal_investigator.md) | A key individual (Principal Investigator) responsible for or overseeing datas... |
| [privacy_techniques](privacy_techniques.md) | What privacy-preserving techniques were applied (e |
| [profile](profile.md) | The frictionless data profile to which the data conforms |
| [publisher](publisher.md) |  |
| [purposes](purposes.md) |  |
| [quote_char](quote_char.md) |  |
| [raw_sources](raw_sources.md) |  |
| [regulatory_compliance](regulatory_compliance.md) | What regulatory frameworks govern this human subjects research (e |
| [regulatory_restrictions](regulatory_restrictions.md) |  |
| [reidentification_risk](reidentification_risk.md) | What is the assessed risk of re-identification? What measures were taken to m... |
| [representative_verification](representative_verification.md) | Explanation of how representativeness was validated or verified |
| [resources](resources.md) |  |
| [response](response.md) | Short explanation describing the primary purpose of creating the dataset |
| [restrictions](restrictions.md) | Description of any restrictions or fees associated with external resources |
| [retention_limit](retention_limit.md) |  |
| [sampling_strategies](sampling_strategies.md) |  |
| [sensitive_elements](sensitive_elements.md) |  |
| [sensitive_elements_present](sensitive_elements_present.md) | Indicates whether sensitive data elements are present |
| [sha256](sha256.md) | sha256 hash of the data |
| [source_data](source_data.md) | Description of the larger set from which the sample was drawn, if any |
| [special_populations](special_populations.md) | Does the research involve any special populations that require additional pro... |
| [special_protections](special_protections.md) | What additional protections were implemented for vulnerable populations? Incl... |
| [status](status.md) |  |
| [strategies](strategies.md) | Description of the sampling strategy (deterministic, probabilistic, etc |
| [subpopulation_elements_present](subpopulation_elements_present.md) | Indicates whether any subpopulations are explicitly identified |
| [subpopulations](subpopulations.md) |  |
| [subsets](subsets.md) |  |
| [tasks](tasks.md) |  |
| [themes](themes.md) | Themes associated with the data |
| [title](title.md) | the official title of the element |
| [updates](updates.md) |  |
| [url](url.md) |  |
| [use_repository](use_repository.md) |  |
| [used_software](used_software.md) | What software was used as part of this dataset property? |
| [version](version.md) |  |
| [version_access](version_access.md) |  |
| [vulnerable_groups_included](vulnerable_groups_included.md) | Are any vulnerable populations included (e |
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
| [Boolean](Boolean.md) |  |
| [CompressionEnum](CompressionEnum.md) |  |
| [CreatorOrMaintainerEnum](CreatorOrMaintainerEnum.md) |  |
| [EncodingEnum](EncodingEnum.md) |  |
| [FormatEnum](FormatEnum.md) |  |
| [MediaTypeEnum](MediaTypeEnum.md) |  |


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
