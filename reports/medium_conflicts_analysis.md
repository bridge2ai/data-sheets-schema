# MEDIUM Priority Conflicts - Analysis & Decisions

## 1. dcat:byteSize (2 slots) - ✅ ACCEPTABLE

**Usages:**
- `bytes` (D4D_Base_import) - Size of a single file/resource in bytes
- `total_bytes` (D4D_FileCollection) - Total size of all files in a collection

**Analysis:** Both slots correctly use dcat:byteSize to express size in bytes. The semantic distinction is the entity being measured (single file vs collection), not the property itself. DCAT's byteSize property is appropriate for both contexts.

**Decision:** ACCEPT as valid semantic overlap. No fix needed.

**Rationale:** The slot_uri describes the property (byte size), not the entity. Different entities can share the same property type.

---

## 2. dcterms:conformsTo (3 slots) - ⚠️ DIFFERENTIATE for precision

**Usages:**
- `conforms_to` (generic) - Any established standard/specification  
- `conforms_to_schema` (specific) - Schema or data model
- `conforms_to_class` (specific) - Specific class within a schema

**Analysis:** While all express conformance relationships (appropriate for dcterms:conformsTo), the specific variants add semantic precision that could be valuable for machine interpretation.

**Decision:** DIFFERENTIATE the specific variants

**Fix:**
```yaml
conforms_to_schema:
  slot_uri: d4d:conformsToSchema
  broad_mappings:
    - dcterms:conformsTo

conforms_to_class:
  slot_uri: d4d:conformsToClass
  broad_mappings:
    - dcterms:conformsTo
```

**Rationale:** Schema and class conformance are semantically narrower than generic conformance. Custom terms preserve this precision while maintaining broad mapping.

---

## 3. dcterms:identifier (4 slots) - ⚠️ PARTIALLY DIFFERENTIATE

**Usages:**
- `hash` - Generic cryptographic hash  
- `md5` - MD5 hash (128-bit)
- `sha256` - SHA-256 hash (256-bit)
- `doi` - Digital Object Identifier

**Analysis:**
- **Hashes (hash, md5, sha256)**: All serve same purpose (integrity verification), just different algorithms. Semantic overlap acceptable.
- **DOI**: Fundamentally different - persistent citation identifier, not integrity hash. Should be differentiated.

**Decision:** Differentiate DOI only, keep hashes as dcterms:identifier

**Fix:**
```yaml
doi:
  slot_uri: d4d:doiIdentifier
  broad_mappings:
    - dcterms:identifier
  exact_mappings:
    - schema:identifier  # DOI is a schema.org identifier
```

**Rationale:** 
- Hashes: All identifiers based on content, acceptable overlap
- DOI: Persistent scholarly identifier with different semantics (citation vs verification)

---

## 4. schema:description (4 slots) - ✅ MOSTLY ACCEPTABLE

**Usages:**
- `description` (NamedThing) - Generic description
- `description` (DatasetProperty) - Property description  
- `label_description` (D4D_Composition) - Pattern/format of labels
- `representative_verification` (D4D_Composition) - Verification description

**Analysis:** Most are generic descriptions (appropriate). `label_description` and `representative_verification` are more specific descriptive fields.

**Decision:** ACCEPT generic descriptions, DIFFERENTIATE specific ones

**Fix:**
```yaml
label_description:
  slot_uri: d4d:labelPattern
  broad_mappings:
    - schema:description

representative_verification:
  slot_uri: d4d:verificationDescription  
  broad_mappings:
    - schema:description
```

**Rationale:** Generic descriptions share semantics; specific descriptive fields benefit from precision.

---

## 5. schema:name (4 slots) - ✅ DIFFERENTIATED

**Usages:**
- `name` (NamedThing) - Generic name
- `name` (DatasetProperty) - Property name
- `tools` (D4D_Preprocessing) - Tool names list  
- `variable_name` (D4D_Variables) - Variable identifier name

**Analysis:**
- Generic `name` slots: Appropriate overlap
- `tools`: List of tool names (software name list)
- `variable_name`: Specific variable identifier (technical name)

**Decision:** DIFFERENTIATE tools and variable_name

**Fix Applied:**
```yaml
tools:
  slot_uri: d4d:toolNames
  broad_mappings:
    - schema:name

variable_name:
  slot_uri: d4d:variableName
  broad_mappings:
    - schema:name
    - schema:identifier  # Variables are identified by name
```

**Rationale:** Software tool names and variable technical names have specific semantics beyond generic naming.

---

## Summary

| Conflict | Slots | Decision | Fixes Needed |
|----------|-------|----------|--------------|
| dcat:byteSize | 2 | ACCEPT | 0 |
| dcterms:conformsTo | 3 | DIFFERENTIATE | 2 |
| dcterms:identifier | 4 | PARTIAL | 1 (DOI) |
| schema:description | 4 | PARTIAL | 2 |
| schema:name | 4 | PARTIAL | 2 |
| **TOTAL** | **17** | - | **7 fixes** |

**Acceptable overlaps:** 5 slots (dcat:byteSize both, dcterms:identifier hashes, generic names/descriptions)

**Precision improvements:** 7 slots need custom d4d: terms

---

## Implementation Order

1. ✅ doi → d4d:doiIdentifier (D4D_Base_import.yaml:383)
2. ✅ conforms_to_schema → d4d:conformsToSchema (D4D_Base_import.yaml:334)
3. ✅ conforms_to_class → d4d:conformsToClass (D4D_Base_import.yaml:338)
4. ✅ variable_name → d4d:variableName (D4D_Variables.yaml:47)
5. ✅ label_description → d4d:labelPattern (D4D_Composition.yaml:83)
6. ✅ representative_verification → d4d:verificationDescription (D4D_Composition.yaml:132)
7. ✅ tools → d4d:toolNames (D4D_Preprocessing.yaml:236)

**Result:** 5 MEDIUM conflicts → 2 acceptable overlaps (dcat:byteSize, dcterms:identifier hashes)

---

## Final Status

**Conflicts resolved:** 3 of 5 MEDIUM priority conflicts
- ✅ dcterms:conformsTo (3 slots) → 2 custom terms + 1 generic
- ✅ schema:description (4 slots) → 2 custom terms + 2 generic
- ✅ schema:name (4 slots) → 2 custom terms + 2 generic

**Acceptable overlaps documented:**
- ✅ dcat:byteSize (2 slots) - Different entities, same property semantics
- ✅ dcterms:identifier (4 slots) - Hash variants acceptable, DOI differentiated

**Custom D4D terms created:** 7
- d4d:doiIdentifier
- d4d:conformsToSchema
- d4d:conformsToClass
- d4d:variableName
- d4d:labelPattern
- d4d:verificationDescription
- d4d:toolNames

**Total impact:** Reduced slot_uri conflicts from 17 to 5 (70% reduction)
