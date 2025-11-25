# RO-Crate / FAIRSCAPE Metadata Specification

## Overview

**RO-Crate** (Research Object Crate) is a community-developed standard for packaging research datasets with their metadata using a lightweight, JSON-LD based approach that builds on schema.org. The **FAIRSCAPE framework** extends RO-Crate specifically for creating AI-ready datasets with enhanced provenance tracking and metadata richness.

- **Specification**: RO-Crate 1.2 (https://w3id.org/ro/crate/1.2-DRAFT)
- **Context**: Uses schema.org vocabulary with custom extensions (EVI namespace)
- **Format**: JSON-LD (@context, @graph structure)
- **Example Implementation**: Cell Maps for Artificial Intelligence (CM4AI) project
- **Source**: https://github.com/fairscape/datasheet-builder

## Key Characteristics

### 1. JSON-LD Native Format
- Uses `@context` to define vocabularies (schema.org + custom namespaces)
- `@graph` array structure for linked data representation
- Machine-actionable and semantic web compatible
- Direct integration with knowledge graphs

### 2. Provenance-Centric
- Explicit provenance graphs using EVI (Evidence Graph) ontology
- Comprehensive tracking of data generation, processing, and lineage
- Links datasets, software, computations, and publications

### 3. Hierarchical Composition
- Main dataset (`@type`: Dataset, ROCrate)
- Sub-crates via `hasPart` relationships
- Nested structure for complex, multi-part datasets

### 4. Schema.org Alignment
- Built on schema.org Dataset vocabulary
- Standard fields: name, description, author, publisher, license, etc.
- Extended with domain-specific properties via `additionalProperty`

## Core Fields

### Standard Schema.org Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `@id` | string | Persistent identifier (ARK/DOI) | `ark:59852/cm4ai-march-2025-release` |
| `@type` | array | Resource types | `["Dataset", "https://w3id.org/EVI#ROCrate"]` |
| `name` | string | Human-readable dataset name | "Cell Maps for Artificial Intelligence..." |
| `description` | string | Detailed dataset description | |
| `keywords` | array | Searchable keywords/tags | `["AI", "CRISPR", "machine learning", ...]` |
| `version` | string | Dataset version | "1.4" |
| `datePublished` | string (ISO 8601) | Publication date | "2025-03-03" |
| `identifier` | string (URL) | DOI or persistent URL | "https://doi.org/10.18130/V3/B35XWX" |
| `license` | string (URL) | License URL | "https://creativecommons.org/licenses/by-nc-sa/4.0/" |
| `publisher` | string | Publishing organization | "University of Virginia Dataverse" |
| `author` | string/object | Dataset authors | "Clark T; Parker J; ..." |
| `contentSize` | string | Total dataset size | "12.53 GB" |

### Research-Specific Fields

| Field | Type | Description |
|-------|------|-------------|
| `principalInvestigator` | string | Lead PI name |
| `contactEmail` | string | Contact email for questions |
| `funder` | string | Funding agencies and grant numbers |
| `associatedPublication` | array | Related publications (full citations) |
| `citation` | string | Recommended dataset citation |
| `usageInfo` | string | Usage guidelines and restrictions |
| `conditionsOfAccess` | string | Access requirements |
| `confidentialityLevel` | string | Data sensitivity level |
| `copyrightNotice` | string | Copyright statement |

### Compositional Fields

| Field | Type | Description |
|-------|------|-------------|
| `hasPart` | array | Sub-datasets or components (RO-Crates) |
| `isPartOf` | array | Parent organizations/projects |

### Structured Extension Fields (additionalProperty)

The `additionalProperty` field contains an array of `PropertyValue` objects with structured metadata beyond schema.org's standard vocabulary:

| Property Name | Description | D4D Mapping |
|---------------|-------------|-------------|
| **Completeness** | Dataset completeness status | → `updates.description` |
| **Maintenance Plan** | Update schedule and long-term preservation | → `updates.description` |
| **Intended Use** | Recommended use cases | → `future_use_impacts` |
| **Limitations** | Known limitations and caveats | → `tasks_not_suitable` |
| **Prohibited Uses** | Explicitly forbidden uses | → `tasks_not_suitable` |
| **Human Subject** | Whether data involves human subjects (Yes/No) | *MISSING in D4D* |
| **De-identified Samples** | De-identification status (Yes/No) | → `cleaning_strategies` |
| **FDA Regulated** | FDA regulatory status (Yes/No) | *MISSING in D4D* |
| **Data Governance Committee** | Contact for governance questions | → `maintainers` |
| **Potential Sources of Bias** | Known bias sources | → `addressing_gaps` |

## Strengths

1. **Machine Actionability**
   - JSON-LD format enables semantic web integration
   - Direct consumption by knowledge graphs and triple stores
   - Standardized vocabularies (schema.org)

2. **Provenance Richness**
   - EVI ontology provides detailed provenance tracking
   - Links between datasets, software, computations
   - Supports reproducibility verification

3. **Hierarchical Structure**
   - `hasPart` allows nested RO-Crates
   - Clean separation of dataset components
   - Supports complex, multi-part datasets

4. **Extensibility**
   - `additionalProperty` mechanism for domain-specific fields
   - Custom namespace support (e.g., EVI)
   - Schema.org compatibility maintained

5. **AI-Ready Focus** (FAIRSCAPE)
   - Designed specifically for AI/ML dataset packaging
   - Rich metadata for model training requirements
   - Provenance for reproducible AI research

## Gaps Relative to D4D

### Fields Present in RO-Crate but Missing/Weak in D4D

1. **Structured Governance Metadata**
   - `Data Governance Committee` → D4D has general `maintainers` but no governance-specific contact
   - `confidentialityLevel` → D4D lacks structured confidentiality classification
   - `FDA Regulated` → D4D has no regulatory compliance tracking

2. **Human Subjects Metadata**
   - Explicit `Human Subject` Yes/No flag → D4D has free-text collection process
   - `De-identified Samples` structured field → D4D has cleaning_strategies but less structured

3. **Hierarchical Composition**
   - `hasPart` / `isPartOf` for dataset relationships → D4D `subsets` is less formal
   - Nested RO-Crate support → D4D flat structure

4. **Usage Documentation**
   - Separate `Intended Use` and `Prohibited Uses` → D4D combines in future_use_impacts
   - `usageInfo` top-level field → D4D embeds in license terms

5. **Publication Linkage**
   - `associatedPublication` array → D4D `related_resources` is less typed
   - `citation` recommended citation → D4D lacks standard citation field

6. **Funding Transparency**
   - Structured `funder` field → D4D lacks dedicated funding field

### Fields Present in D4D but Missing/Weak in RO-Crate

1. **Detailed Collection Process**
   - D4D: `acquisition_methods`, `collection_mechanisms`, `collection_timeframes`, `data_collectors`
   - RO-Crate: Relies on provenance graphs (not in main metadata)

2. **Preprocessing Detail**
   - D4D: `preprocessing_strategies`, `cleaning_strategies`, `labeling_strategies`
   - RO-Crate: Provenance graphs (not in main metadata)

3. **Sampling Methodology**
   - D4D: `sampling_strategies` (is_sample, is_random, is_representative, strategies)
   - RO-Crate: No dedicated sampling field

4. **Subpopulation Demographics**
   - D4D: `subpopulations` (identification, distribution)
   - RO-Crate: Not explicitly captured

5. **Instance-Level Metadata**
   - D4D: `instances` (representation, instance_type, data_type)
   - RO-Crate: Described in text, not structured

## Comparison Summary

| Category | RO-Crate/FAIRSCAPE Strength | D4D Strength |
|----------|----------------------------|--------------|
| **Machine Actionability** | ✅ JSON-LD, linked data, semantic web | ⚠️ YAML (needs JSON-LD export) |
| **Provenance** | ✅ EVI ontology, comprehensive graphs | ⚠️ Text-based provenance |
| **Governance** | ✅ Structured fields (committee, confidentiality) | ⚠️ General maintainer info |
| **Collection Process** | ⚠️ Provenance-based (less accessible) | ✅ Detailed structured fields |
| **Preprocessing** | ⚠️ Provenance-based | ✅ Detailed strategies |
| **Sampling** | ❌ Not captured | ✅ Comprehensive sampling metadata |
| **Demographics** | ⚠️ Keywords/description only | ✅ Structured subpopulations |
| **Hierarchical Data** | ✅ hasPart/isPartOf | ⚠️ Basic subsets |
| **Usage Guidance** | ✅ Separate intended/prohibited uses | ⚠️ Combined use impacts |
| **Regulatory Compliance** | ✅ FDA regulated, confidentiality level | ❌ Missing |

## Recommended Integration into D4D

### Priority 1: Critical Additions

1. **Add `data_governance` class**
   ```yaml
   data_governance:
     committee_contact: string
     confidentiality_level: enum [unrestricted, restricted, confidential]
     regulatory_status:
       fda_regulated: boolean
       gdpr_applicable: boolean
       hipaa_covered: boolean
   ```

2. **Add `human_subjects` structured class**
   ```yaml
   human_subjects:
     involves_human_subjects: boolean
     deidentification_status: enum [identified, de-identified, anonymized]
     consent_obtained: boolean
     irb_approval: string
   ```

3. **Add `funding` class**
   ```yaml
   funding:
     - funder_name: string
       grant_number: string
       grant_url: string (optional)
   ```

4. **Separate `intended_uses` and `prohibited_uses`**
   - Split current `future_use_impacts` and `tasks_not_suitable`
   - Add structured categories

### Priority 2: Enhanced Metadata

5. **Add `dataset_citation` field**
   - Top-level recommended citation string
   - Follows DataCite/BibTeX format

6. **Add hierarchical composition**
   ```yaml
   composition:
     parent_datasets: [identifier references]
     child_datasets: [identifier references]
     related_datasets: [identifier references with relationship type]
   ```

7. **Enhance `related_resources`**
   - Add `associatedPublication` type for formal publications
   - Separate from general resources

### Priority 3: Export Compatibility

8. **Add JSON-LD export capability**
   - Generate schema.org-compatible JSON-LD from D4D YAML
   - Map D4D fields to schema.org vocabulary
   - Support `@context` and `@graph` structure

9. **Add RO-Crate packaging tool**
   - Convert D4D YAML → RO-Crate JSON-LD
   - Preserve all metadata
   - Generate conformant crate structure

## References

- **RO-Crate Specification**: https://w3id.org/ro/crate/1.2
- **FAIRSCAPE Framework**: https://fairscape.github.io
- **EVI Ontology**: https://w3id.org/EVI
- **Example Implementation**: https://github.com/fairscape/datasheet-builder/blob/main/ro-crate-metadata.json
- **CM4AI Project**: https://cm4ai.org
- **Schema.org Dataset**: https://schema.org/Dataset
