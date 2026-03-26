# CLI Reference

The Datasheets for Datasets workflow is exposed through the `d4d` command defined in `pyproject.toml`.

## Installation and Invocation

Use the CLI from a repository checkout:

```bash
poetry install
poetry run d4d --help
```

After `poetry install`, the `d4d` entrypoint is available in the Poetry environment. While developing in the repo, `poetry run d4d ...` is the most reliable form.

Most subcommands assume they can import repo-local modules from `src/` and `.claude/agents/scripts/`, so running inside a clone of `data-sheets-schema` is currently required.

## Top-Level Commands

| Command | Purpose |
| --- | --- |
| `d4d download` | Download, preprocess, and concatenate source documents |
| `d4d evaluate` | Run datasheet evaluation workflows |
| `d4d render` | Render datasheets and evaluation outputs to HTML |
| `d4d rocrate` | Parse, merge, and transform RO-Crate metadata |
| `d4d schema` | Generate schema metrics and validate YAML against the schema |
| `d4d utils` | Inspect pipeline status and validate preprocessing results |

## `d4d download`

### `d4d download sources`

Download source documents from the project tracking sheet.

```bash
poetry run d4d download sources --project AI_READI
```

Options:

| Option | Description |
| --- | --- |
| `--project` | Required. One of `AI_READI`, `CHORUS`, `CM4AI`, `VOICE` |
| `--output-dir PATH` | Output directory for downloads. Default: `data/raw` |

### `d4d download preprocess`

Normalize raw downloads into preprocessed text artifacts.

```bash
poetry run d4d download preprocess --project AI_READI
```

Options:

| Option | Description |
| --- | --- |
| `--project` | Optional. Restrict preprocessing to one project |
| `--input-dir PATH` | Raw download directory. Default: `data/raw` |
| `--output-dir PATH` | Preprocessed output directory. Default: `data/preprocessed/individual` |

### `d4d download concatenate`

Concatenate one project's preprocessed files into a single text file.

```bash
poetry run d4d download concatenate --project AI_READI
```

Options:

| Option | Description |
| --- | --- |
| `--project` | Required. One of `AI_READI`, `CHORUS`, `CM4AI`, `VOICE` |
| `--input-dir PATH` | Preprocessed input directory. Default: `data/preprocessed/individual` |
| `--output-file PATH` | Output path. Default: `data/preprocessed/concatenated/{PROJECT}_preprocessed.txt` |

## `d4d evaluate`

### `d4d evaluate presence`

Run the presence-based evaluator across one project or all projects.

```bash
poetry run d4d evaluate presence --project AI_READI --method gpt5
```

Options:

| Option | Description |
| --- | --- |
| `--project` | Optional. Restrict evaluation to one project |
| `--method` | Generation method. One of `curated`, `gpt5`, `claudecode`, `claudecode_agent`, `claudecode_assistant` |
| `--output-dir PATH` | Evaluation output directory. Default: `data/evaluation` |

### `d4d evaluate llm`

Run the LLM-based quality evaluator for a specific D4D YAML file.

```bash
poetry run d4d evaluate llm \
  --file data/d4d_concatenated/gpt5/AI_READI_d4d.yaml \
  --project AI_READI \
  --method gpt5 \
  --rubric both
```

Requires `ANTHROPIC_API_KEY`.

Options:

| Option | Description |
| --- | --- |
| `--file PATH` | Required. D4D YAML file to evaluate |
| `--project TEXT` | Required. Project name |
| `--method TEXT` | Required. Generation method |
| `--rubric` | `rubric10`, `rubric20`, or `both`. Default: `both` |
| `--output-dir PATH` | LLM evaluation output directory. Default: `data/evaluation_llm` |

## `d4d render`

### `d4d render html`

Render a structured input file to HTML.

```bash
poetry run d4d render html \
  docs/yaml_output/concatenated/gpt5/AI_READI_d4d.yaml \
  -o /tmp/AI_READI_d4d.html
```

Options:

| Option | Description |
| --- | --- |
| `INPUT_FILE` | Required positional argument. Structured input file |
| `-o, --output PATH` | Output HTML path. Default: a canonical name derived from the input filename and rubric |
| `--template` | `human-readable`, `evaluation`, or `linkml`. Default: `human-readable` |

Current behavior notes:

- `human-readable` writes to the exact output path you provide.
- The CLI also copies `datasheet-common.css` into the output directory so the generated HTML can be opened directly with styling intact.
- `linkml` renders a more technical LinkML-style HTML view from YAML or JSON input.
- `evaluation` renders an evaluation JSON file and auto-detects `rubric10` vs `rubric20`.

### `d4d render evaluation`

