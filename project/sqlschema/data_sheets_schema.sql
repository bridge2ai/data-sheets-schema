

CREATE TABLE "AddressingGap" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	response TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "AnatomicalEntity" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	PRIMARY KEY (id)
);

CREATE TABLE "CleaningStrategy" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "CollectionConsent" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "CollectionMechanism" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "CollectionNotification" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "CollectionTimeframe" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "Confidentiality" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	confidential_elements_present BOOLEAN, 
	PRIMARY KEY (id)
);

CREATE TABLE "ConsentRevocation" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "ContentWarning" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	content_warnings_present BOOLEAN, 
	PRIMARY KEY (id)
);

CREATE TABLE "DataAnomaly" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "DataCollector" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "DataProtectionImpact" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "DatasetCollection" (
	compression VARCHAR(7), 
	conforms_to TEXT, 
	conforms_to_class TEXT, 
	conforms_to_schema TEXT, 
	created_on DATETIME, 
	description TEXT, 
	doi TEXT, 
	download_url TEXT, 
	id TEXT NOT NULL, 
	issued DATETIME, 
	language TEXT, 
	last_updated_on DATETIME, 
	license TEXT, 
	modified_by VARCHAR(12), 
	page TEXT, 
	publisher TEXT, 
	status TEXT, 
	title TEXT, 
	version TEXT, 
	was_derived_from TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "DatasetProperty" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "Deidentification" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	identifiable_elements_present BOOLEAN, 
	PRIMARY KEY (id)
);

CREATE TABLE "DirectCollection" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "DiscouragedUse" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "DistributionDate" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "DistributionFormat" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "Erratum" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "EthicalReview" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "ExistingUse" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "ExportControlRegulatoryRestrictions" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "ExtensionMechanism" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "ExternalResource" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "FormatDialect" (
	id TEXT NOT NULL, 
	comment_prefix TEXT, 
	delimiter TEXT, 
	double_quote TEXT, 
	header TEXT, 
	quote_char TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "FutureUseImpact" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "Grant" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	grant_number TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "Grantor" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	ror_id TEXT, 
	wikidata_id TEXT, 
	url TEXT, 
	related_to TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "Information" (
	compression VARCHAR(7), 
	conforms_to TEXT, 
	conforms_to_class TEXT, 
	conforms_to_schema TEXT, 
	created_on DATETIME, 
	description TEXT, 
	doi TEXT, 
	download_url TEXT, 
	id TEXT NOT NULL, 
	issued DATETIME, 
	language TEXT, 
	last_updated_on DATETIME, 
	license TEXT, 
	modified_by VARCHAR(12), 
	page TEXT, 
	publisher TEXT, 
	status TEXT, 
	title TEXT, 
	version TEXT, 
	was_derived_from TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "Instance" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	data_topic TEXT, 
	instance_type TEXT, 
	data_substrate TEXT, 
	counts INTEGER, 
	label BOOLEAN, 
	label_description TEXT, 
	sampling_strategies TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "InstanceAcquisition" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	was_directly_observed BOOLEAN, 
	was_reported_by_subjects BOOLEAN, 
	was_inferred_derived BOOLEAN, 
	was_validated_verified BOOLEAN, 
	PRIMARY KEY (id)
);

CREATE TABLE "IPRestrictions" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "LabelingStrategy" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "LicenseAndUseTerms" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "Maintainer" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "NamedThing" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	PRIMARY KEY (id)
);

CREATE TABLE "Organization" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	ror_id TEXT, 
	wikidata_id TEXT, 
	url TEXT, 
	related_to TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "OrganizationContainer" (
	organizations TEXT, 
	PRIMARY KEY (organizations)
);

CREATE TABLE "OtherTask" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "Person" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	affiliation TEXT, 
	email TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "PreprocessingStrategy" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "Purpose" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	response TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "RawData" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "Relationships" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "RetentionLimits" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "SamplingStrategy" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "SensitiveElement" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	sensitive_elements_present BOOLEAN, 
	PRIMARY KEY (id)
);

CREATE TABLE "Software" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	version TEXT, 
	license TEXT, 
	url TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "Splits" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "Subpopulation" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	subpopulation_elements_present BOOLEAN, 
	PRIMARY KEY (id)
);

