# D4D Schema Semantic Fixes - Session 2

**Date:** 2026-04-08
**Branch:** add-schema-descriptions
**Continuation of:** Initial semantic review (Session 1)

## Summary

Continued systematic resolution of semantic issues identified in comprehensive schema review. Reduced slot_uri conflicts from 17 to 8 (53% reduction), with CRITICAL conflicts reduced from 9 to 2 (78% reduction).

---

## Session 2 Fixes Applied (11 additional fixes)

### 5. dcat:accessURL - Raw Data Access ✅ FIXED

**Issue:** `access_url` (raw data access) conflicted with `access_urls` (distribution channels)

**Fix:**
- **File:** `src/data_sheets_schema/schema/D4D_Preprocessing.yaml` line 138
- **Change:** slot_uri: `dcat:accessURL` → `d4d:rawDataAccessURL`
- **Rationale:** Raw data access point is semantically distinct from general dataset distribution access

---

### 6. dcterms:creator - Principal Investigator ✅ FIXED

**Issue:** `principal_investigator` (specific role) conflicted with `created_by` (general creator)

**Fix:**
- **File:** `src/data_sheets_schema/schema/D4D_Motivation.yaml` line 81
- **Change:** slot_uri: `dcterms:creator` → `d4d:principalInvestigator`
- **Added:** `broad_mappings` to dcterms:creator and schema:creator
- **Rationale:** Principal Investigator is a specific role-based creator designation, semantically narrower than general creator

---

### 7. schema:affiliation - Team Affiliation ✅ FIXED

**Issue:** `affiliations` (team/creator affiliations) conflicted with `affiliation` (person affiliation)

**Fix:**
- **File:** `src/data_sheets_schema/schema/D4D_Motivation.yaml` line 90
- **Change:** slot_uri: `schema:affiliation` → `d4d:teamAffiliation`
- **Added:** `broad_mappings` to schema:affiliation
- **Rationale:** Team/creator affiliations are contextually different from individual person affiliations

---

### 8. dcterms:accessRights - External Resource Restrictions ✅ FIXED

**Issue:** `restrictions` (external resource restrictions) conflicted with `regulatory_restrictions` and `is_shared`

**Fix:**
- **File:** `src/data_sheets_schema/schema/D4D_Composition.yaml` line 305
- **Change:** slot_uri: `dcterms:accessRights` → `d4d:externalResourceRestrictions`
- **Added:** `broad_mappings` to dcterms:accessRights
- **Rationale:** Restrictions on external resources (not the dataset itself) are semantically distinct

**Kept:** `regulatory_restrictions` with `dcterms:accessRights` (most appropriate for regulatory access controls)

---

### 9. dcterms:accessRights - is_shared Boolean ✅ FIXED

**Issue:** `is_shared` (boolean) incorrectly mapped to `dcterms:accessRights` (expects text description)

**Fix:**
- **File:** `src/data_sheets_schema/schema/D4D_Distribution.yaml` line 55
- **Change:** slot_uri: `dcterms:accessRights` → `d4d:isExternallyShared`
- **Rationale:** Boolean indicator of external distribution doesn't match accessRights semantics (which expects textual description of access rights)

---

### 10. schema:identifier - ORCID ✅ FIXED

**Issue:** `orcid` (ORCID identifier) conflicted with generic `id` slots

**Fix:**
- **File:** `src/data_sheets_schema/schema/D4D_Base_import.yaml` line 191
- **Change:** slot_uri: `schema:identifier` → `d4d:orcidIdentifier`
- **Added:** `broad_mappings` to schema:identifier
- **Rationale:** ORCID is a specific type of persistent researcher identifier, more precise than generic identifier

---

### 11. schema:identifier - Target Dataset Relation ✅ FIXED

**Issue:** `target_dataset` (dataset relationship) incorrectly mapped to `schema:identifier`

