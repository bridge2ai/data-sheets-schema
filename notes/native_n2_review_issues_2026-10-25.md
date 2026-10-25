# Offline review issue drafts for N2

These are review findings for AGY to file when publishing the local series.
No GitHub request was made from this offline work.

## N2-R1: track the target schema-event parser in native typed catalog reuse

**Priority:** P1 integration correctness. **Found on:** `0d5bddbc0`.

The current target's `_schema_yaml` / `_SchemaEventLoader` parse path is used
when replaying captured schema members. The recovered pre-owner catalog guard
tracked the generalized YAML reader but omitted this target-specific parser
and its retention limits. Replacing `_schema_yaml` after warming a catalog
left `runtime_token()` eligible even though the literal constructor refused.

**Reproduction:** run
`tests/test_native_catalog_target_schema_events.py::test_warm_catalog_preserves_current_schema_event_refusal[reader]`
against `0d5bddbc0` plus the new regression test. The test first confirms that
the literal constructor observes the injected parser refusal, then fails
because the native eligibility token incorrectly remains non-null. The saved
pre-fix test log is `notes/native_n2_validation_2026-10-25/cache-target-parser-before.log`.

**Correction:** add exact `_schema_yaml` and `_SchemaEventLoader` bindings and
both `MAX_SCHEMA_EVENTS` / `MAX_SCHEMA_EVENT_CHARS` values to the closed guard.
Tests cover replaced function identity, changed function code, loader method,
loader class and both constants. The warm typed route must reproduce the
literal constructor's full refusal chain; changed retention limits take the
current constructor and preserve its exact packet bytes. Independent read-only
review confirmed the existing guard already covers the other parser inputs.

**Disposition:** corrected. The parser/dependency/native typed-catalog group
passed **73 tests** in 4.85 seconds, including all six new mutations; log:
`notes/native_n2_validation_2026-10-25/cache-target-parser-after.log`.
No scoring instrument, deadline or production guard is relaxed.
