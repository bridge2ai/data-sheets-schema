# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

LinkML schema project for "Datasheets for Datasets" (D4D) - standardized dataset documentation inspired by the Gebru et al. paper. Creates structured schemas for 50+ D4D questions.

**Related work**: [Original paper](https://m-cacm.acm.org/magazines/2021/12/256932-datasheets-for-datasets/fulltext), [CheXpert example](https://arxiv.org/abs/2105.03020), [Data Cards](https://arxiv.org/abs/2204.01075)

## Development Commands

### Setup and Testing
```bash
make setup              # Initial setup
make install            # Install dependencies
make test               # All tests
make test-schema        # Validate full merged schema
make test-modules       # Validate individual modules
make lint-modules       # Lint D4D modules
```

### Building
```bash
make gen-project        # Generate Python/JSON/OWL artifacts
make gendoc             # Generate documentation
make site               # Build complete site
make deploy             # Deploy to GitHub Pages
```

## Architecture

### Core Schema Files
- `src/data_sheets_schema/schema/data_sheets_schema.yaml` - Main schema (imports all modules)
- `src/data_sheets_schema/schema/D4D_Base_import.yaml` - Base classes/slots/enums
- D4D modules (in schema/ directory): `D4D_Motivation.yaml`, `D4D_Composition.yaml`, `D4D_Collection.yaml`, `D4D_Preprocessing.yaml`, `D4D_Uses.yaml`, `D4D_Distribution.yaml`, `D4D_Maintenance.yaml`, `D4D_Human.yaml`, `D4D_Ethics.yaml`, `D4D_Data_Governance.yaml`, `D4D_Metadata.yaml`, `D4D_Minimal.yaml`

### Generated Artifacts (DO NOT EDIT)
- `src/data_sheets_schema/datamodel/` - Python classes
- `project/` - JSON Schema, OWL, SHACL, JSON-LD, GraphQL
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` - Merged schema

### Key Configuration
- `about.yaml`, `pyproject.toml`, `Makefile`, `config.env`

## Schema Development Workflow

1. Edit schemas in `src/data_sheets_schema/schema/`
2. `make lint-modules && make test-modules` (fast module validation)
3. `make test-schema` (full validation)
4. `make gen-project` (regenerate artifacts)
5. `make test` (complete validation)

## Keeping Schema Files in Sync

Three representations must stay synchronized:
1. `data_sheets_schema.yaml` (source)
2. `data_sheets_schema_all.yaml` (merged)
3. `data_sheets_schema.py` (Python model)

```bash
make check-sync    # Check synchronization
make regen-all     # Force regenerate everything
```

## Working with Modules

- Each module imports `D4D_Base_import.yaml`
- Classes inherit from base classes (especially `DatasetProperty`)
- Main schema imports all modules
- `make full-schema` generates merged `data_sheets_schema_all.yaml`

## Testing Strategy

1. **Schema Validation** (`make test-schema`): LinkML syntax/structure
2. **Python Tests** (`make test-python`): Datamodel classes (`tests/`)
3. **Example Validation** (`make test-examples`): Validate example data

## D4D Pipeline and Data Organization

AI-powered extraction of D4D metadata from dataset documentation.

### Data Structure

```
data/
  raw/{PROJECT}/                     # Raw downloads: {source}_row{N}.{pdf,html,txt,json}
  preprocessed/
    individual/{PROJECT}/            # Standardized: {source}_row{N}.{txt,json}
    concatenated/                    # {PROJECT}_{preprocessed|concatenated|raw}.txt
  d4d_individual/{METHOD}/{PROJECT}/ # {source}_row{N}_d4d.yaml
  d4d_concatenated/{METHOD}/         # {PROJECT}_d4d.yaml
  d4d_html/{individual|concatenated}/{METHOD}/  # HTML renderings
  ATTIC/                            # Archived legacy data
```

**Projects**: AI_READI, CHORUS, CM4AI, VOICE

### File Naming
- Raw/preprocessed: `{source}_row{N}.{ext}` (e.g., `e097449.full_row2.pdf`)
- D4D individual: `{source}_row{N}_d4d.yaml`
- D4D concatenated: `{PROJECT}_d4d.yaml`
- HTML: `{PROJECT}_d4d_human_readable.html`, `{PROJECT}_evaluation.html`

### Pipeline Workflow

```bash
# 1. Download from Google Sheet
make download-sources  # → data/raw/{PROJECT}/

# 2. Preprocess (PDF→TXT, HTML→TXT)
make preprocess-sources  # → data/preprocessed/individual/{PROJECT}/

# 2.5. Validate quality ⚠️ CRITICAL
make validate-preprocessing  # Check for empty/stub files

# 3. Concatenate by project
make concat-preprocessed  # → {PROJECT}_preprocessed.txt

# 4. Extract D4D (recommended method)
make d4d-agent PROJECT=AI_READI  # → data/d4d_concatenated/claudecode_agent/

# 5. Generate HTML
make gen-d4d-html
```

### D4D Generation Methods

| Method | Status | Best For | Quality | Speed |
|--------|--------|----------|---------|-------|
| **claudecode_agent** | ✅ Current (v5+) | Production datasheets | ⭐⭐⭐⭐⭐ | Fast (parallel) |
| claudecode_assistant | Alternative | Interactive refinement | ⭐⭐⭐⭐⭐ | Medium |
| claudecode | Legacy | API automation | ⭐⭐⭐ | Medium |
| gpt5 | Comparison | Benchmarking | ⭐⭐ | Slow |
| curated | Reference | Gold standard | ⭐⭐⭐⭐⭐ | Manual |

**Key finding**: claudecode_agent outperforms GPT-5 by 3.26× on multi-document synthesis.

**Use claudecode_agent for new datasheets**:
```bash
make d4d-agent PROJECT=AI_READI
make gen-d4d-html
make version-html VERSION=6
```

### Pipeline Commands Reference

**Extraction:**
```bash
make extract-d4d-individual-all-gpt5      # Extract all individual files
make extract-d4d-concat-all-gpt5          # Extract from concatenated
make d4d-pipeline-full-gpt5               # Complete pipeline
```

**Concatenation:**
```bash
make concat-extracted        # Individual D4D YAMLs
make concat-preprocessed     # Preprocessed source files
make concat-raw             # Raw downloads
```

**Validation:**
```bash
make validate-d4d FILE=path/to/file.yaml
make validate-d4d-project PROJECT=AI_READI GENERATOR=gpt5
make validate-d4d-all GENERATOR=gpt5
```

**Monitoring:**
```bash
make data-status            # Full status report
make data-status-quick      # Compact overview
make data-d4d-sizes        # D4D YAML sizes
```

## D4D Assistant Instructions (GitHub Actions)

**For GitHub Actions D4D Assistant only**: Read instruction files FIRST:
- `.github/workflows/d4d_assistant_create.md` - Creating new datasheets
- `.github/workflows/d4d_assistant_edit.md` - Editing existing datasheets
- Both include "Modifying an Existing PR" sections

Critical requirements:
- Scope: D4D tasks only (redirect others)
- Tools: GitHub MCP, ARTL, WebSearch, WebFetch
- Validation: MUST validate YAML before PRs
- Comments: Update both PR and issue

## Document Concatenation

Concatenates multiple documents into single file with reproducible ordering.

```bash
make concat-docs INPUT_DIR=path/to/dir OUTPUT_FILE=output.txt
python src/download/concatenate_documents.py -i input -o output.txt [--extensions .txt .md] [--recursive]
```

Features: Alphabetical sorting, file headers, table of contents, multiple format support.

## Custom Makefile Targets

**Status/Monitoring:**
```bash
make data-status[-quick]    # Data pipeline status
make data-d4d-sizes         # D4D YAML sizes
```

**Concatenation:**
```bash
make concat-{extracted|preprocessed|raw}
```

**D4D Extraction:**
```bash
make extract-d4d-{individual|concat}-{all-}gpt5
make extract-d4d-{individual|concat}-{all-}claude
```

**Validation:**
```bash
make validate-d4d[-project|-all]
```

**HTML:**
```bash
make gen-d4d-html
```

**Pipelines:**
```bash
make d4d-pipeline-{individual|concatenated|full}-gpt5
```

## Null/Empty Value Handling

- **Schema/Python**: Use `null`/`None` for missing values (default for optional fields)
- **HTML rendering**: Converts `None`/`null` → empty strings `""` for cleaner display
- Files: `src/html/human_readable_renderer.py`, `src/renderer/yaml_renderer.py`

## D4D Evaluation Framework

Evaluates D4D generation quality using two rubrics:

**Rubric10** (50 points): 10 hierarchical elements × 5 sub-elements, binary scoring
**Rubric20** (84 points): 20 questions across 4 categories, 0-5 scale

```bash
# Evaluate concatenated files
make evaluate-d4d [PROJECT=VOICE]

# Evaluate individual files
make evaluate-d4d-individual

# View results
make eval-summary[-individual]
make eval-details PROJECT=VOICE METHOD=claudecode
```

**Output**: `data/evaluation/` - summary reports, detailed analyses, scores (CSV/JSON)

**Key findings** (concatenated synthesis):
- Claude Code: 37.5% (R10), 52.4% (R20) - Best
- Curated: 21.3% (R10), 41.7% (R20)
- GPT-5: 11.5% (R10), 17.3% (R20)

Individual files (single-source): Claude Code and GPT-5 identical at 18.8% (R10), 26.3% (R20).

## D4D LLM-based Evaluation (Quality Assessment)

LLM-as-judge agents provide quality assessment complementing field-presence detection.

### Conversational Evaluation Agents

**d4d-rubric10** (`.claude/agents/d4d-rubric10.md`): 10-element hierarchical rubric
**d4d-rubric20** (`.claude/agents/d4d-rubric20.md`): 20-question detailed rubric

**Usage** (no API key required in Claude Code):
```
User: Evaluate data/d4d_concatenated/claudecode/VOICE_d4d.yaml with d4d-rubric10
```

Agent provides: Overall score, strengths, weaknesses, recommendations with evidence quotes.

### External Automation (Optional - Requires ANTHROPIC_API_KEY)

```bash
# Batch evaluation
make evaluate-d4d-llm-batch-concatenated  # ~25min, ~$6
make evaluate-d4d-llm-batch-individual    # ~2hrs, ~$34
make evaluate-d4d-llm-batch-all           # Complete

# Single file (legacy)
make evaluate-d4d-llm-{rubric10|rubric20|both}
make evaluate-d4d-llm FILE=path PROJECT=X METHOD=Y RUBRIC=both

# Compare with presence detection
make compare-evaluations
```

**Settings**: Temperature 0.0, model claude-sonnet-4-5-20250929 (fully deterministic)

**Output**: `data/evaluation_llm/` - rubric10/rubric20 summaries, scores.csv, scores.json

**Comparison**:
| Metric | Presence | LLM Quality |
|--------|----------|-------------|
| Speed | ~1s | ~30-60s |
| Cost | Free | ~$0.10-0.30 |
| Insight | Field exists? | Quality/completeness |
| Evidence | None | Quotes, reasoning |

See `notes/LLM_EVALUATION.md` and `notes/RUBRIC_AGENT_USAGE.md` for details.

## Running Single Tests

```bash
poetry run python -m unittest tests.test_d4d_full_schema[.TestClass[.test_method]]
```

## Important Notes

- **DO NOT EDIT** `project/`, `src/data_sheets_schema/datamodel/`, `data_sheets_schema_all.yaml` (auto-generated)
- Run `make gen-project` after schema changes
- Module files in `src/data_sheets_schema/schema/` (NOT in modules/ subdirectory)
- Prefer inheriting from base classes in `D4D_Base_import.yaml`
- `aurelian/` is git submodule: `git submodule update --init --recursive`
- Legacy data in `data/ATTIC/` (see ATTIC/README.md)
- Always run `make regen-all` after editing schemas to stay in sync

## LinkML-Specific Commands

```bash
linkml-lint <schema.yaml>
linkml-convert -s <schema> -C <Class> <input> -o <output>
gen-linkml -o <output> -f yaml <input>
gen-doc -d docs <schema>
```

## Common Workflows

**Add Module**: Create `D4D_NewModule.yaml`, import `D4D_Base_import`, add to main schema, add to `Dataset` class, run `make gen-project && make test`

**Modify Schema**: Edit file → `make lint-modules` → `make test-modules` → `make test-schema` → `make gen-project` → `make test`

**Example Data**: Add to `src/data/examples/valid/` or `invalid/` → `make test-examples` → check `examples/output/`