CREATE TABLE "Task" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	response TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "ThirdPartySharing" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	description BOOLEAN, 
	PRIMARY KEY (id)
);

CREATE TABLE "UpdatePlan" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "UseRepository" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "VersionAccess" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	PRIMARY KEY (id)
);

CREATE TABLE "Creator" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	principal_investigator TEXT, 
	affiliation TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(principal_investigator) REFERENCES "Person" (id), 
	FOREIGN KEY(affiliation) REFERENCES "Organization" (id)
);

CREATE TABLE "Dataset" (
	compression VARCHAR(7), 
	conforms_to TEXT, 
	conforms_to_class TEXT, 
	conforms_to_schema TEXT, 
	created_on DATETIME, 
	description TEXT, 
	doi TEXT, 
	download_url TEXT, 
	id TEXT NOT NULL, 
	issued DATETIME, 
	language TEXT, 
	last_updated_on DATETIME, 
	license TEXT, 
	modified_by VARCHAR(12), 
	page TEXT, 
	publisher TEXT, 
	status TEXT, 
	title TEXT, 
	version TEXT, 
	was_derived_from TEXT, 
	bytes INTEGER, 
	dialect TEXT, 
	encoding VARCHAR(15), 
	format VARCHAR(22), 
	hash TEXT, 
	md5 TEXT, 
	media_type TEXT, 
	path TEXT, 
	sha256 TEXT, 
	purposes TEXT, 
	tasks TEXT, 
	addressing_gaps TEXT, 
	creators TEXT, 
	funders TEXT, 
	subsets TEXT, 
	instances TEXT, 
	anomalies TEXT, 
	external_resources TEXT, 
	confidential_elements TEXT, 
	content_warnings TEXT, 
	subpopulations TEXT, 
	sensitive_elements TEXT, 
	acquisition_methods TEXT, 
	collection_mechanisms TEXT, 
	sampling_strategies TEXT, 
	data_collectors TEXT, 
	collection_timeframes TEXT, 
	ethical_reviews TEXT, 
	data_protection_impacts TEXT, 
	preprocessing_strategies TEXT, 
	cleaning_strategies TEXT, 
	labeling_strategies TEXT, 
	raw_sources TEXT, 
	existing_uses TEXT, 
	use_repository TEXT, 
	other_tasks TEXT, 
	future_use_impacts TEXT, 
	discouraged_uses TEXT, 
	distribution_formats TEXT, 
	distribution_dates TEXT, 
	license_and_use_terms TEXT, 
	ip_restrictions TEXT, 
	regulatory_restrictions TEXT, 
	maintainers TEXT, 
	errata TEXT, 
	updates TEXT, 
	retention_limit TEXT, 
	version_access TEXT, 
	extension_mechanism TEXT, 
	is_deidentified TEXT, 
	is_tabular BOOLEAN, 
	"DatasetCollection_id" TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(license_and_use_terms) REFERENCES "LicenseAndUseTerms" (id), 
	FOREIGN KEY(ip_restrictions) REFERENCES "IPRestrictions" (id), 
	FOREIGN KEY(regulatory_restrictions) REFERENCES "ExportControlRegulatoryRestrictions" (id), 
	FOREIGN KEY(updates) REFERENCES "UpdatePlan" (id), 
	FOREIGN KEY(retention_limit) REFERENCES "RetentionLimits" (id), 
	FOREIGN KEY(version_access) REFERENCES "VersionAccess" (id), 
	FOREIGN KEY(extension_mechanism) REFERENCES "ExtensionMechanism" (id), 
	FOREIGN KEY(is_deidentified) REFERENCES "Deidentification" (id), 
	FOREIGN KEY("DatasetCollection_id") REFERENCES "DatasetCollection" (id)
);

