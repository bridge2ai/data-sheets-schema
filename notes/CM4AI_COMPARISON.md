# CM4AI D4D Output Comparison

**Date**: 2025-02-10
**Purpose**: Compare expected GitHub Assistant output with existing CM4AI D4D files
**Test Issue**: #109

## Existing CM4AI D4D Files in Repository

| Method | File Size | Lines | Created | Has Metadata |
|--------|-----------|-------|---------|--------------|
| **claudecode_agent** | 41K | 777 | Dec 2025 | ❌ No |
| claudecode_assistant | 36K | 614 | Jan 2025 | ❌ No |
| gpt5 | 23K | 514 | Nov 2024 | ❌ No |
| **curated** | 83K | 2,244 | Nov 2024 | ❌ No |

**Note**: None of the existing CM4AI files have metadata files with SHA-256 hashes and provenance tracking.

## Schema Structure Differences

### Existing Files (Flat Structure)

The existing CM4AI D4D files use a **flat schema structure** where all fields are directly on the Dataset class:

```yaml
id: https://doi.org/10.18130/V3/DXWOS5
name: CM4AI
title: Cell Maps for Artificial Intelligence (CM4AI)
description: >
  Long description...
page: https://www.cm4ai.org
keywords:
  - Cell Maps
  - Artificial Intelligence
purposes:
  - id: purpose-001
    name: AI-Ready Cell Architecture Maps
    description: ...
tasks:
  - id: task-001
    name: Classification
    description: ...
creators:
  - id: creator-001
    description: ...
# ... all fields at top level
```

**Why completeness validator shows "insufficient"**:
- The validator looks for modular section keys: `motivation:`, `composition:`, `collection_process:`
- Flat schema doesn't have these section containers
- Still valid YAML, just different structure
- **416 slots populated** (exceeds comprehensive threshold of 146)
- **738 lines** (exceeds comprehensive threshold of 200)
- The flat structure is actually very comprehensive, just not modular

### Expected GitHub Assistant Output (Modular Structure)

The GitHub Assistant will use a **modular schema structure** with section containers:

```yaml
id: cm4ai_001
name: CM4AI
title: Cell Maps for Artificial Intelligence
description: >
  Dataset description...

motivation:
  purposes:
    - id: cm4ai:purpose:1
      description: ...
  tasks:
    - id: cm4ai:task:1
      description: ...
  addressing_gaps:
    - id: cm4ai:gap:1
      description: ...

composition:
  instances:
    - id: cm4ai:instance:1
      description: ...
  instance_count: 100
  instance_description: ...
  subsets:
    - id: cm4ai:subset:train
      name: Training
      description: ...

collection_process:
  how_was_data_acquired: ...
  collection_mechanisms: ...
  collection_timeframe: ...

preprocessing:
  preprocessing_steps:
    - id: cm4ai:preproc:1
      description: ...

uses:
  tasks:
    - id: cm4ai:use:1
      description: ...
  not_recommended_uses:
    - id: cm4ai:nouse:1
      description: ...

distribution:
  distribution_format: ...
  distribution_date: ...
  access_url: ...

maintenance:
  maintenance_plan: ...
  dataset_version: ...

human_subjects:
  involves_human_subjects: ...
  institutional_review_board: ...

ethics_and_data_protection:
  ethical_review_conducted: ...
  data_protection_impact_assessment: ...

data_governance:
  data_steward:
    - id: cm4ai:steward:1
      description: ...
  license: ...
  terms_of_use: ...
```

**Why this structure is different**:
- Uses D4D module sections as containers
- Matches current D4D schema design
- Cleaner separation of concerns
- Validator expects this structure

## Expected GitHub Assistant Output

### Files to be Created

#### 1. D4D YAML Datasheet
**Location**: `data/sheets_d4dassistant/CM4AI_d4d.yaml`

**Expected metrics**:
- **Size**: 30-50K (comparable to existing)
- **Lines**: 150-300 (aiming for acceptable to comprehensive)
- **Sections**: 7-10 of 10 (based on available documentation)
- **Slots**: 100-200+ (based on detail extraction)
- **Quality**: ACCEPTABLE or COMPREHENSIVE

