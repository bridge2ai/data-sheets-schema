Executive Order 14168: This repository is under review for potential modification in compliance with Administration directives.

# data-sheets-schema

**📚 [View Documentation & Examples](https://bridge2ai.github.io/data-sheets-schema/) · [CLI Reference](https://bridge2ai.github.io/data-sheets-schema/cli/)**

A LinkML schema for Datasheets for Datasets model as published in [Datasheets for Datasets](https://m-cacm.acm.org/magazines/2021/12/256932-datasheets-for-datasets/fulltext). Inspired by datasheets as used in the electronics and other industries, Gebru et al. proposed that every dataset "be accompanied with a datasheet that documents its motivation, composition, collection process, recommended uses, and so on". To this end the authors create a series of topics and over 50 questions addressing different aspects of datasets, also useful in an AI/ML context. An example of completed datasheet for datasets can be found here:
[Structured dataset documentation: a datasheet for CheXpert](https://arxiv.org/abs/2105.03020)

Google is working with a different model called [Data Cards](https://arxiv.org/abs/2204.01075), which in practice is close to the original Datasheets for Datasets template.

This repository stores a LinkML schema representation for the original Datasheets for Datasets model, representing the topics, sets of questions, and expected entities and fields in the answers (work in progress). Beyond a less structured markdown template for this model (e.g. [template for datasheet for dataset](https://github.com/fau-masters-collected-works-cgarbin/datasheet-for-dataset-template)) we are not aware of any other structured form representing Datasheets for Datasets.

We are also tracking related developments, such as augmented Datasheets for Datasets models as in [Augmented Datasheets for Speech Datasets and Ethical Decision-Making](https://dl.acm.org/doi/10.1145/3593013.3594049).

## Bridge2AI Generating Center Datasheets

Curated comprehensive datasheets for each Bridge2AI data generating project:

* **[AI-READI](https://bridge2ai.github.io/data-sheets-schema/html_output/concatenated/curated/AI_READI_human_readable.html)** - Retinal imaging and diabetes dataset
* **[CM4AI](https://bridge2ai.github.io/data-sheets-schema/html_output/concatenated/curated/CM4AI_human_readable.html)** - Cell maps for AI dataset
* **[VOICE](https://bridge2ai.github.io/data-sheets-schema/html_output/concatenated/curated/VOICE_human_readable.html)** - Voice biomarker dataset
* **[CHORUS](https://bridge2ai.github.io/data-sheets-schema/html_output/concatenated/curated/CHORUS_human_readable.html)** - Health data for underrepresented populations

[View all D4D examples →](https://bridge2ai.github.io/data-sheets-schema/d4d_examples.html)

## D4D-Core Schema (Recommended Entry Point)

The **D4D-Core schema** is the curated, interop-focused subset of D4D — the recommended starting point for new datasheets and for systems that exchange datasheets with RO-Crate / FAIRSCAPE / DCAT consumers. Every slot in d4d-core is paired with a SKOS-aligned external term in the [Semantic Exchange Layer](#semantic-exchange-layer-d4d--ro-crate--fairscape).

| Artifact | Path | Description |
|---|---|---|
| Source schema | [`src/data_sheets_schema/schema/data_sheets_schema_core.yaml`](https://github.com/bridge2ai/data-sheets-schema/blob/main/src/data_sheets_schema/schema/data_sheets_schema_core.yaml) | Core schema entry point (imports `D4D_Core.yaml`) |
| Module | [`src/data_sheets_schema/schema/D4D_Core.yaml`](https://github.com/bridge2ai/data-sheets-schema/blob/main/src/data_sheets_schema/schema/D4D_Core.yaml) | `CoreDataset`, `CoreDatasetCollection`, `CoreDistribution` definitions |
| Merged form | [`src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml`](https://github.com/bridge2ai/data-sheets-schema/blob/main/src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml) | Single-file merged schema (auto-generated) |
| HTML examples | [Bridge2AI generating-center datasheets](#bridge2ai-generating-center-datasheets) (above) | Curated d4d-core renderings |
| Validate / build | `make validate-core`, `make gen-core-schema`, `make lint-core` | Core-schema-only Make targets |

**Scope:** ~95 fields across `CoreDataset`, `CoreDatasetCollection`, `CoreDistribution` and supporting classes (`Person`, `Organization`, `Creator`, `Grant`, `FundingMechanism`). The full schema (`data_sheets_schema.yaml`, ~284 attributes) remains the extended reservoir.

## Semantic Exchange Layer (D4D ↔ RO-Crate / FAIRSCAPE)

The **Semantic Exchange Layer** is the canonical SKOS + SSSOM mapping that lets a D4D datasheet round-trip through RO-Crate, FAIRSCAPE EVI, schema.org, DCAT, and Croissant RAI. All artifacts live in two directories:

| Artifact | Path | Description |
|---|---|---|
| SKOS alignment (authoritative) | [`src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl`](https://github.com/bridge2ai/data-sheets-schema/blob/main/src/data_sheets_schema/semantic_exchange/d4d_rocrate_skos_alignment.ttl) | 100+ `skos:exactMatch` / `closeMatch` / `relatedMatch` triples |
| Semantic SSSOM | [`src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_mapping.tsv`](https://github.com/bridge2ai/data-sheets-schema/blob/main/src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_mapping.tsv) | 19-column SSSOM with json_path / pydantic / interface columns |
| URI SSSOM | [`d4d_rocrate_sssom_uri_mapping.tsv`](https://github.com/bridge2ai/data-sheets-schema/blob/main/src/data_sheets_schema/semantic_exchange/d4d_rocrate_sssom_uri_mapping.tsv) + `_comprehensive.tsv` | Auto-regenerated URI variants |
| Structural SSSOM | [`data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv`](https://github.com/bridge2ai/data-sheets-schema/blob/main/data/semantic_exchange/d4d_rocrate_structural_mapping.sssom.tsv) | sssom-py-compatible 17-column structural mapping |
| Generators | [`src/semantic_exchange/`](https://github.com/bridge2ai/data-sheets-schema/tree/main/src/semantic_exchange) | Scripts that derive the URI/comprehensive/structural variants |
| Tests | [`tests/test_semantic_exchange/`](https://github.com/bridge2ai/data-sheets-schema/tree/main/tests/test_semantic_exchange) + `tests/test_fairscape_integration/` | SSSOM column/structure validation |
| Add a new mapping | `/d4d-add-mapping` Claude Code skill ([command](.claude/commands/d4d-add-mapping.md)) | Schema-driven workflow for new SSSOM rows |

**Build / validate:**

```bash
make gen-sssom-all       # regenerate URI + comprehensive + structural variants
poetry run pytest tests/test_semantic_exchange tests/test_fairscape_integration -v
```

## Repository Structure

Browse the source code repository:

* **[src/data/examples/](https://github.com/bridge2ai/data-sheets-schema/tree/main/src/data/examples)** - example YAML data
* **[project/](https://github.com/bridge2ai/data-sheets-schema/tree/main/project)** - project files (do not edit these)
* **[src/](https://github.com/bridge2ai/data-sheets-schema/tree/main/src)** - source files (edit these)
  * **[src/data_sheets_schema/schema/](https://github.com/bridge2ai/data-sheets-schema/tree/main/src/data_sheets_schema/schema)** - LinkML schema (edit this); `data_sheets_schema_core.yaml` is the d4d-core entry point
  * **[src/data_sheets_schema/semantic_exchange/](https://github.com/bridge2ai/data-sheets-schema/tree/main/src/data_sheets_schema/semantic_exchange)** - canonical SKOS + SSSOM exchange-layer artifacts
  * **[src/data_sheets_schema/datamodel/](https://github.com/bridge2ai/data-sheets-schema/tree/main/src/data_sheets_schema/datamodel)** - generated Python datamodel
  * **[src/semantic_exchange/](https://github.com/bridge2ai/data-sheets-schema/tree/main/src/semantic_exchange)** - SSSOM/SKOS generator scripts
* **[data/semantic_exchange/](https://github.com/bridge2ai/data-sheets-schema/tree/main/data/semantic_exchange)** - structural SSSOM + analysis docs
* **[tests/](https://github.com/bridge2ai/data-sheets-schema/tree/main/tests)** - Python tests (`test_semantic_exchange/`, `test_fairscape_integration/`, …)

## D4D CLI

This branch introduces a unified `d4d` CLI for the Datasheets for Datasets workflow. The command is exposed through Poetry:

```bash
poetry install
poetry run d4d --help
```

After installation you can also invoke it as `d4d`, but `poetry run d4d` is the safest form while developing in the repo.

Most subcommands currently expect a repository checkout because they import repo-local code from `src/` and `.claude/agents/scripts/`.

### Command Groups

The CLI is organized into six top-level groups:

- `d4d download`: fetch, preprocess, and concatenate source materials
- `d4d evaluate`: run presence-based and LLM-based evaluations
- `d4d render`: render datasheets and evaluation outputs to HTML
- `d4d rocrate`: parse, merge, and transform RO-Crate metadata
- `d4d schema`: inspect schema metrics and validate D4D YAML
- `d4d utils`: inspect pipeline status and validate preprocessing output

Full option-by-option documentation is available in the docs site: [CLI Reference](https://bridge2ai.github.io/data-sheets-schema/cli/).

### Common Workflows

Download, preprocess, and concatenate source documents for one project:

```bash
poetry run d4d download sources --project AI_READI
poetry run d4d download preprocess --project AI_READI
poetry run d4d download concatenate --project AI_READI
```

Evaluate generated datasheets:

```bash
poetry run d4d evaluate presence --project AI_READI --method gpt5
poetry run d4d evaluate llm \
  --file data/d4d_concatenated/gpt5/AI_READI_d4d.yaml \
  --project AI_READI \
  --method gpt5 \
  --rubric both
```

Render and validate outputs:

```bash
poetry run d4d render html \
  docs/yaml_output/concatenated/gpt5/AI_READI_d4d.yaml \
  -o /tmp/AI_READI_d4d.html
poetry run d4d render html \
  docs/yaml_output/concatenated/gpt5/AI_READI_d4d.yaml \
  --template linkml \
  -o /tmp/AI_READI_d4d_linkml.html
poetry run d4d render evaluation \
  data/evaluation_llm/rubric10/concatenated/AI_READI_claudecode_agent_evaluation.json \
  -o /tmp/AI_READI_evaluation.html
poetry run d4d schema validate docs/yaml_output/concatenated/gpt5/AI_READI_d4d.yaml
poetry run d4d utils status --quick
```

### Current CLI Notes

- `d4d evaluate llm` requires `ANTHROPIC_API_KEY`.
- `d4d render html --template human-readable` renders a single datasheet YAML file to the exact `--output` path you provide and copies `datasheet-common.css` into the same directory so the HTML remains styled when opened directly.
- `d4d render html --template linkml` renders the same structured input into the more technical LinkML-style HTML view.
- `d4d render evaluation` renders evaluation JSON directly and auto-detects `rubric10` vs `rubric20` unless you specify `--rubric`.
- Evaluation naming is now consistent: if you omit `-o`, rubric10 outputs default to `*_evaluation.html`, while rubric20 outputs default to `*_evaluation_rubric20.html`.
- `d4d render generate-all` is a convenience command that points users to the bulk HTML generation workflow (`make gen-d4d-html`).
- `d4d schema` and `d4d rocrate` rely on helper scripts in `.claude/agents/scripts/`, so running from a repository checkout is important.

## Developer Documentation

<details>
Use the `make` command to generate project artefacts:

* `make all`: make everything
* `make deploy`: deploys site
</details>

## Credits

This project was made with
[linkml-project-cookiecutter](https://github.com/linkml/linkml-project-cookiecutter).
