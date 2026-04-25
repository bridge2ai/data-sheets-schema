# D4D GitHub Assistant Output Directory

This directory contains D4D datasheets created by the GitHub D4D Assistant (`@d4dassistant`) in response to issue requests.

## Directory Structure

```
data/sheets_d4dassistant/
├── inputs/                         # File-mode inputs (preferred)
│   └── {dataset}/                  # Files provided in PR or issue
│       ├── source1.txt
│       ├── source2.json
│       └── source3.pdf
├── fetched/                        # URL-mode downloads (fallback)
│   └── {dataset}/                  # Files fetched from URLs
│       └── {url_hash}.txt
├── {dataset}_d4d.yaml              # Output D4D YAML datasheet
├── {dataset}_d4d_metadata.yaml     # Comprehensive extraction metadata
├── {dataset}_d4d.html              # HTML preview for review
└── README.md                       # This file
```

## Input Modes

### File-Based Mode (Preferred)

**When to use**: User provides documentation files directly in issue or PR.

**Location**: `inputs/{dataset}/`

**Benefits**:
- Reproducible (files are hashed and tracked)
- No network dependencies
- Faster processing
- Full provenance tracking

**Example**:
```bash
# User attaches files or provides local paths
data/sheets_d4dassistant/inputs/mydataset/
├── documentation.pdf
├── metadata.json
└── readme.md
```

### URL-Based Mode (Fallback)

**When to use**: User provides URLs to documentation.

**Location**: `fetched/{dataset}/`

**Behavior**:
- Assistant downloads content from URLs
- Saves to `fetched/{dataset}/{url_hash}.txt`
- URL hashes tracked in metadata
- Files cached for reproducibility

**Example**:
```bash
# URLs provided: https://example.com/doc1, https://example.com/doc2
data/sheets_d4dassistant/fetched/mydataset/
├── a1b2c3d4_doc1.txt
└── e5f6g7h8_doc2.txt
```

## Output Files

### `{dataset}_d4d.yaml`

The primary D4D datasheet in YAML format, conforming to the D4D LinkML schema.

**Structure**:
```yaml
# D4D extracted by GitHub Assistant
# Generated: 2025-02-10
# Metadata: See {dataset}_d4d_metadata.yaml

id: dataset_identifier
name: Dataset Name
motivation:
  purposes:
    - id: project:purpose:1
      description: "Purpose description..."
  # ... additional sections
```

### `{dataset}_d4d_metadata.yaml`

Comprehensive extraction metadata for reproducibility and provenance.

**Structure**:
```yaml
extraction_metadata:
  timestamp: 2025-02-10T12:00:00+00:00
  extraction_id: github-assistant-abc123
  extraction_type: github_assistant_claude_code
  input_mode: file  # or url
  github_context:
    issue_number: 42
    pr_number: 43
    assistant_name: d4dassistant

input_documents:
  - filename: documentation.pdf
    sha256_hash: abc123...
    format: pdf
    size_bytes: 1048576

datasheets_schema:
  version: 1.0.0
  sha256_hash: def456...
  path: src/data_sheets_schema/schema/data_sheets_schema_all.yaml

llm_model:
  model_name: claude-sonnet-4-5-20250929
  temperature: 0.0  # Deterministic
  max_tokens: 16000

prompts:
  system_prompt_hash: ghi789...
  user_prompt_hash: jkl012...

provenance:
  git_commit: abc123def456...
  extraction_performed_by: github_d4d_assistant
```

### `{dataset}_d4d.html`

Human-readable HTML preview for easy review.

**Purpose**:
- Reviewers can view datasheet in browser
- No need to parse YAML
- Includes all sections and fields
- Formatted for readability

## Deterministic Generation

All assistant-created datasheets follow the deterministic approach:

**Settings**:
- **Model**: `claude-sonnet-4-5-20250929` (date-pinned)
- **Temperature**: `0.0` (maximum determinism)
- **Schema**: Local version-controlled file
- **Prompts**: External version-controlled files

**Reproducibility**:
- Same input → Same output
- SHA-256 hashes track all inputs
- Git commit tracked for provenance
- Comprehensive metadata enables verification

**Comparability**:
- Metadata structure matches batch extraction (`process_concatenated_d4d_claude.py`)
- Scientifically comparable to batch methods
- Same quality thresholds and validation

## Quality Validation

Before PR creation, datasheets are validated for completeness:

**Quality Levels**:
- **Comprehensive**: 10+ sections, 146+ slots, 200+ lines
- **Acceptable**: 7+ sections, 100+ slots, 150+ lines
- **Minimal**: 4+ sections, 50+ slots, 100+ lines
- **Insufficient**: Below minimal (BLOCKS PR)

