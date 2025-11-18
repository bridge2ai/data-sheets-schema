# OTDI Dataset Specification Summary

## Core Framework

The Open Trusted Data Initiative (OTDI) establishes a "minimally sufficient" specification for cataloging datasets. The approach builds on established standards including Hugging Face Dataset Cards, MLCommons Croissant metadata format, and the Data Provenance Standard.

## Essential Requirements

**Ownership & Licensing**: Dataset providers must confirm they either own the data or possess rights enabling distribution under the CDLA Permissive 2.0 license. This addresses the complexity of crawled web data with mixed provenance.

**Dataset Card Mandate**: Every dataset requires a standardized card following Hugging Face conventions, functioning as the `README.md` file. As the spec notes, this reflects that "most AI-centric datasets are already likely to be available on the Hugging Face Hub."

**Metadata Structure**: The card contains two components:
- A YAML header block with standardized fields
- Markdown content sections documenting dataset details

## Key Metadata Fields

Required YAML entries include:
- Dataset identifier and description
- License information (permissive licenses preferred)
- Task categories (NLP, audio, vision, tabular, etc.)
- Personal/sensitive information indicators
- Source dataset references

Markdown sections must cover dataset motivation, composition, intended uses, bias/limitations, and ethical considerations.

## Derived Dataset Handling

Derived or synthetic datasets require new cards that reference upstream sources. Critically, "the most restrictive upstream license must be used"—permissive licensing cannot override more restrictive upstream sources.

## Processing Categories

OTDI defines dataset maturity levels:
- **Raw**: Original discovery with validated provenance
- **Filtered**: Processed for quality and content standards
- **Structured**: Reformatted for specific AI applications
- **Derived**: Created from other datasets

This tiered approach enables clear governance tracking throughout data pipelines.
