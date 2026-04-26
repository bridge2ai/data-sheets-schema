# Comprehensive URI Mapping Recommendations

## Summary by Vocabulary

- **d4d**: 64 mappings
- **schema**: 31 mappings
- **DUO**: 20 mappings
- **dcterms**: 8 mappings
- **dcat**: 1 mappings
- **prov**: 1 mappings
- **qudt**: 1 mappings

**Total recommendations: 126**


## Mappings by Category

### Standard Vocabularies (High Confidence)

- `array` → `schema:ItemList` (schema)
- `boolean` → `schema:Boolean` (schema)
- `category` → `schema:category` (schema)
- `date` → `schema:Date` (schema)
- `datetime` → `schema:DateTime` (schema)
- `derivation` → `dcterms:provenance` (dcterms)
- `derives_from` → `prov:wasDerivedFrom` (prov)
- `description` → `schema:description` (schema)
- `double` → `schema:Number` (schema)
- `extension_details` → `dcterms:description` (dcterms)
- `float` → `schema:Float` (schema)
- `identifier` → `schema:identifier` (schema)
- `integer` → `schema:Integer` (schema)
- `json` → `schema:PropertyValue` (schema)
- `labeling_details` → `dcterms:description` (dcterms)
- `measurement_technique` → `qudt:measurementMethod` (qudt)
- `method` → `schema:method` (schema)
- `minimum_value` → `schema:minValue` (schema)
- `name` → `schema:name` (schema)
- `object` → `schema:StructuredValue` (schema)
- `quality_notes` → `dcterms:description` (dcterms)
- `repository_url` → `dcat:accessURL` (dcat)
- `source_description` → `dcterms:description` (dcterms)
- `source_type` → `dcterms:type` (dcterms)
- `string` → `schema:Text` (schema)
- `type` → `schema:type` (schema)
- `url` → `schema:url` (schema)
- `usage_notes` → `dcterms:description` (dcterms)
- `version` → `schema:version` (schema)
- `version_details` → `dcterms:description` (dcterms)

### D4D-Specific Terms (use d4d: prefix)

These terms are domain-specific and don't have standard equivalents:

#### Collection Module
- `was_validated_verified` → `d4d:wasValidated`
- `was_inferred_derived` → `d4d:wasInferred`
- `was_reported_by_subjects` → `d4d:wasReportedBySubjects`
- `was_directly_observed` → `d4d:wasDirectlyObserved`
- `acquisition_details` → `d4d:acquisitionDetails`
- `collection_details` → `d4d:collectionDetails`
- `collector_details` → `d4d:collectorDetails`
- `handling_strategy` → `d4d:handlingStrategy`
- `missing_data_causes` → `d4d:missingDataCauses`
- `access_details` → `d4d:accessDetails`
- `raw_data_format` → `d4d:rawDataFormat`

#### Composition Module
- `is_sample` → `d4d:isSample`
- `is_random` → `d4d:isRandom`
- `is_representative` → `d4d:isRepresentative`
- `representative_verification` → `d4d:representativeVerification`
- `label_description` → `d4d:labelDescription`
- `bias_description` → `d4d:biasDescription`
- `identifiers_removed` → `d4d:identifiersRemoved`
- `recommended_mitigation` → `d4d:recommendedMitigation`
- `strategies` → `d4d:strategies`
- `missing` → `d4d:missing`
- `restrictions` → `d4d:restrictions`
- `identification` → `d4d:identification`
- `source_data` → `d4d:sourceData`

