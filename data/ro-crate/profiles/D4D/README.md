# RO-Crate Profile: Datasheets for Datasets (D4D)

**Profile URI**: `https://w3id.org/bridge2ai/ro-crate-profile/d4d/1.0`
**Version**: 1.0
**Date**: 2026-03-11
**Status**: Draft
**Authors**: Bridge2AI Data Standards Core

---

## Overview

This directory contains a complete RO-Crate profile for the **Datasheets for Datasets (D4D)** methodology. The profile defines how to package comprehensive dataset documentation within RO-Crate metadata following the D4D framework.

The profile enables:
- ✅ **Structured dataset documentation** using the Datasheets for Datasets framework
- ✅ **Machine-readable metadata** for dataset discovery and assessment
- ✅ **FAIR compliance** through comprehensive, standardized documentation
- ✅ **Responsible AI** support via detailed bias, limitation, and ethics documentation
- ✅ **Interoperability** between D4D YAML/JSON and RO-Crate packaging

---

## FAIRSCAPE Reference Implementation

The **FAIRSCAPE** (FAIR Structured Computational Archive for Provenance and Execution) framework provides a canonical reference implementation of RO-Crate metadata for the Bridge2AI **Cell Maps for AI (CM4AI)** project.

### Reference File

**Location**: `../fairscape/full-ro-crate-metadata.json`

This file demonstrates production-quality RO-Crate metadata for a large-scale computational biology dataset (CM4AI January 2026 Data Release, 19.1 TB, 647 entities).

### Key FAIRSCAPE Patterns

The D4D profile aligns with and extends the following FAIRSCAPE patterns:

#### 1. **@context Structure**
FAIRSCAPE uses object notation with `@vocab`:
```json
{
  "@context": {
    "@vocab": "https://schema.org/",
    "EVI": "https://w3id.org/EVI#"
  }
}
```

D4D extends this with URI references:
```json
{
  "@context": [
    "https://w3id.org/ro/crate/1.2/context",
    "https://w3id.org/bridge2ai/d4d-context/1.0",
    {
      "@vocab": "https://schema.org/",
      "EVI": "https://w3id.org/EVI#"
    }
  ]
}
```

#### 2. **EVI Namespace Properties**
FAIRSCAPE tracks computational provenance with EVI properties:
- `evi:datasetCount` (330) - Number of datasets
- `evi:computationCount` (312) - Number of computations
- `evi:softwareCount` (5) - Software tools used
- `evi:totalContentSizeBytes` (19.1 TB) - Total data size
- `evi:formats` - File formats present (`.d`, `.tsv`, `h5ad`, etc.)

D4D profiles include these properties for computational RO-Crates.

#### 3. **Author Formatting**
FAIRSCAPE uses semicolon-separated author strings:
```json
{
  "author": "Clark T; Parker J; Al Manir S; Axelsson U; ..."
}
```

D4D adopts this pattern for compatibility.

#### 4. **additionalProperty Pattern**
FAIRSCAPE uses PropertyValue objects for custom metadata:
```json
{
  "additionalProperty": [
    {
      "@type": "PropertyValue",
      "name": "Completeness",
      "value": "These data are not yet in completed final form..."
    },
    {
      "@type": "PropertyValue",
      "name": "Human Subject",
      "value": "None - data collected from commercially available cell lines"
    }
  ]
}
```

D4D uses the same pattern for domain-specific metadata not in standard vocabularies.

### Key Differences Between FAIRSCAPE and D4D Profile

| Aspect | FAIRSCAPE | D4D Profile |
|--------|-----------|-------------|
| **Primary focus** | Computational provenance | Dataset documentation |
| **@context** | Object with @vocab | Array with URI references + @vocab |
| **Namespace scope** | schema.org + EVI | schema.org + d4d + rai + EVI |
| **Property count** | ~50 (computational focus) | ~130 (comprehensive documentation) |
| **Ethics/compliance** | Minimal (cell lines) | Extensive (human subjects, IRB, consent) |
| **Use documentation** | Basic (usageInfo) | Extensive (intended, discouraged, prohibited) |
| **Biases/limitations** | Basic (RAI properties) | Extensive (structured arrays, mitigation) |

### Using FAIRSCAPE as Reference

When creating D4D RO-Crates:

1. **For computational datasets** (multiple datasets, workflows, software):
   - Include EVI namespace properties
   - Document provenance relationships (generatedBy, derivedFrom)
   - Use FAIRSCAPE-style additionalProperty for custom metadata

2. **For simple data-only datasets**:
   - Focus on D4D documentation properties
   - Minimal EVI properties (datasetCount, formats) if needed
   - Emphasize ethics, biases, uses sections

