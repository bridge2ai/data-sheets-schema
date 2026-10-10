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
| `d4d rocrate` | Parse and transform RO-Crate metadata; raw merge is retired |
| `d4d schema` | Generate schema metrics and validate YAML against the schema |
| `d4d utils` | Inspect pipeline status and validate preprocessing results |
| `d4d validate` | Validate and lint data-sheet instances (CI-friendly) |

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
| `--sheet-url URL_OR_PATH` | Public CSV export URL or local CSV file. Defaults to the Bridge2AI GC input sheet |
| `--manifest PATH` | Stage downloads and promote only canonical artifacts, retaining valid prior fallbacks. Default: `data/preprocessed/source_manifest.yaml` |

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
| `--manifest PATH` | Canonical source selection manifest. Default: `data/preprocessed/source_manifest.yaml` |

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
| `--manifest PATH` | Canonical source selection manifest. Default: `data/preprocessed/source_manifest.yaml` |

The manifest fixes the active source inventory, normalizes every processed
artifact to `.txt`, and supplies a deterministic concatenation order. To run the
repository-level workflow for all four projects:

```bash
make download-and-preprocess
```

## `d4d evaluate`

### Captured support and fitness workflows

These explicit commands separate planning, saved-evidence checks, registered
execution and reporting. Only `support-execution run` below dispatches requests;
the other listed commands operate offline. Available software and declared
decision references do not grant scientific acceptance or paid-run authority.

| Command | Purpose and detailed workflow |
| --- | --- |
| `d4d evaluate support-plan`, `support-request` | [Capture a plan and reconstruct exact requests](offline_support_plan.md); `--plan-version 2` selects nested support targets and separate top-level fitness. |
| `d4d evaluate support-results prepare/accept/recheck/report` | [Bind selected target attempts and check saved nested-support responses](nested-support-results.md). |
| `d4d evaluate support-execution prepare/run/recheck` | [Register and execute one explicitly selected support or fitness instrument](nested-support-execution.md), then reconstruct its captured execution evidence. |
| `d4d evaluate support-calibration prepare/report/recheck` | [Bind declared control labels and inspect captured calibration evidence](../notes/support_calibration_2026-10-07/README.md); unresolved labels and missing observations remain visible. |
| `d4d evaluate fitness-results prepare/accept/recheck/index/recheck-index` | [Check top-level fitness and build a portable index](top-level-fitness-results.md); `--support-execution` includes all registered support selections, and `--rubric-associations` adds declared rubric identity checks. |

Saved-response acceptance is mechanical. Rubric association checks do not accept
ratings or certify scores. Independently reviewed controls, empirical calibration
and applicable campaign authorization remain separate requirements under #2929,
#3342 and #3343.

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
# Explicit compatible legacy TSV; also supported with --merge:
poetry run d4d rocrate transform path/to/ro-crate-metadata.json -o output.yaml \
  --mapping path/to/reviewed-mapping.tsv
