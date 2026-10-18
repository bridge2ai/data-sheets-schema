# Explicit Dataset API result contract (#4630)

The legacy transformation API can now retain provenance while publishing a
closed Dataset. Callers must select `result_contract="dataset_v1"`; the default
remains `"legacy"`, and `preserve_provenance` still defaults to `True`.

```python
from pathlib import Path
from src.transformation.transform_api import SemanticTransformer, TransformationConfig

transformer = SemanticTransformer(TransformationConfig(
    mapping_file=Path("path/to/reviewed-mapping.tsv"),
    result_contract="dataset_v1",
))
result = transformer.rocrate_to_d4d("input.json", output_path="dataset.yaml")
dataset = result.data
metadata = result.transformation_metadata
published_sha256 = metadata["publication"]["sha256"]
```

`path/to/reviewed-mapping.tsv` stands for an explicitly selected table that maps
the given source to valid Dataset fields, including its required `id`. The
current default `d4d_rocrate_mapping_v2_semantic.tsv` does not map `Dataset.id`;
it remains unchanged and cannot publish a Dataset through this API. There is no
automatic switch to another table or mapper. Other legacy TSV mappings can also
produce invalid Dataset candidates.
The publication gate refuses those candidates and retains the original files.
This contract does not repair mappings, select scientific criteria, reclassify
SKOS relationships, or count retired rows as increased coverage. Issues
[#4594](https://github.com/bridge2ai/data-sheets-schema/issues/4594) and
[#2915](https://github.com/bridge2ai/data-sheets-schema/issues/2915) remain open.

## Compatibility and explicit selection

| Operation | Default `legacy` draft | Explicit `dataset_v1` |
| --- | --- | --- |
| Single | Existing `TransformationResult`; provenance embedded in `.data` and aliased by `.transformation_metadata` | Same dataclass fields; `.data` contains the mapped Dataset candidate, `.transformation_metadata` is separate |
| Merge | `{"d4d": ..., "merge_report": ...}` | `{"format": "d4d_transformation_result_v1", "data": ..., "transformation_metadata": ..., "merge_report": ...}` |
| Batch | List of existing result objects | List of result objects using the explicit contract |

`rocrate_to_d4d` and `merge_rocrates` also accept a keyword-only
`result_contract="dataset_v1"` override. It does not mutate the transformer's
configuration. `transform_rocrate_file` and `batch_transform_rocrates` accept the
same keyword-only selector. Unsupported selectors fail before source parsing or
publication.

The convenience and batch helpers additionally accept a keyword-only
`mapping_file=Path(...)` (or string path). Omitting it preserves the existing
default table. For example:

```python
from src.transformation.transform_api import transform_rocrate_file, batch_transform_rocrates

result = transform_rocrate_file("input.json", "dataset.yaml",
    result_contract="dataset_v1", mapping_file="path/to/reviewed-mapping.tsv")
results = batch_transform_rocrates("inputs", "outputs",
    result_contract="dataset_v1", mapping_file="path/to/reviewed-mapping.tsv")
```

The selected table is the table read by the existing loader, pinned in the
returned metadata, and protected from replacement by any output. This closes the
wrapper selection gap in [#4635](https://github.com/bridge2ai/data-sheets-schema/issues/4635)
without repairing the default table under #4594.

No-output calls remain drafts: they do not acquire the required file-publication
schema check. Their separate metadata has `"publication": null`, so a draft does
not claim to be an accepted or published Dataset. Optional validation behavior is
unchanged. `preserve_provenance=False` leaves `.transformation_metadata` (or the
merge envelope field) as `None`, including after publication; no provenance field
is reintroduced to hold a publication hash.

Legacy no-output shapes and the legacy `v2_semantic` metadata string remain
unchanged. Legacy file publication with embedded metadata continues to refuse it:
`transformation_metadata` is not a Dataset field. The refusal now points to the
explicit selector. The opt-in path never removes unknown mapped fields: a real
mapping to `transformation_metadata` or any other unsupported slot still fails the
required Dataset gate.

## Evidence carried by the opt-in metadata

The separate metadata retains source(s), time, profile declaration and existing
coverage information. For single transformations, `.mapping_version` and the
metadata's `mapping_version` are `sha256:<digest>`, where the digest identifies the
TSV bytes captured before and after the existing mapping loader read them.
`mapping` records the resolved path, SHA256 and byte count. The file is checked
again before returning a draft, before publication and before returning a
published result. A changed or unavailable mapping requires a fresh transformer.
These are local byte checks, not algorithm authentication, an atomic filesystem
snapshot, or proof against concurrent changes that restore the same bytes.

Merge metadata uses `configured_merge_strategy` to identify the legacy config
declaration, since that value is not passed as a global strategy to the existing
per-field merger. `source_order` lists the actual ranked parser order separately
from the caller's `sources`. The existing textual merge report is unchanged.

After successful publication, preserved metadata contains:

```json
{
  "publication": {
    "format": "d4d_dataset_publication_v1",
    "path": "/resolved/path/dataset.yaml",
    "sha256": "<SHA256 of the actual published bytes>",
    "bytes": 123,
    "encoding": "utf-8",
    "root_class": "Dataset"
  }
}
```

The shared [publication gate](../../src/data_sheets_schema/legacy_publication.py)
serializes the candidate once, checks that exact representation and validates it
against the closed Dataset schema. The publisher writes those bytes. The API
checks that the destination matches them and hashes them without reserializing
the result. This includes a configured encoding such as UTF-16. The hash describes
the file at return time; mutating the returned object or editing the file later
does not update that historical binding.

The batch path still validates all roots and prepares every candidate before
publishing any output. A later schema-invalid candidate leaves earlier
destinations untouched. Publication stages all files before individual atomic
replacements; it is not a rollback transaction across several destinations if
the filesystem fails during replacement. Existing source/mapping/schema
protection and optional-validation refusals remain in force.

## CLI result output

The API script accepts the selector and `--mapping` after `transform`, `batch`
or `merge`. Replace the example input and mapping paths with a compatible source
and a reviewed table that produces a valid Dataset; these are caller-selected
paths, not replacement mappings distributed by this change:

```bash
uv run python src/transformation/transform_api.py transform input.json dataset.yaml \
  --result-contract dataset_v1 --mapping path/to/reviewed-mapping.tsv > result.json
uv run python src/transformation/transform_api.py batch inputs outputs \
  --result-contract dataset_v1 --mapping path/to/reviewed-mapping.tsv > batch-results.json
uv run python src/transformation/transform_api.py merge merged.yaml first.json second.json \
  --result-contract dataset_v1 --mapping path/to/reviewed-mapping.tsv > merge-result.json
```

The requested output files remain Dataset YAML. Only opted-in CLI stdout becomes
JSON; construction/validation/progress text goes to stderr. Single JSON contains
`format="d4d_transformation_result_v1"` plus the existing dataclass fields. Batch
JSON has the same `format` and a `results` list of those dataclass representations.
Merge JSON is the versioned merge envelope described above. Keeping this JSON
preserves the separate provenance; no automatic sidecar or new multi-file
transaction is implied. Other RO-Crate CLI wrappers keep their existing formats.

## Validation scope

Focused tests cover real mapped records, single/merge/batch entry points, retained
legacy draft shapes, explicit provenance disabling, exact UTF-8/UTF-16 publication
hashes, mapping drift, invalid mapped fields, late batch refusals and parseable
CLI JSON with explicitly selected mappings and actual configuration. Default
table/legacy contract refusals and selected-mapping output protection are also
covered. The existing required publication tests continue to exercise closed
Dataset validation and protected artifacts.

## Recorded validation result

The coordinator's serialized nine-module run passed **319 tests**, with zero
failures, errors or skips. The terminal summary reported 58.14 seconds and 14
dependency deprecation warnings; JUnit records 58.107 seconds and does not encode
the warning count. No applications or tests were rerun to prepare this evidence.

- Tested commit: `2cfbfa016291b5f80be28abef1faed8fb4af693e`.
- Tested tree: `dc405c72723c8da5f5d868e6161e272cc723687d`.
- JUnit: `legacy-envelope-tests-01.xml`, 52,182 bytes, SHA-256
  `cec2c725a1f8f1c06c69c9cd16d50fe575bf5450ca52e31ae0362e996edb09f8`.
- [validation.json](validation.json) pins nine production/dependency files, two
  resources and all nine test modules. Each hash was checked against both the
  tested commit blob and the working file bytes during evidence preparation.

| Test module | Passed |
| --- | ---: |
| `tests.test_rocrate.test_legacy_result_contract` | 19 |
| `tests.test_rocrate.test_legacy_envelope_adversarial` | 28 |
| `tests.test_rocrate.test_legacy_publication` | 51 |
| `tests.test_rocrate.test_legacy_publication_adversarial` | 39 |
| `tests.test_rocrate.test_legacy_root_gates` | 30 |
| `tests.test_rocrate.test_production_root_gates` | 104 |
| `tests.test_rocrate.test_transform_api` | 3 |
| `tests.test_cli.test_rocrate_cli` | 27 |
| `tests.test_fairscape_integration.test_rocrate_merger` | 18 |
| Total | 319 |

These results exercise synthetic mapped records and existing software regression
fixtures with the real packaged closed Dataset schema. The positive publication
controls use explicit compatible mappings. They do not establish that the unchanged
default TSV, a real project's mapping interpretation, or a current generation is
valid. The default table still lacks required `Dataset.id`, and default legacy
publication with embedded metadata still refuses; migration is explicit.

The tested tree includes required publication gate commit
`9c8b73ee7d0be062aff2532b2a9bd64ba73702e5` from
[PR #4634](https://github.com/bridge2ai/data-sheets-schema/pull/4634), which was
still open when this evidence was captured. The result-contract PR depends on
that change and addresses only #4630/#4635. Parents #4594/#2915 remain open.
No real-project replay, fresh comparison publication, provider run or scientific
score was produced. Human review, paid-run authorization, audit28 and held figure
decisions remain unchanged; moving metadata is not increased source coverage.
