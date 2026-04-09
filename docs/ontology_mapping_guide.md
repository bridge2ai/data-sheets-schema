# D4D Ontology Mapping Guide

## Overview

Ontology mappings in the D4D schema serve two purposes: **RDF serialization** and **semantic
interoperability**. Every `slot_uri` becomes the RDF predicate when D4D YAML is serialized to
Turtle, JSON-LD, or other RDF formats. `exact_mappings`, `broad_mappings`, and `close_mappings`
declare alignment with terms in external vocabularies, enabling federated queries and FAIR
data discovery without requiring consumers to adopt the D4D namespace.

Where a well-established ontology term exists and is semantically accurate, it is used directly
as the `slot_uri`. Where no suitable standard term exists, a custom `d4d:` term is minted.

---

## Namespace Prefixes

| Prefix | Full URI | Ontology / Standard |
|--------|----------|---------------------|
| `d4d` | `https://w3id.org/bridge2ai/data-sheets-schema/` | D4D custom terms (this project) |
| `data_sheets_schema` | `https://w3id.org/bridge2ai/data-sheets-schema/` | Alias for `d4d` used as default prefix |
| `dcterms` | `http://purl.org/dc/terms/` | Dublin Core Terms — general metadata |
| `dcat` | `http://www.w3.org/ns/dcat#` | Data Catalog Vocabulary — dataset/distribution metadata |
| `schema` | `http://schema.org/` | Schema.org — broad structured data vocabulary |
| `prov` | `http://www.w3.org/ns/prov#` | PROV-O — provenance ontology |
| `qudt` | `http://qudt.org/schema/qudt/` | QUDT — quantities, units, dimensions, types |
| `skos` | `http://www.w3.org/2004/02/skos/core#` | SKOS — knowledge organization / concept schemes |
| `AIO` | `https://w3id.org/aio/` | Artificial Intelligence Ontology — AI/ML concepts |
| `DUO` | `http://purl.obolibrary.org/obo/DUO_` | Data Use Ontology — data access and use conditions |
| `biolink` | `https://w3id.org/biolink/vocab/` | Biolink Model — biomedical knowledge graph vocabulary |
| `sh` | `https://w3id.org/shacl/` | SHACL — shapes constraint language |
| `linkml` | `https://w3id.org/linkml/` | LinkML framework built-ins |
| `mediatypes` | `https://www.iana.org/assignments/media-types/` | IANA media type registry |
| `B2AI_TOPIC` | `https://w3id.org/bridge2ai/b2ai-standards-registry/` | Bridge2AI standards registry |
| `rai` | `http://mlcommons.org/croissant/RAI/` | Responsible AI (Croissant/MLCommons) |

---

## Mapping Strategy

LinkML supports four mapping mechanisms:

| Mechanism | Meaning | Use in D4D |
|-----------|---------|------------|
| `slot_uri` | The primary RDF predicate; the slot's canonical identity in RDF | Used for every slot; chosen to be the best single match |
| `exact_mappings` | Semantically equivalent term in another ontology | Used when a second vocabulary has an identical concept |
| `broad_mappings` | A related but broader or less precise term | Used when no exact match exists; indicates approximate alignment |
| `close_mappings` | Similar but not identical — overlapping semantics | Used at the class level or when meaning is analogous but scope differs |

The guiding rule: prefer `dcterms`, `dcat`, or `schema:` terms for `slot_uri` when an accurate
match exists. Fall back to `d4d:` for D4D-specific concepts (consent details, bias types,
annotation protocols, etc.).

---

## Core Slot Mappings (D4D_Base_import.yaml)

