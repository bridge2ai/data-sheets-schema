# D4D Mapping Files

This directory contains all D4D mapping files including SSSOM mappings, structural mappings, and URI mapping analysis.

## SSSOM Mapping Files

SSSOM (Simple Standard for Sharing Ontological Mappings) files documenting D4D ↔ RO-Crate mappings:

### Comprehensive Mappings
- `d4d_rocrate_sssom_comprehensive.tsv` (105K) - Complete D4D to RO-Crate SSSOM mappings
- `d4d_rocrate_sssom_mapping.tsv` (35K) - Core D4D property mappings
- `d4d_rocrate_sssom_mapping_subset.tsv` (31K) - Focused subset of mappings

### URI-Level Mappings
- `d4d_rocrate_sssom_uri_comprehensive_v1.tsv` (70K) - URI-level comprehensive mapping (version 1)
- `d4d_rocrate_sssom_uri_comprehensive_v2.tsv` (81K) - URI-level comprehensive mapping (version 2)
- `d4d_rocrate_sssom_uri_mapping.tsv` (11K) - Core URI mappings
- `d4d_rocrate_sssom_uri_interface.tsv` (29K) - Interface-level URI mappings

### Structural Mappings
- `d4d_rocrate_structural_mapping.sssom.tsv` (34K) - Structural mapping between D4D and RO-Crate schemas

**Note**: Two versions of `d4d_rocrate_sssom_uri_comprehensive.tsv` exist (v1 and v2) with different contents. Both preserved for comparison.

## Analysis and Documentation

- `uri_mapping_recommendations.md` - Comprehensive mapping recommendations for all unmapped slots
- `STRUCTURAL_MAPPING_ANALYSIS.md` - Analysis of structural schema mappings
- `d4d_rocrate_structural_mapping_summary.md` - Summary of structural mapping coverage

## Vocabulary Sources

Analysis based on:
  - EBI OLS (Ontology Lookup Service) API searches
  - Schema.org vocabulary
  - DCTerms (Dublin Core)
  - DCAT (Data Catalog)
  - PROV (Provenance)
  - DUO (Data Use Ontology)
  - QUDT (Quantities, Units, Dimensions and Types)
  - FAIRSCAPE Evidence (EVI) namespace
  - RAI (Responsible AI) namespace

## Summary

**Total Recommendations: 126 slot URIs**

### By Vocabulary:
- **d4d** (D4D-specific): 64 mappings (51%)
- **schema.org**: 31 mappings (25%)
- **DUO**: 20 mappings (16%)
- **dcterms**: 8 mappings (6%)
- **dcat**: 1 mapping (1%)
- **prov**: 1 mapping (1%)
- **qudt**: 1 mapping (1%)

### Confidence Levels:

**High Confidence (Standard Vocabularies): 30 mappings**
- Well-established standards
- Direct semantic matches
- Ready to implement

**Domain-Specific (d4d prefix): 64 mappings**
- No standard equivalents found
- Unique to D4D/dataset documentation domain
- Use d4d: prefix

**DUO Terms: 20 mappings**
- Standard data use restrictions
- Validated against DUO ontology
- High confidence

**RO-Crate Relationships: 13 mappings**
- Dataset relationship predicates
- Schema.org based
- High confidence

## Next Steps

1. Review recommendations for accuracy
2. Implement high-confidence mappings first
3. Validate D4D-specific terms with domain experts
4. Update schema files with new slot_uri definitions
5. Run schema validation tests
6. Update documentation

## Implementation Priority

### Phase 1: High Confidence (Standard Vocabularies)
Add 30 slot_uri mappings using schema.org, dcterms, dcat, prov, qudt

### Phase 2: DUO Terms
Add 20 DUO mappings for data governance

### Phase 3: RO-Crate Relationships
Add 13 relationship predicates

### Phase 4: D4D-Specific Terms
Add 64 d4d: prefix mappings

**Total Impact: ~126 additional slot URIs**
**Current Coverage: 125/270 (46.3%)**
**Projected Coverage: 251/270 (93.0%)**

