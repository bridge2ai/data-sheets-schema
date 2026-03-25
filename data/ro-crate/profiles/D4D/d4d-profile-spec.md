# RO-Crate Profile: Datasheets for Datasets (D4D)

**Profile URI**: `https://w3id.org/bridge2ai/ro-crate-profile/d4d/1.0`
**Version**: 1.0
**Date**: 2026-03-11
**Status**: Draft
**Authors**: Bridge2AI Data Standards Core

---

## Overview

This RO-Crate profile defines how to package dataset documentation following the "Datasheets for Datasets" (D4D) methodology within RO-Crate metadata. It extends the base RO-Crate 1.2 specification with D4D-specific properties for comprehensive dataset documentation covering motivation, composition, collection, preprocessing, uses, distribution, maintenance, and ethical considerations.

### FAIRSCAPE Reference Implementation

The **FAIRSCAPE** (FAIR Structured Computational Archive for Provenance and Execution) framework provides a canonical reference implementation of RO-Crate metadata for the Bridge2AI Cell Maps for AI (CM4AI) project. The FAIRSCAPE RO-Crate example (`../fairscape/full-ro-crate-metadata.json`) demonstrates best practices for:

- **@context** structure using object notation with `@vocab`
- **EVI namespace** properties for computational provenance (datasetCount, computationCount, etc.)
- **additionalProperty** pattern with PropertyValue objects
- **Author formatting** as semicolon-separated strings

