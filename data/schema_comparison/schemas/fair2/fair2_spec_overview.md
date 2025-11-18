# FAIR² Specification Overview

## Core Definition
FAIR² extends the original FAIR principles by making datasets "AI-ready, context-rich, and machine-actionable." The framework ensures datasets are structured for ML workflows while including rich metadata for provenance and responsible AI alignment.

## Key Extensions Beyond FAIR

The specification adds four primary enhancements:

1. **Context-Rich Metadata** – Domain-specific annotations compatible with ML Croissant and Schema.org, including licensing and ethical context documentation

2. **AI-Ready Design** – Uses JSON-LD/RDF for machine-actionable metadata with SHACL validation and QUDT unit definitions for interpretability

3. **Responsible AI Alignment** – Incorporates transparency documentation about biases and limitations using the Croissant RAI vocabulary

4. **Contributor Attribution** – Implements CRediT and CRO ontologies to track "dataset lineage using the PROV-O standard"

## Croissant Integration

FAIR² builds directly on ML Croissant by:
- Adding SHACL validation for structural enforcement
- Introducing AI-specific metadata for training data and preprocessing
- Integrating ethical governance metadata aligned with responsible AI practices
- Supporting scientific units through QUDT vocabulary
- Maintaining full backward compatibility with existing Croissant specifications

## Technical Implementation

The framework relies on JSON-LD, RDF, SHACL validation, Schema.org semantics, and persistent identifiers for findability and machine readability.
