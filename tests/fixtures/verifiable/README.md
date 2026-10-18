# Historical verifiability schema fixture

`historical_full_88142c4.yaml.gz` is a deterministic gzip copy of the existing
public repository file:

- Commit: `88142c4fc0bbc2dea15fd7960ccefc8adc9ee686`
- Path: `src/data_sheets_schema/schema/data_sheets_schema_all.yaml`
- Uncompressed SHA256: `533f561ba3c85a31486ff2ff962be83555a9d81ac57a0891aaf39b411d283f4b`
- Uncompressed bytes: 1,014,047

The regression test verifies this digest and exercises its actual `Grantor`
reference range. Shipping the fixture keeps that test effective in shallow
CI checkouts. It contains schema definitions, no dataset records, source
bundles, evaluation outcomes or audit annotations.