**Validation Script**:
```bash
python src/github/validate_d4d_completeness.py data/sheets_d4dassistant/mydataset_d4d.yaml
```

**Exit codes**:
- `0`: Quality acceptable (proceed with PR)
- `1`: Quality insufficient (block PR)

## Prerequisites Validation

Before D4D generation, prerequisites are validated:

**Checks**:
- Schema file exists
- Prompt files exist
- Input files/URLs accessible
- API key set
- Python dependencies installed

**Validation Script**:
```bash
./src/github/validate_prerequisites.sh --dataset mydataset --mode file
```

## Workflow Integration

The GitHub Assistant uses these scripts in sequence:

1. **Prerequisites** → Validate before generation (fail fast)
2. **Generation** → Extract D4D from sources
3. **Metadata** → Generate comprehensive metadata
4. **Validation** → Check completeness (block if insufficient)
5. **PR Creation** → Only if validation passes

## Configuration

Central configuration: `.github/workflows/d4d_assistant_deterministic.config`

**Key settings**:
```yaml
model:
  name: claude-sonnet-4-5-20250929
  temperature: 0.0

validation:
  block_threshold: minimal  # Don't create PR if below this
  min_sections_acceptable: 7

output:
  base_dir: data/sheets_d4dassistant
```

## Comparison with Batch Methods

| Aspect | GitHub Assistant | Batch Extraction |
|--------|------------------|------------------|
| **Trigger** | Issue mention | Makefile target |
| **Input** | URLs or files | Concatenated files |
| **Model** | claude-sonnet-4-5-20250929 | Same |
| **Temperature** | 0.0 | 0.0 |
| **Metadata** | Same structure | Same structure |
| **Output** | `data/sheets_d4dassistant/` | `data/d4d_concatenated/claudecode/` |
| **Reproducibility** | Full | Full |

## Usage Examples

### File-Based Extraction

```bash
# User provides files in issue
# Assistant validates prerequisites
./src/github/validate_prerequisites.sh --dataset mydataset --mode file

# Assistant generates D4D
# (via GitHub Actions workflow)

# Assistant generates metadata
python src/github/generate_d4d_metadata.py \
  --d4d-file data/sheets_d4dassistant/mydataset_d4d.yaml \
  --dataset-name mydataset \
  --input-dir data/sheets_d4dassistant/inputs/mydataset

# Assistant validates completeness
python src/github/validate_d4d_completeness.py \
  data/sheets_d4dassistant/mydataset_d4d.yaml

# If validation passes → Create PR
```

### URL-Based Extraction

```bash
# User provides URLs in issue
# Assistant validates prerequisites
./src/github/validate_prerequisites.sh \
  --dataset mydataset \
  --mode url \
  --urls "https://example.com/doc1 https://example.com/doc2"

# Assistant fetches URLs
# Assistant generates D4D
# (via GitHub Actions workflow)

# Assistant generates metadata
python src/github/generate_d4d_metadata.py \
  --d4d-file data/sheets_d4dassistant/mydataset_d4d.yaml \
  --dataset-name mydataset \
  --input-sources "https://example.com/doc1" "https://example.com/doc2"

# Assistant validates completeness
# If validation passes → Create PR
```

## Verification

To verify an assistant-created datasheet:

```bash
# Check metadata
cat data/sheets_d4dassistant/mydataset_d4d_metadata.yaml

# Verify schema validation
poetry run linkml-validate \
  -s src/data_sheets_schema/schema/data_sheets_schema_all.yaml \
  -C Dataset \
  data/sheets_d4dassistant/mydataset_d4d.yaml

# Check completeness
python src/github/validate_d4d_completeness.py \
  data/sheets_d4dassistant/mydataset_d4d.yaml

# View HTML preview
open data/sheets_d4dassistant/mydataset_d4d.html
```

## Contributing

If you find issues with assistant-generated datasheets:

1. Comment on the PR with specific corrections
2. Request the assistant to make edits
3. Assistant will update the PR branch
4. Review updated files

The assistant can modify existing PRs to apply corrections and improvements.

## References

- **Instruction files**:
  - `.github/workflows/d4d_assistant_create.md` - Creating datasheets
  - `.github/workflows/d4d_assistant_edit.md` - Editing datasheets
- **Configuration**: `.github/workflows/d4d_assistant_deterministic.config`
- **Batch extraction**: `src/download/process_concatenated_d4d_claude.py`
- **D4D schema**: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