Render evaluation JSON directly to HTML.

```bash
poetry run d4d render evaluation \
  data/evaluation_llm/rubric10/concatenated/AI_READI_claudecode_agent_evaluation.json \
  -o /tmp/AI_READI_evaluation.html
```

Options:

| Option | Description |
| --- | --- |
| `INPUT_FILE` | Required positional argument. Evaluation JSON file |
| `-o, --output PATH` | Output HTML path. Default: `<input_file>.html` |
| `--rubric` | `auto`, `rubric10`, or `rubric20`. Default: `auto` |

Naming convention notes:

- If you omit `-o`, rubric10 outputs default to the canonical `*_evaluation.html` name.
- If you omit `-o`, rubric20 outputs default to `*_evaluation_rubric20.html` so they do not collide with rubric10 outputs.

### `d4d render generate-all`

Show the bulk rendering workflow.

```bash
poetry run d4d render generate-all --method curated
```

Options:

| Option | Description |
| --- | --- |
| `--method` | Optional. One of `gpt5`, `claudecode_agent`, `claudecode_assistant`, `curated` |

This command currently prints instructions for bulk generation rather than rendering every file itself.

## `d4d rocrate`

These commands depend on helper scripts under `.claude/agents/scripts/`.

### `d4d rocrate parse`

Parse an RO-Crate JSON-LD file and optionally write the extracted entities to disk.

```bash
poetry run d4d rocrate parse path/to/ro-crate-metadata.json --output parsed.json
```

Options:

| Option | Description |
| --- | --- |
| `INPUT_FILE` | Required positional argument. RO-Crate JSON-LD file |
| `--output PATH` | Optional JSON output path |

### `d4d rocrate transform`

Transform one RO-Crate or a merged set of RO-Crates into D4D YAML.

```bash
poetry run d4d rocrate transform path/to/ro-crate-metadata.json -o output.yaml
```

Options:

| Option | Description |
| --- | --- |
| `INPUT_FILE` | Required positional argument for single-file mode |
| `-o, --output PATH` | Required. Output D4D YAML path |
| `--merge` | Enable merge mode |
| `--inputs PATH` | Additional RO-Crate inputs for merge mode |
| `--primary PATH` | Primary RO-Crate for conflict resolution in merge mode |

### `d4d rocrate merge`

Merge multiple RO-Crate files into one JSON document.

```bash
poetry run d4d rocrate merge crate1.json crate2.json -o merged.json
```

Options:

| Option | Description |
| --- | --- |
| `INPUT_FILES...` | Required positional arguments. One or more RO-Crate files |
| `-o, --output PATH` | Required. Output merged RO-Crate path |
| `--primary PATH` | Primary RO-Crate file for conflict precedence |

## `d4d schema`

These commands also depend on helper scripts under `.claude/agents/scripts/`.

### `d4d schema stats`

Generate metrics for the LinkML schema.

```bash
poetry run d4d schema stats --level 1 --format markdown
```

Options:

| Option | Description |
| --- | --- |
| `--level` | Detail level from `1` to `4`. Default: `1` |
| `--format` | Output format: `json`, `markdown`, or `csv`. Default: `markdown` |
| `--output PATH` | Optional output file. Otherwise writes to stdout |
| `--schema-file PATH` | Override schema path. Default: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` |

### `d4d schema validate`

Validate a D4D YAML file against the schema.

```bash
poetry run d4d schema validate docs/yaml_output/concatenated/gpt5/AI_READI_d4d.yaml
```

Options:

| Option | Description |
| --- | --- |
| `D4D_FILE` | Required positional argument. D4D YAML file to validate |
| `--schema-file PATH` | Override schema path. Default: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` |

## `d4d utils`

### `d4d utils status`

Show pipeline file counts.

```bash
poetry run d4d utils status --quick
```

Options:

| Option | Description |
| --- | --- |
| `--quick` | Show the compact view instead of the detailed breakdown |

### `d4d utils validate-preprocessing`

Check the preprocessing output for empty or stub artifacts.

```bash
poetry run d4d utils validate-preprocessing --project AI_READI
```

Options:

| Option | Description |
| --- | --- |
| `--raw-dir PATH` | Raw data directory. Default: `data/raw` |
| `--preprocessed-dir PATH` | Preprocessed data directory. Default: `data/preprocessed/individual` |
| `--project` | Optional. Restrict validation to one project |

## Recommended Starting Points

- `poetry run d4d --help` for the top-level command list
- `poetry run d4d utils status --quick` for a quick pipeline sanity check
- `poetry run d4d download preprocess --project AI_READI` to start working on one project
- `poetry run d4d evaluate presence --project AI_READI --method gpt5` to generate evaluation output
