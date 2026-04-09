# dcterms:description Conflict Analysis

**Issue:** 40 slots map to `dcterms:description`, causing semantic flattening
**Severity:** CRITICAL
**Status:** Architectural decision required

---

## Distribution by Pattern

### Pattern 1: *_details suffix (30 slots - 75%)

**Data Collection (6):**
- acquisition_details
- collection_details
- collector_details
- mechanism_details
- timeframe_details
- source_description (close to _details pattern)

**Data Quality/Issues (3):**
- anomaly_details
- bias_description (should group with quality)
- limitation_description (should group with quality)

**Privacy/Security (3):**
- confidentiality_details
- deidentification_details
- sensitivity_details

**Ethics (5):**
- consent_details
- impact_details (ethics context)
- notification_details
- review_details
- revocation_details

**Maintenance/Versioning (6):**
- erratum_details
- extension_details
- maintainer_details
- retention_details
- update_details
- version_details

**Preprocessing/Processing (4):**
- cleaning_details
- labeling_details
- preprocessing_details
- raw_data_details

**Use Cases (4):**
- discouragement_details
- impact_details (use case context)
- repository_details
- task_details

**Data Structure (2):**
- relationship_details
- split_details

### Pattern 2: Question-oriented (2 slots - 5%)
- why_missing
- missing

### Pattern 3: Content-specific (8 slots - 20%)
- distribution (subpopulation distribution)
- future_guarantees (external resource commitments)
- identification (subpopulation identification methods)
- quality_notes (variable quality notes)
- response (appears 3× in D4D_Motivation - different question contexts)
- warnings (content warnings)

---

## Semantic Analysis

### Are these truly "descriptions"?

**YES - appropriate dcterms:description:**
- bias_description
- limitation_description
- source_description
- quality_notes
- warnings

**BORDERLINE - could use more specific terms:**
- why_missing → dcterms:description is OK but could be more specific
- missing → describes what's missing (dcterms:description acceptable)
- future_guarantees → commitment/policy statement (not pure description)
- identification → methodology (dcterms:description acceptable)
- distribution → statistical distribution (schema:description more specific?)

**NO - semantically different from pure description:**
- 30× *_details fields → procedural/technical details, not descriptions
- response → answer to specific question (not description of the dataset)

---

## Options Analysis

### Option 1: Accept As-Is (Status Quo)

**Approach:** Keep all 40 slots using `dcterms:description`

**Pros:**
- ✅ Zero effort
- ✅ No breaking changes
- ✅ Simple schema
- ✅ Uses standard vocabulary

**Cons:**
- ❌ Semantic flattening - loses distinction between description types
- ❌ RDF consumers can't distinguish collection details from quality notes
- ❌ Misses opportunity for semantic precision
- ❌ Not best practice for domain-specific schemas

**Use case impact:**
- SPARQL queries: "Get all descriptions" returns mixed semantic content
- RDF reasoning: Cannot distinguish procedural details from quality issues
- Interoperability: Generic mapping provides no domain context

---

### Option 2: Full Differentiation (40 custom terms)

**Approach:** Create 40 custom d4d: terms (one per slot)

**Examples:**
- d4d:acquisitionDetails
- d4d:collectorDetails
- d4d:biasDescription
- etc.

**Pros:**
- ✅ Maximum semantic precision
- ✅ Every field has unique ontology identity
- ✅ Best for machine reasoning

**Cons:**
- ❌ Significant effort (40 terms to define/document)
- ❌ No reuse of standard vocabulary
- ❌ Maintenance burden
- ❌ Potential over-engineering

**Use case impact:**
- SPARQL queries: Very specific ("get acquisition details")
- RDF reasoning: Can distinguish every detail type
- Interoperability: Requires d4d ontology understanding

---

### Option 3: Hybrid - Pattern-Based Grouping (RECOMMENDED)

**Approach:** Group by semantic category, use specific terms where clear standards exist

#### Phase 1: High-Value Differentiations (immediate)

**A. Quality/Issues → Specific terms**
- bias_description → KEEP `dcterms:description` (pure description)
- limitation_description → KEEP `dcterms:description` (pure description)
- anomaly_details → `d4d:anomalyDetails` (technical details, not description)