**Content expectations**:
- `id`: DOI or identifier from documentation
- `name`: CM4AI
- `title`: Cell Maps for Artificial Intelligence
- Rich description from papers
- Keywords extracted from all sources
- Comprehensive purposes (AI-ready data, cell maps)
- Tasks (classification, analysis, visualization)
- Composition details from dataverse
- Collection methodology from papers
- Distribution information from dataverse
- License: CC-BY-NC-SA (from documentation)
- Governance: Data steward info from NIH grant

#### 2. Metadata File (NEW!)
**Location**: `data/sheets_d4dassistant/CM4AI_d4d_metadata.yaml`

**Expected content**:
```yaml
extraction_metadata:
  timestamp: 2025-02-10T...
  extraction_id: github-assistant-...
  extraction_type: github_assistant_claude_code
  input_mode: file
  github_context:
    issue_number: 109
    pr_number: (TBD)
    assistant_name: d4dassistant

input_documents:
  - filename: 2024.05.21.589311v1.full.txt
    relative_path: data/sheets_d4dassistant/inputs/CM4AI/...
    format: txt
    size_bytes: 54181
    sha256_hash: (calculated)
  - filename: RePORT ⟩ RePORTER - CM4AI.txt
    sha256_hash: (calculated)
  # ... all 6 files

datasheets_schema:
  version: 1.0.0
  source: local
  path: src/data_sheets_schema/schema/data_sheets_schema_all.yaml
  sha256_hash: 5bf1ccdc21e210ba...

llm_model:
  provider: anthropic
  model_name: claude-sonnet-4-5-20250929
  temperature: 0.0
  max_tokens: 16000

prompts:
  system_prompt_file: src/download/prompts/d4d_concatenated_system_prompt.txt
  system_prompt_hash: 6e519922d9ede350...
  user_prompt_file: src/download/prompts/d4d_concatenated_user_prompt.txt
  user_prompt_hash: db9dbc9e8153603c...

provenance:
  extraction_performed_by: github_d4d_assistant
  git_commit: (current commit)
```

**This is NEW**: Previous CM4AI extractions don't have metadata files with provenance tracking.

#### 3. HTML Preview
**Location**: `data/sheets_d4dassistant/CM4AI_d4d.html`

**Purpose**: Human-readable view for reviewers
**Size**: Similar to YAML or slightly larger

## Key Differences: GitHub Assistant vs Existing

| Aspect | Existing (claudecode_agent) | GitHub Assistant (Expected) |
|--------|----------------------------|----------------------------|
| **Schema Structure** | Flat (fields at top level) | Modular (section containers) |
| **File Size** | 41K (777 lines) | 30-50K (150-300 lines) |
| **Metadata File** | ❌ None | ✅ Comprehensive with hashes |
| **Provenance** | Comment header only | Full YAML metadata |
| **SHA-256 Hashes** | ❌ None | ✅ All inputs, schema, prompts |
| **Git Tracking** | ❌ None | ✅ Commit hash included |
| **Determinism** | Temperature=0.0 | Temperature=0.0 |
| **Model** | claude-sonnet-4-5-20250929 | claude-sonnet-4-5-20250929 |
| **Input Sources** | Concatenated file (122K) | Individual files (6 files) |
| **Validation** | Not validated with completeness | Must pass completeness check |
| **Quality Gate** | No quality gate | Blocks PR if insufficient |
| **GitHub Integration** | Manual process | Automated issue → PR |

## Input Source Differences

### Existing claudecode_agent
**Source**: `data/preprocessed/concatenated/CM4AI_preprocessed.txt` (122K)
- All 6 files concatenated into one large file
- Generated: Dec 2025

### GitHub Assistant Test
**Source**: `data/sheets_d4dassistant/inputs/CM4AI/` (6 individual files)
- Same source documents, but kept separate
- Copied from: `data/preprocessed/individual/CM4AI/`
- Total: ~2,978 lines across 6 files

**Advantage of individual files**:
- Can track each file's hash separately
- Better provenance granularity
- Easier to update individual sources

## Expected Quality Comparison