| Slot | `slot_uri` | Ontology | Rationale |
|------|-----------|----------|-----------|
| `title` | `dcterms:title` | Dublin Core | Standard bibliographic title term |
| `language` | `dcterms:language` | Dublin Core | Standard language declaration; `schema:inLanguage` as exact mapping |
| `publisher` | `dcterms:publisher` | Dublin Core | Entity responsible for making resource available |
| `issued` | `dcterms:issued` | Dublin Core | Formal publication/issuance date |
| `page` | `dcat:landingPage` | DCAT | Web page describing (not delivering) the resource |
| `download_url` | `dcat:downloadURL` | DCAT | Direct data download link; `schema:url` as exact mapping |
| `bytes` | `dcat:byteSize` | DCAT | File size in bytes — DCAT distribution property |
| `format` | `dcterms:format` | Dublin Core | File format/extension |
| `media_type` | `dcat:mediaType` | DCAT | MIME type; `schema:encodingFormat` as exact mapping |
| `compression` | `dcat:compressFormat` | DCAT | Compression algorithm used |
| `keywords` | `dcat:keyword` | DCAT | Discovery keywords for the resource |
| `license` | `dcterms:license` | Dublin Core | Legal license term |
| `version` | `schema:version` | Schema.org | Version string |
| `created_by` | `dcterms:creator` | Dublin Core | Primary creator |
| `created_on` | `dcterms:created` | Dublin Core | Creation datetime |
| `last_updated_on` | `dcterms:modified` | Dublin Core | Last modification datetime |
| `modified_by` | `dcterms:contributor` | Dublin Core | Contributor to update |
| `conforms_to` | `dcterms:conformsTo` | Dublin Core | Standard or schema conformed to |
| `was_derived_from` | `prov:wasDerivedFrom` | PROV-O | Derivation provenance; `dcterms:source` as exact mapping |
| `external_resources` | `dcterms:references` | Dublin Core | Links to related resources |
| `resources` | `schema:hasPart` | Schema.org | Sub-datasets or component files |
| `sha256` | `schema:sha256` | Schema.org | Schema.org has a dedicated sha256 property |
| `hash` | `d4d:hashValue` | D4D custom | Generic hash; no standard single-algorithm-neutral term |
| `md5` | `d4d:md5Checksum` | D4D custom | MD5-specific; schema.org only defines sha256 |
| `encoding` | `d4d:characterEncoding` | D4D custom | Character encoding; no precise DCAT/DC term at enum level |
| `doi` | `d4d:doiIdentifier` | D4D custom | DOI-specific; `dcterms:identifier` is broad mapping |
| `status` | `d4d:publicationStatus` | D4D custom | Publication lifecycle status; no standard enum-backed term |
| `conforms_to_schema` | `d4d:conformsToSchema` | D4D custom | Schema-specific refinement of `dcterms:conformsTo` |
| `conforms_to_class` | `d4d:conformsToClass` | D4D custom | Class-specific refinement of `dcterms:conformsTo` |

### Base Class URIs

| Class | `class_uri` | Rationale |
|-------|------------|-----------|
| `NamedThing` | `schema:Thing` | Root Schema.org class for any identifiable entity |
| `Organization` | `schema:Organization` | Direct Schema.org match |
| `Person` | `schema:Person` | Direct Schema.org match |
| `Software` | `schema:SoftwareApplication` | Direct Schema.org match |
| `Information` | — (inherits `NamedThing`) | Abstract grouping; close mapping to `schema:CreativeWork` |
| `DatasetCollection` | — | Exact mapping: `dcat:Dataset`; close mapping: `dcat:Catalog` |

---

## Module-Specific Mapping Decisions

### D4D_Distribution.yaml — DCAT alignment
Distribution metadata (access URLs, release dates, formats, access rights) maps heavily to
DCAT. `dcat:accessURL` is used for access points, `dcterms:accessRights` for access conditions,
`dcterms:rights` for rights statements, and `dcat:theme` for thematic classification.

### D4D_Data_Governance.yaml — DUO for data use permissions
Data Use Ontology (DUO) terms are used as `meaning:` values on `DataUsePermissionEnum` permissible
values (e.g., `DUO:0000004` for no restriction, `DUO:0000007` for disease-specific research).
The enum itself uses `d4d:` for the slot_uri since DUO is an OBO ontology for values, not
predicates. Regulatory compliance and license slots use `dcterms:` terms.

### D4D_Collection.yaml and D4D_Preprocessing.yaml — RAI/Croissant
The Responsible AI (RAI) vocabulary from MLCommons/Croissant is used for `data_annotation_platform`
(`rai:dataAnnotationPlatform`). Other collection-specific concepts (consent, collector demographics,
acquisition methods) use `d4d:` terms, as no standard ontology covers these at the required
specificity.

### D4D_Variables.yaml — QUDT for units
Variable unit declarations use `qudt:unit` as the `slot_uri`. This is the primary QUDT predicate
for associating a unit of measurement with a quantity. Range is `uriorcurie` to allow QUDT unit
URIs (e.g., `qudt:KilogramPerCubicMeter`) or custom values.

### D4D_Motivation.yaml — Schema.org for funding and contributors
Funder and funding information use `schema:funder` and `schema:funding`. Creator credit roles
use `d4d:creditRoles` (no standard slot for CRediT taxonomy associations).

### D4D_Composition.yaml — AIO for bias types
`BiasTypeEnum` permissible values use `meaning:` to map to AIO ontology terms
(e.g., `AIO:MeasurementBias`, `AIO:HistoricalBias`). For bias types without a 1:1 AIO match,
`broad_mappings` to the closest AIO term is used instead.

### D4D_Maintenance.yaml and D4D_Distribution.yaml — DCTERMS for versions
`dcterms:hasVersion` covers version availability; `dcterms:available` is used for availability
dates. Errata and update tracking use `d4d:` terms.