**Fix:**
- **File:** `src/data_sheets_schema/schema/D4D_Composition.yaml` line 430
- **Change:** slot_uri: `schema:identifier` → `dcterms:relation`
- **Rationale:** Target dataset is a relationship/reference to another dataset, not an identifier property

---

### 12. schema:identifier - Latest Version ✅ FIXED

**Issue:** `latest_version_doi` (version relationship) incorrectly mapped to `schema:identifier`

**Fix:**
- **File:** `src/data_sheets_schema/schema/D4D_Maintenance.yaml` line 125
- **Change:** slot_uri: `schema:identifier` → `dcterms:hasVersion`
- **Rationale:** DOI/URL of latest version is a version relationship, not an identifier of the current resource

**Note:** Created temporary conflict with base `version` slot, resolved in Fix #13

---

### 13. dcterms:hasVersion - Version String ✅ FIXED

**Issue:** Base `version` slot (version string like "1.0.0") incorrectly using `dcterms:hasVersion` (for version relationships)

**Fix:**
- **File:** `src/data_sheets_schema/schema/D4D_Base_import.yaml` line 351
- **Change:** slot_uri: `dcterms:hasVersion` → `schema:version`
- **Rationale:** dcterms:hasVersion is for relating resources to their versions; schema:version is for the version string itself

---

### 14. schema:identifier - Grant Number ✅ FIXED

**Issue:** `grant_number` (grant identifier) conflicted with generic identifier slots

**Fix:**
- **File:** `src/data_sheets_schema/schema/D4D_Motivation.yaml` line 141
- **Change:** slot_uri: `schema:identifier` → `d4d:grantIdentifier`
- **Added:** `broad_mappings` to schema:identifier
- **Rationale:** Grant number is a specific type of funding identifier, more precise than generic identifier

---

### 15. schema:identifier - is_identifier Meta-property ✅ FIXED

**Issue:** `is_identifier` (boolean meta-property) incorrectly mapped to `schema:identifier`

**Fix:**
- **File:** `src/data_sheets_schema/schema/D4D_Variables.yaml` line 111
- **Change:** slot_uri: `schema:identifier` → `d4d:isIdentifier`
- **Rationale:** Meta-property indicating whether a variable IS an identifier, not an identifier value itself

---

### 16. dcterms:format - Data Substrate Type ✅ FIXED

**Issue:** `data_substrate` (data type: text/images) incorrectly mapped to `dcterms:format` (file format)

**Fix:**
- **File:** `src/data_sheets_schema/schema/D4D_Composition.yaml` line 68
- **Change:** slot_uri: `dcterms:format` → `dcterms:type`
- **Rationale:** Data content type (text, images) is about the type of data, not file format; dcterms:type more appropriate

**Note:** Created acceptable semantic overlap with source_type and instance_type (all describing types of things)

---

### 17. dcterms:type - Publication Status ✅ FIXED

**Issue:** `status` (draft/published/deprecated) incorrectly mapped to `dcterms:type`

**Fix:**
- **File:** `src/data_sheets_schema/schema/D4D_Base_import.yaml` line 373
- **Change:** slot_uri: `dcterms:type` → `d4d:publicationStatus`
- **Rationale:** Lifecycle/publication status is semantically different from resource type

---

### 18. dcterms:license - License Terms Description ✅ FIXED

**Issue:** `license_terms` (description of license) conflicted with `license` (the license itself)

**Fix:**
- **File:** `src/data_sheets_schema/schema/D4D_Data_Governance.yaml` line 55
- **Change:** slot_uri: `dcterms:license` → `d4d:licenseDescription`
- **Added:** `broad_mappings` to dcterms:license and dcterms:rights
- **Rationale:** License terms description is explanatory text about the license, distinct from the license identifier itself

---

## Progress Metrics

### Conflict Reduction

