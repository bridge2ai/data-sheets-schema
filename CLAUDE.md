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

## Unified CLI (d4d command)

The project provides a unified CLI via the `d4d` command for common operations:

### Installation
```bash
poetry install          # Installs d4d command
d4d --help              # Show all commands
```

### Utility Commands
```bash
d4d utils status        # Show detailed pipeline status
d4d utils status --quick                      # Compact overview
d4d utils validate-preprocessing              # Check preprocessing quality
```

### Download & Preprocessing
```bash
d4d download sources --project AI_READI       # Download from Google Sheet
d4d download preprocess --project AI_READI    # Preprocess to text
d4d download preprocess                       # Preprocess all projects
d4d download concatenate --project AI_READI   # Concatenate files
```

### Evaluation
```bash
d4d evaluate presence --project AI_READI --method gpt5  # Presence-based
d4d evaluate presence --method claudecode_agent         # All projects
d4d evaluate llm --file path/to/file.yaml --project X --method Y  # LLM quality
```

### RO-Crate Integration
```bash
d4d rocrate parse input.json                          # Parse RO-Crate
d4d rocrate transform input.json -o output.yaml       # Convert to D4D
d4d rocrate merge file1.json file2.json -o merged.json  # Merge RO-Crates
```

### Schema Operations
```bash
d4d schema stats --level 2 --format json              # Schema statistics
d4d schema validate file.yaml                         # Validate D4D YAML
```

### Rendering
```bash
d4d render html input.yaml -o output.html             # Render to HTML
```

### Benefits
- **Auto-validation**: Project/method names validated via click.Choice
- **Consistent interface**: All commands use same patterns
- **Help everywhere**: `--help` on any command/group
- **Constants**: Uses centralized constants from `data_sheets_schema.constants`

### Complete Command Reference
- **d4d utils**: status, validate-preprocessing
- **d4d download**: sources, preprocess, concatenate
- **d4d evaluate**: presence, llm
- **d4d rocrate**: parse, transform, merge
- **d4d schema**: stats, validate
- **d4d render**: html, generate-all

### Backward Compatibility
All existing Makefile targets and standalone scripts continue to work. The CLI is an additive enhancement.

## Architecture

### Core Schema Files
- `src/data_sheets_schema/schema/data_sheets_schema.yaml` - Main schema (imports all modules)
- `src/data_sheets_schema/schema/D4D_Base_import.yaml` - Base classes/slots/enums
- D4D modules (in schema/ directory): `D4D_Motivation.yaml`, `D4D_Composition.yaml`, `D4D_Collection.yaml`, `D4D_Preprocessing.yaml`, `D4D_Uses.yaml`, `D4D_Distribution.yaml`, `D4D_Maintenance.yaml`, `D4D_Human.yaml`, `D4D_Ethics.yaml`, `D4D_Data_Governance.yaml`, `D4D_Metadata.yaml`, `D4D_Minimal.yaml`

### Generated Artifacts (DO NOT EDIT)
- `src/data_sheets_schema/datamodel/` - Python classes
- `project/` - JSON Schema, OWL, SHACL, JSON-LD, GraphQL
- `src/data_sheets_schema/schema/data_sheets_schema_all.yaml` - Merged schema

### Centralized Constants
- `src/data_sheets_schema/constants/` - Project names, methods, paths, modules
  - `projects.py` - PROJECTS list, path helpers
  - `methods.py` - METHODS list (generation methods)
  - `schemas.py` - MODULE_MAP, schema paths
  - `evaluation.py` - Rubric paths, scoring constants

Usage: `from data_sheets_schema.constants import PROJECTS, METHODS`

### Key Configuration
- `about.yaml`, `pyproject.toml`, `Makefile`, `config.env`

## Schema Development Workflow

1. Edit schemas in `src/data_sheets_schema/schema/`
2. `make lint-modules && make test-modules` (fast module validation)
3. `make test-schema` (full validation)
4. `make gen-project` (regenerate artifacts)
5. `make test` (complete validation)