---

## Custom d4d: Terms

The following `d4d:` slot URIs were minted because no standard ontology provided a
sufficiently precise predicate. All resolve under `https://w3id.org/bridge2ai/data-sheets-schema/`.

### Identity and Provenance
| d4d term | Used for |
|----------|---------|
| `d4d:doiIdentifier` | DOI-specific identifier (broader `dcterms:identifier` used as broad mapping) |
| `d4d:orcidIdentifier` | ORCID researcher identifier |
| `d4d:hashValue` | Generic cryptographic hash (algorithm-neutral) |
| `d4d:md5Checksum` | MD5-specific checksum |
| `d4d:conformsToSchema` | Schema-specific conformance (refinement of `dcterms:conformsTo`) |
| `d4d:conformsToClass` | Class-specific conformance (refinement of `dcterms:conformsTo`) |
| `d4d:publicationStatus` | Publication lifecycle status |
| `d4d:characterEncoding` | Character encoding scheme |

### Collection and Annotation
| d4d term | Used for |
|----------|---------|
| `d4d:collectionMechanisms` | Data collection mechanisms |
| `d4d:collectionType` | Type of collection (direct, inferred, etc.) |
| `d4d:collectionTimeframes` | Time period(s) of data collection |
| `d4d:dataCollectors` | Who collected the data |
| `d4d:dataAnnotationProtocol` | Annotation protocol description |
| `d4d:annotationsPerItem` | Number of annotations per data item |
| `d4d:annotatorDemographics` | Demographics of annotators |
| `d4d:agreementMetric` | Inter-annotator agreement metric |
| `d4d:disagreementPatterns` | Patterns in annotation disagreements |
| `d4d:wasDirectlyObserved` | Observation acquisition method flag |
| `d4d:wasReportedBySubjects` | Self-report acquisition flag |
| `d4d:wasInferred` | Inference/derivation acquisition flag |
| `d4d:wasValidated` | Validation acquisition flag |
| `d4d:directCollection` | Whether directly collected from subjects |

### Consent and Ethics
| d4d term | Used for |
|----------|---------|
| `d4d:consentObtained` | Whether consent was obtained |
| `d4d:consentType` | Type of consent obtained |
| `d4d:consentScope` | Scope/breadth of consent |
| `d4d:consentDocumentation` | Where consent documentation lives |
| `d4d:consentRevocations` | Revocation information |
| `d4d:collectionConsents` | Consent details for collection |
| `d4d:collectionNotifications` | Notifications given to data subjects |
| `d4d:assentProcedures` | Assent procedures for minors/vulnerable groups |
| `d4d:withdrawalMechanism` | How subjects can withdraw data |
| `d4d:ethicalReviews` | IRB/ethics review details |
| `d4d:ethicsReviewBoard` | Name of reviewing ethics board |
| `d4d:ethicsContactPoint` | Contact for ethics questions |
| `d4d:dataProtectionImpacts` | Data protection impact assessments |

### Sensitive and Confidential Data
| d4d term | Used for |
|----------|---------|
| `d4d:sensitiveElements` | Description of sensitive data elements |
| `d4d:sensitive_elements_present` | Boolean flag for sensitivity |
| `d4d:confidentialElements` | Confidential element descriptions |
| `d4d:confidential_elements_present` | Boolean flag for confidentiality |
| `d4d:confidentialityLevel` | Level of confidentiality |
| `d4d:contentWarnings` | Content warning descriptions |
| `d4d:content_warnings_present` | Boolean flag for content warnings |
| `d4d:reidentificationRisk` | Re-identification risk description |
| `d4d:anonymizationMethod` | Method used for anonymization |
| `d4d:removedIdentifierTypes` | Types of identifiers removed |

### Preprocessing and Cleaning
| d4d term | Used for |
|----------|---------|
| `d4d:cleaningStrategies` | Data cleaning strategy objects |
| `d4d:strategies` | Generic preprocessing strategy list |

### Uses and Distribution
| d4d term | Used for |
|----------|---------|
| `d4d:useCategory` | Category of intended use |
| `d4d:discouragedUses` | Uses that are discouraged but not prohibited |
| `d4d:existingUses` | Known prior uses of the dataset |
| `d4d:useRepository` | Repository indexing dataset uses |
| `d4d:distributionFormats` | Formats in which dataset is distributed |
| `d4d:distributionDates` | Distribution date information |
| `d4d:thirdPartySharing` | Third-party sharing arrangements |
| `d4d:regulatoryRestrictions` | Legal/regulatory distribution restrictions |
| `d4d:externalResourceRestrictions` | Restrictions on external resource access |
| `d4d:availabilityGuarantee` | Long-term availability commitments |
| `d4d:retentionPeriod` | Data retention period |
| `d4d:retentionLimit` | Maximum retention limit |