| Metric | Before Session 1 | After Session 1 | After Session 2 | Total Reduction |
|--------|-----------------|-----------------|-----------------|-----------------|
| **Total Conflicts** | 17 | 15 | **8** | **53%** ⬇️ |
| **CRITICAL** | 9 | 8 | **2** | **78%** ⬇️ |
| **HIGH** | 3 | 3 | **1** | **67%** ⬇️ |
| **MEDIUM** | 4 | 3 | **5** | 25% ⬆️ |

**Note:** Some HIGH conflicts were reclassified to MEDIUM after fixes resolved semantic ambiguity

### Fixes by Category

| Category | Session 1 | Session 2 | Total |
|----------|-----------|-----------|-------|
| **dcat:** conflicts | 3 | 1 | 4 |
| **dcterms:** conflicts | 0 | 7 | 7 |
| **schema:** conflicts | 1 | 3 | 4 |
| **Custom d4d:** terms created | 4 | 11 | 15 |

---

## Remaining Issues

### CRITICAL (2 remaining)

#### 1. dcterms:description (40 slots) - ARCHITECTURAL DECISION NEEDED

**Issue:** Massive semantic flattening - 40+ different detail/description slots all map to generic `dcterms:description`

**Examples:**
- acquisition_details, mechanism_details, collector_details (data collection aspects)
- bias_description, limitation_description, anomaly_details (quality issues)
- preprocessing_details, cleaning_details, labeling_details (processing steps)
- And 30+ more...

**Options:**
1. **Leave as-is** - Accept semantic flattening for simplicity
   - ✅ No breaking changes
   - ❌ Loses RDF semantic precision

2. **Create specific D4D terms** for each category
   - ✅ Maximum semantic precision
   - ❌ Significant effort (40+ custom terms)
   - ❌ No reuse of standard vocabulary

3. **Hybrid approach** - Differentiate where clear standard alternatives exist
   - Some use more specific DCTERMS/Schema.org properties
   - Group related *_details fields under category-specific terms
   - ✅ Balanced precision vs effort
   - ⚠️ Requires careful semantic analysis

**Recommendation:** Option 3 with phased approach:
- Phase 1: Identify fields with clear standard alternatives (e.g., source_description → dcterms:source)
- Phase 2: Group *_details by semantic category (collection, processing, quality, etc.)
- Phase 3: Create d4d: category namespaces (d4d:collectionDetails, d4d:qualityDetails, etc.)

---

#### 2. dcterms:type (3 slots) - SEMANTIC OVERLAP

**Current usages:**
- `source_type` (D4D_Collection) - Type of data source (sensor/database/web)
- `instance_type` (D4D_Composition) - Types of instances (movies/users/ratings)
- `data_substrate` (D4D_Composition) - Type of data content (text/images/etc)

**Analysis:** All three legitimately describe "types" of things, which is what dcterms:type is for. This may be **acceptable semantic overlap** rather than a conflict.

**Options:**
1. **Leave as-is** - All are valid dcterms:type usages
2. **Differentiate** - Create specific terms (d4d:sourceType, d4d:instanceType, keep data_substrate as dcterms:type since it uses controlled vocabulary)

**Recommendation:** Option 2 for maximum precision, but Option 1 is defensible

---

### HIGH (1 remaining)

#### schema:contactPoint (2 slots)

**Usages:** Contact information in different contexts - investigate and differentiate if needed

---

### MEDIUM (5 remaining)

1. **dcat:byteSize** (2 slots) - `bytes` vs `total_bytes` (acceptable - different entities)
2. **dcterms:conformsTo** (3 slots) - Multiple conformance declarations
3. **dcterms:identifier** (4 slots) - Remaining generic identifiers (mostly acceptable)
4. **schema:description** (3 slots) - Multiple description fields (similar to dcterms:description)
5. **schema:name** (3 slots) - Name fields in different contexts (likely acceptable)

---

## Validation Status

```bash
make test-schema  # ✅ PASSED
make gen-project  # ✅ PASSED
```