3. **For Bridge2AI projects**:
   - Align with FAIRSCAPE patterns for CM4AI interoperability
   - Extend with D4D properties for comprehensive documentation
   - Use consistent author formatting (semicolon-separated)

### References

- **FAIRSCAPE**: https://fairscape.github.io/
- **CM4AI Project**: https://cm4ai.org/
- **FAIRSCAPE Paper**: Clark T, Parker J, et al. (2024) "Cell Maps for Artificial Intelligence" bioRxiv 2024.05.21.589311

---

## Profile Components

### 1. Profile Specification
**File**: `d4d-profile-spec.md`

Complete specification document defining:
- Profile URI and conformance requirements
- Three conformance levels (Minimal, Basic, Complete)
- Property catalog organized by D4D sections
- Property value object patterns
- Validation requirements

### 2. JSON-LD Context
**File**: `d4d-context.jsonld`

JSON-LD context defining all D4D vocabulary terms:
- Namespace prefixes (d4d:, rai:, evi:, schema:)
- Term definitions with URIs
- Data type specifications
- Container specifications for arrays

**Usage**:
```json
{
  "@context": [
    "https://w3id.org/ro/crate/1.2/context",
    "https://w3id.org/bridge2ai/d4d-context/1.0"
  ]
}
```

### 3. Example RO-Crates
**Directory**: `examples/`

Three complete examples demonstrating conformance levels:

| File | Level | Properties | Description |
|------|-------|------------|-------------|
| `d4d-rocrate-minimal.json` | Level 1 | 8 | Minimal viable D4D documentation |
| `d4d-rocrate-basic.json` | Level 2 | 25 | Basic recommended documentation |
| `d4d-rocrate-complete.json` | Level 3 | 100+ | Comprehensive D4D documentation |

### 4. SHACL Validation Shapes
**Directory**: `validation/`

SHACL shapes for automated conformance testing:

| File | Level | Validation |
|------|-------|------------|
| `d4d-minimal-shape.ttl` | Level 1 | Required properties (strict) |
| `d4d-basic-shape.ttl` | Level 2 | Required + recommended (warnings) |
| `d4d-complete-shape.ttl` | Level 3 | All D4D properties (info) |

---

## Conformance Levels

### Level 1: Minimal (8 properties)

**Target**: Basic dataset discoverability and citation

**Required Properties**:
1. `@type` - "Dataset"
2. `name` - Dataset title
3. `description` - Dataset description (≥5 characters)
4. `datePublished` - Publication date
5. `license` - Dataset license
6. `keywords` - Searchable keywords (≥3)
7. `author` - Dataset creator(s)
8. `identifier` - Persistent identifier (DOI, ARK)

**Use when**:
- Quick dataset registration
- Minimum viable documentation
- Lightweight catalogs

### Level 2: Basic (25 properties)

**Target**: Responsible AI and FAIR compliance

**Adds 17 recommended properties**:
- Motivation (purposes, addressing_gaps)
- Composition (contentSize, formats)
- Collection (dataCollection, timeframe)
- Preprocessing (manipulation, preprocessing protocols)
- Ethics (ethicalReview, humanSubjects, deidentified, confidentiality)
- Quality (limitations, biases)
- Uses (use cases, prohibited uses)
- Maintenance (publisher, maintenance plan)

**Use when**:
- Publishing research datasets
- Sharing ML/AI datasets
- FAIR repository submission

### Level 3: Complete (100+ properties)

**Target**: Comprehensive documentation for high-stakes datasets

**Includes all D4D sections**:
1. **Motivation** (5 properties) - Purpose, gaps, tasks, funding
2. **Composition** (12 properties) - Instances, subpopulations, splits, errors
3. **Collection** (7 properties) - Methods, timeframes, collectors, sampling
4. **Preprocessing** (10 properties) - Cleaning, imputation, annotation, tools
5. **Uses** (7 properties) - Intended, existing, discouraged, prohibited
6. **Distribution** (11 properties) - Access, licensing, formats, restrictions
7. **Maintenance** (6 properties) - Versioning, updates, errata
8. **Ethics** (12 properties) - IRB, consent, at-risk populations, DPIA
9. **Quality** (6 properties) - Biases, limitations, anomalies, validation
10. **Governance** (10 properties) - PI, committee, provenance, EVI metadata

**Use when**:
- Clinical/biomedical datasets
- Regulatory compliance (HIPAA, GDPR)
- High-impact scientific repositories
- Commercial dataset releases

---

## Usage Examples

### Creating a Level 1 RO-Crate