CREATE TABLE "DataSubset" (
	compression VARCHAR(7), 
	conforms_to TEXT, 
	conforms_to_class TEXT, 
	conforms_to_schema TEXT, 
	created_on DATETIME, 
	description TEXT, 
	doi TEXT, 
	download_url TEXT, 
	id TEXT NOT NULL, 
	issued DATETIME, 
	language TEXT, 
	last_updated_on DATETIME, 
	license TEXT, 
	modified_by VARCHAR(12), 
	page TEXT, 
	publisher TEXT, 
	status TEXT, 
	title TEXT, 
	version TEXT, 
	was_derived_from TEXT, 
	bytes INTEGER, 
	dialect TEXT, 
	encoding VARCHAR(15), 
	format VARCHAR(22), 
	hash TEXT, 
	md5 TEXT, 
	media_type TEXT, 
	path TEXT, 
	sha256 TEXT, 
	purposes TEXT, 
	tasks TEXT, 
	addressing_gaps TEXT, 
	creators TEXT, 
	funders TEXT, 
	subsets TEXT, 
	instances TEXT, 
	anomalies TEXT, 
	external_resources TEXT, 
	confidential_elements TEXT, 
	content_warnings TEXT, 
	subpopulations TEXT, 
	sensitive_elements TEXT, 
	acquisition_methods TEXT, 
	collection_mechanisms TEXT, 
	sampling_strategies TEXT, 
	data_collectors TEXT, 
	collection_timeframes TEXT, 
	ethical_reviews TEXT, 
	data_protection_impacts TEXT, 
	preprocessing_strategies TEXT, 
	cleaning_strategies TEXT, 
	labeling_strategies TEXT, 
	raw_sources TEXT, 
	existing_uses TEXT, 
	use_repository TEXT, 
	other_tasks TEXT, 
	future_use_impacts TEXT, 
	discouraged_uses TEXT, 
	distribution_formats TEXT, 
	distribution_dates TEXT, 
	license_and_use_terms TEXT, 
	ip_restrictions TEXT, 
	regulatory_restrictions TEXT, 
	maintainers TEXT, 
	errata TEXT, 
	updates TEXT, 
	retention_limit TEXT, 
	version_access TEXT, 
	extension_mechanism TEXT, 
	is_deidentified TEXT, 
	is_tabular BOOLEAN, 
	is_data_split BOOLEAN, 
	is_subpopulation BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(license_and_use_terms) REFERENCES "LicenseAndUseTerms" (id), 
	FOREIGN KEY(ip_restrictions) REFERENCES "IPRestrictions" (id), 
	FOREIGN KEY(regulatory_restrictions) REFERENCES "ExportControlRegulatoryRestrictions" (id), 
	FOREIGN KEY(updates) REFERENCES "UpdatePlan" (id), 
	FOREIGN KEY(retention_limit) REFERENCES "RetentionLimits" (id), 
	FOREIGN KEY(version_access) REFERENCES "VersionAccess" (id), 
	FOREIGN KEY(extension_mechanism) REFERENCES "ExtensionMechanism" (id), 
	FOREIGN KEY(is_deidentified) REFERENCES "Deidentification" (id)
);

CREATE TABLE "FundingMechanism" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	grantor TEXT, 
	grant TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(grantor) REFERENCES "Grantor" (id), 
	FOREIGN KEY(grant) REFERENCES "Grant" (id)
);

CREATE TABLE "MissingInfo" (
	id TEXT NOT NULL, 
	category TEXT, 
	name TEXT, 
	description TEXT, 
	subclass_of TEXT, 
	related_to TEXT, 
	contributor_name TEXT, 
	contributor_github_name TEXT, 
	contributor_orcid TEXT, 
	contribution_date DATE, 
	used_software TEXT, 
	"Instance_id" TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY("Instance_id") REFERENCES "Instance" (id)
);

CREATE TABLE "CleaningStrategy_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "CleaningStrategy" (id)
);

CREATE TABLE "CollectionConsent_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "CollectionConsent" (id)
);

CREATE TABLE "CollectionMechanism_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "CollectionMechanism" (id)
);

CREATE TABLE "CollectionNotification_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "CollectionNotification" (id)
);

CREATE TABLE "CollectionTimeframe_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "CollectionTimeframe" (id)
);

CREATE TABLE "Confidentiality_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "Confidentiality" (id)
);

CREATE TABLE "ConsentRevocation_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "ConsentRevocation" (id)
);

CREATE TABLE "ContentWarning_warnings" (
	backref_id TEXT, 
	warnings TEXT, 
	PRIMARY KEY (backref_id, warnings), 
	FOREIGN KEY(backref_id) REFERENCES "ContentWarning" (id)
);

CREATE TABLE "DataAnomaly_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "DataAnomaly" (id)
);

CREATE TABLE "DataCollector_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "DataCollector" (id)
);