This D4D profile aligns with FAIRSCAPE patterns while extending them with comprehensive D4D documentation fields. See [FAIRSCAPE documentation](https://fairscape.github.io/) for more details.

## Purpose

The D4D RO-Crate Profile enables:
- **Structured dataset documentation** using the Datasheets for Datasets framework
- **Machine-readable metadata** for dataset discovery and assessment
- **FAIR compliance** through comprehensive, standardized documentation
- **Responsible AI** support via detailed bias, limitation, and ethics documentation
- **Interoperability** between D4D YAML/JSON and RO-Crate packaging

## Conformance

An RO-Crate conforms to this profile if:
1. It includes the D4D profile URI in the `conformsTo` property of the metadata descriptor
2. The root Dataset entity includes required D4D properties (see §4)
3. All D4D properties use the vocabulary defined in the D4D JSON-LD context
4. The metadata validates against the D4D SHACL shapes (optional but recommended)

### Conformance Levels

**Level 1 (Minimal)**: Required properties only (8 properties)
**Level 2 (Basic)**: Required + recommended properties (25 properties)
**Level 3 (Complete)**: All applicable D4D sections (100+ properties)

---

## Namespaces and Context

### Required Namespaces

**Option 1: Array with URI references (Recommended for D4D)**
```json
{
  "@context": [
    "https://w3id.org/ro/crate/1.2/context",
    "https://w3id.org/bridge2ai/d4d-context/1.0",
    {
      "@vocab": "https://schema.org/",
      "d4d": "https://w3id.org/bridge2ai/data-sheets-schema/",
      "rai": "http://mlcommons.org/croissant/RAI/",
      "evi": "https://w3id.org/EVI#"
    }
  ]
}
```

**Option 2: Object with @vocab (FAIRSCAPE pattern)**
```json
{
  "@context": {
    "@vocab": "https://schema.org/",
    "EVI": "https://w3id.org/EVI#"
  }
}
```

**Note**: Both patterns are valid JSON-LD. The FAIRSCAPE pattern (Option 2) is more compact but requires explicit namespace declarations for all non-schema.org terms. The D4D pattern (Option 1) references external contexts and adds local namespace extensions. Use Option 1 for full D4D compliance; Option 2 is shown for FAIRSCAPE compatibility reference.

### Vocabulary Sources

- **schema.org**: Core metadata (name, description, author, datePublished, etc.)
- **d4d:**: D4D-specific properties (addressing_gaps, known_biases, etc.)
- **rai:**: Responsible AI metadata (ML Commons Croissant RAI extension)
- **evi:**: FAIRSCAPE Evidence metadata (dataset counts, formats, etc.)

---

## Required Properties (Level 1)

All D4D RO-Crates MUST include these 8 properties on the root Dataset:

| Property | Type | Description |
|----------|------|-------------|
| `@type` | Type | Must include "Dataset" |
| `name` | Text | Dataset title |
| `description` | Text | Dataset description (minimum 5 characters) |
| `datePublished` | Date | Publication or release date |
| `license` | URL/Text | Dataset license |
| `keywords` | Array[Text] | Searchable keywords (minimum 3) |
| `author` | Text/Person | Dataset creator(s) |
| `identifier` | URL/Text | Persistent identifier (DOI, ARK, etc.) |

### Example

```json
{
  "@type": ["Dataset", "https://w3id.org/EVI#ROCrate"],
  "name": "My Dataset",
  "description": "A comprehensive dataset for...",
  "datePublished": "2026-03-11",
  "license": "https://creativecommons.org/licenses/by/4.0/",
  "keywords": ["machine learning", "genomics", "protein interactions"],
  "author": "Jane Doe; John Smith",
  "identifier": "https://doi.org/10.1234/example"
}
```

---

## Recommended Properties (Level 2)

D4D RO-Crates SHOULD include these additional 17 properties:

### Motivation & Purpose
- `d4d:purposes` - Why the dataset was created
- `d4d:addressingGaps` - Gaps addressed by dataset creation

### Composition
- `contentSize` - Dataset size
- `evi:formats` - File formats included

### Collection
- `rai:dataCollection` - Data collection methodology
- `rai:dataCollectionTimeframe` - Collection time period

### Preprocessing
- `rai:dataManipulationProtocol` - Data cleaning procedures
- `rai:dataPreprocessingProtocol` - Preprocessing steps

### Ethics & Compliance
- `ethicalReview` - Ethical review information
- `humanSubjectResearch` - Human subjects research details
- `deidentified` - De-identification status
- `confidentialityLevel` - Data confidentiality classification

### Quality & Limitations
- `rai:dataLimitations` - Known limitations
- `rai:dataBiases` - Known biases

### Uses
- `rai:dataUseCases` - Intended use cases
- `prohibitedUses` - Prohibited uses

### Distribution & Maintenance
- `publisher` - Publisher/host
- `rai:dataReleaseMaintenancePlan` - Maintenance plan

---

## Complete D4D Properties (Level 3)

### 1. Motivation Section

Properties documenting why the dataset was created:

| Property | Type | D4D Class | Description |
|----------|------|-----------|-------------|
| `d4d:purposes` | Array[Text] | Purpose | Why dataset was created |
| `d4d:addressingGaps` | Text | AddressingGap | Gaps addressed |
| `d4d:tasks` | Array[Text] | Task | Specific tasks dataset enables |
| `funder` | Array[Text] | FundingMechanism | Funding sources |
| `d4d:sponsors` | Array[Text] | SponsoringEntity | Sponsors |

### 2. Composition Section

Properties describing what the dataset contains:

| Property | Type | D4D Class | Description |
|----------|------|-----------|-------------|
| `d4d:instances` | Object | Instance | Instance descriptions |
| `d4d:instanceCount` | Integer | Instance | Number of instances |
| `contentSize` | Text/Integer | - | Dataset size |
| `evi:totalContentSizeBytes` | Integer | - | Size in bytes |
| `evi:formats` | Array[Text] | - | File formats |
| `encodingFormat` | Text | - | Primary encoding format |
| `d4d:subpopulations` | Array[Object] | SubpopulationElement | Subpopulations present |
| `d4d:missingInfo` | Array[Object] | MissingInfo | Missing information |
| `d4d:relationshipsBetweenInstances` | Text | - | Relationships |
| `d4d:splits` | Array[Object] | DataSplit | Train/test/validation splits |
| `d4d:errorSources` | Array[Text] | - | Potential error sources |
| `d4d:confidentialElements` | Array[Object] | ConfidentialElement | Confidential data |

### 3. Collection Section

Properties documenting how data was collected:

| Property | Type | D4D Class | Description |
|----------|------|-----------|-------------|
| `rai:dataCollection` | Text | CollectionMechanism | Collection methodology |
| `rai:dataCollectionType` | Array[Text] | CollectionMechanism | Collection types |
| `rai:dataCollectionTimeframe` | Array[Date] | CollectionTimeframe | Collection dates |
| `d4d:samplingStrategy` | Text | SamplingStrategy | Sampling methodology |
| `d4d:dataCollectors` | Array[Object] | DataCollector | Who collected data |
| `rai:dataCollectionMissingData` | Text | - | Missing data documentation |
| `rai:dataCollectionRawData` | Text | RawDataSource | Raw data sources |

### 4. Preprocessing Section

Properties documenting data processing:

| Property | Type | D4D Class | Description |
|----------|------|-----------|-------------|
| `rai:dataManipulationProtocol` | Text | CleaningStrategy | Data cleaning |
| `rai:dataImputationProtocol` | Text | ImputationProtocol | Imputation methodology |
| `rai:dataPreprocessingProtocol` | Array[Text] | PreprocessingStrategy | Preprocessing steps |
| `rai:dataAnnotationProtocol` | Array[Text] | LabelingStrategy | Annotation methodology |
| `rai:dataAnnotationPlatform` | Array[Text] | LabelingStrategy | Annotation platform |
| `rai:annotationsPerItem` | Integer | LabelingStrategy | Annotations per item |
| `rai:machineAnnotationTools` | Array[Text] | MachineAnnotationTools | Automated tools |
| `rai:dataAnnotationAnalysis` | Array[Text] | AnnotationAnalysis | Quality analysis |
| `d4d:rawDataSaved` | Boolean | RawData | Raw data preserved |
| `d4d:rawDataLocation` | URL | RawData | Raw data access |

### 5. Uses Section

Properties documenting intended and prohibited uses:

| Property | Type | D4D Class | Description |
|----------|------|-----------|-------------|
| `rai:dataUseCases` | Array[Text] | IntendedUse | Intended use cases |
| `d4d:existingUses` | Array[Text] | ExistingUse | Already used for |
| `d4d:otherUses` | Array[Text] | OtherUse | Other potential uses |
| `d4d:discouragedUses` | Array[Text] | DiscouragedUse | Discouraged uses |
| `prohibitedUses` | Array[Text] | ProhibitedUse | Prohibited uses |
| `d4d:useRepository` | URL | UseRepository | Use case repository |
| `rai:dataSocialImpact` | Text | FutureUseImpact | Social impact |

### 6. Distribution Section

Properties documenting how dataset is distributed:

| Property | Type | D4D Class | Description |
|----------|------|-----------|-------------|
| `publisher` | Text/URL | - | Publisher |
| `contentUrl` | URL | - | Download URL |
| `conditionsOfAccess` | Text | - | Access conditions |
| `usageInfo` | Text | - | Usage guidelines |
| `copyrightNotice` | Text | - | Copyright information |
| `citation` | Text | - | Recommended citation |
| `d4d:distributionFormat` | Array[Text] | DistributionFormat | Distribution formats |
| `d4d:distributionDates` | Date | - | Distribution date |
| `d4d:ipRestrictions` | Text | LicenseAndUseTerms | IP restrictions |
| `d4d:exportControls` | Text | RegulatoryRestriction | Export controls |
| `d4d:retentionLimit` | Text | - | Retention limits |

### 7. Maintenance Section

Properties documenting maintenance and versioning:

| Property | Type | D4D Class | Description |
|----------|------|-----------|-------------|
| `version` | Text | - | Dataset version |
| `rai:dataReleaseMaintenancePlan` | Text | Update | Maintenance plan |
| `d4d:maintainer` | Array[Person] | Maintainer | Maintainers |
| `d4d:errataURL` | URL | Errata | Errata location |
| `dateModified` | Date | - | Last modified date |
| `d4d:versionAccess` | Text | VersionAccess | Version access policy |

### 8. Ethical Considerations

Properties documenting ethical review and compliance:

| Property | Type | D4D Class | Description |
|----------|------|-----------|-------------|
| `ethicalReview` | Text | EthicalReview | Ethical review details |
| `irb` | Text | EthicalReview | IRB information |
| `irbProtocolId` | Text | EthicalReview | IRB protocol ID |
| `humanSubjectResearch` | Text | HumanSubjectResearch | Human subjects details |
| `humanSubjectExemption` | Text | HumanSubjectResearch | Exemption details |
| `d4d:informedConsent` | Text | InformedConsent | Consent procedures |
| `d4d:atRiskPopulations` | Array[Text] | VulnerablePopulation | At-risk populations |
| `rai:personalSensitiveInformation` | Array[Text] | SensitiveElement | PII/sensitive data |
| `deidentified` | Boolean | - | De-identification status |
| `fdaRegulated` | Boolean | - | FDA regulation status |
| `confidentialityLevel` | Text | - | Confidentiality level |
| `d4d:dataProtectionImpactAssessment` | Text | DataProtectionImpact | DPIA details |

### 9. Quality & Limitations

Properties documenting quality, biases, and limitations:

| Property | Type | D4D Class | Description |
|----------|------|-----------|-------------|
| `rai:dataBiases` | Array[Text] | KnownBias | Known biases |
| `rai:dataLimitations` | Array[Text] | KnownLimitation | Known limitations |
| `d4d:dataAnomalies` | Array[Text] | Anomaly | Data anomalies |
| `d4d:contentWarning` | Text | ContentWarning | Content warnings |
| `d4d:validationAnalysis` | Text | - | Validation procedures |
| `hasSummaryStatistics` | Text/URL | - | Summary statistics |

### 10. Governance & Provenance

Properties documenting governance and provenance:

| Property | Type | D4D Class | Description |
|----------|------|-----------|-------------|
| `dataGovernanceCommittee` | Text | - | Governance committee |
| `principalInvestigator` | Text | - | Principal investigator |
| `contactEmail` | Email | - | Contact email |
| `isPartOf` | Array[Reference] | - | Parent datasets |
| `hasPart` | Array[Reference] | - | Sub-datasets |
| `generatedBy` | Array[Reference] | - | Generating computations |
| `derivedFrom` | Array[Reference] | - | Source datasets |

---

## FAIRSCAPE Evidence Metadata (Optional)

For RO-Crates generated by FAIRSCAPE tools or following FAIRSCAPE patterns:

| Property | Type | Description | FAIRSCAPE Example |
|----------|------|-------------|-------------------|
| `evi:datasetCount` | Integer | Number of datasets in crate | `330` |
| `evi:computationCount` | Integer | Number of computations | `312` |
| `evi:softwareCount` | Integer | Number of software entities | `5` |
| `evi:schemaCount` | Integer | Number of schemas | `20` |
| `evi:totalEntities` | Integer | Total entities | `647` |
| `evi:entitiesWithSummaryStats` | Integer | Entities with statistics | `1` |
| `evi:entitiesWithChecksums` | Integer | Entities with checksums | `6` |
| `evi:totalContentSizeBytes` | Integer | Total size in bytes | `19454700000000` |
| `evi:formats` | Array[Text] | File formats present | `[".d", ".tsv", ".xml", "h5ad"]` |

### FAIRSCAPE Usage Pattern

FAIRSCAPE RO-Crates use EVI properties to document computational provenance and content characteristics. Example from CM4AI dataset:

```json
{
  "@type": ["Dataset", "https://w3id.org/EVI#ROCrate"],
  "name": "Cell Maps for AI - January 2026 Data Release",
  "evi:datasetCount": 330,
  "evi:computationCount": 312,
  "evi:softwareCount": 5,
  "evi:schemaCount": 20,
  "evi:totalContentSizeBytes": 19454700000000,
  "evi:formats": [".d", ".tsv", ".xml", "h5ad", "pdf"]
}
```

**Note**: EVI properties are particularly useful for large computational RO-Crates with multiple datasets, workflows, and software components. For simple data-only crates, minimal EVI properties (datasetCount, formats) may suffice.

---

## Property Value Objects

Many D4D properties use structured objects rather than simple strings.

### Person/Organization

```json
{
  "@type": "Person",
  "name": "Jane Doe",
  "email": "jane@example.org",
  "affiliation": {
    "@type": "Organization",
    "name": "Example University"
  }
}
```

### Date Range

```json
{
  "@type": "PropertyValue",
  "name": "Collection Timeframe",
  "startDate": "2022-01-01",
  "endDate": "2023-12-31"
}
```

### Bias/Limitation Objects

```json
{
  "@type": "d4d:KnownBias",
  "description": "Selection bias due to...",
  "type": "selection_bias",
  "mitigation": "Stratified sampling was used to..."
}
```

---

## additionalProperty Pattern

For D4D properties not yet in schema.org or custom extensions, use the **PropertyValue** pattern following FAIRSCAPE conventions:

```json
{
  "additionalProperty": [
    {
      "@type": "PropertyValue",
      "name": "Completeness",
      "value": "Dataset is 95% complete..."
    },
    {
      "@type": "PropertyValue",
      "name": "Human Subject",
      "value": "No human subjects involved"
    },
    {
      "@type": "PropertyValue",
      "name": "Data Governance Committee",
      "value": "Jilian Parker"
    },
    {
      "@type": "PropertyValue",
      "name": "Prohibited Uses",
      "value": "These laboratory data are not to be used in clinical decision-making..."
    }
  ]
}
```

### FAIRSCAPE Usage Example

The FAIRSCAPE CM4AI dataset uses `additionalProperty` for metadata not directly expressible in schema.org:

```json
{
  "additionalProperty": [
    {
      "@type": "PropertyValue",
      "name": "Completeness",
      "value": "These data are not yet in completed final form, and some datasets are under temporary pre-publication embargo..."
    },
    {
      "@type": "PropertyValue",
      "name": "Human Subject",
      "value": "None - data collected from commercially available cell lines"
    }
  ]
}
```

**Note**: Prefer direct schema.org or D4D namespace properties when available. Use `additionalProperty` only for truly custom or domain-specific metadata not covered by standard vocabularies.

---

## Validation

### SHACL Shapes

The profile includes SHACL shapes for validation:

- **`d4d-minimal-shape.ttl`** - Level 1 conformance
- **`d4d-basic-shape.ttl`** - Level 2 conformance
- **`d4d-complete-shape.ttl`** - Level 3 conformance

### Python Validation

```python
from linkml.validators import JsonschemaValidator

validator = JsonschemaValidator("d4d-profile-schema.yaml")
report = validator.validate(rocrate_data, target_class="Dataset")
```

---

## Examples

### Minimal D4D RO-Crate (Level 1)

See: `examples/d4d-rocrate-minimal.json`

### Basic D4D RO-Crate (Level 2)

See: `examples/d4d-rocrate-basic.json`

### Complete D4D RO-Crate (Level 3)

See: `examples/d4d-rocrate-complete.json`

### Real-world Example

See: `data/ro-crate/reference/full-ro-crate-metadata.json`

---

## Transformation Tools

### RO-Crate → D4D YAML

```bash
python .claude/agents/scripts/rocrate_to_d4d.py \
  --input rocrate-metadata.json \
  --output datasheet.yaml \
  --mapping mapping.tsv \
  --validate
```

### D4D YAML → RO-Crate

```bash
python .claude/agents/scripts/d4d_to_rocrate.py \
  --input datasheet.yaml \
  --output rocrate-metadata.json \
  --validate
```

---

## References

- **RO-Crate 1.2**: https://w3id.org/ro/crate/1.2
- **D4D Schema**: https://w3id.org/bridge2ai/data-sheets-schema/
- **Datasheets for Datasets (paper)**: https://arxiv.org/abs/1803.09010
- **FAIR Principles**: https://www.go-fair.org/fair-principles/
- **ML Commons Croissant**: https://github.com/mlcommons/croissant
- **FAIRSCAPE**: https://fairscape.github.io/

---

## License

This profile is licensed under CC-BY 4.0.

---

## Changelog

### Version 1.0 (2026-03-11)
- Initial release
- 124 mapped properties
- Three conformance levels
- FAIRSCAPE Evidence metadata support
- Bidirectional transformation support