```json
{
  "@context": [
    "https://w3id.org/ro/crate/1.2/context",
    "https://w3id.org/bridge2ai/d4d-context/1.0"
  ],
  "@graph": [
    {
      "@type": "CreativeWork",
      "@id": "ro-crate-metadata.json",
      "conformsTo": {"@id": "https://w3id.org/ro/crate/1.2"},
      "about": {"@id": "./"}
    },
    {
      "@type": ["Dataset", "https://w3id.org/EVI#ROCrate"],
      "@id": "./",
      "conformsTo": {
        "@id": "https://w3id.org/bridge2ai/ro-crate-profile/d4d/1.0"
      },
      "name": "My Dataset",
      "description": "A comprehensive dataset for...",
      "datePublished": "2026-03-11",
      "license": "https://creativecommons.org/licenses/by/4.0/",
      "keywords": ["machine learning", "genomics", "protein"],
      "author": "Jane Doe; John Smith",
      "identifier": "https://doi.org/10.1234/example"
    }
  ]
}
```

### Validating Conformance

**Using SHACL (Python with pyshacl)**:
```python
from pyshacl import validate

# Load your RO-Crate
with open('ro-crate-metadata.json') as f:
    data_graph = f.read()

# Load validation shape
with open('validation/d4d-basic-shape.ttl') as f:
    shapes_graph = f.read()

# Validate
conforms, results_graph, results_text = validate(
    data_graph=data_graph,
    shacl_graph=shapes_graph,
    data_graph_format='json-ld',
    shacl_graph_format='turtle'
)

if conforms:
    print("✅ RO-Crate conforms to D4D Basic profile")
else:
    print("❌ Validation errors:")
    print(results_text)
```

**Using SHACL (Command line with shacl-cli)**:
```bash
# Install shacl tool
npm install -g shacl

# Validate Level 1
shacl validate \
  -d ro-crate-metadata.json \
  -s validation/d4d-minimal-shape.ttl \
  -f json-ld

# Validate Level 2
shacl validate \
  -d ro-crate-metadata.json \
  -s validation/d4d-basic-shape.ttl \
  -f json-ld
```

### Transforming D4D YAML to RO-Crate

```bash
# Using the d4d_to_rocrate.py script
python .claude/agents/scripts/d4d_to_rocrate.py \
  --input dataset.yaml \
  --output ro-crate-metadata.json \
  --validate
```

### Transforming RO-Crate to D4D YAML

```bash
# Using the rocrate_to_d4d.py script
python .claude/agents/scripts/rocrate_to_d4d.py \
  --input ro-crate-metadata.json \
  --output dataset.yaml \
  --mapping "data/ro-crate_mapping/D4D - RO-Crate - RAI Mappings.xlsx - Class Alignment.tsv" \
  --validate
```

---

## Property Value Patterns

### Simple String Values
```json
{
  "name": "Dataset Title",
  "description": "Dataset description text"
}
```

### Arrays (@container: @set)
```json
{
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "d4d:purposes": [
    "Enable X research",
    "Support Y development"
  ]
}
```

### Person/Organization
```json
{
  "author": {
    "@type": "Person",
    "name": "Jane Doe",
    "email": "jane@example.edu",
    "affiliation": {
      "@type": "Organization",
      "name": "Example University"
    }
  }
}
```

### PropertyValue Objects
```json
{
  "d4d:subpopulations": [
    {
      "@type": "PropertyValue",
      "name": "European Ancestry",
      "value": "60% of samples"
    }
  ]
}
```

### Date Values
```json
{
  "datePublished": "2026-03-11",
  "rai:dataCollectionTimeframe": [
    {
      "@type": "PropertyValue",
      "name": "Collection Period",
      "startDate": "2023-01-01",
      "endDate": "2024-12-31"
    }
  ]
}
```

### URLs and References
```json
{
  "license": "https://creativecommons.org/licenses/by/4.0/",
  "identifier": "https://doi.org/10.1234/example",
  "d4d:rawDataLocation": {
    "@id": "https://dbgap.ncbi.nlm.nih.gov/..."
  }
}
```

### Boolean Values
```json
{
  "d4d:deidentified": true,
  "d4d:fdaRegulated": false,
  "d4d:rawDataSaved": true
}
```

---

## Namespace Prefixes

| Prefix | Namespace | Description |
|--------|-----------|-------------|
| `schema:` | `https://schema.org/` | Core metadata terms |
| `d4d:` | `https://w3id.org/bridge2ai/data-sheets-schema/` | D4D-specific terms |
| `rai:` | `http://mlcommons.org/croissant/RAI/` | Responsible AI metadata |
| `evi:` | `https://w3id.org/EVI#` | FAIRSCAPE Evidence metadata |

---

## Validation Severity Levels

SHACL shapes use different severity levels:

