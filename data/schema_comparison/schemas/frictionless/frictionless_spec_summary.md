# Frictionless Data Package Specification Summary

## Core Definition
The Data Package specification defines "a simple container format for describing a coherent collection of data in a single 'package'" that facilitates dataset delivery, installation, and management.

## Essential Components

**Required Structure:**
A Data Package consists of two main parts:
1. A descriptor file (`datapackage.json`) containing metadata
2. Data resources (files, remote URLs, or inline data)

**Descriptor Requirements:**
The descriptor must be valid JSON with a `resources` property that "MUST be an array of objects" following the Data Resource specification.

## Key Metadata Fields

**Required:**
- `resources`: Array of at least one resource object

**Strongly Recommended:**
- `name`: URL-friendly, lowercase identifier (alphanumeric with dots, underscores, hyphens)
- `id`: Globally unique identifier (UUID or DOI format)
- `licenses`: Array of license objects with `name` and/or `path` properties
- `profile`: Identifies descriptor profile type

**Optional Common Fields:**
- `title`: Single-sentence description
- `description`: Markdown-formatted overview
- `version`: Semantic versioning string
- `sources`: Data origin references with title, path, email
- `contributors`: Team members with roles (author, publisher, maintainer, wrangler)
- `keywords`: Search terms
- `created`: RFC3339-formatted timestamp
- `homepage`: Related web URL
- `image`: Visual representation (URL or relative path)

## Example Structure
```json
{
  "name": "package-identifier",
  "title": "Description",
  "licenses": [{...}],
  "resources": [{...}]
}
```

The specification explicitly allows custom properties beyond those defined, enabling community-specific extensions.
