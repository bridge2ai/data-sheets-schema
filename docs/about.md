# About data-sheets-schema

**Repository:** [github.com/bridge2ai/data-sheets-schema](https://github.com/bridge2ai/data-sheets-schema)

## Overview

This project provides a comprehensive LinkML schema implementation of the **Datasheets for Datasets** framework proposed by [Gebru et al. (2021)](https://m-cacm.acm.org/magazines/2021/12/256932-datasheets-for-datasets/fulltext).

### What are Datasheets for Datasets?

Inspired by datasheets used in the electronics industry, Datasheets for Datasets propose that every dataset should be accompanied by documentation that addresses:

- **Motivation**: Why was the dataset created?
- **Composition**: What's in the dataset?
- **Collection**: How was the data collected?
- **Preprocessing**: What preprocessing was performed?
- **Uses**: What should the dataset be used for?
- **Distribution**: How is the dataset distributed?
- **Maintenance**: Who maintains the dataset?
- **Ethics**: What ethical considerations apply?

## Project Details

### Schema Information

- **Name**: data-sheets-schema
- **URI**: https://w3id.org/bridge2ai/data-sheets-schema
- **Version**: See [GitHub releases](https://github.com/bridge2ai/data-sheets-schema/releases)
- **Format**: LinkML (Linked Data Modeling Language)
- **Generated Artifacts**: JSON Schema, OWL, SHACL, Python datamodel, GraphQL

### Schema Statistics

- **76 classes** organized into 13 modules
- **272 unique slots** (properties/attributes)
- **15+ enumerations** with 200+ controlled vocabulary terms
- **10+ ontology integrations**: DUO, AIO, QUDT, B2AI vocabularies, CRediT, DataCite

### Bridge2AI Program

This schema is developed as part of the [NIH Bridge2AI program](https://commonfund.nih.gov/bridge2ai), a $130M initiative to create AI-ready biomedical datasets. The schema supports standardized metadata documentation for four Bridge2AI data generating projects:

- **AI-READI** - Artificial Intelligence Ready and Equitable Atlas for Diabetes Insights
- **CM4AI** - Cell Maps for AI
- **VOICE** - Voice as a Biomarker of Health
- **CHORUS** - Collaborative Hospital Repository Uniting Standards

## Development

### Technology Stack

- **Schema Language**: [LinkML](https://linkml.io/)
- **Documentation**: [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- **Python Package**: Available via Poetry
- **Build System**: Make + LinkML generators

### Key Features

1. **Modular Design**: 13 modules (Motivation, Composition, Collection, Preprocessing, Uses, Distribution, Maintenance, Ethics, Human Subjects, Data Governance, Metadata, Minimal, Variables)

2. **Ontology Integration**:
   - Data Use Ontology (DUO) - 20+ machine-readable permission terms
   - AI Ontology (AIO) - 50+ bias types
   - QUDT - Standardized units of measurement
   - CRediT - 14 contributor roles
   - DataCite - 14 relationship types

3. **Machine-Readable**: Full JSON Schema, OWL, SHACL, and GraphQL generation

4. **AI-Ready**: Comprehensive mapping to [Bridge2AI AI-Readiness criteria](https://www.biorxiv.org/content/10.1101/2024.10.23.619844v4)

### Repository Structure

- **[src/data_sheets_schema/schema/](https://github.com/bridge2ai/data-sheets-schema/tree/main/src/data_sheets_schema/schema)** - LinkML schema source (edit here)
- **[src/data_sheets_schema/datamodel/](https://github.com/bridge2ai/data-sheets-schema/tree/main/src/data_sheets_schema/datamodel)** - Generated Python datamodel
- **[project/](https://github.com/bridge2ai/data-sheets-schema/tree/main/project)** - Generated artifacts (JSON Schema, OWL, SHACL, etc.)
- **[data/](https://github.com/bridge2ai/data-sheets-schema/tree/main/data)** - Example D4D metadata and evaluation data
- **[tests/](https://github.com/bridge2ai/data-sheets-schema/tree/main/tests)** - Python unit tests
- **[docs/](https://github.com/bridge2ai/data-sheets-schema/tree/main/docs)** - Documentation source

## Related Work

- **Google's Data Cards**: [arxiv.org/abs/2204.01075](https://arxiv.org/abs/2204.01075)
- **Augmented Datasheets for Speech**: [doi.org/10.1145/3593013.3594049](https://dl.acm.org/doi/10.1145/3593013.3594049)
- **CheXpert Datasheet Example**: [arxiv.org/abs/2105.03020](https://arxiv.org/abs/2105.03020)
- **GitHub Datasheet Template**: [github.com/fau-masters-collected-works-cgarbin/datasheet-for-dataset-template](https://github.com/fau-masters-collected-works-cgarbin/datasheet-for-dataset-template)

## Credits

This project was created with [linkml-project-cookiecutter](https://github.com/linkml/linkml-project-cookiecutter).

**Lead Institution**: Lawrence Berkeley National Laboratory (LBNL)
**Program**: NIH Bridge2AI Standards Working Group
**Contact**: See [GitHub repository](https://github.com/bridge2ai/data-sheets-schema) for maintainer information

## License

See [LICENSE](https://github.com/bridge2ai/data-sheets-schema/blob/main/LICENSE) in the repository.
