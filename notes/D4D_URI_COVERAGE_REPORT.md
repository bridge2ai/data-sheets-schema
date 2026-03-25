# D4D URI Coverage Analysis and Recommendations

**Date**: 2026-03-19
**Schema Version**: data_sheets_schema_all.yaml
**Total D4D Attributes**: 270 unique attributes across 76 classes

---

## Executive Summary

This report analyzes URI (Uniform Resource Identifier) coverage in the D4D (Datasheets for Datasets) LinkML schema using the `slot_uri` property, which maps D4D attributes to standard vocabulary terms from Dublin Core (dcterms), Data Catalog Vocabulary (dcat), Schema.org, PROV, and other ontologies.

### Key Findings

- **Current URI Coverage**: 112/270 attributes (41.5%)
- **Attributes that COULD have URIs**: 97 (35.9%)
- **Novel D4D concepts**: 47 (17.4%) - domain-specific terms without standard equivalents
- **Free text fields**: 17 (6.3%) - narrative fields that don't require URIs
- **Missing descriptions**: 66 attributes (24.4%) - documentation gap

### Comparison with FAIRSCAPE RO-Crate

| Metric | D4D | FAIRSCAPE |
|--------|-----|-----------|
| URI Coverage | 41.5% (112/270) | 100% (67/67) |
| Mechanism | `slot_uri` in LinkML | `@vocab` + namespace prefixes in JSON-LD @context |
| Vocabularies | dcterms, dcat, schema, prov | schema.org, EVI, RAI, D4D |

FAIRSCAPE achieves 100% URI coverage by using JSON-LD's `@vocab` to provide a default namespace (schema.org) for all unprefixed properties, plus explicit namespace prefixes for domain-specific vocabularies (EVI, RAI, D4D).

---

## Detailed Analysis

### 1. Attributes WITH slot_uri (112 attributes, 41.5%)

D4D currently maps 112 attributes to standard vocabularies:

**Dublin Core Terms (dcterms)**: ~20 mappings
- Examples: `title → dcterms:title`, `publisher → dcterms:publisher`, `issued → dcterms:issued`

**Data Catalog Vocabulary (dcat)**: ~8 mappings
- Examples: `bytes → dcat:byteSize`, `page → dcat:landingPage`, `keywords → dcat:keyword`

**Schema.org**: ~4 mappings
- Examples: `dialect → schema:encodingFormat`, `path → schema:contentUrl`

**PROV Ontology**: ~1 mapping
- Example: `was_derived_from → prov:wasDerivedFrom`

### 2. Attributes that COULD Have URIs (97 attributes, 35.9%)

These are standard metadata attributes that have equivalents in common vocabularies but currently lack `slot_uri` definitions.

**High confidence recommendations (16)**: Clear vocabulary matches
- `contact_point` → `dcat:contactPoint`
- `spatial_coverage` → `schema:spatialCoverage` or `dcat:spatialResolutionInMeters`
- `temporal_coverage` → `schema:temporalCoverage` or `dcat:temporalResolution`
- `funding` → `schema:funding`
- `citation` → `schema:citation`

**Medium confidence recommendations (5)**: Likely matches requiring validation
- Distribution-related properties → `dcat:distribution`, `dcat:accessURL`
- Agent/contributor properties → `prov:Agent`, `schema:contributor`

**Low confidence recommendations (76)**: Domain-specific properties requiring research
- These need manual review to identify appropriate vocabulary terms
- May require extending existing vocabularies or creating D4D-specific URIs

**See**: `notes/D4D_MISSING_URI_RECOMMENDATIONS.tsv` for complete list with suggestions

### 3. Novel D4D Concepts (47 attributes, 17.4%)

These represent domain-specific innovations in the D4D schema that don't have direct equivalents in standard vocabularies:

