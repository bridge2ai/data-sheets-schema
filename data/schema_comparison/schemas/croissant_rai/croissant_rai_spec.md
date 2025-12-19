# Croissant RAI Specification: Key Components

## Overview
The Croissant RAI (Responsible AI) Specification Version 1.0 extends the Croissant format with machine-readable metadata for ethical AI dataset documentation. It builds on schema.org/Dataset and uses the namespace `http://mlcommons.org/croissant/RAI/`.

## Core Vocabulary Structure

**Namespace Declaration:**
```
"rai": "http://mlcommons.org/croissant/RAI/"
"sc": "https://schema.org/"
"cr": "http://mlcommons.org/croissant/"
```

**Conformance Declaration:**
```json
"dct:conformsTo": "http://mlcommons.org/croissant/RAI/1.0"
```

## Primary RAI Properties

The specification defines 20 properties organized across five use cases:

### Data Lifecycle (Dataset Level)
- `rai:dataCollection` - Description of the data collection process
- `rai:dataCollectionType` - Enumerated types (surveys, web scraping, manual curation, etc.)
- `rai:dataCollectionTimeframe` - Temporal scope of data collection
- `rai:dataCollectionMissingData` - Documentation of missing data patterns
- `rai:dataCollectionRawData` - Raw data sources before preprocessing
- `rai:dataLimitations` - Known constraints and generalization limits
- `rai:dataPreprocessingProtocol` - Preparation steps for ML processing

### Data Labeling
- `rai:dataAnnotationProtocol` - Annotation methodology and task definitions
- `rai:dataAnnotationPlatform` - Tools and platforms used for annotation
- `rai:annotationsPerItem` - Number of labels per instance
- `rai:annotatorDemographics` - Demographic specifications of annotators
- `rai:dataAnnotationAnalysis` - Analysis of annotation quality and agreement
- `rai:machineAnnotationTools` - Automated annotation tools and models

### Safety & Fairness Evaluation
- `rai:dataBiases` - Documented bias descriptions
- `rai:dataSocialImpact` - Social impact discussion
- `rai:personalSensitiveInformation` - PII categories (gender, location, age, etc.)
- `rai:dataUseCases` - Intended applications and usage guidelines

### Compliance & Governance
- `rai:dataManipulationProtocol` - Data cleaning and transformation procedures
- `rai:dataImputationProtocol` - Missing data imputation methodology
- `rai:dataReleaseMaintenancePlan` - Versioning and deprecation policies

## Example Implementation

Datasets declare RAI properties in JSON-LD format within their Croissant metadata, enabling automated discovery and assessment of responsible AI practices across dataset ecosystems.