## Testing

### Test Structure
```
tests/
├── test_d4d_full_schema.py     # Schema generation tests
├── test_data.py                # Data validation tests
├── test_renderer.py            # Rendering tests
├── test_schema/                # Schema utility tests
│   └── test_schema_stats.py    # Schema statistics tests (8 tests)
├── test_download/              # Download pipeline tests
├── test_rocrate/               # RO-Crate integration tests
└── test_evaluation/            # Evaluation framework tests
```

### Running Tests
```bash
make test                       # All tests
make test-python                # Python unit tests only
python -m unittest tests.test_schema.test_schema_stats  # Specific test
```

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
| **claudecode_agent** | ✅ Current (v5+) | Production datasheets (agentic runtime; both runtimes through v7) | ⭐⭐⭐⭐⭐ | Fast (parallel) |
| **claudecode_api** | ✅ From generic_v8 (#690) | Production datasheets, API runtime baseline | — | Fast (batch) |
| claudecode_assistant | Alternative | Interactive refinement | ⭐⭐⭐⭐⭐ | Medium |
| claudecode | Legacy | API automation | ⭐⭐⭐ | Medium |
| gpt5 | Comparison | Benchmarking | ⭐⭐ | Slow |
| curated | Comparison | ChatGPT chat arm — **not** a gold standard | ⭐⭐ | Manual paste |

**Key finding**: claudecode_agent outperforms GPT-5 by 3.26× on multi-document synthesis.

⚠️ **`curated` is a misnomer.** Those records were generated through a ChatGPT
chat interface by pasting in the prompt, schema and input docs — they were not
hand-curated and are not a reference. They also document superseded releases
(AI-READI v2.0.0, VOICE v2.0, CM4AI B35XWX v1.4), so scoring current output
against them penalises correct facts as errors. There is no CHORUS record.
**The repository has no gold standard.** See issue #177.

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

## Dataset Scope (what a record is about)

Declared per project in the `scope:` block of
`data/preprocessed/source_manifest.yaml`, not in any prompt or launch message.

```bash
d4d download scope --project VOICE        # show the declaration
d4d download scope --check --strict       # check every record against it
d4d download audit-bundles --strict       # are the derived bundles current?
```

`audit-bundles` rebuilds each derived bundle into a temp file and compares
(#446). Not mtime: `crate_only` and `healthsheet_only` are legitimately older
than the document bundles because they do not derive from them. The crate
bundles embed the document bundle verbatim, and after #421 stripped curator
prose they were not rebuilt — so the de novo arm read 9 curation notes the
baseline arm no longer saw, for a day, with nothing to detect it.

**One layer up, `d4d runs check` reports bundle drift** (#452): does the file at
a record's `inputs.bundle_path` still hash to the `bundle_md5` that record
pinned? As of 2026-09-03: **136 records drifted, 41 current, 82 with no hash
recorded** (64/12/82 when #452 was filed; the mojibake repair #874 rewrote
the AI_READI and CM4AI bundles and the docx/accent fixes #921 the AI_READI,
VOICE and VOICE_PEDIATRIC ones; CHORUS has not changed since #421). The test
that guards this no longer pins the count (#910): every drifted record must
pin a hash some `bundle_hash_history` event in the source manifest names as
its `before`, and every bundle the history names must still hash to its last
event's `after` — a rewrite nobody recorded there is what fails.

The two checks are mirror images. `audit-bundles` asks whether a *bundle* still
matches what its inputs produce; this asks whether a *record's declared input*
still matches what that record consumed. A drifted record is not wrong — it
correctly states the bytes it read — but the path it names no longer resolves
to them, so anyone re-reading its declared input reads something else.

Reported and never fatal, for the same reason as the unobserved-values counter
(#447): these records stay usable, they just cannot be re-derived from the path
they name. #421 caused most of the drift by stripping curator notes and #445
added to it by stripping `verification_url`; **both strips were correct**. The
defect was that the corpus absorbed a corpus-wide input change with no report.

Derived records (`record_mode: derived`) are out of scope by construction: they
consume replicates rather than a bundle and declare `bundle_md5` not-applicable.

Each entry names the `referent_id` and any `related_but_distinct` dataset, with
the slot that carries the relation (`express_as: related_datasets`) and, where
the related dataset's documentation is legitimately in the bundle, the source id
that carries it (`in_bundle`).

**A scope constraint belongs in the manifest, never in the launch text** (#422).
The VOICE run of 2026-08-07 was sent a paragraph naming the project, the
companion pediatric dataset and a file not to read; it worked, and it was per-GC
adaptation that no future dataset inherits and no prompt test can see. The
manifest declaration is checkable (`check_record` catches a record that
identifies itself as a dataset its project declares distinct) and inherited by
any project that declares one.

`--check` reports two things. The **verdict** is on the record's `id`:
`out_of_scope` when a record identifies itself as a dataset its project declares
distinct. Separately and never fatally, it lists values where a related-but-
distinct dataset's identifiers appear **outside** the declared slot (#441) — 32
records place the pediatric release inside VOICE's own `resources`,
`distribution_formats[].access_urls` and `file_collections[].download_url`.
Citing the related dataset's page is legitimate; absorbing it into this
dataset's distribution is not, and the line between them is a judgement the
check surfaces rather than settles.

## Chunk Manifests (receipts substrate, #707)

`data/preprocessed/chunks/{PROJECT}_chunks.yaml` (document bundle) and
`{bundle stem}_chunks.yaml` for every other kind — `_crate_only`,
`_preprocessed_with_crate`, `_healthsheet_only` (#725; a bundle with no
`FILE:` headers is one `<unsegmented>` document) — is a pure function of the
bundle's bytes and a recorded rule (`unit: source-document`, windows
bounded in both lines and bytes, the summary/TOC preamble as its own chunk):
same bytes + same rule = same file, and the chunks' texts concatenate back to
the bundle. A coverage receipt (#708) names these chunk ids; the manifest is
what anchors them to bytes. The manifest names the bundle by basename, so the file — and the sha256
provenance records — is the same wherever the bundle was read from (#713).
`d4d provenance record` writes `inputs.chunks: {path, sha256, rule,
chunk_count}` only when a readable manifest exists for exactly the md5 the
record hashed, and `null` otherwise. `--check` reports `off_rule` for a
manifest that reproduces under a non-default rule (#714) — reproducible, but
not the instrument the other manifests use.

```bash
d4d bundle chunk                     # (re)write every project's manifest
d4d bundle chunk --check --strict    # rebuild under the recorded rule and compare
d4d download audit-bundles           # also reports a stale or missing manifest
```

The byte bound (48,000) is what keeps a chunk readable in one file-tool call
(~25k-token cap, #700); a line count alone does not, since AI_READI has
13k-character lines. A single line above the bound becomes its own chunk
marked `oversize`, and a test fails if a committed manifest has one.

## Coverage Receipts (#708)

`{PROJECT}_coverage_receipt.yaml` beside the core record: one entry per
manifest chunk with a closed status — `extracted` (verbatim `{slot,
snippet}` pairs from *that* chunk), `redundant_with` (relevant, already
receipted from named chunks), `nothing_relevant` (with a reason),
`duplicate_of`. Inverted by slot it is the claim receipt
(`{PROJECT}_receipts.yaml`, each claim naming its derived-core path).

```bash
d4d receipts check --label L --project P [--write] [--strict]
d4d receipts invert --receipt R --full F
```

The validator is deterministic and offline and reports **affirmative
counts** — `chunks N/N reviewed · snippets M/M verified · slots S/T with a
receipt` — written as the `receipts` block of the provenance record (also
by `backfill-checks` and inline at `d4d provenance record`). Snippet outcomes
are verified / mismatched / unchecked; no "relaxed", no editorial `[...]`
stripping (the chunk is the source bytes), and a snippet part shorter than
8 normalised characters attests nothing (#720). A receipt on an *entry*
(`funders[0]`) covers its leaves — that is how a boolean or enum gets one —
but a receipt on a *list* (`funders`) covers only itself (#721). The slot
denominator excludes `conforms_to_schema`/`conforms_to_class`, `notes` and
`source_caveats` at any depth, and ids minted on the record's own id (#722).
Named non-checks: that `nothing_relevant` was true, and that a real snippet
supports its value. `backfill-checks` writes a `receipts` block only where a
receipt exists or the record claims one (#726). Every bundle kind a run may declare has a manifest (#725), so
receipts are checkable on any arm.

**The agentic protocol** (#709, `.claude/commands/d4d-full-core.md` Phase 1):
read the manifest, then per chunk read it with the file tool (never a
shell — the transcript cross-check counts `Read` windows only) and write
its receipt entry before the next chunk. `scripts/agentic_observed.py
--receipt R --manifest M` reports `receipt_chunks_unopened`: chunks marked
reviewed that no read window covers — recorded under `run_observed`.

**The API condition** (#710, `generic_v7`): under `RECEIPT_CONDITIONS` the
cached bundle carries `[cNNN]` marker lines at each manifest chunk's start
(refused if the manifest is absent or stale) and the `full` phase must end
with `--- COVERAGE RECEIPT ---` and the receipt document; a response without
it is retried as unusable. The receipt is written beside the core record
and checked into the provenance record in-process; `receipt_expected` is
true for those conditions. Both the prompt pin and the assembly digest move.
The receipt describes the record the `full` phase wrote: `reconcile_full`
and repair rewrite it afterwards with no receipt route on this path, so
their slots are reported under `slots.without_receipt`, never gated (#742).
A full record with no receipt beside it does not resume past `full`.
**Re-addressing (#952, API path only — the agentic protocol has no
equivalent)**: before the receipt is accepted, an entry whose
`slot` is not a path in the record just written (the `slot_not_in_record`
class `receipts.check` gates on) gets one follow-up turn asking where the
value went; an answer moves the entry only to a path that resolves, `drop`
removes it, anything else is left as written for the gate to count. The
receipt as the model wrote it is kept as `intermediate/{P}_coverage_receipt_as_written.yaml`,
and the `full_readdress` entry in `api_usage` records what was unresolved
before and after. The v8 CM4AI canary stopped on exactly one such entry.
**Report gate (#929, v8 step E, API path only)**: the report phase ends
with a `## Dispositions` table (`| slot | disposition | record | reason |`),
the claim form `report_claims` reads — `removed` rows must be absent,
`retained`/`changed`/`added` rows present (`retention_not_shown`,
`change_not_shown`). The runner checks the report before the run completes
and regenerates it once with the contradictions named (`report_regate`;
the first report is kept as `intermediate/{P}_report_before_regate.md`);
`report_gate` in the record says what was found before and after. **Gate
reading (#684)**: a report with no finding and no readable claim is
vacuous (`canary.report_vacuous`), never a held floor of 0. A run whose
report block says `dispositions_expected` (every run this runner writes)
and is still vacuous is blind — UNMEASURABLE, the receipt precedent; an
earlier record's vacuous row is shown as unmeasured and not gated, so the
arm that defined the gate still satisfies it. The baseline skips vacuous
replicates; a baseline arm whose replicates ran the check and read no
claim, none measuring one (`canary.report_basis`: the v7 production arm for
CHORUS, CM4AI and VOICE; AI_READI measured 0 on rep3), is a floor of 0 with
`baseline_basis` on the row, while a baseline whose checker never ran stays
a missing baseline (#599). A report without the table is regenerated once
like a contradiction; a rewrite that is truncated, drops the table or
carries more contradictions is rolled back to the report as written (#967). The expectation is
recorded on `inputs.dispositions_expected` too, so a backfill cannot drop
it (#961). Residual: a run whose report phase completed under the pre-E
runner and is resumed under this one gets no table and is blind by
construction; no such run exists. `companions` is hashed after the last
phase (#652).

**The gate** (`canary.verdict`): when `inputs.receipt_expected` is true — set
by `d4d provenance record --receipt-expected`, which the receipt-writing
playbook passes — an unchecked receipt is UNMEASURABLE and any unreviewed
chunk, unverified snippet, finding, or vacuous receipt (zero snippets over a
non-empty bundle) is a regression against a floor of 0. A snippet that is
verbatim in the bundle but in a chunk other than the one cited is
`adjacent`/`elsewhere` — reported as "snippets in another chunk", never
gated (#763; ~2% on the v7 API canaries): support holds, attribution
precision is its own number. When false, the
block is not a metric for that run: earlier arms and the API arm before v7
(#710) wrote none, and "no receipt" from them is not a measurement.

## Receipt paths after reconciliation (#899)

A receipt is written against the `full`-phase record; reconciliation then
inserts, splits, reorders and rewrites (#742). With the phase-1 snapshot
(`intermediate/{P}_full.yaml`) the validator, the claims sidecar and the
review pack follow each receipt path to its entry **by identity**
(`receipts.remap_path`: `id`/`name`/… keys, else the unique best overlap of
scalar pairs, else the same index for a keyless entry of the same shape) —
reported as `slots.remapped_by_identity`, with coverage credited at the new
address. A value rewritten *at the same path* after the receipt is
`slots.value_changed_after_receipt` — reported, never gated, coverage left
as it stands; normalisation (`str` → `[str]`) and extension (a dict that
gained keys, a list that gained items) are not rewrites. On the 2026-09-01
arm's 1,412 unique receipt paths: 1,146 unchanged · 184 rewritten in place
(13.0%) · 48 leaves and 17 entries removed · 5 moved · 6 the snapshot never
had · 3 whose index another entry now occupies · 1 ambiguous · 2 unresolved. The pack
shows the reviewer both `value_at_receipt` and the current `value`; items
carry `resolved_path`/`resolution` from `pack_version` 4, and
`pack.receipt_join.basis` is `index` on the agentic path, which writes no
snapshot. **With a snapshot, identity decides**: a path whose entry is gone
(`entry_dropped`, `leaf_dropped`, `ambiguous`) or that the snapshot never
had (`not_in_snapshot` — the model mis-addressed it at phase 1) is never
resolved as written even when another entry now sits at that index; those
are reported as `index_reused_by_another_entry` / `path_not_in_snapshot`
and carry no coverage credit; the gone-entry classes also count under
`reshaped_by_reconcile` (they resolved in the snapshot), a never-present
path does not.
Keyless entries whose only leaves are lists still join by position (#908).

## Method directories and runtime-scoped canonicals (#690, v8 D6)

Through generic_v7 the API and agentic runtimes both wrote under
`claudecode_agent/` and were told apart only by the label (`-api-` /
`-claudecode-`) and `model.agent_runtime` (104 API-runtime and 90 agentic
records there). From generic_v8 the API path's baseline arm writes under
**`claudecode_api/`** (+ `_core`); the crate/healthsheet arms keep their
directories; nothing historical moves (a migration of the old labels is a
filed follow-up). A canonical mark is **scoped to a runtime**: `d4d runs
select` supersedes only prior marks of the winner's runtime (read from
`model.agent_runtime`; `--supersede-all-runtimes` restores the old
behaviour), the `canonical` block records `runtime`, and `canonical_runs`
/ `d4d runs canonical --runtime api|agentic` pick one — a project marked
under both runtimes without a runtime filter is ambiguous and refused, as
two configurations are. The v6 agentic canonicals (2026-08-28 rep1/rep3)
were re-marked beside the v7 API ones.

**The `--method` of every review, receipt, telemetry, evaluate and runs
command defaults to the directory the label lives in** (#934,
`runs.method_for_label`): `claudecode_agent` through v7, `claudecode_api`
for the v8 API baseline. An exact directory wins over prefix matches; with
a project, the directory holding its record is preferred and the one that
exists is the fallback (the receipt check runs before the record, #730). A
label under both families, or under neither, or one also present under a
crate/healthsheet arm, is a click error naming the directories — pass
`--method`. `canary.baseline_for` and `report_basis`
search both directories when given no method and refuse a prefix that
spans them. Not resolved: `agreement.DEFAULT_METHOD` (a script argument)
and `form_defects.attribute` (its callers name the method). `d4d receipts
check --strict` fails on exactly the gate's receipt floors (#881) plus an
expected-but-unchecked receipt, not on wrong-chunk attributions, which are
reported and never gated. A reviewer's `pair_consistency.semantic_review`
and a reviewer's `review.reliability` survive every recomputation of
their block — backfill, the runner's record write, `provenance record`
re-recording and `review check --write` (#856/#973,
`backfill_checks.carry_attestations`) — marked `stale` with the artifacts
they attested when the pair or the pack has since changed (#969).

## Canonical selection with the review (#660)

`d4d runs select` ranks validity → **fewest review adverse verdicts**
(differences ≤ `--review-margin`, default 2, are a tie: a 50-slot sample
carries ±2–3 of binomial noise) → most slots → label. The review rank
applies only when every eligible replicate carries a checked `review` block
(`--ignore-reviews` switches it off), and the `canonical` block records
`reviews_applied`, each candidate's `review_adverse`, and the criterion
text. Under the coverage-only criterion the v7 arm picked the most-adverse
replicate in 3 of 4 projects; under this one AI_READI and VOICE moved to
rep1.

## Review dispositions (#903)

`d4d review disposition --item slot-008 --disposition retain|amend --note …
[--path P --replace OLD --with NEW] --execute` records a curator's answer to
a review finding under `dispositions` in the provenance record. `retain`
documents and leaves the record as generated. `amend` edits the raw record
text (the records are the model's own YAML and no dumper round-trips them),
matching `--replace` across line wrapping, and is proven by the parse:
exactly one leaf changes, at `--path`, by exactly the replacement — then the
check blocks are recomputed and the validation verdict refreshed, all
naming this command. Evaluations that predate an amendment are listed as
predating it, never re-attributed. A generated record edited without an
entry here is indistinguishable from one the generator wrote.

`d4d provenance backfill-checks --blocks form,receipts` restricts a backfill
to the named blocks and computes only those — an instrument revision to one
block must not overwrite a grounding block the run attested on bytes that
have since drifted. British spellings are instrument **v3** (#836/#859):
the form blocks of all 264 records were recomputed under it in the same
change; v2 numbers in earlier notes are not comparable (see #906 for the
canary consequence).

## Canonical Prompt Registry

Each condition's prompt files are pinned by hash in
`src/download/prompts/canonical_hashes.yaml`.

### Stopping a sweep

A running `d4d api batch` **cannot be found by name** — a console-script entry
point runs as `python -c import sys; …` and carries none of its own name, so
`pgrep -f "d4d api"` returns nothing while the sweep is still spending. On
2026-08-11 that cost roughly two hours of unobserved generation after the batch
was reported stopped (#513).

```bash
d4d api status                          # which sweeps are running, and their pids
d4d api stop --label-prefix <prefix>    # stop one; --force for SIGKILL
```

**Never switch branches while a sweep or an agentic run is live** (#795).
Run data is untracked until its data PR merges; committing it on a branch
and checking out `main` removes it from the working tree, and on 2026-08-30
(UTC) a live sweep then regenerated a run under the same label. `d4d api
batch` refuses a run whose core directory (`{method}_core/{label}`) is
tracked on any local or remote-tracking ref but is neither on disk nor
archived under `data/ATTIC/` — once before it spends and again before each
run (`run_guard`); a run removed on purpose looks the same and takes
`--no-branch-guard`. Open data PRs from the branch and merge them before
checking out `main`, or commit data from a separate worktree.

A sweep writes a lock under `data/.run_locks/` naming its pid, label and
projects, and **refuses to start while a live lock holds the same prefix** —
two batches writing one label directory produce a record that is a mixture of
both runs with provenance describing neither. Stopping is safe: each run
resumes from its progress file, so the cost is the unfinished phases of the
current run. `status` reports a stale lock rather than deleting it, because a
lock outliving its process is evidence a sweep died without cleaning up.

```bash
d4d api prompts check --strict          # working tree vs the pins (CI gate)
d4d api prompts pin --file <path> --reason '<why this is the text>'
```

**Editing a prompt file without rotating its pin fails
`tests/test_prompt_registry.py` and blocks `d4d api run`.** That is deliberate:
the edit and the declaration that it is now the condition's canonical text are
two acts, and the second is small enough for a reviewer to read. Commit the
prompt edit before pinning it — a pin records the commit it was taken at and
offers `git show <commit>:<path>` as the audit route, so pinning uncommitted
bytes is refused.

Why it exists (#432): the render gate re-renders a record's spec and compares it
to the recorded instruction, which catches text edited *after* rendering. Text
edited into the prompt file *before* rendering re-renders to itself and reports
`match`. The pin is the only value the file can be checked against. `d4d runs
check` is fatal under `--strict` on `uncanonical` (a prompt that was never
pinned, or a labelled condition whose record hashes no condition prompt at all —
the `cp`-to-another-path bypass, #436) and on `missing` (a pinned path the
record hashed nothing for). `superseded` (pinned once, since rotated),
`unpinned`, and `pre_registry` are reported and not failed.

`pre_registry` is a prompt recovered from git at the run's own commit
(`d4d provenance backfill-prompts`, #399). Those bytes are attested by a
different instrument than the registry and predate it, so calling them
`uncanonical` would put honest recovered evidence in the same bucket as the
`cp`-to-another-path bypass, where the bytes are attested by nothing. Every
recovered hash is reproducible with `git show <commit>:<path>`, and a test
asserts it. **The hash is of the bytes at that commit, never today's** —
`d4d_generic_arm_prompt.md` was edited the day after the 15 runs that name it,
16 lines apart, so today's hash would assert they used a prompt that did not
yet exist.

This is not tamper-proofing. Whoever can edit a prompt can rotate its pin.

## Model Reasoning Capture

**Reasoning effort** is established by the provenance recorder, not by the
prompt header (#397). No generic prompt names it, so records made before this
simply lacked it — 12 of the 2026-08 API runs. Three sources, in order:

1. the model route, where the provider expresses effort as a name suffix
   (`google/claude-opus-5-high`) — recorded as observed. `d4d provenance
   backfill-effort` applies this retroactively; it reports by default and
   writes only under `--execute`, and has already populated the 49 records
   whose route named an effort they did not carry (#448);
2. `d4d provenance record --reasoning-effort <x>` — recorded as asserted by the
   launcher, and still listed under `unverified`;
3. nothing — the field is left absent and the gap is named.

Never write "default", "unspecified" or a guess — `d4d provenance
backfill-effort-basis` removes such a value and names the gap it leaves, rather
than relabelling it (#470). A run that did not choose an
effort is a different claim from a run whose effort is unknown, and neither is
a run at high. The fix lives in the recorder because adding a header line to a
generic prompt would re-baseline that condition for every project and require a
pin rotation.


Each API generation phase and each evidence-scoring judgement writes a
structured reasoning record beside the run's provenance:

```
data/d4d_concatenated/{METHOD}_core/{LABEL}/{PROJECT}_reasoning.jsonl
```

One JSON line per phase (`full`, `core`, `audit`, …) recording whether a
thinking block was returned, whether its text was available, an estimate of the
tokens spent reasoning, and the `stop_reason`.

```bash
d4d provenance reasoning --method claudecode_agent --label 2026-07-29_...
d4d provenance reasoning --path some/log.jsonl
```

⚠️ **The agentic path produces no reasoning log at all, and that is a runtime
limit rather than a gap** (#400). A Claude Code subagent has no access to its
own token accounting. Writing a log carrying only the effort level would be
worse than writing none: `d4d provenance reasoning` would then report something
that looks comparable with the API path's and is not.

So the command distinguishes three empty cases rather than printing one message
for all of them — currently **96 runs whose runtime cannot capture, 6 predating
capture (before 2026-07-31), 0 missing**:

| status | meaning |
|---|---|
| `runtime_cannot_capture` | agentic run; no log can exist |
| `capture_postdates_run` | API run before capture; unrecoverable |
| `missing` | API run after capture with no log — a **defect**, not a limit |

**Any comparison of reasoning spend between the arms is one-sided.** A run with
no log has not spent zero reasoning; it has no measurement. Do not average the
two, and do not read an absent figure for the agentic arm as a low one.

⚠️ **Through CBORG the reasoning text is not available.** Verified 2026-07-29 on
`google/claude-opus-5-high`: the thinking block arrives with a valid
`signature` and `thinking: ''`, both streaming and non-streaming, and the stream
emits no `thinking_delta` events at all. The proxy forwards the signed envelope
and strips the plaintext. The logs therefore record `reasoning_present: true,
reasoning_available: false` — a deliberately different claim from "no reasoning
happened". Runs made directly against the Anthropic API (`ANTHROPIC_API_KEY`)
capture the text with no code change.

Because `output_tokens` bills thinking and visible text together,
`reasoning_tokens_estimate` (output tokens minus a 4-chars-per-token estimate of
the visible text) is the only surviving measure of reasoning effort when the
text is withheld. It is sound for comparison, not for cost attribution.

This is also why `max_tokens` must be sized for the reasoning rather than the
answer — a call can spend its entire budget thinking and return empty text. See
`src/data_sheets_schema/reasoning.py`.

## Write-time normalisation (API runner)

Every record the API runner writes passes through `normalise_record_text`:
temporal values quoted to their range, declared enum aliases rewritten,
scalars in multivalued slots listed, and — since #974 — a resolver URL in a
`uriorcurie` slot rewritten to the CURIE it names (`https://doi.org/10.1/x`
→ `doi:10.1/x`, fragments kept), for the prefixes the schema declares and
the slots whose induced range is `uriorcurie`; a `uri`-ranged slot such as
`download_url` keeps its URL. Each is a mechanism behind a rule the prompt
already states, added when a run broke the rule (#974: the v8 CM4AI
re-canary wrote its own DOI as a URL under `id`, 16 resolver URLs against 0
on every 12-record fill since v5 — five arms, 60 records; two exploratory
canaries were not 0). Text-level, so the `#` provenance header survives;
block scalars are skipped whole and trailing comments kept. Because the
record as written is then clean by construction, the canary's resolver-URL
row is an invariant for forms the normaliser does not cover, and what the
model actually wrote is in the record's `normalisation.identifier_form`
block (occurrences and distinct values by phase and slot). Since #981 a
`mailto:` written as an identifier becomes a fragment on the record's own
id (`doi:10.1/x#person-jane-at-ucsd-edu`) with the address kept in
`email`, for `id`s inside Person-ranged slots only, logged under
`normalisation.mailto_ids` — the v8 prompt's R5 says the same, and a person
whose ORCID the documents list is a review matter (rule-03), not the
normaliser's. The undeclared-prefix counter is
instrument **v3** (#982): `ark:` and `mailto:` excluded, `urn:` by NID; the
form block records `prefix_instrument`.

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
