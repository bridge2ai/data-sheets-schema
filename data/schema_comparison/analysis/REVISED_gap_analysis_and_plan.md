# REVISED D4D Schema Gap Analysis and Implementation Plan

**Date:** 2025-01-18
**Based on:** Complete analysis of `data_sheets_schema_all.yaml` (65 classes, 144 slots, 5 enums)

---

## Executive Summary

After comprehensive analysis of the current D4D LinkML schema, **D4D already covers ~70% of concepts** from the 16 analyzed schemas. The schema is **much more comprehensive than initially assessed**, with strong coverage of:
- Ethics and privacy (7+ dedicated classes)
- Data collection and preprocessing (10+ classes)
- Human subjects research (5+ classes)
- Distribution and maintenance (5+ classes)
- File integrity (sha256, md5, hash slots)
- Licensing and governance

**The real gaps are:**
1. **Semantic interoperability** - Only 14% of slots have slot_uri mappings
2. **Variable/field-level metadata** - No way to document individual columns/fields
3. **Structured fairness documentation** - Missing bias taxonomy and fairness-specific classes
4. **Contributor attribution** - No ORCID or CRediT roles
5. **Data quality metrics** - Missing quantitative quality assessments

---

## Current D4D Coverage Analysis

### ✅ WELL COVERED (Already in D4D)

**Classes (65 total):**
- Person, Organization, Software (creator attribution)
- EthicalReview, InformedConsent, Deidentification, VulnerablePopulations (ethics)
- DirectCollection, CollectionMechanism, CollectionTimeframe (data collection)
- PreprocessingStrategy, LabelingStrategy, CleaningStrategy (preprocessing)
- DistributionFormat, DistributionDate (distribution)
- UpdatePlan, Erratum, VersionAccess (maintenance)
- HumanSubjectResearch, HumanSubjectCompensation (human subjects)
- LicenseAndUseTerms, IPRestrictions, RegulatoryRestrictions (governance)
- ExistingUse, DiscouragedUse, Task (uses)
- Many more...

**Slots (144 total including):**
- keywords, doi, version, license, page, publisher, download_url
- sha256, md5, hash (file integrity)
- language, themes, status
- was_derived_from (provenance)
- Comprehensive attributes for all classes above

### ❌ CRITICAL GAPS

**Priority Tier 1: Semantic Interoperability & Core Metadata**

1. **slot_uri Coverage: Only 14%** (20/144 slots)
   - **Impact:** D4D data can't interoperate with other systems
   - **Fix:** Add slot_uri for ~100 more slots mapping to schema.org, dcterms, dcat, prov

2. **class_uri Coverage: Only 3%** (2/65 classes)
   - **Impact:** D4D classes aren't recognized by semantic web tools
   - **Fix:** Add class_uri for major classes (Person, Organization, Software, etc.)

3. **Missing Prefix Definitions** (Bug!)
   - **Problem:** 4 prefixes used but not defined (dcterms, prov, bibo, oslc)
   - **Impact:** Schema validation errors, broken mappings
   - **Fix:** Add to prefixes section

4. **Variable/Field-Level Metadata** (Biggest Content Gap)
   - **Missing:** No VariableMetadata class to document columns/fields
   - **Impact:** Can't document what's IN the data files
   - **Need:**
     - VariableMetadata class
     - Attributes: variable_name, data_type, unit, min/max, missing_value_codes
     - Link to schema:variableMeasured

5. **schema:sameAs**
   - **Missing:** No slot for alternative/canonical dataset URLs
   - **Impact:** Can't link to same dataset on different platforms
   - **Fix:** Add sameAs slot with slot_uri: schema:sameAs

**Priority Tier 2: Structured Fairness & Quality**

6. **Structured Bias Taxonomy**
   - **Current:** Has "anomalies" slot (free text)
   - **Missing:** BiasTypeEnum (selection, measurement, historical, representation, etc.)
   - **Fix:** Add BiasTypeEnum and enhance documentation

7. **Fairness-Specific Classes**
   - **Missing:** FairnessFraming, ProtectedAttributes, SocialImpact classes
   - **Impact:** No structured way to document fairness considerations
   - **Fix:** New D4D_Fairness module (but may be overkill - could enhance existing)

8. **ORCID for Person**
   - **Current:** Person class exists
   - **Missing:** orcid attribute
   - **Fix:** Add orcid slot with pattern validation

9. **CRediT Taxonomy**
   - **Missing:** Contributor role enumeration
   - **Fix:** Add CRediTRoleEnum (14 standard roles)

10. **Annotation Quality Metrics**
    - **Current:** LabelingStrategy class exists
    - **Missing:** annotations_per_item, inter_annotator_agreement
    - **Fix:** Enhance LabelingStrategy class

11. **Data Quality Metrics**
    - **Missing:** Completeness, accuracy, outlier detection
    - **Fix:** Add DataQuality class or enhance existing classes

