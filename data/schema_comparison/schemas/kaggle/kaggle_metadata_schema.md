# Kaggle Dataset Metadata Schema

## Overview
The Kaggle API implements the [Frictionless Data Package specification](https://frictionlessdata.io/specs/data-package/) for dataset metadata. A `dataset-metadata.json` file must accompany uploaded files.

## Core Structure

**Required fields for dataset creation:**
- `title`: 6-50 characters
- `id`: Username/organization slug + unique dataset slug (3-50 chars)
- `licenses`: Exactly one license entry

**Optional fields:**
- `subtitle`: 20-80 characters
- `description`: Dataset overview
- `id_no`: Numeric dataset identifier
- `resources`: File metadata array
- `keywords`: Tags from existing Kaggle taxonomy

## Resources Schema

The `resources` array defines file-level metadata:

```
- path: File location
- description: File explanation
- schema: Field definitions
  - fields: Array of field objects
    - name: Field identifier
    - title: Field description
    - type: Data type specification
```

## Supported Data Types

The specification includes 15+ types: `string`, `boolean`, `integer`, `decimal`, `numeric`, `datetime`, `id`, `uuid`, `email`, `url`, `address`, `city`, `country`, `province`, `postalcode`, `latitude`, `longitude`, `coordinates`.

## Key Constraint

"All fields in data must be included in order or they won't match correctly," indicating schema completeness is critical for proper field alignment during upload.

## Relationship to Frictionless

Kaggle's implementation is a subset of the Frictionless Data Package specification, adding platform-specific constraints like character limits and license requirements.