**Categories**:
- **Ethical/responsible AI**: `addressing_gaps`, `content_warnings`, `vulnerable_populations`
- **Data quality strategies**: `cleaning_strategies`, `preprocessing_strategies`, `labeling_strategies`
- **Annotation protocols**: `annotation_analyses`, `machine_annotation_analyses`, `imputation_protocols`
- **Human subjects**: `compensation_amount`, `compensation_rationale`, `informed_consent`
- **Data governance**: `data_protection_impacts`, `prohibited_uses`, `discouraged_uses`

**Recommendation**: Create D4D-specific URIs for these concepts
- Use D4D namespace: `https://w3id.org/bridge2ai/data-sheets-schema/`
- Examples:
  - `d4d:addressingGaps`
  - `d4d:compensationProtocol`
  - `d4d:contentWarning`

**See**: `notes/D4D_NOVEL_CONCEPTS.tsv` for complete list

### 4. Free Text Fields (17 attributes, 6.3%)

These are narrative/descriptive fields that don't require URIs:

**Examples**:
- `access_details` - Paragraphs describing access procedures
- `consent_documentation` - Free-text consent information
- `annotation_quality_details` - Descriptive quality notes
- `annotator_demographics` - Narrative demographic information

**Recommendation**: No action needed - these are documentation fields

**See**: `notes/D4D_FREE_TEXT_FIELDS.tsv` for complete list

---

## Recommendations

### Priority 1: High Confidence Mappings (16 attributes)

Add `slot_uri` definitions for attributes with clear vocabulary matches:

```yaml
slots:
  contact_point:
    description: Contact information for dataset inquiries
    slot_uri: dcat:contactPoint

  spatial_coverage:
    description: Geographic area covered by the dataset
    slot_uri: schema:spatialCoverage

  temporal_coverage:
    description: Time period covered by the dataset
    slot_uri: schema:temporalCoverage

  funding:
    description: Funding sources for dataset creation
    slot_uri: schema:funding

  citation:
    description: Preferred citation for the dataset
    slot_uri: schema:citation
```

**Impact**: Increases URI coverage from 41.5% → 47.4%

### Priority 2: Medium Confidence Mappings (5 attributes)

Research and validate vocabulary matches for distribution and provenance properties.

**Impact**: Increases URI coverage to ~49.3%

### Priority 3: Novel D4D Concepts (47 attributes)

Create D4D-specific URIs for domain innovations:

```yaml
slots:
  addressing_gaps:
    description: How this dataset addresses gaps in existing data
    slot_uri: d4d:addressingGaps

  content_warnings:
    description: Content warnings for sensitive data
    slot_uri: d4d:contentWarning

  compensation_protocols:
    description: Protocols for compensating data subjects
    slot_uri: d4d:compensationProtocol
```

**Impact**: Increases URI coverage to ~66.7%

### Priority 4: Low Confidence Attributes (76 attributes)

Manual review to identify appropriate vocabularies:
1. Research existing vocabulary terms
2. Propose new terms to relevant vocabulary communities (Schema.org, DCAT, etc.)
3. Create D4D extensions where no suitable terms exist

**Impact**: Could achieve 80-90% URI coverage

### Priority 5: Missing Descriptions (66 attributes)

Add descriptions to undocumented attributes to improve schema quality:
- Current description coverage: 75.6% (204/270)
- Target: 95%+ coverage

---

## Implementation Strategy

### Phase 1: Quick Wins (Weeks 1-2)
- Add high confidence `slot_uri` mappings (16 attributes)
- Create D4D URIs for top 10 novel concepts
- **Target**: 50% URI coverage

### Phase 2: Standard Vocabularies (Weeks 3-4)
- Research and validate medium/low confidence mappings
- Engage with Schema.org, DCAT communities for new terms
- **Target**: 65% URI coverage

### Phase 3: D4D Extensions (Weeks 5-8)
- Formalize D4D vocabulary for novel concepts
- Create proper ontology documentation
- Publish at w3id.org/bridge2ai/data-sheets-schema/
- **Target**: 80% URI coverage

### Phase 4: Documentation (Weeks 9-10)
- Add missing descriptions
- Create mapping documentation
- Update SSSOM files
- **Target**: 95% description coverage, 85% URI coverage

---