12. **Regulatory Compliance Tracking**
    - **Current:** Has regulatory_restrictions slot
    - **Missing:** Structured compliance tracking (GDPR, HIPAA, EU AI Act)
    - **Fix:** Add ComplianceStatusEnum, AIActRiskEnum

**Priority Tier 3: Advanced Features**

13. **Semantic Versioning Type** - Add VersionTypeEnum (MAJOR/MINOR/PATCH)
14. **Processing Maturity Levels** - Add enum: raw/filtered/structured/derived
15. **Spatial Coverage** - Add spatialCoverage slot mapped to schema:spatialCoverage
16. **Temporal Coverage** - Enhance collection_timeframes, map to schema:temporalCoverage
17. **PROV-O Provenance** - Comprehensive provenance beyond was_derived_from
18. **License Inheritance** - Track most restrictive upstream license
19. **Deprecation Policy** - Add deprecation tracking
20. **Foreign Key Relationships** - Document table relationships

---

## Revised Implementation Plan

### Phase 1: Fix Bugs & Add Critical Semantic Mappings (Week 1-2)

**Goal:** Fix schema bugs and boost semantic interoperability from 14% to 80%+

**Tasks:**
1. **Fix missing prefixes** - Add dcterms, prov, bibo, oslc to prefixes section
2. **Add slot_uri to ~100 unmapped slots**
   - Map to schema.org where possible
   - Map to dcterms, dcat, prov, foaf as appropriate
   - Document mapping rationale
3. **Add class_uri to major classes**
   - Person → foaf:Person / schema:Person
   - Organization → foaf:Organization / schema:Organization
   - Software → schema:SoftwareApplication
   - Dataset classes → appropriate dcat/schema mappings
4. **Add schema:sameAs slot**
5. **Validate:** Run `make gen-project` and check generated JSON-LD

**Expected Outcome:**
- All prefixes properly defined
- 80%+ slot coverage with semantic mappings
- 50%+ class coverage with semantic mappings
- Generated JSON-LD is valid and interoperable

### Phase 2: Variable/Field Metadata (Week 3-4)

**Goal:** Enable documentation of individual data columns/fields

**Tasks:**
1. **Create D4D_Variables.yaml module** (or add to existing module)
2. **Define VariableMetadata class:**
   ```yaml
   VariableMetadata:
     is_a: DatasetProperty
     attributes:
       variable_name:
         description: Name of the variable/column
         range: string
         required: true
         slot_uri: schema:name
       data_type:
         description: Data type
         range: string
         slot_uri: schema:DataType
       unit:
         description: Unit of measurement (QUDT preferred)
         range: uriorcurie
         slot_uri: qudt:unit
       missing_value_code:
         description: Code(s) for missing values
         range: string
         multivalued: true
       minimum_value:
         range: float
       maximum_value:
         range: float
       categories:
         description: Allowed values for categorical variables
         range: string
         multivalued: true
   ```
3. **Add variables slot to Dataset class** (links to schema:variableMeasured)
4. **Create example datasheet** with variable metadata
5. **Update documentation**

**Expected Outcome:**
- Can document individual fields/columns in datasets
- Maps to schema:variableMeasured
- Addresses biggest content gap

### Phase 3: Enhanced Fairness & Attribution (Week 5-6)

**Goal:** Structured bias/fairness documentation and better contributor attribution

**Tasks:**
1. **Add BiasTypeEnum:**
   ```yaml
   BiasTypeEnum:
     permissible_values:
       selection_bias:
       measurement_bias:
       historical_bias:
       representation_bias:
       aggregation_bias:
       algorithmic_bias:
   ```
2. **Enhance existing classes with bias_type attribute**
3. **Add orcid to Person class:**
   ```yaml
   Person:
     attributes:
       orcid:
         description: ORCID identifier
         pattern: "^\\d{4}-\\d{4}-\\d{4}-\\d{3}[0-9X]$"
         slot_uri: schema:identifier
   ```
4. **Add CRediTRoleEnum (14 standard roles)**
5. **Add credit_roles to Person/Creator**
6. **Consider:** Do we need separate D4D_Fairness module or enhance existing Ethics module?

**Expected Outcome:**
- Structured bias taxonomy
- ORCID support for persistent identifiers
- CRediT roles for contributor attribution
- Better fairness documentation

### Phase 4: Data Quality & Compliance (Week 7-8)

**Goal:** Add quality metrics and regulatory compliance tracking

**Tasks:**
1. **Enhance LabelingStrategy:**
   - Add annotations_per_item
   - Add inter_annotator_agreement
   - Add annotation_platform
2. **Add DataQuality class** (or enhance preprocessing):
   - completeness_percentage
   - accuracy_metrics
   - outlier_count
3. **Enhance regulatory compliance:**
   - Add ComplianceStatusEnum
   - Add AIActRiskEnum
   - Add compliance tracking to data governance
