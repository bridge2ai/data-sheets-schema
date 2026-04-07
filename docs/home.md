# Datasheets for Datasets Schema

**📚 View:** [Schema Documentation](index.md) | [CLI Reference](cli.md) | [D4D Examples](d4d_examples.md) | [About](about.md)

A LinkML schema for Datasheets for Datasets model as published in [Datasheets for Datasets](https://m-cacm.acm.org/magazines/2021/12/256932-datasheets-for-datasets/fulltext). Inspired by datasheets as used in the electronics and other industries, Gebru et al. proposed that every dataset "be accompanied with a datasheet that documents its motivation, composition, collection process, recommended uses, and so on".

## Bridge2AI Generating Center Datasheets

Curated comprehensive datasheets for each Bridge2AI data generating project:

* **[AI-READI](html_output/concatenated/curated/AI_READI_human_readable.html)** - Retinal imaging and diabetes dataset
* **[CM4AI](html_output/concatenated/curated/CM4AI_human_readable.html)** - Cell maps for AI dataset
* **[VOICE](html_output/concatenated/curated/VOICE_human_readable.html)** - Voice biomarker dataset
* **[CHORUS](html_output/concatenated/curated/CHORUS_human_readable.html)** - Health data for underrepresented populations

[View all D4D examples →](d4d_examples.md)

## Repository Structure

Browse the source code repository on GitHub:

* **[src/data/examples/](https://github.com/bridge2ai/data-sheets-schema/tree/main/src/data/examples)** - Example data files
* **[project/](https://github.com/bridge2ai/data-sheets-schema/tree/main/project)** - Generated project files (JSON Schema, OWL, SHACL, etc.)
* **[src/](https://github.com/bridge2ai/data-sheets-schema/tree/main/src)** - Source files
  * **[src/data_sheets_schema/schema/](https://github.com/bridge2ai/data-sheets-schema/tree/main/src/data_sheets_schema/schema)** - LinkML schema source (edit here)
  * **[src/data_sheets_schema/datamodel/](https://github.com/bridge2ai/data-sheets-schema/tree/main/src/data_sheets_schema/datamodel)** - Generated Python datamodel
* **[tests/](https://github.com/bridge2ai/data-sheets-schema/tree/main/tests)** - Python tests
* **[data/](https://github.com/bridge2ai/data-sheets-schema/tree/main/data)** - D4D metadata and evaluation data

## Quick Links

- **[Schema Documentation](index.md)** - Complete schema reference (classes, slots, enumerations)
- **[CLI Reference](cli.md)** - Command groups, flags, and workflow examples for `d4d`
- **[D4D Examples](d4d_examples.md)** - View rendered datasheets for Bridge2AI projects
- **[GitHub Repository](https://github.com/bridge2ai/data-sheets-schema)** - Source code and development
- **[Issues](https://github.com/bridge2ai/data-sheets-schema/issues)** - Report bugs or request features

## Related Resources

- **Original Paper**: [Datasheets for Datasets (Gebru et al. 2021)](https://m-cacm.acm.org/magazines/2021/12/256932-datasheets-for-datasets/fulltext)
- **Example**: [Structured dataset documentation: a datasheet for CheXpert](https://arxiv.org/abs/2105.03020)
- **Google's Alternative**: [Data Cards](https://arxiv.org/abs/2204.01075)
- **Augmented Model**: [Augmented Datasheets for Speech Datasets](https://dl.acm.org/doi/10.1145/3593013.3594049)

## About This Project

This repository stores a LinkML schema representation for the original Datasheets for Datasets model, representing the topics, sets of questions, and expected entities and fields in the answers. The schema includes **76 classes**, **272 unique slots**, and comprehensive coverage of:

- **Motivation** - Why was the dataset created?
- **Composition** - What's in the dataset?
- **Collection** - How was data collected?
- **Preprocessing** - What preprocessing was done?
- **Uses** - What should the dataset be used for?
- **Distribution** - How is the dataset distributed?
- **Maintenance** - Who maintains the dataset?
- **Ethics** - What ethical reviews were conducted?
- **Human Subjects** - What protections for human subjects?
- **Data Governance** - How is the data governed?

This project was made with [linkml-project-cookiecutter](https://github.com/linkml/linkml-project-cookiecutter).
