# Croissant Format Specification Summary

## Core Purpose
"Croissant metadata format simplifies how data is used by ML models" by providing standardized vocabulary for dataset attributes across PyTorch, TensorFlow, JAX, and other frameworks.

## Key Components

### Dataset-Level Information
Required properties include `@context`, `@type` (schema.org/Dataset), `dct:conformsTo` (version URL), `description`, `license`, `name`, `url`, `creator`, and `datePublished`. The specification recommends semantic versioning (MAJOR.MINOR.PATCH) following Semantic Versioning 2.0.0.

### Resources Layer
Two resource types describe dataset organization:

**FileObject** - Individual files with properties like `contentUrl`, `encodingFormat`, `contentSize`, and `sha256` checksums for integrity verification.

**FileSet** - Homogeneous collections using glob patterns (`includes`/`excludes`) to specify file groups like image directories within archives.

### RecordSet & Field Structure
RecordSets describe structured records with:
- **Field** elements representing columns or data attributes
- **DataSource** specifications for extraction and transformation
- Support for nested and hierarchical data structures
- Foreign key relationships via `references` property

### ML-Specific Features

**Categorical Data** - Uses `sc:Enumeration` dataType for finite value sets with required `name` field and optional `url` for semantic disambiguation.

**Splits** - Defines training/validation/test partitions using `cr:Split` dataType, enabling selective data loading.

**Labels** - Marked with `cr:Label` dataType for annotation data.

**Bounding Boxes & Segmentation** - `cr:BoundingBox` (4-float arrays) and `cr:SegmentationMask` support polygon or image-based representations.

## JSON-LD Context
The specification provides standardized namespace mappings:
- `sc`: schema.org vocabulary
- `cr`: mlcommons.org/croissant namespace
- `dct`: Dublin Core terms
- `wd`: Wikidata references

This enables compact JSON-LD encoding while maintaining semantic clarity across ML ecosystems.
