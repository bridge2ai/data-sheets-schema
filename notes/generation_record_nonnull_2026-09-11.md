**Required provenance values — 2026-09-11 Pacific (#614)**

A required key containing null previously satisfied the generation-record
mode rules because LinkML's unconstrained `AnyBlock` range includes null.
Adding `value_presence: PRESENT` to the source did not fix that compiled
JSON Schema behavior. A live record could therefore carry no model, input
or system block while passing the structural gate.

The record schema now explicitly declares `required_values_non_null: true`.
The shared compiler turns every generated required-key constraint into both
key presence and a non-null value constraint, keeping each mode condition
intact. It derives these constraints from the schema's actual requirements;
there is no second list of required fields in Python.

The runtime validator and `d4d provenance validate-records` use the same
compiled JSON contract. `d4d provenance record-schema` exports it for other
JSON Schema validators. Generic LinkML generation does not implement the
repository annotation; the export states that limitation explicitly. Use
the exported contract or the D4D CLI for the full check. The original
closed-object, enum, range and date/time-format checks remain enabled.

Required live/reconstructed blocks reject null; reconstructed records also
require a non-null unrecoverable-fields value. Derived records require
non-null derivation, sources and not-applicable values. Universal required
blocks such as outputs, software and repository facts also reject null.
Block interiors remain open, including nested nulls and arrays. Optional
blocks remain optional by mode: derived records need no model, and an
unfinished record may still have no validation block (#612).

The CLI continues past malformed files and treats an unavailable validator
as a failed check. Its success message describes the matched records, not
every possible corpus layout; the separate curated-layout issue #616 is
not resolved by this change. No unavailable provenance fact is invented,
and no historical record or score is rewritten.

Regression tests check all mode-specific and universal required fields
against both the runtime and exported schema; optional/null interiors;
format checking; a newly added required block; schema-policy changes;
captured source bytes; and CLI failure behavior. Existing corpus-conformance
and recorder tests are included in validation. The Dataset schema and the
reference evaluation instrument are not changed by this record contract.