### Maintenance and Versioning
| d4d term | Used for |
|----------|---------|
| `d4d:versionsAvailable` | Available dataset versions |
| `d4d:versionAccess` | How to access specific versions |
| `d4d:updates` | Planned or past update information |
| `d4d:errata` | Error corrections |
| `d4d:erratumURL` | URL for errata publication |
| `d4d:extensionMechanism` | How the dataset can be extended |
| `d4d:contributionURL` | How to contribute to the dataset |

### Human Subjects and At-Risk Populations
| d4d term | Used for |
|----------|---------|
| `d4d:atRiskPopulations` | At-risk population documentation |
| `d4d:atRiskGroupsIncluded` | Specific at-risk groups present |
| `d4d:specialProtections` | Special protections in place |
| `d4d:specialPopulations` | Other special population designations |

### Composition and Subpopulations
| d4d term | Used for |
|----------|---------|
| `d4d:subpopulations` | Subpopulation objects |
| `d4d:subpopulationIdentification` | How subpopulations are identified |
| `d4d:subpopulationDistribution` | Distribution across subpopulations |
| `d4d:subpopulationElementsPresent` | Whether subpopulation info is present |
| `d4d:samplingStrategies` | Sampling strategy objects |
| `d4d:sourceData` | Source of sampled data |
| `d4d:whyNotRepresentative` | Explanation of non-representativeness |
| `d4d:relationships` | Relationships between dataset instances |
| `d4d:dataSubset` | Subset description |
| `d4d:splits` | Train/val/test split information |

### Miscellaneous
| d4d term | Used for |
|----------|---------|
| `d4d:usedSoftware` | Software used in this property/process |
| `d4d:tasks` | ML tasks the dataset supports |
| `d4d:biasType` | Type of bias (linked to AIO enum) |
| `d4d:anomalies` | Dataset anomaly objects |
| `d4d:fileCollections` | Nested file collection list |
| `d4d:fileCount` | Number of files |
| `d4d:totalFileCount` | Total file count across nested collections |
| `d4d:variableName` | Name of a variable/feature |
| `d4d:regulatoryCompliance` | Regulatory compliance declarations |
| `d4d:teamAffiliation` | Team or institutional affiliation |

---

## Known Limitations

### Approximate (broad_mappings) mappings
The following slots use `broad_mappings` because no ontology provides an exact match:

- **`d4d:hash`** → `broad_mappings: dcterms:identifier` — a hash value is a form of identifier
  but `dcterms:identifier` is not specific to cryptographic hashes.
- **`d4d:md5`** → same rationale; `schema:sha256` exists but MD5 has no Schema.org term.
- **`d4d:doi`** → `broad_mappings: dcterms:identifier`; DOI is a specific identifier scheme
  but no dedicated ontology predicate for DOI is widely used in DCAT/DC contexts.
- **`d4d:conforms_to_schema` / `d4d:conforms_to_class`** → `broad_mappings: dcterms:conformsTo`;
  these are refinements of conformance but LinkML has no standard sub-property for schema/class
  specificity.
- **`d4d:orcidIdentifier`** → `broad_mappings: schema:identifier`; ORCID has no dedicated
  Schema.org property, though `schema:identifier` with a type qualifier is the recommended
  approach.

### DUO as value vocabulary, not predicate vocabulary
DUO terms are used as `meaning:` values on enum members in `DataUsePermissionEnum` and
`DataUseModifierEnum`. They are not used as `slot_uri` predicates because DUO defines controlled
vocabulary *concepts*, not RDF predicates. The slot predicate remains `d4d:` while the enum value's
semantic meaning points to the DUO term.

### RAI/Croissant coverage
The RAI (Responsible AI) vocabulary from MLCommons/Croissant is only partially developed.
Only `rai:dataAnnotationPlatform` is currently used. Many other collection and annotation
concepts (demographics, protocols, agreement metrics) have no RAI equivalent and use `d4d:` terms.
As RAI matures, these may be replaced with canonical RAI predicates.

### AIO ontology gaps
For `BiasTypeEnum`, some bias types have no 1:1 AIO mapping:
- `selection_bias` → `broad_mappings: AIO:SelectionAndSamplingBias` (covers both selection and sampling)
- `sampling_bias` → same broad mapping as selection_bias
- `aggregation_bias` → `broad_mappings: AIO:EcologicalFallacyBias` (closest available)
- `algorithmic_bias` → `broad_mappings: AIO:ProcessingBias, AIO:ComputationalBias` (split concept)
- `annotation_bias` → `broad_mappings: AIO:AnnotatorReportingBias` (narrower than intended)