## Benefits of Improved URI Coverage

### 1. Semantic Interoperability
- Easier mapping to RO-Crate, DCAT, Schema.org
- Machine-readable relationships between schemas
- Automated crosswalks via SSSOM mappings

### 2. Discoverability
- Dataset catalogs can index D4D metadata
- Search engines understand semantic relationships
- Federated queries across data repositories

### 3. Standards Compliance
- Alignment with FAIR principles (Findable, Accessible, Interoperable, Reusable)
- Compatibility with W3C standards (JSON-LD, DCAT)
- Integration with knowledge graphs

### 4. Reduced Maintenance
- Leverage existing vocabulary definitions
- Benefit from community updates to vocabularies
- Clearer semantics for implementers

---

## Vocabulary Resources

### Primary Vocabularies

**Dublin Core Terms (dcterms)**
- URL: http://purl.org/dc/terms/
- Use for: bibliographic metadata, dates, identifiers
- Documentation: https://www.dublincore.org/specifications/dublin-core/dcmi-terms/

**Data Catalog Vocabulary (DCAT)**
- URL: https://www.w3.org/ns/dcat#
- Use for: dataset distribution, access, catalogs
- Documentation: https://www.w3.org/TR/vocab-dcat-3/

**Schema.org**
- URL: https://schema.org/
- Use for: general metadata, agents, measurements
- Documentation: https://schema.org/docs/schemas.html

**PROV Ontology**
- URL: http://www.w3.org/ns/prov#
- Use for: provenance, derivation, attribution
- Documentation: https://www.w3.org/TR/prov-o/

### Domain-Specific Extensions

**FAIRSCAPE EVI (Evidence)**
- URL: https://w3id.org/EVI#
- Use for: computational provenance, checksums, statistics

**MLCommons Croissant RAI (Responsible AI)**
- URL: http://mlcommons.org/croissant/RAI/
- Use for: responsible AI metadata, biases, limitations

**D4D (Datasheets for Datasets)**
- URL: https://w3id.org/bridge2ai/data-sheets-schema/
- Use for: novel D4D concepts without standard equivalents

---

## Files Generated

1. **D4D_MISSING_URI_RECOMMENDATIONS.tsv** (97 attributes)
   - Attributes that could map to standard vocabularies
   - Suggested URIs with confidence levels
   - Primary action list for improving coverage

2. **D4D_NOVEL_CONCEPTS.tsv** (47 attributes)
   - Novel D4D-specific concepts
   - Candidates for D4D namespace URIs
   - Require ontology development

3. **D4D_FREE_TEXT_FIELDS.tsv** (17 attributes)
   - Narrative/descriptive fields
   - No URI needed
   - For reference only

---

## Appendix: Vocabulary Crosswalk Challenges

### Dublin Core vs Schema.org

D4D currently uses Dublin Core (dcterms) for many properties, while FAIRSCAPE RO-Crate uses Schema.org. This creates a vocabulary crosswalk requirement:

| D4D (dcterms) | FAIRSCAPE (schema.org) | Match Type |
|---------------|------------------------|------------|
| dcterms:title | schema:name | closeMatch |
| dcterms:publisher | schema:publisher | closeMatch |
| dcterms:issued | schema:datePublished | closeMatch |
| dcterms:creator | schema:creator | closeMatch |

**Impact**: 29/33 (88%) of D4D slot URIs require vocabulary translation when converting to FAIRSCAPE RO-Crate.

**Recommendation**: Consider dual URIs or preference for Schema.org alignment to reduce translation complexity.

---

## Next Steps

1. **Review this report** with the D4D team
2. **Prioritize attributes** for URI assignment
3. **Research vocabularies** for medium/low confidence recommendations
4. **Create PR** with high confidence slot_uri additions
5. **Engage communities** for new vocabulary term proposals
6. **Develop D4D ontology** for novel concepts
7. **Update SSSOM mappings** after URI additions

---

**Questions or feedback**: Please open an issue at https://github.com/bridge2ai/data-sheets-schema/issues