**B. Question-Answer → Specific terms**
- response (3×) → `d4d:questionResponse` (answer to question, not description)

**C. Statistical → Schema.org**
- distribution (subpopulation) → Consider `schema:description` or custom

**D. Content Warnings → Keep**
- warnings → KEEP `dcterms:description` (content description)

#### Phase 2: *_details Pattern (deferred/optional)

**Option 3A: Single umbrella term**
- All 30 *_details → `d4d:technicalDetails`
- Broad enough to cover all contexts
- Distinguishes from pure descriptions

**Option 3B: Category-specific namespaces**
- Collection: `d4d:collectionDetails`
- Ethics: `d4d:ethicsDetails`
- Maintenance: `d4d:maintenanceDetails`
- Preprocessing: `d4d:preprocessingDetails`
- Quality: `d4d:qualityDetails`
- Use: `d4d:useDetails`
- etc.

**Option 3C: Keep as dcterms:description**
- Accept that *_details is a common pattern
- Semantic overlap acceptable for "details about X"

---

## Recommended Decision: Option 3 - Minimal Hybrid

### Immediate Actions (4 changes):

1. **response (3 slots) → d4d:questionResponse**
   - File: D4D_Motivation.yaml
   - Rationale: Answers to questions, not dataset descriptions
   - Impact: Clarifies Q&A pattern vs descriptive text

2. **anomaly_details → d4d:anomalyDetails**
   - File: D4D_Composition.yaml
   - Rationale: Technical error/noise details, semantically distinct from quality descriptions
   - Impact: Separates technical details from descriptive content

3. **quality_notes → d4d:qualityNotes**
   - File: D4D_Variables.yaml
   - Rationale: Variable-level quality notes, specific context
   - Impact: Distinguishes variable quality from general descriptions

4. **future_guarantees → d4d:availabilityGuarantee**
   - File: D4D_Composition.yaml
   - Rationale: Commitment/policy about external resources, not description
   - Impact: Clarifies this is a guarantee statement

### Accept as dcterms:description (36 slots):

**Pure descriptions (semantically correct):**
- bias_description
- limitation_description
- source_description
- warnings
- identification
- missing
- why_missing
- distribution

**Details fields (acceptable semantic overlap):**
- All 30× *_details fields
- Rationale: "Details about X" is a form of description
- Benefit: Reuses standard vocabulary
- Trade-off: Loses some semantic precision but acceptable

---

## Impact Assessment

### Recommended Approach Impact

**Conflicts reduced:** 40 → 36 slots (10% reduction)
**Custom terms created:** 4 (minimal)
**Standard vocabulary retained:** 90% of fields still use dcterms:description
**Semantic clarity gained:** 
- Question responses separated from descriptions
- Technical anomaly details distinguished
- Variable quality notes contextualized
- Resource guarantees clarified

### Effort vs. Benefit

| Approach | Effort | Benefit | Ratio |
|----------|--------|---------|-------|
| Option 1 (status quo) | 0 | 0 | - |
| Option 2 (40 terms) | Very High | High | Low |
| **Option 3 (4 terms)** | **Low** | **Medium** | **High** |

---

## Alternative: Deferred Decision

If immediate decision is difficult, can:
1. Document dcterms:description semantic overlap as ACCEPTABLE
2. Add comment explaining the 40 slots represent different detail types
3. Revisit if real-world usage shows need for differentiation

**Recommendation:** Proceed with Option 3 (4 targeted changes) - best balance of precision and pragmatism.

---

## Next Steps (if Option 3 approved)

1. Apply 4 fixes:
   - response → d4d:questionResponse (D4D_Motivation.yaml, 3 instances)
   - anomaly_details → d4d:anomalyDetails (D4D_Composition.yaml)
   - quality_notes → d4d:qualityNotes (D4D_Variables.yaml)
   - future_guarantees → d4d:availabilityGuarantee (D4D_Composition.yaml)

2. Document in ontology_mapping_guide.md:
   - Rationale for 4 custom terms
   - Justification for accepting 36 dcterms:description slots
   - Explain semantic overlap is intentional and acceptable

3. Update semantic_fixes_session3.md with decision

4. Regenerate schema and validate

5. Mark Task #4 complete
