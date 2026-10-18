# Finite FAIRSCAPE forward projections

The forward converter returns a genuine FAIRSCAPE model. Model validity does
not mean that every D4D assertion or its original structure was preserved.
The fifteen fields below now use explicit text projections instead of passing
structured values into incompatible model fields (#4954).

| D4D source | FAIRSCAPE alias | Source shape | Wire shape | Admitted single text member |
| --- | --- | --- | --- | --- |
| `known_limitations` | `rai:dataLimitations` | list | string | `limitation_description`, `description`, `name` |
| `known_biases` | `rai:dataBiases` | list | string | `bias_description`, `description`, `name` |
| `intended_uses` | `rai:dataUseCases` | list | string | `usage_notes`, `description`, `name` |
| `updates` | `rai:dataReleaseMaintenancePlan` | object | string | `update_details`, `description`, `name` |
| `missing_data_documentation` | `rai:dataCollectionMissingData` | list | string | `missing_data_patterns`, `description`, `name` |
| `raw_data_sources` | `rai:dataCollectionRawData` | list | string | `source_description` |
| `collection_timeframes` | `rai:dataCollectionTimeframe` | list | list of strings | `timeframe_details`, `description`, `name` |
| `preprocessing_strategies` | `rai:dataPreprocessingProtocol` | list | list of strings | `preprocessing_details`, `description`, `name` |
| `annotation_analyses` | `rai:dataAnnotationAnalysis` | list | list of strings | `annotation_quality_details`, `description`, `name` |
| `distribution_formats` | `evi:formats` | list | list of strings | `format`, `media_type`, `name` |
| `addressing_gaps` | `d4d:addressingGaps` | list | string | `response`, `description`, `name` |
| `anomalies` | `d4d:dataAnomalies` | list | string | `anomaly_details`, `description`, `name` |
| `content_warnings` | `d4d:contentWarning` | list | string | `description`, `name` |
| `informed_consent` | `d4d:informedConsent` | list | string | `description`, `name` |
| `at_risk_populations` | `d4d:atRiskPopulations` | object | string | `description`, `name` |

An object is admitted only when it has exactly one listed member and that
member's value is an exact string. Even a second equal narrative member, an
explicit null extra member, or an identifier makes the richer object
unsupported. Strings retain their whitespace, newlines, Unicode and empty
values. Dates, booleans, numbers, nested lists and dictionary representations
are never converted into invented narrative text.

For a scalar wire field with a list source, exactly one narrative object is
required. Multiple entries, including duplicates, are omitted; they are not
joined, deduplicated or first-picked. An object-shaped source requires the
object directly. Existing direct scalar strings remain supported and are
labelled as legacy input compatibility, not schema-valid D4D objects.

List wire fields require an outer list. Each immediate narrative object or
legacy string can contribute one value, in original order with duplicates and
empty strings retained. Unsupported units keep their original indices and raw
values in evidence. A mixed list can produce a partial projection. Explicit
`[]` stays `[]`; a nonempty list with no supported units is omitted, not turned
into an invented empty list. A missing key and explicit null both emit no wire
value but have distinct evidence. Null normalization is reported separately
from unsupported non-null omission.

The existing compatibility alias `vulnerable_populations`, when present, wins
over `at_risk_populations`, including when its value is null or unsupported.
Both raw assertions remain visible. Superseded non-null canonical data is
reported as omitted even when the winning alias successfully projects. A
refused projection never falls back to the original invalid pass-through.

## Evidence and warnings

`D4DToFairscapeConverter.route_evidence` returns a detached snapshot. Existing
assertion fields remain; rows for these fields are tagged with
`projection_scope: fairscape-forward-types-v1`. Their `units` preserve each
original `source_index`, pointer, raw value, projection decision and reason,
projected value, and observed final model retention. `projection_index` is the
separate output position for an admitted list value. No raw index is compacted.
A retained projection describes text surviving the model, not equality to the
original object shape.

`projection_summary` contains `omitted`, `partial`, `null_not_emitted` and
`superseded` source-pointer/reason lists, plus `incomplete`, `model_valid` and
`status`. Its scope is these fifteen fields and their one compatibility alias.
An empty omission list does not establish complete conversion of other fields,
file resources, inverse preservation or scientific coverage. `status: complete`
means conversion completed. Failure retains the current rows with failed
status; reuse starts a new conversion and clears earlier results.

The convenience `convert_d4d_to_fairscape` helper keeps its existing
`(model, (valid, errors))` return type. On incomplete projection it emits
`ForwardProjectionWarning` naming omitted or partial source pointers, and says
that raw evidence was not saved. Use the converter instance when full detached
evidence is needed. The validity flag concerns model validity and exact JSON
readback, not complete source preservation.

## Nested collections and JSON readback

FileCollections are emitted as plain schema.org Datasets with the explicit
`https://schema.org/Dataset` type (#4956). The previous compact `Dataset`
spelling denotes the same IRI under this converter's fixed `@vocab`, but the
pinned FAIRSCAPE model dispatches that compact name to its stricter EVI Dataset
class when reading JSON. A file collection does not thereby assert an EVI
Dataset's publication date or format, or that it is itself an RO-Crate.

The converter first retains the existing `ROCrateMetadataElem` validation of
collection fields, including its defaults and invalid-input refusals. It then
transfers all validated alias fields into a genuine `GenericMetadataElem`,
changing only the collection's type spelling. Optional nulls are retained in
that transfer; the existing `exclude_none=True` publication policy still omits
null values. Collection IDs, order, root `hasPart` references and aggregate
metadata remain. The actual root retains its existing RO-Crate type. The
reverse reader recognizes both compact and explicit Dataset types; this does
not add file-resource conversion or an EVI Dataset enumeration guarantee.

Before conversion marks evidence complete, the validated model's Python-mode
dump is checked for nonfinite floats, including ordinary dictionary keys and
values and nested lists, tuples, sets and frozen sets (#4957). This happens
before JSON-mode serialization can silently turn infinity or NaN into null.
It does not scan unrelated caller input, arbitrary attributes or custom
iterators. Finite values and supported date serialization keep their existing
behavior. The resulting readback model receives the same check.

The entire published model is serialized to finite JSON, decoded into
independent objects, and read back by the genuine `ROCrateV1_2` validator.
The resulting JSON tree must retain exact
value types and array order. Object-key ordering is not a byte-preservation
claim. `validate()` performs this same check rather than merely dumping an
already constructed model. Readback or serialization failures leave conversion
evidence failed and propagate the original error; they cannot reach the CLI's
publication step or model-valid success message. Reusing a converter starts
fresh evidence as before.

The forward CLI always writes incomplete-projection warnings to stderr,
including when no report was requested:

```sh
fairscape-cli d4d-to-rocrate dataset.yaml --output crate.json --report projection.json
```

`--report PATH` explicitly saves the complete detached evidence as ASCII-safe
JSON. Without it, the warning says that the raw evidence was not saved. With
no `--output`, stdout contains only the RO-Crate JSON and diagnostics stay on
stderr. Valid partial conversion remains successful, with mandatory warnings;
actual model, serialization and report-write errors remain failures.

Input, output and report collisions, including symlink and existing hardlink
aliases, are refused before writes. The command reuses existing staged
publication: all bytes are prepared and staged before replacement, but OS
errors during replacement can leave a partially published set. It does not
promise a multi-file transaction or reserve paths against another writer.

This outgoing policy leaves reverse `ROUTES`, optional supplied-evidence
identity checks, schemas, model definitions, ranking and scientific decisions
unchanged. Supplied reverse evidence cannot authorize an unsupported
fifteen-field projection. The separate #4044 root/alias/Make concerns and
parent #2915 obligations are not resolved by model-valid output.