```

Options:

| Option | Description |
| --- | --- |
| `INPUT_FILE` | Required positional argument for single-file mode |
| `-o, --output PATH` | Required. Output D4D YAML path |
| `--merge` | Enable merge mode |
| `--inputs PATH` | Additional RO-Crate inputs for merge mode |
| `--primary PATH` | Primary RO-Crate for conflict resolution in merge mode |
| `--mapping PATH` | Explicit legacy mapping TSV. Omitted uses `data/ro-crate_mapping/d4d_rocrate_mapping_v2_semantic.tsv` |

The selected table is passed to the existing legacy transformer for both single
and merge modes. Dataset files must pass the mandatory closed-schema publication
gate before any output or report is replaced. The default table now has explicit
root-identity, maintenance-narrative and Creator-literal constructors, but other
construction defects and unsupported reference assertions can still refuse
publication. An explicit mapping must produce a valid Dataset;
this option does not repair a table or switch to another mapper. Source files,
the selected mapping, and existing outputs are preserved on validation refusal.
See [the mapping-selection scope](../notes/legacy_cli_mapping_2026-10-07/README.md).

The default Creator route preserves complete root `author` strings as
`Creator.description`, and preserves other assertions without inferring people,
IDs or PI roles. Marked merges retain every assertion, including duplicates.
Reports label their existing output-key count as **constructed-field presence**,
including null-valued keys; it is neither source coverage nor validation success.
A separate raw-author diagnostic distinguishes missing, null, empty and present
assertions. The API retains its different non-null-value count with an explicit
`coverage_basis` and exposes `source_presence` even when provenance is disabled.
See the [Creator construction and measurement contract](../notes/legacy_creator_assertions_2026-10-08/README.md).

### `d4d rocrate merge` (retired)

Raw RO-Crate merging is unsupported. The command remains recognizable but
always refuses with a nonzero exit and an explanation of
[#4593](https://github.com/bridge2ai/data-sheets-schema/issues/4593), before
loading a merger, reading crate contents or writing an output. Keep the source
crates separate. Existing files are preserved.

The former implementation called a Dataset-producing merger through methods
that did not exist. No raw-graph identity, root/descriptor, context or source
provenance contract was defined. `--primary` did not resolve those missing
policies. Restoring raw merge requires an explicit contract and real producer
tests; this retirement does not invent one.

The legacy syntax is retained for a useful diagnostic:

| Option | Status |
| --- | --- |
| `INPUT_FILES...` | Required positional paths; their contents are not read. |
| `-o, --output PATH` | Required legacy option; no output is created or replaced. |
| `--primary PATH` | Recognized legacy option; no conflict precedence is applied. |

`d4d rocrate transform --merge` remains a separate Dataset YAML operation.
The retired command does not redirect to it or to the graph-concatenation
helper. Dataset mapping construction remains tracked in #4594, and #2915
retains its linked fidelity, comparison and publication obligations.

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

## `d4d validate`

Validate and lint one or more data-sheet instance files (YAML or JSON)
against the D4D LinkML schema. Unlike `d4d schema validate`, this command
runs the validator in-process (no `poetry run` subprocess), works from an
installed wheel in any directory, and adds linter checks that go beyond
schema validity:

- **unknown fields** (with did-you-mean hints for typos),
- **scalar type mismatches** (`count: not-a-number` on an integer slot —
  missed by `linkml-validate` itself),
- **placeholder prose** (`TBD`, `N/A`, `?`) and **empty values**,
- **missing identifier prose** (`title`, `name`, `description`),
- **British spellings** in prose (the datasheet convention is American English),
- **per-section completeness** against the Gebru et al. datasheet sections,
  with a 0–100 completeness score.

```bash
poetry run d4d validate datasheet.yaml
poetry run d4d validate --schema core datasheet.yaml --format json --output report.json
poetry run d4d validate --fail-on-warning datasheets/*.yaml
```

Options:

| Option | Description |
| --- | --- |
| `FILES...` | One or more data-sheet YAML/JSON files to check |
| `--schema` | `full` (target class `Dataset`) or `core` (target class `CoreDataset`). Default: `full` |
| `--schema-file PATH` | Validate against this schema file instead of `--schema` |
| `--target-class NAME` | Target class in the schema (default: `Dataset` for full, `CoreDataset` for core) |
| `--format` | `human` (summary + findings) or `json` (machine-readable report). Default: `human` |
| `--output PATH` | Write the report to this file instead of stdout |
| `--fail-on-warning` | Exit 1 on lint warnings, not just on schema errors |
| `--quiet`, `-q` | Human format: print only the per-file summary lines |

Exit codes: `0` = all files valid (warnings allowed unless
`--fail-on-warning`); `1` = at least one file invalid, or warnings with
`--fail-on-warning`; `2` = usage error (missing file, unknown target class,
unreadable schema).

Issue codes emitted in reports:

| Code | Severity | Meaning |
| --- | --- | --- |
| `schema-violation` | error | Failed LinkML schema validation, with JSON path |
| `unknown-field` | error | Field not in the schema (typo candidate), with hint |
| `type-mismatch` | error | Scalar value that cannot be coerced to the slot range |
| `unparseable` | error | File could not be parsed as YAML/JSON |
| `not-a-mapping` | error | Instance is not a mapping for the target class |
| `placeholder-value` | warning | `TBD`/`N/A`/`?` instead of an answer |
| `empty-value` | warning | Empty string value |
| `missing-identifier` | warning | `title`/`name`/`description` missing or empty |
| `british-spelling` | warning | British spelling in prose |
| `empty-section` | warning | An always-applicable section (identification, motivation, composition, uses, distribution) with no answered questions |

### CI recipe

Gate pull requests on datasheet validity with a job like this (no
repository checkout of `data-sheets-schema` needed beyond the schema
itself — point `--schema-file` at a pinned copy, or install the package):

```yaml
- name: Validate datasheets
  run: |
    pip install "linkml==1.9.3" "linkml-runtime==1.9.4" click pyyaml
    python -m data_sheets_schema.cli validate \
      --schema core --format json --output d4d-report.json \
      datasheets/*.yaml
    # or, with the d4d entrypoint installed:
    # d4d validate --schema core --fail-on-warning datasheets/*.yaml
```

## Recommended Starting Points

- `poetry run d4d --help` for the top-level command list
- `poetry run d4d utils status --quick` for a quick pipeline sanity check
- `poetry run d4d download preprocess --project AI_READI` to start working on one project
- `poetry run d4d evaluate presence --project AI_READI --method gpt5` to generate evaluation output
