# D4D Slim Schema

**A streamlined version of Datasheets for Datasets optimized for RO-Crate transformations**

## Overview

D4D Slim is a reduced-complexity version of the full [Datasheets for Datasets (D4D)](https://w3id.org/bridge2ai/data-sheets-schema) schema, designed specifically for:

- **RO-Crate JSON-LD to D4D YAML transformations**
- **Minimal dataset documentation requirements**
- **Progressive enhancement** (start simple, add detail as needed)
- **Rapid prototyping** of dataset documentation

## Key Statistics

```
Full D4D Schema:  74 classes, 680 attributes
D4D Slim:          5 classes, 237 attributes

Reduction:        93% fewer classes, 65% fewer attributes
RO-Crate Coverage: 40% of full schema (272 mapped attributes)
```

## Included Classes

D4D Slim includes only classes with **≥50% RO-Crate mapping coverage**:

### Core Classes (3)

1. **Dataset** (87.9% coverage - 91 attributes)
   - Single data file or coherent data resource
   - Most comprehensive class with file metadata, provenance, composition, ethics, etc.

2. **DataSubset** (86.0% coverage - 93 attributes)
   - Subset of a dataset (train/test split, subpopulation, etc.)
   - Inherits all Dataset attributes + subset-specific fields

3. **DatasetCollection** (83.3% coverage - 24 attributes)
   - Collection of related datasets
   - Top-level container for grouping resources

### Base Classes (2)

4. **Information** (82.6% coverage - 23 attributes)
   - Abstract base class for information resources
   - Provides common metadata (title, description, license, etc.)

5. **Software** (50.0% coverage - 6 attributes)
   - Software used in dataset creation/processing
   - Basic identification and licensing

## Excluded Classes

**69 classes excluded** (all module-specific detail classes):

- **Motivation module** (7 classes): Purpose, Task, Gap, Grantor, Grant, Funder, etc.
- **Composition module** (15 classes): Instance, SamplingStrategy, DataAnomaly, Bias, Limitation, etc.
- **Collection module** (7 classes): CollectionMechanism, Timeframe, AcquisitionMethod, etc.
- **Preprocessing module** (7 classes): PreprocessingStrategy, CleaningStrategy, LabelingStrategy, etc.
- **Uses module** (7 classes): IntendedUse, DiscouragedUse, FutureUseImpact, etc.
- **Distribution module** (3 classes): DistributionFormat, DistributionDate, LicenseAndUseTerms
- **Maintenance module** (6 classes): Maintainer, Update, Errata, VersionAccess, etc.
- **Ethics module** (5 classes): EthicalReview, DataProtectionImpact, CollectionConsent, etc.
- **Human module** (3 classes): HumanSubjectResearch, InformedConsent, VulnerablePopulations
- **Data Governance module** (3 classes): IPRestrictions, RegulatoryRestrictions, ThirdPartySharing
- **Variables module** (1 class): Variable
- **Base module** (1 class): FormatDialect (0% coverage)

## Design Principles

### 1. Simplification Strategy

Complex type references in the full D4D schema have been simplified:

**Full D4D:**
```yaml
preprocessing_strategies:
  range: PreprocessingStrategy  # Complex object
  multivalued: true
```

**D4D Slim:**
```yaml
preprocessing_strategies:
  range: string  # Simplified to string
  multivalued: true
```

### 2. Complete-Class Approach

Rather than cherry-picking attributes, D4D Slim includes **all attributes** from classes with ≥50% coverage. This:

- Maintains schema coherence
- Provides clear documentation of what's available vs. what's missing
- Allows progressive enhancement (populate more fields as data becomes available)
- Simplifies migration path to full D4D

### 3. Unmapped Attribute Documentation

Every class includes comments documenting:
- RO-Crate mapping coverage percentage
- List of unmapped attributes
- Transformation notes

**Example:**
```yaml
# RO-Crate mapping coverage: 87.9% (80/91 attributes)
# Unmapped attributes: citation, conforms_to_class, conforms_to_schema,
#   external_resources, format, id, machine_annotation_tools, name,
#   parent_datasets, related_datasets, variables
```

## Usage

### 1. RO-Crate to D4D Slim Transformation

```bash
# Transform RO-Crate to D4D Slim
python .claude/agents/scripts/rocrate_to_d4d.py \
  --input rocrate-metadata.json \
  --output dataset_slim.yaml \
  --mapping data/ro-crate_mapping/D4D\ -\ RO-Crate\ -\ RAI\ Mappings.xlsx\ -\ Class\ Alignment.tsv \
  --schema src/data_sheets_schema/schema/D4D_Slim.yaml \
  --validate
```

### 2. Programmatic Access (Python)

```python
from project.slim.D4D_Slim import Dataset, DatasetCollection

# Create a minimal dataset
dataset = Dataset(
    title="My Dataset",
    description="A sample dataset",
    license="CC-BY-4.0",
    creators=["Jane Doe", "John Smith"],
    bytes=1024000,
    md5="abc123..."
)

# Create a collection
collection = DatasetCollection(
    title="My Dataset Collection",
    description="A collection of related datasets",
    resources=["dataset1.yaml", "dataset2.yaml"]
)
```

### 3. JSON Schema Validation

```bash
# Validate a D4D Slim YAML against the JSON Schema
poetry run linkml-validate \
  -s src/data_sheets_schema/schema/D4D_Slim.yaml \
  -C Dataset \
  my_dataset.yaml
```

## Critical Gaps in D4D Slim

When using D4D Slim instead of full D4D, you lose:

### 1. Workflow/Process Documentation (11 classes)
- Detailed collection mechanisms, acquisition methods, timeframes
- Preprocessing, cleaning, labeling strategy details
- Annotation quality analysis, imputation protocols

**Workaround:** Use simplified string fields (`collection_mechanisms`, `preprocessing_strategies`, etc.) for basic documentation.

### 2. Quality/Validation (5 classes)
- Structured bias documentation with types, mitigation strategies
- Detailed limitation descriptions with scope and impact
- Anomaly tracking with affected subsets
- Missing data patterns and analysis

**Workaround:** Use `known_biases`, `known_limitations`, `anomalies` string arrays.

### 3. Ethical/Compliance (6 classes)
- Detailed IRB approval documentation
- Consent procedures, withdrawal mechanisms, consent scope
- At-risk population protections, assent procedures
- Data protection impact analysis details

**Workaround:** Use `ethical_reviews`, `informed_consent`, `vulnerable_populations` string arrays.

### 4. Technical Metadata (3 classes)
- Format dialect details (CSV headers, delimiters, quote characters)
- Distribution format specifications
- Detailed file structure information

**Workaround:** Use `dialect`, `format`, `distribution_formats` string fields.

### 5. Distribution/Access (7 classes)
- Licensing term details and fees
- Version access policies and procedures
- Export control and regulatory compliance details
- Third-party sharing agreements

**Workaround:** Use `license_and_use_terms`, `version_access`, `regulatory_restrictions` string arrays.

## Migration Path

### From D4D Slim → Full D4D

1. **Start with D4D Slim** for rapid documentation
2. **Identify gaps** using unmapped attribute comments
3. **Progressively enhance** by adding detail classes:
   - Replace string arrays with structured objects
   - Add nested classes for complex information
   - Use full module classes for detailed documentation

### Example Enhancement

**D4D Slim (simplified):**
```yaml
preprocessing_strategies:
  - "Tokenization using NLTK 3.8"
  - "Removed stop words"
```

**Full D4D (structured):**
```yaml
preprocessing_strategies:
  - strategy_type: tokenization
    tools:
      - name: NLTK
        version: "3.8"
    description: "Text tokenization using NLTK word tokenizer"
  - strategy_type: filtering
    description: "Removed English stop words using NLTK corpus"
    validation_method: "Manual review of 100 random samples"
```

## Files

```
project/slim/
├── README.md                    # This file
├── D4D_Slim.py                  # Generated Python datamodel (57 KB)
├── jsonschema/
│   └── D4D_Slim.schema.json    # JSON Schema for validation
└── jsonld/
    └── D4D_Slim.jsonld         # JSON-LD context
```

## Comparison: D4D Slim vs. Full D4D

| Aspect | D4D Slim | Full D4D |
|--------|----------|----------|
| **Classes** | 5 core classes | 74 classes (13 modules) |
| **Attributes** | ~237 total | 680 total |
| **Complexity** | Low - strings/arrays | High - nested objects |
| **RO-Crate Coverage** | 40% (direct mapping) | 100% (full coverage) |
| **Use Case** | Quick documentation, RO-Crate transform | Comprehensive documentation |
| **Learning Curve** | Easy (1-2 hours) | Moderate (1-2 days) |
| **Validation** | Fast (<1 sec) | Slower (complex validation) |
| **Documentation Depth** | Surface-level | Deep, structured |

## When to Use D4D Slim

✅ **Use D4D Slim when:**
- Transforming from RO-Crate metadata
- Creating quick dataset documentation
- Prototyping dataset catalog systems
- Need simple, flat data structures
- Minimal documentation requirements
- Want to avoid complex nested objects

❌ **Use Full D4D when:**
- Comprehensive dataset documentation needed
- Regulatory compliance requires detail (HIPAA, GDPR)
- Publishing to scientific repositories
- Tracking complex provenance/workflow
- Documenting ethical review processes in detail
- Need structured quality/bias documentation

## Support & Documentation

- **Full D4D Schema**: https://w3id.org/bridge2ai/data-sheets-schema
- **RO-Crate Spec**: https://www.researchobject.org/ro-crate/
- **LinkML**: https://linkml.io/
- **Issues**: https://github.com/bridge2ai/data-sheets-schema/issues

## License

MIT License (same as full D4D schema)

---

**Generated from:** D4D Schema v2024-03 with Complete-Class approach (≥50% coverage threshold)
**Analysis Date:** 2026-03-09
**Coverage Report:** `notes/D4D_SLIM_ANALYSIS.md`
