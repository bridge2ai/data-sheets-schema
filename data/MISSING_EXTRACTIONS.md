# Missing D4D Extractions

## AI_READI - 2 Source Files Missing D4D YAMLs

The following source files in `downloads_by_column/AI_READI/` do not have corresponding D4D YAML extractions:

### 1. doi_row9.json
- **Location**: `downloads_by_column/AI_READI/doi_row9.json`
- **Size**: 119 bytes
- **Status**: No D4D extraction exists (neither GPT-5 nor Claude Code)
- **Note**: During validation (Nov 14), relevance check showed score: 0 (limited relevance to AI_READI)
- **Action needed**: Extract D4D metadata or create minimal D4D YAML

### 2. fairhub_row10.json
- **Location**: `downloads_by_column/AI_READI/fairhub_row10.json`
- **Size**: 107 bytes
- **Status**: No D4D extraction exists (neither GPT-5 nor Claude Code)
- **Note**: Validation successful (score: 4, found keyword: fairhub)
- **Action needed**: Extract D4D metadata using validated_d4d_wrapper.py

## Validation Report Reference

See `data/ATTIC/extracted_by_column/validated_d4d_processing_report.md` for details on why these files were skipped during the Nov 14, 2025 extraction run.

## Recommendations

1. **fairhub_row10.json**: Should be extracted - it's a valid FairHub API response
2. **doi_row9.json**: May be low-value extraction (only 119 bytes, no AI_READI keywords found) - consider manual review first

## Commands to Extract

```bash
# Extract both files using validated_d4d_wrapper
cd aurelian
uv run python ../src/download/validated_d4d_wrapper.py -i ../downloads_by_column/AI_READI -o ../data/d4d_individual/gpt5/AI_READI

# Or extract using Claude Code (future)
# <instructions for Claude Code extraction when implemented>
```

Generated: 2025-11-14
