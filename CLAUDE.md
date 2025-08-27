# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LinkML schema project for representing "Datasheets for Datasets" - a standardized way to document datasets inspired by electronic component datasheets. The project creates structured schemas for the 50+ questions and topics outlined in the original Datasheets for Datasets paper by Gebru et al.

## Development Commands

This project uses Poetry for dependency management and Make for build automation:

### Setup and Installation
```bash
make setup          # Initial setup (run this first)
make install        # Install dependencies only
poetry install      # Alternative direct poetry install
```

### Testing and Validation
```bash
make test           # Run all tests (schema validation, Python tests, examples)
make test-schema    # Test schema validation only
make test-python    # Run Python unit tests only
make test-examples  # Test example data validation
make lint           # Run LinkML schema linting
```

### Building and Generation
```bash
make all            # Generate all project artifacts
make gen-project    # Generate Python datamodel, JSON schema, OWL, etc.
make gen-examples   # Copy example data to examples/ directory
make gendoc         # Generate documentation
```

### Documentation and Site
```bash
make site           # Build complete site (gen-project + gendoc)
make serve          # Serve documentation locally
make testdoc        # Build docs and serve locally
make deploy         # Deploy site to GitHub Pages
```

## Architecture and Structure

### Core Schema Files
- `src/data_sheets_schema/schema/data_sheets_schema.yaml` - Main LinkML schema
- `src/data_sheets_schema/schema/modules/` - Modular schema components for different D4D sections:
  - `D4D_Motivation.yaml` - Dataset motivation questions
  - `D4D_Composition.yaml` - Dataset composition questions  
  - `D4D_Collection.yaml` - Data collection process questions
  - `D4D_Preprocessing.yaml` - Data preprocessing questions
  - `D4D_Uses.yaml` - Recommended uses questions
  - `D4D_Distribution.yaml` - Distribution questions
  - `D4D_Maintenance.yaml` - Maintenance questions
  - `D4D_Human.yaml` - Human subjects questions
  - Additional modules for ethics, governance, etc.

### Generated Artifacts
- `src/data_sheets_schema/datamodel/` - Auto-generated Python datamodel classes
- `project/` - Generated schemas in multiple formats (JSON Schema, OWL, SHACL, etc.)
- `docs/` - Generated documentation site

### Key Configuration
- `about.yaml` - Project metadata and configuration
- `pyproject.toml` - Poetry dependencies and build configuration
- `Makefile` - Build automation and commands

## Schema Development Workflow

1. Edit schema files in `src/data_sheets_schema/schema/`
2. Run `make test-schema` to validate changes
3. Run `make gen-project` to regenerate Python datamodel and other artifacts
4. Run `make test` to validate everything works
5. Run `make gendoc` to update documentation

## Working with Modules

The schema is modularized by D4D sections. Each module contains:
- YAML schema definition with classes and slots
- Text file with question descriptions
- Separate files allow focused editing of specific D4D topic areas

## Testing Strategy

- Schema validation ensures LinkML schema is valid
- Python unit tests in `tests/` directory test generated datamodel
- Example validation tests ensure sample data conforms to schema
- Use `poetry run python -m unittest discover` for direct Python test execution

## Important Notes

- Do not edit files in `project/` or `src/data_sheets_schema/datamodel/` - these are auto-generated
- The main schema imports standards schemas for reusable components
- Poetry manages all dependencies - use Poetry commands rather than pip
- LinkML generates multiple output formats from single YAML schema source