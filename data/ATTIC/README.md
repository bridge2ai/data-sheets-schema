# ATTIC - Archived Legacy Data

This directory contains deprecated data extraction attempts, old download structures,
and superseded pipeline outputs that are no longer actively used but preserved for
historical reference.

## Directory Organization

### root_downloads/ (from repository root)

Legacy directories moved from repository root level on 2024-12-19:

| Directory | Size | Description | Replaced By |
|-----------|------|-------------|-------------|
| `downloads_by_column_enhanced/` | 14 MB | Enhanced download structure with metadata | `data/raw/` |
| `old/` | 9.1 MB | Previous miscellaneous archive | Current pipeline |
| `test_downloads/` | 4.0 MB | Old test data | `data/raw/` with validation |
| `downloads_by_column_combined/` | 912 KB | Merged old downloads | `data/raw/` |
| `downloads_by_column_enhanced_combined/` | 620 KB | Variant of enhanced downloads | `data/raw/` |

**Why archived**: These directories used an older download organization pattern. The current
pipeline uses `data/raw/` with standardized file naming conventions (`{source}_row{N}.{ext}`)
and quality validation.

### sheets_concatenated/ (84 KB)

Old concatenated sheets structure.

**Replaced by**: `data/preprocessed/concatenated/`

The current pipeline uses a more robust concatenation process with:
- Reproducible alphabetical ordering
- File metadata headers
- Table of contents generation
- Quality validation checks

### validated_extracted_html_only/ (132 KB)

HTML-only outputs from old validated extraction process.

**Note**: This is a different variant from the main `validated_extracted/` directory
(also in ATTIC), which contains D4D YAML files. This variant only has HTML subdirectories.

**Replaced by**: Current D4D pipeline with `data/d4d_individual/` and `data/d4d_html/`

### Legacy Extraction Attempts (existing, from earlier)

Earlier D4D extraction experiments archived before the current consolidation:

| Directory | Type | Description |
|-----------|------|-------------|
| `validated_extracted/` | D4D YAMLs | Validated extraction outputs with processing reports |
| `extracted_by_column*/` (5 variants) | D4D YAMLs | Early column-based D4D extractions |
| `claude_max_extractions/` | D4D YAMLs | Claude model outputs |
| `extracted_claude_code/` | D4D YAMLs | Early Claude Code attempts |
| `extracted_coding_agent/` | D4D YAMLs | Agent-based extraction experiments |
| `extracted_d4d_agent/` | D4D YAMLs | D4D agent outputs (early version) |
| `sheets*/` (3 variants) | Alternative | Sheet data variants |
| `GC_data_sheets/` | Alternative | Grand Challenge format |
| `RO-Crate/` | Alternative | RO-Crate format experiments |

## Current Active Pipeline (for reference)

The active data pipeline structure is:

```
data/
├── raw/                         # Raw source downloads
│   ├── AI_READI/, CHORUS/, CM4AI/, VOICE/
│   └── Files: {source}_row{N}.{ext}
│
├── preprocessed/
│   ├── individual/              # Processed sources (PDF→TXT, HTML→TXT)
│   │   └── {PROJECT}/{source}_row{N}.{ext}
│   └── concatenated/            # All docs per project merged
│       └── {PROJECT}_preprocessed.txt
│
├── d4d_individual/              # D4D YAMLs from individual docs
│   ├── claudecode_agent/        # ✅ Current (v5+)
│   ├── gpt5/                    # Comparison
│   └── curated/                 # Hand-curated reference
│
├── d4d_concatenated/            # Synthesized comprehensive D4D YAMLs
│   ├── claudecode_agent/        # ✅ Current (v5+)
│   │   └── {PROJECT}_d4d.yaml
│   ├── gpt5/
│   └── curated/
│
├── d4d_html/                    # HTML renderings
│   ├── individual/
│   └── concatenated/
│       └── claudecode_agent/    # ✅ Current (v5+)
│
├── evaluation/                  # Evaluation results (rubric-based)
└── evaluation_llm/              # LLM-based evaluation results
```

**Documentation**: See `CLAUDE.md` for complete pipeline details and file naming conventions.

## Archive Timeline

### December 19, 2024

Comprehensive repository cleanup - archived deprecated directories:

**Context**: After establishing the current D4D pipeline (`claudecode_agent` as canonical method)
and standardizing all paths, these legacy directories were consolidated into ATTIC/.