| Metric | claudecode_agent | GitHub Assistant (Expected) |
|--------|------------------|----------------------------|
| **Sections** | 0/10 (flat schema) | 7-10/10 (modular schema) |
| **Slots** | 416 | 100-200+ |
| **Lines** | 738 | 150-300 |
| **Keywords** | 18 | 15-25 |
| **Purposes** | 3 | 2-4 |
| **Tasks** | Multiple | 2-5 |
| **Creators** | Listed | Listed with affiliations |
| **License** | CC-BY-NC-SA | CC-BY-NC-SA |
| **Quality (flat)** | Very comprehensive | N/A (different structure) |
| **Quality (modular)** | N/A (different structure) | Acceptable to Comprehensive |

## Reproducibility Comparison

### Existing claudecode_agent
**Reproducibility**: Limited
- No input hashes
- No prompt hashes
- No git commit tracking
- Header comment only

**To reproduce**:
- Would need same concatenated file
- Same model and temperature
- Same prompts (not tracked)
- No verification possible

### GitHub Assistant (Expected)
**Reproducibility**: Full
- SHA-256 hash of each input file
- SHA-256 hash of schema
- SHA-256 hash of prompts
- Git commit tracked
- Model and temperature recorded
- All settings in metadata

**To reproduce**:
- Verify input file hashes match
- Verify schema hash matches
- Verify prompt hashes match
- Use same model and temperature
- Expect identical output

## Scientific Comparability

The GitHub Assistant implementation enables:

✅ **Verification**: Compare output hashes
✅ **Reproducibility**: Re-run with same inputs
✅ **Provenance**: Full lineage tracking
✅ **Comparison**: Metadata structure identical to batch extraction
✅ **Quality Control**: Automated completeness checks
✅ **Scientific Rigor**: All inputs tracked and hashed

## What to Compare After Test Runs

When the GitHub Assistant generates CM4AI:

### 1. Content Comparison
```bash
# Compare YAML content (will differ due to structure)
diff data/d4d_concatenated/claudecode_agent/CM4AI_d4d.yaml \
     data/sheets_d4dassistant/CM4AI_d4d.yaml

# Focus on: Are key facts consistent?
# - Dataset name, ID, description
# - License, access information
# - Key purposes and tasks
```

### 2. Metadata Presence
```bash
# Existing: No metadata file
ls data/d4d_concatenated/claudecode_agent/CM4AI*metadata* # None

# GitHub Assistant: Should have metadata
ls data/sheets_d4dassistant/CM4AI*metadata* # Expected
```

### 3. Quality Metrics
```bash
# Existing (flat schema): Shows as insufficient due to structure
python3 src/github/validate_d4d_completeness.py \
  data/d4d_concatenated/claudecode_agent/CM4AI_d4d.yaml

# GitHub Assistant (modular schema): Should pass
python3 src/github/validate_d4d_completeness.py \
  data/sheets_d4dassistant/CM4AI_d4d.yaml
```

### 4. Provenance Tracking
```bash
# Existing: Header comments only
head -10 data/d4d_concatenated/claudecode_agent/CM4AI_d4d.yaml

# GitHub Assistant: Full metadata file
cat data/sheets_d4dassistant/CM4AI_d4d_metadata.yaml
```

## Success Criteria for Comparison

After GitHub Assistant generates CM4AI, success means:

✅ **Content accuracy**: Key facts match existing extractions
✅ **Modular structure**: Uses section containers as designed
✅ **Quality threshold**: Passes completeness validation
✅ **Metadata present**: Full provenance file with hashes
✅ **Reproducible**: All inputs tracked and hashed
✅ **PR created**: Automated workflow succeeds
✅ **Documentation**: Clear communication in issue/PR

## Conclusion

The GitHub Assistant CM4AI output will:

1. **Use different schema structure** (modular vs flat)
2. **Include comprehensive metadata** (new capability)
3. **Track full provenance** (SHA-256 hashes, git commit)
4. **Meet quality thresholds** (validated before PR)
5. **Enable reproducibility** (all inputs tracked)
6. **Demonstrate automation** (issue → PR workflow)

The **content should be comparable** to existing extractions, but the **structure and metadata will be enhanced** with modern provenance tracking and quality controls.

This represents the evolution from manual/batch extraction to automated, reproducible, quality-controlled D4D generation.
