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
pinned? As of 2026-09-09: **191 records drifted, 86 current, 0 with no hash
recorded in the live corpus** (64/12/82 when #452 was filed; 136/41/82 on
2026-09-03; 19 archived records under `data/ATTIC/` record `bundle_md5:
null` with no `bundle_sha256`, so this proof cannot reach them — outside
`CONCAT_DIR`, not visited, not a backlog; the
mojibake repair #874 rewrote the AI_READI and CM4AI bundles and the
docx/accent fixes #921 the AI_READI, VOICE and VOICE_PEDIATRIC ones;
CHORUS has not changed since #421). The 82 records that predated md5
recording carried `inputs.bundle_sha256` of the bytes they read, and
`d4d provenance backfill-bundle-md5` (#1121) recovered each md5 from the
committed bundle version whose sha256 equals it — all 82 the 2026-07-28
version — writing `inputs.bundle_md5_basis` to say so. Not from
`repo.commit`: those runs read bundles regenerated in a dirty tree, and
the bytes at the recorded commit are an older version the run never
read. The search refuses a shallow clone (`git rev-parse
--is-shallow-repository`): CI checks out one commit, and a one-commit
history would report every earlier version's record as unrecoverable. The test
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
`source_caveats` at any depth, and ids minted on the record's own id (#722)
or — receipts instrument **v2**, #1123 — on any identifier the record
carries for the dataset at its top level: its `id` in CURIE or resolver
form, its bare `doi`, its landing `page` (trailing slash and DOI case
aside). The v5 rule licenses a label "on an identifier the evidence *does*
supply", and a record taking the landing-page option must not lose
coverage for it. A fragment on any other base — a component dataset's DOI
under `resources`, a project homepage the record does not carry as its
page — is a claim about that identifier and stays receiptable. The block
names its `instrument`, and `slots.exempt_on_carried_identifier` counts
what v2 exempts that v1's byte-for-byte own-id test did not: 4 leaves in
the corpus, all CHORUS API v7 records, and every one of them the record's
own top-level `id` (`https://chorus4ai.org/#chorus-dataset` on `page:
https://chorus4ai.org/`) — so the exemption reaches the record's own
identity slot, and a bare site root declared as `page` exempts every
fragment on that root under the same scheme. One of the four had a receipt
(coverage 59/170 → 58/169); three had none (never-receipted fell by one,
coverage rose). The file-collections case the issue names exists only in
the withheld AI_READI 2026-09-01 rep1 record. The recompute reached 29
records; the 18 receipted records whose bundle has drifted are withheld by
the #907 guard and stay under v1 (#1140). v9 R8 still tells the model a
landing-page label "needs a receipt like any other value" — the cost v2
removes; #1147 rotates that sentence.
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
it (#961). A `both` row on a slot the core class does not declare
(`citation`, `consent_revocations`, …) is read as written — the
instruction defines `both` as present in both — and the finding names
the cause so the regate can fix the row (`claims_core_cannot_hold` counts
those the full record does carry, apart from substantive contradictions;
#990/#992); the block carries
`instrument` from v2 (#996) and, from v4 (#1122), `rows_by_record` — the
dispositions rows tallied by their record column (`full`, `core`, `both`,
`either` for an empty cell, `no_record_column` for a table that has none —
a report format that names no record, "not measurable" rather than "no
`both` rows"; two v2 reports do name one — `invalid` for anything else),
because a `both` row wrongly flipped to
`full` resolves against the full record only and raises nothing, so the
count, or the rate over the row total, is what a reader compares. Over the
18 v8-labelled API records — the 12-record fill plus six canaries — it is
617 `both` of 682 (90.5%); the fill alone is 419 of 461 (90.9%); the five
rows on slots the core cannot hold are all on the VOICE 2026-09-04d canary.
The recorded tally is the post-regate reading, and the regate is the step
that flips rows — `report_gate` carries `rows_by_record_before`/`_after` on
runs made since #1122. Since #998 the report phase carries the core
class's top-level slot inventory (`core_inventory_block`) before its
instruction, so the model can see which slots the core declares rather
than infer it from the carried core record, where an empty slot and an
undeclared one look the same; the gate is unchanged — it judges presence
in the two records, and the declaration decides only whether a finding
carries the "core class declares no such slot" cause (every report
finding on the v8 fill was of that class). `ASSEMBLY_LAYOUT` names it, so
the assembly digest moves; no v9 record predates it, and the v8 labels
already carry three assembly digests (2026-09-04 rep1; b/c/d; e/f/g), so
a v8 run was not comparable with the fill before this either. Residual: a run whose report phase completed under the pre-E
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
**Duplicate mapping keys** (#1029) are a validation failure read off the
record's text — `safe_load` keeps the last value and validates that, so
the AI_READI 2026-09-04f record's three top-level `source_caveats`
passed as one — recorded under `validation.duplicate_keys` per artifact
and gated against a floor of 0 as a count of distinct duplicated keys
(none of the 270 full records of the model-written arms, nor their
cores, had one); the repair round is told what to merge like any other
validation failure, `d4d provenance recheck-validation` brings an earlier
record under the instrument, `d4d api verdict` re-verdicts it
offline with the gate's own functions, keeping the prior block under
`prior_verdict`, and `d4d runs check` reports such records without
failing `--strict`, which gates attestation, not validity (#1035). Since
#1020 the batch writes the verdict it acts on to the record at the gate
(`canary`, `recorded_by: d4d api batch`), the same block shape the offline
command writes; a dropped stream leaves a bounded snapshot under
`intermediate/{P}_{phase}_incomplete_attempt{N}_{n}.txt` and an `api_usage`
row with `outcome: stream ended without message_stop` (#1017); the
`outputs.*.bytes` are re-read at record write, after repair and the regate
(#1021); `repo.dirty_paths` names the paths a dirty tree differed in
(#1023). The
AI_READI 2026-09-04f record is the one such record in the corpus:
declared invalid by its own block, kept as evidence, not retained.

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
they attested when the pair or the pack has since changed (#969). A `reviewed_at` that is a date with no time, one at exactly midnight
(indistinguishable from a date, reported as that), one that does not
parse, or none at all is **reported, never failed** by `d4d review check`
and `d4d review agree` (#1057): the judgements are attested by hash, and
only when they were made is unrecoverable. 15 of the 47 reviews on disk
carry one (14 a datetime at exactly midnight, one no value) — on the v6
and v7 reviews and their second ratings (7 of 17 and 6 of 18) and two of
the twelve v8 ones; every review is made by the same agentic subagent
whichever runtime generated the record.

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

## Id slots in the review pack (#803, #901)

The pack's `id_slots` block lists every populated `…id` leaf with `forced`
(the schema declares that class's id an identifier or required — `File`,
`FileCollection`, `DataSubset`, `Person`, `Software`) and, from
`pack_version` 5, `origin`: `minted` (a urn, or a fragment on the record's
own id in any form), `stated` (a reference used as written — DOI, ROR,
URL), or `constructed` — a fragment on a base the record did not mint,
with `base` and `base_in_bundle` (the base in the bytes the record read,
as itself and in written or alias form; null on a drift or a missing
md5, with `bundle_state` naming why); the block also carries the
record's own `record_id`. The `d4d-review-record` agent judges the
fragment rule on mints and constructed ids, a forced one never violates
it, and `stated` entries are the evidence rules' business. The two-way flag filed the AI_READI 2026-09-01 rep1
`file_collections[*].id` (`https://fairhub.io/datasets/3#cardiac_ecg`, the
attested fairhub page plus a label) with the DOIs. Corpus-wide the
classifier finds 953 constructed ids in 57 of 281 records — 800 of them
schema-forced (`File`, `FileCollection`, `DataSubset`, `Person`, `Software`), most on
the dataset's own DOI or landing page — so the reading matters: the rule
licenses a fragment on an identifier the evidence supplies, and a
constructed id on the dataset's own attested identifier is judged exactly
as a mint (forced never violates; unforced must be pointed at), one on
another entity's identifier is the false claim the identifier rule names,
one whose base is not in the bundle is an unsupported reference.
`base_in_bundle` is attested only against the bytes the record read: the
pack checks the on-disk bundle's md5 against `inputs.bundle_md5` and on a
drift — 35 of those 57 records, the AI_READI rep1 record among them —
reports `null` with `bundle_state` naming it. The match is the base as
itself, not as the prefix of a longer URL, in written or alias form.

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
have since drifted. British spellings are instrument **v4** (#1006; v3
#836/#859): the form blocks of all 282 records were recomputed under it in
the same change and now carry `british_instrument`; v2 numbers in earlier
notes are not comparable (see #906 for the canary consequence). v4 admits
labourers, honourably, millilitres, micrometres, paediatricians,
haematopoietic, sulphide and grey — forms the Codex review of #1003 found
the v3 patterns could not see. None of the eight occurs in any record; the
patterns they widened do (`haematocrit` 19, `microlitre` 15, `micrometres`
12, `nanometres` 6 — 52 occurrences), and 18 records moved on those, none
of them a gate baseline or a record carrying a canary block (the v7
production arm stays 139 and 2026-08-22c 88); the v6 agentic arm reads 49
(47 under v3). A surname Grey is counted like the Temerty Centre is — the
count is a fact about the text — and the normaliser leaves it as written
only inside a title-case run ("Jane Grey", "Grey Institute"); a bare
`family_name: Grey` or "led by Grey" is rewritten and logged under
`british_rewrites`, and `d4d review disposition --amend` restores it.

## Proving which agent definition a subagent read (#1077)

An edit to `.claude/agents/*.md` does not always reach a subagent spawned
afterwards. On 2026-09-08 the #1059 threshold was written and verified on
disk and the next evaluator reported the pre-edit criteria verbatim, while an
earlier batch the same session did pick up its edit — intermittent, which is
worse than consistent: a rescore can silently measure the old instrument and
nothing in the output says so.

`instrument_sha256` (#1099) does not detect this. The agent computes it by
reading the file from disk, which is current, while the definition it was
handed may be stale; the two agree even when the run is wrong.

```bash
d4d agents preamble --agent d4d-rubric10-semantic   # prepend to the spawn prompt
d4d agents check-echo --agent d4d-rubric10-semantic --reply -   # exit 1 if stale
d4d agents digest                                   # the pin each output records
```

The preamble names a **section** of the definition and the **opening
words** of one sentence in it, and asks the agent to quote that sentence in
full. The sentence itself is withheld: the first version printed it, so
`preamble | check-echo` returned a tick and a stale agent that copied the
prompt passed the check it exists to fail (#1102). The expected text lives
only in the verifier. The second version asked for the section's *longest*
sentence while the verifier held the longest fresh *line*; on the
review-record definition the sentence carrying that line ranked 2nd of 38,
so an agent that answered exactly as asked was told to stop (#1145). The
question and the answer are now the same unit, and a fenced block is never
prose.

That text is chosen by being **verifiably absent from the previous version**
of the file — not by being long (replayed against the real incident,
`8813c8e6` against `119e3171`, the longest line is a paragraph both versions
share) and not by appearing in a diff (a reformat "changes" a shared line).
`tests/test_agent_pin.py` pins both the replay and the reformat case.

Where a definition carries nothing its predecessor lacked — or nothing that
can be named by its opening words without handing over more than half the
sentence (#1145) — `preamble` and `check-echo` **exit non-zero** rather than
issue a question that cannot fail; `digest` marks those definitions. A check that cannot fail is worse than no
check, because it is reported as a pass.

**What a pass does and does not prove.** A refusal is strong evidence: the
agent could not produce text that is in the definition on disk. A pass is
weaker — it shows the reply contains that text, which an agent with the
current definition can do and a stale one cannot, but it does not
independently establish which file the runtime loaded. Do not describe a pass
as having verified the subagent's definition; describe it as the subagent
having quoted the current text.

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

**A record states its condition** (#1094): `run.condition` is what the run
claims, from the strongest source available and `run.condition_basis`
says which — stated by the runner (`d4d api run --condition`, `d4d
provenance record --condition`; a `d4d api` run given no `--condition`
uses `generic` and does *not* call that a statement), else the prompt
file the record hashes (the bytes the run consumed — 15 #420 records are
labelled v3 and hashed v1), else the label (an assertion by whoever typed
it). `d4d runs check` fails under `--strict` on a record whose stated
condition the hashed prompt, the label, or the registry contradicts, and
reports one that nothing can check. `d4d api run|batch` refuse before
any spend when the label names a condition the run would not use
(`--allow-condition-mismatch` records the mismatch as declared — the label
is the weakest source, so `runs check` reports a declared label
disagreement and does not fail it; a hashed-prompt or registry
disagreement always fails). A label names a condition only as a
delimited registered token: `generic-v99` before v99 is registered, or a
label naming two conditions, names none. Before this
the field `arm_confounds` compared was a top-level key no record had, so
it compared "None" with "None" and never reported a condition difference;
`arm_facts` now reads `run.condition`, else the hashed prompt, else the
label, and `compare-arms` reads the same field. Labels that name no
registered condition (the 2026-07-27 series — the one `runs.py` calls the
tuned arm, whose records hash no prompt and so cannot attest it — and the
crate/healthsheet arms) still read `None` unless their records hash a
condition prompt. The `full` phase's output cap is a procedure field too
(`full max_tokens`, #771): three of the five v7 canaries ran at 96k and
two at 128k with nothing reading it, so `compare-arms` now reports a cap
that is not constant within an arm and `arm_confounds` one that differs
between arms — read from the `full` rows of `api_usage` (every distinct
cap they carry: the rows are what each call sent, and a resumed run keeps
its earlier rows), else from `model.max_tokens_by_phase`, which is
recomputed at record write; an agentic record carries no per-phase cap
(54 carry `shared_config.max_tokens: 16000`, a config assertion like the
`temperature` beside it, not the runtime's cap) and is skipped like an
absent reviewer.

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

⚠️ **The agentic path writes no reasoning log of its own** (#400): a Claude
Code subagent has no access to its own token accounting, and a log carrying
only the effort level would look comparable with the API path's and is not.
**Its transcript does carry a measure** (#1000, 2026-09-04): usage per turn
(`output_tokens`), signed thinking blocks (empty in the sampled generation
transcripts, text in some others — the observer records
`thinking_text_chars` either way), and — in transcripts written by recent
Claude Code versions — `usage.output_tokens_details.thinking_tokens`. `scripts/agentic_observed.py`
now emits `assistant_turns`, `output_tokens`, `thinking_blocks`,
`thinking_text_chars`, `visible_text_chars`, `tool_input_chars`,
`reasoning_tokens_estimate` (output tokens minus a 4-chars-per-token
estimate of the text *and the tool-call payloads*, which in an agentic
transcript are most of the visible output — the datasheet itself is a
Write; #1011) and, where any turn carries it, `thinking_tokens` /
`turns_with_thinking_tokens`; `d4d provenance annotate-observed` records
them under `phase_log.run_observed`, and `d4d provenance reasoning` reports
such a run as `recovered_from_transcript`. Cache-inclusive orchestrator
accounting, one number per run: the same subtraction as the API log's
estimate, on a runtime whose output is mostly tool payloads, so an upper
bound rather than a like-for-like figure; never averaged with `api_usage`. Existing agentic records carry the older
`run_observed` shape until re-annotated from their transcripts.

So the command distinguishes four empty cases rather than printing one message
for all of them:

| status | meaning |
|---|---|
| `recovered_from_transcript` | agentic run whose `run_observed` carries the transcript's measure |
| `runtime_cannot_capture` | agentic run with no such measure recorded |
| `capture_postdates_run` | API run before capture; unrecoverable |
| `missing` | API run after capture with no log — a **defect**, not a limit |

**Any comparison of reasoning spend between the arms is one-sided.** A run with
no log has not spent zero reasoning; it has no measurement. Do not average the
two, and do not read an absent figure for the agentic arm as a low one.

⚠️ **Through CBORG the reasoning text is not available.** Verified 2026-07-29 on
`google/claude-opus-5-high` and again 2026-09-04: the thinking block arrives
with a valid `signature` and `thinking: ''`, both streaming and non-streaming.
The proxy forwards the signed envelope and strips the plaintext. The logs
therefore record `reasoning_present: true, reasoning_available: false` — a
deliberately different claim from "no reasoning happened". Runs made directly
against the Anthropic API (`ANTHROPIC_API_KEY`) capture the text with no code
change.

**The count is available since 2026-09-04** (#999): CBORG returns
`usage.output_tokens_details.thinking_tokens` in the non-streaming body and
on the stream's `message_delta` usage. The SDK's `get_final_message()` drops
it, so the runner reads it off the delta event and each log entry and
`api_usage` entry carries `reasoning_tokens_observed` / `thinking_tokens`
beside `reasoning_tokens_estimate` (output tokens minus a 4-chars-per-token
estimate of the visible text), with `estimate_error` where both exist. The
estimate stays for the records that predate the count and for comparison
across them; it is sound for comparison, not for cost attribution.

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
id (`doi:10.1/x#person-jane-parker` from the mapping's `name`, else from the
address) with the address kept in `email`, for `id`s inside Person-ranged
slots only; every `mailto:` id it leaves is logged as skipped, under
`normalisation.mailto_ids` — the v8 prompt's R5 says the same, and a person
whose ORCID the documents list is a review matter (rule-03), not the
normaliser's. Since #1002 (v8 step J) British
forms in prose are rewritten to American, one rule per pattern of the
form block's instrument (v4 since #1006), double-quoted spans and identifier-shaped
tokens (`://`, `/`, `@`, `:x`, `.x` inside a token) left as written, keys
and the `#` header untouched; each rewrite is logged under
`normalisation.british_spellings` by phase and slot, so the model's own
count is on record while the canary's British row becomes, on the API
path only (the agentic runtime writes no normaliser), an invariant for
what the normaliser does not cover. The form count sums full + core and
counts a skip; `british_occurrences` logs each rewrite once — the VOICE
canary's 8 is `british_occurrences` 4. A Capitalised match in a
title-case run ("Temerty Centre for …", a real institution the VOICE
bundle names) or a genus name is left as written and logged under
`british_skipped`; a lower-case proper noun is rewritten, and `d4d
review disposition --amend` restores it (#1004). The undeclared-prefix counter is
instrument **v3** (#982): `ark:` excluded, `mailto:` excluded on a Person's id
only and counted anywhere else, `urn:` by NID; the form block records
`prefix_instrument`.

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