4. **Add VersionTypeEnum** for semantic versioning

**Expected Outcome:**
- Quantitative quality metrics
- Structured compliance tracking
- Enhanced annotation quality documentation

### Phase 5: Testing, Documentation, Examples (Week 9-10)

**Goal:** Validate changes and create comprehensive documentation

**Tasks:**
1. **Run full test suite:**
   - `make test-schema`
   - `make test-modules`
   - `make test`
2. **Create example datasheets** using ALL new features
3. **Generate all artifacts:**
   - `make full-schema`
   - `make gen-project`
   - `make gendoc`
4. **Update CLAUDE.md** with new capabilities
5. **Create migration guide** for existing datasheets
6. **Validate JSON-LD output** with external tools

**Expected Outcome:**
- All tests pass
- Comprehensive examples
- Updated documentation
- Migration guide for users

---

## Success Metrics

After implementation, D4D should achieve:

### Semantic Interoperability
- ✅ 80%+ slots have slot_uri mappings (from 14%)
- ✅ 50%+ classes have class_uri mappings (from 3%)
- ✅ All used prefixes properly defined (fix 4 missing)
- ✅ Valid JSON-LD generation via LinkML
- ✅ Compatible with schema.org, DCAT, PROV-O

### Content Coverage
- ✅ Variable/field-level metadata capability
- ✅ Structured bias taxonomy
- ✅ ORCID and CRediT support
- ✅ Data quality metrics
- ✅ Regulatory compliance tracking

### Backward Compatibility
- ✅ All existing datasheets still valid
- ✅ All new features are optional
- ✅ No breaking changes to existing schema

---

## What NOT to Do

Based on actual schema analysis, **DO NOT** create these (already exist):

❌ Person class - already exists
❌ Organization class - already exists
❌ Software class - already exists
❌ EthicalReview class - already exists
❌ InformedConsent class - already exists
❌ Deidentification class - already exists
❌ LabelingStrategy class - already exists (enhance instead)
❌ PreprocessingStrategy class - already exists
❌ DistributionFormat class - already exists
❌ UpdatePlan class - already exists
❌ Splits class - already exists
❌ Task class - already exists
❌ DiscouragedUse class - already exists
❌ keywords slot - already exists
❌ doi slot - already exists
❌ version slot - already exists
❌ license slot - already exists
❌ sha256/md5/hash slots - already exist
❌ was_derived_from slot - already exists

**Instead:** ENHANCE existing classes/slots and ADD semantic mappings!

---

## Priority Summary

**Must Do (Tier 1):**
1. Fix 4 missing prefix definitions
2. Add 100+ slot_uri mappings
3. Add 30+ class_uri mappings
4. Create VariableMetadata class
5. Add schema:sameAs

**Should Do (Tier 2):**
6. Add BiasTypeEnum
7. Add ORCID to Person
8. Add CRediT roles
9. Enhance LabelingStrategy
10. Add data quality metrics
11. Enhance regulatory compliance

**Nice to Have (Tier 3):**
12-20. Advanced features (versioning types, spatial coverage, PROV-O, etc.)

---

## Files to Modify

**Phase 1:**
- `src/data_sheets_schema/schema/data_sheets_schema.yaml` - Add missing prefixes
- `src/data_sheets_schema/schema/D4D_Base_import.yaml` - Add slot_uri to base slots
- All D4D module files - Add slot_uri and class_uri throughout

**Phase 2:**
- `src/data_sheets_schema/schema/D4D_Variables.yaml` - NEW MODULE
- `src/data_sheets_schema/schema/data_sheets_schema.yaml` - Import new module

**Phase 3:**
- `src/data_sheets_schema/schema/D4D_Base_import.yaml` - Add enums, enhance Person
- `src/data_sheets_schema/schema/D4D_Ethics.yaml` - Add BiasTypeEnum

**Phase 4:**
- `src/data_sheets_schema/schema/D4D_Preprocessing.yaml` - Enhance LabelingStrategy
- `src/data_sheets_schema/schema/D4D_Data_Governance.yaml` - Add compliance tracking

---

## Appendix: Schema Statistics

**Current State:**
- **Classes:** 65
- **Slots (top-level):** 31
- **Unique attributes:** 144
- **Enums:** 5
- **Slots with slot_uri:** 20 (14%)
- **Classes with class_uri:** 2 (3%)
- **Prefixes defined:** 29
- **Prefixes missing:** 4

**After Implementation (Projected):**
- **Classes:** ~70 (+5 new)
- **Slots:** ~180 (+36 new)
- **Enums:** ~12 (+7 new)
- **Slots with slot_uri:** ~140 (78%)
- **Classes with class_uri:** ~35 (50%)
- **Prefixes defined:** 35 (+6 new: dcterms, prov, bibo, oslc, foaf, qudt)
