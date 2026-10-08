# Required validation before legacy publication

This is the bounded publication work in [#4629](https://github.com/bridge2ai/data-sheets-schema/issues/4629),
under [#4594](https://github.com/bridge2ai/data-sheets-schema/issues/4594) and
[#2915](https://github.com/bridge2ai/data-sheets-schema/issues/2915).
The implementation prepares the final YAML once, reads those exact bytes back,
rejects duplicate keys or changed values/types, and validates the resulting
record as a closed `Dataset` with the current packaged full LinkML schema.
Validator or schema unavailability is refusal. No mapped value is repaired,
removed, moved, or inferred by this gate.

The shared boundary is `src/data_sheets_schema/legacy_publication.py`.
Packaged `fairscape-cli transform`/`merge`, the hidden single/merge/auto scripts,
the delegating `d4d rocrate transform` command, and transformation API file
outputs all use it. Standalone Dataset and merge/transformation report helpers
also gate their final Dataset. Merge inputs can be incomplete drafts when the
final merged Dataset is valid. Construction, ranking and no-output-path API
returns keep their existing draft semantics; a returned draft is not thereby
schema validated. Existing API diagnostic result fields retain their optional
diagnostic meaning.

All records in an API batch are constructed and validated before publication
starts. Reports and concatenated intermediates are prepared first too. Auto
mode reads a combined graph through a private temporary input and retains the
intended public source label. Every final file is fully staged before the first
atomic replacement. A validation, rendering, diagnostic or staging failure
preserves existing destinations; staging can create destination directories.
Replacement is atomic **per file**, not a transaction over the complete set:
an operating-system failure after replacements start can leave a partial set.

[#4631](https://github.com/bridge2ai/data-sheets-schema/issues/4631) identified
an input-overwrite path during review. Before staging, the publisher rejects
canonical aliases and ancestor collisions among destinations or with protected
source crates, mapping TSVs and schema inputs. Existing directory destinations
are refused. This is an explicit publication-path check, not a filesystem
sandbox or a claim of protection from concurrent filesystem changes.

## Intentional refusals and work still open

The current default legacy TSV does not map required `Dataset.id`, so a default
legacy command may now refuse a record it previously wrote. Error messages
identify the input/output roles and the failing schema requirement. The
maintained validated converter and static mapper remain separate generation
methods; this gate does not automatically reroute to either one.

The API's default `preserve_provenance=True` inserts `transformation_metadata`
inside the Dataset. That field is schema invalid, so file publication now
refuses it and points to the separate compatibility decision in
[#4630](https://github.com/bridge2ai/data-sheets-schema/issues/4630). The draft and
its metadata remain intact. Valid controls explicitly choose provenance off;
the implementation does not silently change that default or relocate metadata.

`--validate`, `--strict`, `validate=False`, `validate_output=False`, and absence
of the optional `UnifiedValidator` cannot bypass required Dataset validation.
Requested legacy CLI diagnostics and strict checks run before publication too.
The review in [#4632](https://github.com/bridge2ai/data-sheets-schema/issues/4632)
also closes the API path that published after a requested optional diagnostic
returned failure. File outputs and batches now refuse that negative result;
no-output drafts retain their prior diagnostic flags and reporting behavior.

#4594 and #2915 stay open for producer/mapping decisions, the metadata envelope,
current-crate replay, fresh labels, comparison and publication obligations.
Historical records and source bundles are retained. This change claims neither
repaired mapping semantics nor improved source coverage. Retiring rows is not
coverage gain; intact copied text alone does not justify `exactMatch`/`none`.

## Validation plan

No application, test or real-crate replay was run while editing this change.
The coordinator will serialize validation after source and review freeze.

New integration tests call the real packaged/hidden/API entry points with an
explicit source-supplied ID mapping and the actual current Dataset validator.
They cover valid text/list preservation, missing IDs, unknown and malformed
nested fields, all auto strategies, final-merge validation, late invalid batch
members, metadata refusals, configured encoding, optional-validator absence,
strict/diagnostic refusals and existing-file sentinels. Independent adversarial
tests cover typed readback and duplicate keys, header injection, actual closed
schema validation, protected aliases, complete staging and injected I/O failure.

Run the new `test_legacy_publication*.py` modules together with
`test_legacy_root_gates.py`, `test_production_root_gates.py`,
`test_transform_api.py`, `tests/test_cli/test_rocrate_cli.py` and the existing
FAIRSCAPE merger tests. Existing root/member and encoding refusals must remain
earlier than publication. Success fixtures use a genuine ID mapping rather than
an always-accepting validator. No scientific scoring or provider calls belong
to this validation.
