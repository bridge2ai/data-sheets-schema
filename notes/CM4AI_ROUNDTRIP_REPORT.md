# CM4AI Round-Trip Conversion Report

## Summary

**Source:** CM4AI FAIRSCAPE RO-Crate (DOI: 10.18130/V3/K7TGEM)
**Dataset:** Cell Maps for Artificial Intelligence - January 2026 Data Release (Beta)

### Conversion Path

```
Original FAIRSCAPE RO-Crate
          ↓
    D4D YAML (44 fields)
          ↓
  Round-trip RO-Crate
```

## Property Preservation Statistics

| Metric | Count | Percentage |
|--------|-------|------------|
| Original properties | 69 | 100% |
| Preserved properties | 39 | 56.5% |
| Lost properties | 30 | 43.5% |

## Preservation by Namespace

| Namespace | Preserved | Lost | Total | Rate |
|-----------|-----------|------|-------|------|
| schema.org | 14 | 22 | 36 | 38.9% |
| EVI | 6 | 3 | 9 | 66.7% |
| RAI | 14 | 5 | 19 | 73.7% |
| D4D | 5 | 0 | 5 | 100.0% |

## Core Property Fidelity

All core metadata properties preserved:

- ✓ **Dataset Name** (`name`)
- ✓ **Description** (`description`)
- ✓ **Keywords** (`keywords`)
- ✓ **Version** (`version`)
- ✓ **License** (`license`)
- ✓ **Authors** (`author`)
- ✓ **Publication Date** (`datePublished`)
- ✓ **DOI** (`identifier`)

## Lost Properties

Properties not preserved in round-trip (not yet in D4D schema):

### schema.org

- `additionalProperty`
- `associatedPublication`
- `citation`
- `completeness`
- `conditionsOfAccess`
- `confidentialityLevel`
- `contactEmail`
- `copyrightNotice`
- `dataGovernanceCommittee`
- `deidentified`
- `ethicalReview`
- `fdaRegulated`
- `funder`
- `hasSummaryStatistics`
- `humanSubjectExemption`
- `humanSubjectResearch`
- `humanSubjects`
- `irb`
- `irbProtocolId`
- `principalInvestigator`
- `prohibitedUses`
- `usageInfo`

### EVI

- `evi:entitiesWithChecksums`
- `evi:entitiesWithSummaryStats`
- `evi:totalContentSizeBytes`

### RAI

- `rai:annotationsPerItem`
- `rai:dataAnnotationPlatform`
- `rai:dataCollectionType`
- `rai:dataImputationProtocol`
- `rai:dataManipulationProtocol`

## File Sizes

- Original: 13,615 bytes
- Round-trip: 7,533 bytes
- Retention: 55.3%

## Conclusion

✅ **Core metadata**: 100% preserved (all 8 properties)
✅ **Overall fidelity**: 39/69 properties (56.5%)
✅ **D4D namespace**: 100% preserved (all 5 properties)
⚠️  **Schema.org extensions**: 22/36 properties lost (not in D4D schema yet)

The round-trip successfully preserves all core metadata and namespace-specific properties that have D4D equivalents.