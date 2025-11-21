# Schema.org Dataset Vocabulary Summary

## Core Definition
The Dataset type represents "a body of structured information describing some topic(s) of interest." It extends `schema:CreativeWork`, inheriting properties from CreativeWork and Thing while adding dataset-specific capabilities.

## Dataset-Specific Properties

**distribution** (DataDownload)
Specifies downloadable forms of the dataset in particular formats and locations. Multiple distributions may contain different subsets of data.

**includedInDataCatalog** (DataCatalog)
Identifies which data catalog contains this dataset. Supersedes deprecated properties `includedDataCatalog` and `catalog`.

**issn** (Text)
The International Standard Serial Number identifying serial publications, repeatable for different formats.

**measurementMethod** (DefinedTerm | MeasurementMethodEnum | Text | URL)
Subproperty of `measurementTechnique` specifying particular measurement methods, especially via controlled enumerations.

**measurementTechnique** (DefinedTerm | MeasurementMethodEnum | Text | URL)
Describes the technique, method, or technology used for measuring variables. Examples: "mass spectrometry," "Zung Scale," or "HAM-D" depression assessment.

**variableMeasured** (Property | PropertyValue | StatisticalVariable | Text)
Indicates variables measured in the dataset, described as text or PropertyValue pairs with identifiers and descriptions.

## Inherited Key Properties

From CreativeWork: `author`, `creator`, `publisher`, `dateCreated`, `dateModified`, `datePublished`, `license`, `citation`, `keywords`, `abstract`, `description`, `version`, `isAccessibleForFree`, `spatialCoverage`, `temporalCoverage`, `provider`

From Thing: `name`, `identifier`, `url`, `sameAs`, `image`, `description`

## Equivalent Classes
The Dataset type aligns with:
- `void:Dataset`
- `dcmitype:Dataset`
- `dcat:Dataset`

## Related Types
- **DataFeed**: More specific subtype of Dataset
- **DataCatalog**: Contains datasets
- **DataDownload**: Represents distribution formats
- **Observation**: Can reference datasets
- **StatisticalVariable**: Describes measured variables

## Usage Context
Datasets may appear as values for properties on:
- `DataCatalog.dataset`
- `SpecialAnnouncement.diseaseSpreadStatistics`
- `Hospital.healthcareReportingData`
