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

### RO-Crate to D4D Field Mapping Analysis

#### ✅ Fields Already Integrated in D4D Dataset Class

| RO-Crate Field | D4D Equivalent | Location |
|----------------|----------------|----------|
| **funder** | `FundingMechanism.grantor` (Grantor) | `Dataset.funders` ✅ |
| **grant number** | `Grant.grant_number` | Via `FundingMechanism.grant` ✅ |
| **GDPR/HIPAA** | `ExportControlRegulatoryRestrictions.gdpr_compliant`, `.hipaa_compliant` | `Dataset.regulatory_restrictions` ✅ |
| **regulatory compliance** | `ExportControlRegulatoryRestrictions.regulatory_compliance`, `.other_compliance` | `Dataset.regulatory_restrictions` ✅ |
| **De-identified** | `Deidentification` class | `Dataset.is_deidentified` ✅ |

#### ⚠️ Fields Defined in D4D Modules but NOT Integrated into Dataset Class

**CRITICAL FINDING:** D4D_Human module (D4D_Human.yaml) defines comprehensive human subjects classes but they are **NOT referenced in the Dataset class**:

| RO-Crate Field | D4D Class (Exists but Unused) | Required Action |
|----------------|-------------------------------|-----------------|
| **Human Subject** (boolean) | `HumanSubjectResearch.involves_human_subjects` | Add `Dataset.human_subject_research` attribute |
| **IRB Approval** | `HumanSubjectResearch.irb_approval` | Already defined in unused class |
| **Ethics Review** | `HumanSubjectResearch.ethics_review_board` | Already defined in unused class |
| **Regulatory Compliance** | `HumanSubjectResearch.regulatory_compliance` | Already defined in unused class |
| **Consent Obtained** | `InformedConsent.consent_obtained` | Add `Dataset.informed_consent` attribute |
| **Consent Type** | `InformedConsent.consent_type` | Already defined in unused class |
| **Withdrawal Mechanism** | `InformedConsent.withdrawal_mechanism` | Already defined in unused class |
| **Anonymization Method** | `ParticipantPrivacy.anonymization_method` | Add `Dataset.participant_privacy` attribute |
| **Reidentification Risk** | `ParticipantPrivacy.reidentification_risk` | Already defined in unused class |
| **Compensation** | `HumanSubjectCompensation` (full class) | Add `Dataset.compensation` attribute |
| **Vulnerable Populations** | `VulnerablePopulations` (full class) | Add `Dataset.vulnerable_populations` attribute |

**Note:** These classes are imported via `D4D_Human` module but never added as attributes to the Dataset class in data_sheets_schema.yaml.

#### ❌ Fields Truly Missing from D4D

1. **Structured Confidentiality Level**
   - `confidentialityLevel` enum [unrestricted, restricted, confidential] → D4D has compliance enums but no general confidentiality classification
   - Recommendation: Add `ConfidentialityLevelEnum` to D4D_Data_Governance module

2. **Data Governance Committee**
   - `Data Governance Committee` contact → D4D has `Maintainer.contact_person` but no specific governance committee
   - Recommendation: Add `governance_committee` field to `ExportControlRegulatoryRestrictions`

3. **Dataset Citation**
   - `citation` recommended citation → D4D lacks standard citation field
   - Recommendation: Add top-level `Dataset.citation` field

4. **Hierarchical Composition**
   - `hasPart` / `isPartOf` for dataset relationships → D4D `subsets` is informal
   - Recommendation: Add `Dataset.parent_datasets` and formalize composition relationships

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

### Priority 0: CRITICAL - Integrate Existing D4D_Human Module (IMMEDIATE)

**The D4D_Human module already exists but is not integrated into the Dataset class. This is the highest priority fix.**

Add the following attributes to the `Dataset` class in `data_sheets_schema.yaml`:

```yaml
Dataset:
  attributes:
    # ... existing attributes ...

    # Human subjects module classes (ADD THESE)
    human_subject_research:
      range: HumanSubjectResearch
      description: Information about whether dataset involves human subjects research
    informed_consent:
      range: InformedConsent
      multivalued: true
      description: Details about informed consent procedures
    participant_privacy:
      range: ParticipantPrivacy
      multivalued: true
      description: Privacy protections and anonymization procedures
    participant_compensation:
      range: HumanSubjectCompensation
      description: Compensation provided to participants
    vulnerable_populations:
      range: VulnerablePopulations
      description: Protections for vulnerable populations
```

**Impact:** This single change adds all RO-Crate human subjects fields that were already defined but unused.

### Priority 1: Add Truly Missing Fields

1. **Add `ConfidentialityLevelEnum` to D4D_Data_Governance module**
   ```yaml
   ConfidentialityLevelEnum:
     permissible_values:
       unrestricted:
         description: No confidentiality restrictions
       restricted:
         description: Restricted access with approval required
       confidential:
         description: Highly confidential with strict access controls
   ```

2. **Add governance committee to `ExportControlRegulatoryRestrictions`**
   ```yaml
   ExportControlRegulatoryRestrictions:
     attributes:
       # ... existing attributes ...
       governance_committee_contact:
         description: Contact for data governance committee
         range: Person
   ```

3. **Add `citation` field to Dataset**
   ```yaml
   Dataset:
     attributes:
       # ... existing attributes ...
       citation:
         description: Recommended citation for this dataset (DataCite/BibTeX format)
         range: string
         slot_uri: schema:citation
   ```

4. **Add hierarchical composition to Dataset**
   ```yaml
   Dataset:
     attributes:
       # ... existing attributes ...
       parent_datasets:
         description: Parent datasets that this is part of
         range: Dataset
         multivalued: true
         slot_uri: schema:isPartOf
       related_datasets:
         description: Related datasets with typed relationships
         range: DatasetRelationship  # New class
         multivalued: true
   ```

### Priority 2: Enhanced Metadata

5. **Add `DatasetRelationship` class for typed relationships**
   ```yaml
   DatasetRelationship:
     description: Typed relationship to another dataset
     is_a: DatasetProperty
     attributes:
       target_dataset:
         range: Dataset
       relationship_type:
         range: DatasetRelationshipTypeEnum

   DatasetRelationshipTypeEnum:
     permissible_values:
       derives_from: {}
       supplements: {}
       is_version_of: {}
       replaces: {}
       is_required_by: {}
   ```

6. **Separate `intended_uses` and `prohibited_uses`**
   - Current: `future_use_impacts` combines both
   - Recommendation: Split into separate classes with structured categories

### Priority 3: Export Compatibility

7. **Add JSON-LD export capability**
   - Generate schema.org-compatible JSON-LD from D4D YAML
   - Map D4D fields to schema.org vocabulary
   - Support `@context` and `@graph` structure
   - Tool location: `src/export/d4d_to_jsonld.py`

8. **Add RO-Crate packaging tool**
   - Convert D4D YAML → RO-Crate JSON-LD
   - Preserve all metadata
   - Generate conformant crate structure
   - Tool location: `src/export/d4d_to_rocrate.py`

## References

- **RO-Crate Specification**: https://w3id.org/ro/crate/1.2
- **FAIRSCAPE Framework**: https://fairscape.github.io
- **EVI Ontology**: https://w3id.org/EVI
- **Example Implementation**: https://github.com/fairscape/datasheet-builder/blob/main/ro-crate-metadata.json
- **CM4AI Project**: https://cm4ai.org
- **Schema.org Dataset**: https://schema.org/Dataset
