Read-only review of G2's prepared `scripts/adhoc/g2_collection_type_release_20261110.py` found two path-provenance defects before execution.

1. JSON-LD generated in the staging directory is copied unchanged to the repository. The installed generator emits an absolute file URI for its staging context. That context reference must be relocated to the committed artifact-relative form before copying, as the existing generation helper workflow already does.
2. Default `--bin-dir` resolves the existing virtualenv Python symlink before taking its parent, selecting the Miniforge base bin directory rather than the assigned project virtualenv bin directory. Preserve the logical virtualenv bin path or require the explicitly assigned primary `.venv/bin` and verify it.

Fix these in the helper before generating products. Keep the existing environment and actual repository generator options; no dependency installation or environment redesign is requested.

Completed review also confirmed the generator receives absolute schema input paths, causing `SchemaView` to preserve an absolute `source_file` in merged output. `schema_sync.py:365,408` expects repository-relative source spelling. Run both gen-linkml invocations and gen-project from ROOT with the schema argument relative to ROOT. Relocate only the expected staged JSON-LD context URI to `project/jsonld/data_sheets_schema.context.jsonld`, checking that the expected replacement occurred. Existing generator flags and profile/digest APIs were otherwise verified valid.