**Verification performed**:
- ✅ No references in GitHub Actions workflows
- ✅ No active usage in Makefiles (only old examples/comments)
- ✅ No active usage in source code (only deprecated script defaults)
- ✅ No breaking references in documentation
- ✅ Preserved `utils/` directory (actively used by workflows)

**Moved**:
- 5 root-level directories → `root_downloads/`
- 2 data-level directories → `ATTIC/`
- Total archived: ~29 MB

### November 17, 2024 (earlier)

Initial ATTIC creation with 19 subdirectories of early extraction experiments.

## Notes on Archived Content

### downloads_by_column vs data/raw

The old `downloads_by_column*/` structure organized downloads differently:
- **Old**: `downloads_by_column/{PROJECT}/{files}`
- **New**: `data/raw/{PROJECT}/{source}_row{N}.{ext}`

Key improvements in current structure:
1. Standardized naming from Google Sheet metadata
2. Quality validation (checks for empty files, stubs, data loss)
3. Preprocessing validation before D4D extraction
4. Integration with full data pipeline

### sheets_concatenated vs preprocessed/concatenated

The old `sheets_concatenated/` had simpler concatenation:
- **Old**: Basic file concatenation
- **New**: Alphabetical ordering, metadata headers, table of contents, validation

### Extraction Method Evolution

1. **Early experiments** (ATTIC, older): Various extraction approaches tested
2. **GPT-5** (comparison): API-based extraction for benchmarking
3. **claudecode** (legacy): Deterministic API approach (temperature=0.0)
4. **claudecode_agent** (current): Claude Code Task tool with comprehensive synthesis

**Quality comparison** (from evaluation):
- Claude Code Agent: 37.5% (Rubric10), 52.4% (Rubric20)
- GPT-5: 11.5% (Rubric10), 17.3% (Rubric20)
- **3.26× improvement** with current method

See `notes/D4D_EVALUATION.md` for complete evaluation methodology.

## Safe to Delete?

These archived directories can be **safely deleted after 6-12 months** if:
- No historical reference needed
- Disk space constraints require cleanup
- Current pipeline (v5+) proven stable

**Before deletion**, verify:
```bash
# Ensure current pipeline is complete
make data-status-quick

# Verify all projects have current generation
ls data/d4d_concatenated/claudecode_agent/
# Should show: AI_READI_d4d.yaml, CHORUS_d4d.yaml, CM4AI_d4d.yaml, VOICE_d4d.yaml

# Verify versioned HTML exists
ls src/html/output/D4D_-_*_v5_*.html
```

**Recommendation**: Keep until v7+ is deployed to GitHub Pages (at least 2-3 stable versions).

## Cleanup Actions Needed

After archiving these directories, the following files should be updated (low priority):

### 1. Update Script Defaults

```python
# src/download/interactive_d4d_wrapper.py
# Change: default="downloads_by_column"
# To:     default="data/raw"

# src/download/process_concatenated_d4d.py
# Update example paths in docstrings
```

### 2. Update Documentation

```markdown
# README.md - Update examples
# Old: downloads_by_column
# New: data/raw
```

### 3. Update Makefile Comments

```makefile
# project.Makefile lines 662, 665
# Old: data/sheets_concatenated/AI_READI_concatenated.txt
# New: data/preprocessed/concatenated/AI_READI_preprocessed.txt
```

### 4. Clean Claude Code Permissions

```json
// .claude/settings.local.json lines 22, 62
// Remove old permission entries for downloads_by_column
```

**Status**: Non-critical - these are default values and comments that are overridden
or not used in active code.

## Total Archive Size

```
root_downloads/                  28.6 MB
sheets_concatenated/               84 KB
validated_extracted_html_only/    132 KB
validated_extracted/             (earlier, size varies)
[other 19 legacy dirs]           (earlier, size varies)
--------------------------------------------------
TOTAL (approximate)              ~45-50 MB
```

## Archive Date

**Created**: November 17, 2024 (initial)
**Updated**: December 19, 2024 (comprehensive cleanup)

## Related Documentation

- **Pipeline**: `CLAUDE.md` - Complete D4D pipeline documentation
- **Evaluation**: `notes/D4D_EVALUATION.md` - Method comparison and rubrics
- **Versioning**: `docs/VERSIONING.md` - HTML versioning workflow
- **Quality**: `docs/D4D_GAPS_COMPLETED.md` - Gap analysis and quality issues

---

*This ATTIC preserves the evolution of the D4D pipeline from early experiments
to the current production-ready approach.*