#### Human Subjects Module
- `consent_obtained` → `d4d:consentObtained`
- `consent_type` → `d4d:consentType`
- `consent_documentation` → `d4d:consentDocumentation`
- `consent_scope` → `d4d:consentScope`
- `withdrawal_mechanism` → `d4d:withdrawalMechanism`
- `irb_approval` → `d4d:irbApproval`
- `ethics_review_board` → `d4d:ethicsReviewBoard`
- `guardian_consent` → `d4d:guardianConsent`
- `assent_procedures` → `d4d:assentProcedures`
- `compensation_provided` → `d4d:compensationProvided`
- `reidentification_risk` → `d4d:reidentificationRisk`
- `privacy_techniques` → `d4d:privacyTechniques`
- `data_linkage` → `d4d:dataLinkage`
- `regulatory_compliance` → `d4d:regulatoryCompliance`
- `special_populations` → `d4d:specialPopulations`

#### Data Governance Module (non-DUO)
- `confidentiality_level` → `d4d:confidentialityLevel`
- `restricted` → `d4d:restricted`
- `unrestricted` → `d4d:unrestricted`
- `confidential` → `d4d:confidential`
- `clinical_care_use` → `d4d:clinicalCareUse`
- `compliant` → `d4d:compliant`
- `not_compliant` → `d4d:notCompliant`
- `partially_compliant` → `d4d:partiallyCompliant`
- `under_review` → `d4d:underReview`
- `not_applicable` → `d4d:notApplicable`
- `other_compliance` → `d4d:otherCompliance`

#### Preprocessing Module
- `tool_accuracy` → `d4d:toolAccuracy`
- `tools` → `d4d:tools`
- `tool_descriptions` → `d4d:toolDescriptions`
- `inter_annotator_agreement` → `d4d:interAnnotatorAgreement`
- `agreement_metric` → `d4d:agreementMetric`
- `analysis_method` → `d4d:analysisMethod`
- `annotation_quality_details` → `d4d:annotationQualityDetails`

#### Uses Module
- `prohibition_reason` → `d4d:prohibitionReason`
- `use_category` → `d4d:useCategory`
- `repository_details` → `d4d:repositoryDetails`

#### Maintenance Module
- `versions_available` → `d4d:versionsAvailable`

#### Variables Module
- `categorical` → `d4d:categoricalVariable`
- `ordinal` → `d4d:ordinalVariable`
- `identifier` → `d4d:identifierVariable`

### DUO (Data Use Ontology) Terms (20 mappings)
Standard data use restriction terms:

- `collaboration_required` → `DUO:0000020`
- `disease_specific_research` → `DUO:0000007`
- `ethics_approval_required` → `DUO:0000021`
- `general_research_use` → `DUO:0000042`
- `genetic_studies_only` → `DUO:0000016`
- `geographic_restriction` → `DUO:0000022`
- `health_medical_biomedical_research` → `DUO:0000006`
- `institution_specific` → `DUO:0000028`
- `no_commercial_use` → `DUO:0000046`
- `no_methods_development` → `DUO:0000015`
- `no_population_ancestry_research` → `DUO:0000044`
- `no_restriction` → `DUO:0000004`
- `non_profit_use_only` → `DUO:0000045`
- `population_origins_ancestry_research` → `DUO:0000011`
- `project_specific` → `DUO:0000027`
- `publication_moratorium` → `DUO:0000024`
- `publication_required` → `DUO:0000019`
- `return_to_database` → `DUO:0000029`
- `time_limit` → `DUO:0000025`
- `user_specific` → `DUO:0000026`

### RO-Crate Relationship Terms (13 mappings)
Dataset relationship predicates (schema.org):

- `has_part` → `schema:hasPart`
- `is_part_of` → `schema:isPartOf`
- `is_version_of` → `schema:isVersionOf`
- `is_new_version_of` → `schema:isNewVersionOf`
- `replaces` → `schema:replacesAction`
- `is_replaced_by` → `schema:replacesAction`
- `references` → `schema:citation`
- `is_referenced_by` → `schema:citation`
- `requires` → `schema:requirements`
- `is_required_by` → `schema:requirements`
- `supplements` → `schema:supplementTo`
- `is_supplemented_by` → `schema:supplementTo`
- `is_identical_to` → `schema:sameAs`