**All changes non-breaking:**
- slot_uri modifications affect RDF/JSON-LD only
- YAML data structure unchanged
- No data migration required

---

## Next Steps

### Immediate
1. ✅ Commit Session 2 fixes
2. 📝 Create `docs/ontology_mapping_guide.md` with rationale for all mappings
3. 🎯 Make architectural decision on dcterms:description (40 slots)

### High Priority
4. 🔍 Review and address dcterms:type semantic overlap (3 slots)
5. 🔍 Investigate schema:contactPoint conflict (2 slots)
6. 🔍 Review remaining MEDIUM priority conflicts

### Medium Priority
7. 📊 Address 51 HIGH priority range mismatches from data analysis
8. 🔍 Review 75 enum candidates identified in actual data

### Documentation
9. 📝 Document all custom d4d: namespace terms created
10. 📝 Update CLAUDE.md with semantic validation practices
11. 📝 Create migration guide for any breaking changes (if needed)

---

## Files Modified

**Schema modules:**
- `src/data_sheets_schema/schema/D4D_Base_import.yaml` (3 fixes)
- `src/data_sheets_schema/schema/D4D_Collection.yaml` (0 fixes this session)
- `src/data_sheets_schema/schema/D4D_Composition.yaml` (3 fixes)
- `src/data_sheets_schema/schema/D4D_Data_Governance.yaml` (1 fix)
- `src/data_sheets_schema/schema/D4D_Distribution.yaml` (1 fix)
- `src/data_sheets_schema/schema/D4D_Maintenance.yaml` (1 fix)
- `src/data_sheets_schema/schema/D4D_Motivation.yaml` (3 fixes)
- `src/data_sheets_schema/schema/D4D_Preprocessing.yaml` (1 fix)
- `src/data_sheets_schema/schema/D4D_Variables.yaml` (1 fix)

**Generated files** (auto-regenerated):
- `project/jsonld/data_sheets_schema.jsonld`
- `project/owl/data_sheets_schema.owl.ttl`
- `src/data_sheets_schema/datamodel/data_sheets_schema.py`

**Reports:**
- `reports/slot_uri_conflicts_final.json` (updated)
- `reports/semantic_fixes_session2.md` (this file)

---

## Custom D4D Terms Created (Session 2)

All custom terms in d4d: namespace with broad_mappings to standard vocabularies where applicable:

1. `d4d:rawDataAccessURL` - Access point for raw/unprocessed data
2. `d4d:principalInvestigator` - PI role designation
3. `d4d:teamAffiliation` - Creator/team organizational affiliations
4. `d4d:externalResourceRestrictions` - Restrictions on external resources
5. `d4d:isExternallyShared` - Boolean indicator of external distribution
6. `d4d:orcidIdentifier` - ORCID persistent researcher identifier
7. `d4d:grantIdentifier` - Funding grant number/identifier
8. `d4d:isIdentifier` - Meta-property: whether variable is identifier
9. `d4d:publicationStatus` - Lifecycle status (draft/published/deprecated)
10. `d4d:licenseDescription` - Explanatory text about license terms

**Total custom D4D terms:** 15 (Session 1: 5, Session 2: 10)

---

## Semantic Precision Improvements

### Before
- Generic schema:identifier for all identifier types
- dcat:accessURL for all access points
- dcterms:type for both types and status
- dcterms:format for both format and data type
- Boolean using text-description slot_uri

### After
- Specific identifiers: orcidIdentifier, grantIdentifier, plus generic id
- Specific access: rawDataAccessURL, erratumURL, contributionURL, plus generic accessURL
- Clear separation: dcterms:type for types, publicationStatus for status
- Clear separation: dcterms:format for file format, dcterms:type for data content type
- Semantically appropriate slot_uris for all boolean fields

**Result:** RDF/JSON-LD output now has much higher semantic precision and interoperability