CREATE TABLE "DataProtectionImpact_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "DataProtectionImpact" (id)
);

CREATE TABLE "DatasetCollection_created_by" (
	backref_id TEXT, 
	created_by VARCHAR(12), 
	PRIMARY KEY (backref_id, created_by), 
	FOREIGN KEY(backref_id) REFERENCES "DatasetCollection" (id)
);

CREATE TABLE "DatasetCollection_keywords" (
	backref_id TEXT, 
	keywords TEXT, 
	PRIMARY KEY (backref_id, keywords), 
	FOREIGN KEY(backref_id) REFERENCES "DatasetCollection" (id)
);

CREATE TABLE "Deidentification_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "Deidentification" (id)
);

CREATE TABLE "DirectCollection_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "DirectCollection" (id)
);

CREATE TABLE "DiscouragedUse_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "DiscouragedUse" (id)
);

CREATE TABLE "DistributionDate_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "DistributionDate" (id)
);

CREATE TABLE "DistributionFormat_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "DistributionFormat" (id)
);

CREATE TABLE "Erratum_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "Erratum" (id)
);

CREATE TABLE "EthicalReview_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "EthicalReview" (id)
);

CREATE TABLE "ExistingUse_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "ExistingUse" (id)
);

CREATE TABLE "ExportControlRegulatoryRestrictions_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "ExportControlRegulatoryRestrictions" (id)
);

CREATE TABLE "ExtensionMechanism_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "ExtensionMechanism" (id)
);

CREATE TABLE "ExternalResource_external_resources" (
	backref_id TEXT, 
	external_resources TEXT, 
	PRIMARY KEY (backref_id, external_resources), 
	FOREIGN KEY(backref_id) REFERENCES "ExternalResource" (id)
);

CREATE TABLE "ExternalResource_future_guarantees" (
	backref_id TEXT, 
	future_guarantees TEXT, 
	PRIMARY KEY (backref_id, future_guarantees), 
	FOREIGN KEY(backref_id) REFERENCES "ExternalResource" (id)
);

CREATE TABLE "ExternalResource_archival" (
	backref_id TEXT, 
	archival BOOLEAN, 
	PRIMARY KEY (backref_id, archival), 
	FOREIGN KEY(backref_id) REFERENCES "ExternalResource" (id)
);

CREATE TABLE "ExternalResource_restrictions" (
	backref_id TEXT, 
	restrictions TEXT, 
	PRIMARY KEY (backref_id, restrictions), 
	FOREIGN KEY(backref_id) REFERENCES "ExternalResource" (id)
);

CREATE TABLE "FutureUseImpact_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "FutureUseImpact" (id)
);

CREATE TABLE "Information_created_by" (
	backref_id TEXT, 
	created_by VARCHAR(12), 
	PRIMARY KEY (backref_id, created_by), 
	FOREIGN KEY(backref_id) REFERENCES "Information" (id)
);

CREATE TABLE "Information_keywords" (
	backref_id TEXT, 
	keywords TEXT, 
	PRIMARY KEY (backref_id, keywords), 
	FOREIGN KEY(backref_id) REFERENCES "Information" (id)
);

CREATE TABLE "InstanceAcquisition_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "InstanceAcquisition" (id)
);

CREATE TABLE "IPRestrictions_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "IPRestrictions" (id)
);

CREATE TABLE "LabelingStrategy_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "LabelingStrategy" (id)
);

CREATE TABLE "LicenseAndUseTerms_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "LicenseAndUseTerms" (id)
);

CREATE TABLE "Maintainer_description" (
	backref_id TEXT, 
	description VARCHAR(12), 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "Maintainer" (id)
);

CREATE TABLE "OtherTask_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "OtherTask" (id)
);

CREATE TABLE "PreprocessingStrategy_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "PreprocessingStrategy" (id)
);

CREATE TABLE "RawData_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "RawData" (id)
);

CREATE TABLE "Relationships_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "Relationships" (id)
);

CREATE TABLE "RetentionLimits_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "RetentionLimits" (id)
);

CREATE TABLE "SamplingStrategy_is_sample" (
	backref_id TEXT, 
	is_sample BOOLEAN, 
	PRIMARY KEY (backref_id, is_sample), 
	FOREIGN KEY(backref_id) REFERENCES "SamplingStrategy" (id)
);

