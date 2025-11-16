Executive Order 14168: This repository is under review for potential modification in compliance with Administration directives.

# data-sheets-schema

**📚 [View Documentation & Examples](https://bridge2ai.github.io/data-sheets-schema/)**

A LinkML schema for Datasheets for Datasets model as published in [Datasheets for Datasets](https://m-cacm.acm.org/magazines/2021/12/256932-datasheets-for-datasets/fulltext). Inspired by datasheets as used in the electronics and other industries, Gebru et al. proposed that every dataset "be accompanied with a datasheet that documents its motivation, composition, collection process, recommended uses, and so on". To this end the authors create a series of topics and over 50 questions addressing different aspects of datasets, also useful in an AI/ML context. An example of completed datasheet for datasets can be found here:
[Structured dataset documentation: a datasheet for CheXpert](https://arxiv.org/abs/2105.03020)

Google is working with a different model called [Data Cards](https://arxiv.org/abs/2204.01075), which in practice is close to the original Datasheets for Datasets template.

This repository stores a LinkML schema representation for the original Datasheets for Datasets model, representing the topics, sets of questions, and expected entities and fields in the answers (work in progress). Beyond a less structured markdown template for this model (e.g. [template for datasheet for dataset](https://github.com/fau-masters-collected-works-cgarbin/datasheet-for-dataset-template)) we are not aware of any other structured form representing Datasheets for Datasets.

We are also tracking related developments, such as augmented Datasheets for Datasets models as in [Augmented Datasheets for Speech Datasets and Ethical Decision-Making](https://dl.acm.org/doi/10.1145/3593013.3594049).

## Repository Structure

* [examples/](examples/) - example data
* [project/](project/) - project files (do not edit these)
* [src/](src/) - source files (edit these)
  * [data_sheets_schema](src/data_sheets_schema)
    * [schema](src/data_sheets_schema/schema) -- LinkML schema
      (edit this)
    * [datamodel](src/data_sheets_schema/datamodel) -- generated
      Python datamodel
* [tests/](tests/) - Python tests

## D4D Metadata Generation

This repository supports two distinct approaches for generating D4D (Datasheets for Datasets) metadata from dataset documentation:

### Approach 1: Automated LLM API Agents 🤖

**Use when**: You need to batch-process many files automatically with minimal human intervention.

Automated scripts that use LLM APIs (OpenAI/Anthropic) to extract D4D metadata from dataset documentation. These agents run autonomously and can process hundreds of files in batch mode.

#### 1.1 Validated D4D Wrapper (Recommended)

```bash
python src/download/validated_d4d_wrapper.py -i downloads_by_column -o data/extracted_by_column
```

**Features**:
- Validates downloads succeeded
- Checks content relevance to projects
- Generates D4D YAML metadata via GPT-5
- Creates detailed validation reports
- Processes HTML, JSON, PDF, and text files
- Adds generation metadata to YAML headers

**Generated Metadata Includes**:
```yaml
# D4D Metadata extracted from: dataset_page.html
# Column: AI_READI
# Validation: Download ✅ success
# Relevance: ✅ relevant
# Generated: 2025-10-31 14:23:15
# Generator: validated_d4d_wrapper (GPT-5)
# Schema: https://raw.githubusercontent.com/monarch-initiative/ontogpt/main/...
```

#### 1.2 Aurelian D4D Agent (Library Usage)

For integration into Python applications:

```python
from aurelian.agents.d4d.d4d_agent import d4d_agent
from aurelian.agents.d4d.d4d_config import D4DConfig

# Process multiple sources (URLs and local files)
sources = [
    "https://example.com/dataset",
    "/path/to/metadata.json",
    "/path/to/documentation.html"
]

config = D4DConfig()
result = await d4d_agent.run(
    f"Extract metadata from: {', '.join(sources)}",
    deps=config
)

print(result.data)  # D4D YAML output
```

**Supported File Types**: PDF, HTML, JSON, text/markdown (URLs and local files)

#### 1.3 Basic D4D Wrapper (Simpler Version)

```bash
python src/download/d4d_agent_wrapper.py -i downloads_by_column -o data/extracted_by_column
```

Simpler version without validation steps, suitable for clean input data.

**Requirements for API Agents**:
- Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` environment variable
- Wrappers use GPT-5 by default (configurable)
- Files organized in column directories

---

### Approach 2: Interactive Coding Agents 👨‍💻

**Use when**: You need human oversight, domain expertise, or customized metadata extraction.

Use coding assistants like **Claude Code**, **GitHub Copilot**, or **Cursor** to generate D4D metadata interactively. This approach provides human-in-the-loop quality control and domain-specific reasoning.

#### 2.1 Using Claude Code (Recommended)

**Step 1**: Provide the schema and dataset documentation to Claude Code

```
Please generate D4D (Datasheets for Datasets) metadata for the dataset at:
https://example.com/dataset

Use the D4D schema at:
https://raw.githubusercontent.com/monarch-initiative/ontogpt/main/src/ontogpt/templates/data_sheets_schema.yaml

Generate a complete YAML file following the schema structure.
```

**Step 2**: Claude Code will:
- Fetch the dataset documentation
- Analyze the content
- Generate structured D4D YAML
- Include reasoning about field mappings
- Iterate based on your feedback

**Generated Metadata Includes**:
```yaml
# D4D Metadata for: Example Dataset
# Generated: 2025-10-31
# Generator: Claude Code (claude-sonnet-4-5)
# Method: Interactive extraction with human oversight
# Schema: https://raw.githubusercontent.com/monarch-initiative/ontogpt/main/...
# Reviewed by: [Your Name]
```

#### 2.2 Workflow Example

```bash
# 1. Start interactive session with Claude Code
claude-code

# 2. Provide instructions
"Generate D4D metadata for datasets in downloads_by_column/AI_READI/
following the schema at [schema URL]"

# 3. Review and refine
# Claude Code will generate metadata and you can provide feedback:
# - "Add more detail to the preprocessing section"
# - "Include information from the supplementary materials"
# - "Ensure all required fields are populated"

# 4. Save validated output
# Output is saved with generation metadata in YAML header
```

**Benefits of Interactive Approach**:
- ✅ Human oversight and quality control
- ✅ Domain expertise applied to field mapping
- ✅ Iterative refinement based on feedback
- ✅ Reasoning captured in generation process
- ✅ Can handle complex, ambiguous documentation
- ✅ Better handling of edge cases

---

### Comparison: When to Use Each Approach

| Aspect | API Agents 🤖 | Interactive Coding Agents 👨‍💻 |
|--------|---------------|-------------------------------|
| **Speed** | Fast (batch processing) | Slower (interactive) |
| **Scale** | Hundreds of files | Few files at a time |
| **Quality** | Consistent, good | Variable, can be excellent |
| **Human oversight** | Minimal | Full |
| **Cost** | API costs × files | Time + API costs |
| **Best for** | Standardized docs | Complex/ambiguous docs |
| **Customization** | Limited | High |
| **Domain expertise** | Model knowledge only | Human + model knowledge |

### Recommended Workflow

**For large-scale extraction**:
1. Use API agents for initial batch processing
2. Use coding agents to review and refine difficult cases
3. Document any manual corrections

**For high-value datasets**:
1. Use coding agents with human oversight
2. Validate against domain expertise
3. Iterate until metadata is complete

---

### Generation Metadata Standards

Both approaches should include standardized generation metadata in YAML headers:

```yaml
# D4D Metadata for: [Dataset Name]
# Source: [URL or file path]
# Generated: [ISO 8601 timestamp]
# Generator: [Tool name and version/model]
# Method: [automated | interactive | hybrid]
# Schema: [D4D schema URL]
# Validator: [Name/email if human reviewed]
# Notes: [Any relevant generation notes]
```

### Script Locations

- **This repo**: https://github.com/bridge2ai/data-sheets-schema
- **API Agent Scripts**: [src/download/](src/download/)
  - Validated wrapper: `src/download/validated_d4d_wrapper.py`
  - Basic wrapper: `src/download/d4d_agent_wrapper.py`
- **Aurelian D4D Agent**: [aurelian/src/aurelian/agents/d4d/](aurelian/src/aurelian/agents/d4d/)
  - Agent: `d4d_agent.py`
  - Tools: `d4d_tools.py`
  - Config: `d4d_config.py`

## Developer Documentation

<details>
Use the `make` command to generate project artefacts:

* `make all`: make everything
* `make deploy`: deploys site
</details>

## Credits

This project was made with
[linkml-project-cookiecutter](https://github.com/linkml/linkml-project-cookiecutter).