| Severity | Level | Meaning |
|----------|-------|---------|
| `sh:Violation` | 1 (Minimal) | **MUST** have - validation fails |
| `sh:Warning` | 2 (Basic) | **SHOULD** have - warnings issued |
| `sh:Info` | 3 (Complete) | **MAY** have - info messages |

---

## Testing Conformance

### Manual Checklist

**Level 1 Checklist** (8 items):
- [ ] Dataset has `@type` including "Dataset"
- [ ] Dataset has `name`
- [ ] Dataset has `description` (≥5 chars)
- [ ] Dataset has `datePublished`
- [ ] Dataset has `license`
- [ ] Dataset has `keywords` (≥3)
- [ ] Dataset has `author`
- [ ] Dataset has `identifier`
- [ ] `conformsTo` includes D4D profile URI

**Level 2 Checklist** (25 items):
- [ ] All Level 1 requirements ✓
- [ ] Has `d4d:purposes`
- [ ] Has `d4d:addressingGaps`
- [ ] Has `contentSize`
- [ ] Has `evi:formats`
- [ ] Has `rai:dataCollection`
- [ ] Has `rai:dataCollectionTimeframe`
- [ ] Has `rai:dataManipulationProtocol`
- [ ] Has `rai:dataPreprocessingProtocol`
- [ ] Has `ethicalReview`
- [ ] Has `humanSubjectResearch`
- [ ] Has `deidentified`
- [ ] Has `confidentialityLevel`
- [ ] Has `rai:dataLimitations`
- [ ] Has `rai:dataBiases`
- [ ] Has `rai:dataUseCases`
- [ ] Has `prohibitedUses`
- [ ] Has `publisher`
- [ ] Has `rai:dataReleaseMaintenancePlan`

**Level 3 Checklist**: See `d4d-profile-spec.md` for complete list

### Automated Testing

```python
#!/usr/bin/env python3
"""Test RO-Crate conformance to D4D profile."""

import json
from pyshacl import validate

def test_conformance(rocrate_file, level='basic'):
    """Test conformance to D4D profile level."""

    # Load RO-Crate
    with open(rocrate_file) as f:
        data = json.load(f)

    # Select validation shape
    shapes = {
        'minimal': 'validation/d4d-minimal-shape.ttl',
        'basic': 'validation/d4d-basic-shape.ttl',
        'complete': 'validation/d4d-complete-shape.ttl'
    }

    with open(shapes[level]) as f:
        shape = f.read()

    # Validate
    conforms, _, report = validate(
        data_graph=json.dumps(data),
        shacl_graph=shape,
        data_graph_format='json-ld',
        shacl_graph_format='turtle'
    )

    return conforms, report

# Test all levels
for level in ['minimal', 'basic', 'complete']:
    conforms, report = test_conformance('ro-crate-metadata.json', level)
    print(f"{level.upper()}: {'✅ PASS' if conforms else '❌ FAIL'}")
    if not conforms:
        print(report)
```

---

## References

- **RO-Crate 1.2**: https://w3id.org/ro/crate/1.2
- **D4D Schema**: https://w3id.org/bridge2ai/data-sheets-schema/
- **Datasheets for Datasets**: https://arxiv.org/abs/1803.09010
- **FAIR Principles**: https://www.go-fair.org/fair-principles/
- **ML Commons Croissant**: https://github.com/mlcommons/croissant
- **FAIRSCAPE**: https://fairscape.github.io/
- **SHACL**: https://www.w3.org/TR/shacl/

---

## Profile Development

### Adding New Properties

1. **Update d4d-context.jsonld**:
   ```json
   "d4d:newProperty": {
     "@id": "d4d:newProperty",
     "@container": "@set"
   }
   ```

2. **Update d4d-profile-spec.md**:
   - Add to appropriate section
   - Document type, description, D4D class mapping

3. **Update SHACL shapes**:
   ```turtle
   sh:property [
     sh:path d4d:newProperty ;
     sh:minCount 1 ;
     sh:severity sh:Warning ;
     sh:message "Description here" ;
   ] ;
   ```

4. **Add to examples** as appropriate

5. **Test validation**

### Versioning

Profile versions follow semantic versioning:
- **Major** (X.0.0): Breaking changes to required properties
- **Minor** (1.X.0): New optional properties, recommendations
- **Patch** (1.0.X): Bug fixes, clarifications

---

## License

This profile is licensed under **CC-BY 4.0**.

© 2026 Bridge2AI Data Standards Core

---

## Contact

For questions or feedback:
- **GitHub Issues**: https://github.com/bridge2ai/data-sheets-schema/issues
- **Email**: bridge2ai-standards@example.edu
- **Profile URI**: https://w3id.org/bridge2ai/ro-crate-profile/d4d/1.0