CREATE TABLE "SamplingStrategy_is_random" (
	backref_id TEXT, 
	is_random BOOLEAN, 
	PRIMARY KEY (backref_id, is_random), 
	FOREIGN KEY(backref_id) REFERENCES "SamplingStrategy" (id)
);

CREATE TABLE "SamplingStrategy_source_data" (
	backref_id TEXT, 
	source_data TEXT, 
	PRIMARY KEY (backref_id, source_data), 
	FOREIGN KEY(backref_id) REFERENCES "SamplingStrategy" (id)
);

CREATE TABLE "SamplingStrategy_is_representative" (
	backref_id TEXT, 
	is_representative BOOLEAN, 
	PRIMARY KEY (backref_id, is_representative), 
	FOREIGN KEY(backref_id) REFERENCES "SamplingStrategy" (id)
);

CREATE TABLE "SamplingStrategy_representative_verification" (
	backref_id TEXT, 
	representative_verification TEXT, 
	PRIMARY KEY (backref_id, representative_verification), 
	FOREIGN KEY(backref_id) REFERENCES "SamplingStrategy" (id)
);

CREATE TABLE "SamplingStrategy_why_not_representative" (
	backref_id TEXT, 
	why_not_representative TEXT, 
	PRIMARY KEY (backref_id, why_not_representative), 
	FOREIGN KEY(backref_id) REFERENCES "SamplingStrategy" (id)
);

CREATE TABLE "SamplingStrategy_strategies" (
	backref_id TEXT, 
	strategies TEXT, 
	PRIMARY KEY (backref_id, strategies), 
	FOREIGN KEY(backref_id) REFERENCES "SamplingStrategy" (id)
);

CREATE TABLE "SensitiveElement_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "SensitiveElement" (id)
);

CREATE TABLE "Splits_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "Splits" (id)
);

CREATE TABLE "Subpopulation_identification" (
	backref_id TEXT, 
	identification TEXT, 
	PRIMARY KEY (backref_id, identification), 
	FOREIGN KEY(backref_id) REFERENCES "Subpopulation" (id)
);

CREATE TABLE "Subpopulation_distribution" (
	backref_id TEXT, 
	distribution TEXT, 
	PRIMARY KEY (backref_id, distribution), 
	FOREIGN KEY(backref_id) REFERENCES "Subpopulation" (id)
);

CREATE TABLE "UpdatePlan_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "UpdatePlan" (id)
);

CREATE TABLE "UseRepository_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "UseRepository" (id)
);

CREATE TABLE "VersionAccess_description" (
	backref_id TEXT, 
	description TEXT, 
	PRIMARY KEY (backref_id, description), 
	FOREIGN KEY(backref_id) REFERENCES "VersionAccess" (id)
);

CREATE TABLE "Dataset_created_by" (
	backref_id TEXT, 
	created_by VARCHAR(12), 
	PRIMARY KEY (backref_id, created_by), 
	FOREIGN KEY(backref_id) REFERENCES "Dataset" (id)
);

CREATE TABLE "Dataset_keywords" (
	backref_id TEXT, 
	keywords TEXT, 
	PRIMARY KEY (backref_id, keywords), 
	FOREIGN KEY(backref_id) REFERENCES "Dataset" (id)
);

CREATE TABLE "DataSubset_created_by" (
	backref_id TEXT, 
	created_by VARCHAR(12), 
	PRIMARY KEY (backref_id, created_by), 
	FOREIGN KEY(backref_id) REFERENCES "DataSubset" (id)
);

CREATE TABLE "DataSubset_keywords" (
	backref_id TEXT, 
	keywords TEXT, 
	PRIMARY KEY (backref_id, keywords), 
	FOREIGN KEY(backref_id) REFERENCES "DataSubset" (id)
);

CREATE TABLE "MissingInfo_missing" (
	backref_id TEXT, 
	missing TEXT, 
	PRIMARY KEY (backref_id, missing), 
	FOREIGN KEY(backref_id) REFERENCES "MissingInfo" (id)
);

CREATE TABLE "MissingInfo_why_missing" (
	backref_id TEXT, 
	why_missing TEXT, 
	PRIMARY KEY (backref_id, why_missing), 
	FOREIGN KEY(backref_id) REFERENCES "MissingInfo" (id)
);
