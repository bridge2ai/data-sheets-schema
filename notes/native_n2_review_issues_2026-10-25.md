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

## N2-R2: derive the validated caller-side native/API selector boundary

**Priority:** P1 integration / audit correctness. **Found on:**
`2db091164469401d82cb7dd10ffd425658a1351c`.

The recovered native constructor leaves the protected API selector unchanged:
it calls the native validator unconditionally, then skips the final API selector
only under `if not self.native_shared_generation_version`. The specificity
scanner still requires that final API call to be a direct top-level expression.
It therefore cannot derive the current API follow-up tuples and the full scan
raises `ConfigError: shared selector call guards/order changed` rather than
reporting completed scan violations.

**Reproduction:** the unchanged
`tests/test_generation_specificity_skill.py::TestTheExitStatus::test_violations_are_exit_1`
failed at scanner `_delegated_turn_selection`, line 13406, in the preserved
`/private/tmp/d4d-n2-scanner-first-failure.log` (one failure, 57.26 seconds).
The broader frozen unit4 run remains separately recorded by the orchestrator.

**Correction:** recognize only the exact two-statement caller
branch, after proving its unique unconditional same-instance native validator,
finite typed domain and mandatory zero-companion loop. Reuse those facts to
derive native-disabled API tuples. Preserve the old helper-side bypass and
ordinary API constructor modes. Refuse inverted/broadened/duplicated guards,
changed call order or bindings, receiver replacement/escape, reflective mutation,
and mutation after the native zero-axis proof. The constructor's two actual
receiver methods require their exact harmless bodies; an unknown receiver call
cannot inherit that permission.

Focused tests use AST-only copies of the five real input modules, plus a
standalone API constructor. They check every canonical receipt/API tuple and
the adversarial mutations without running discovery, importing generation code
or invoking a provider. Production selectors, protected files, deadlines and
scientific instructions remain unchanged.

The proof admits the existing receipt-registration adapter only through its
exact read-only body/import binding. Constructor properties and methods require
their finite reviewed bodies; arbitrary properties and shadowed declared fields
are refused. This is a bounded source-shape proof, not an interpreter for
arbitrary runtime objects or metaprogramming. Two development runs each passed
four cases and refused the two positive native modes because the new receiver
check was too strict; their logs remain at
`/private/tmp/d4d-n2-scanner-repair-focused.log` and
`/private/tmp/d4d-n2-scanner-repair-focused-r2.log`. They are failed development
runs, not acceptance evidence.

**Disposition:** corrected locally, with independent static review clear.
Verification runs are distinct and are not summed:

| Run | Result | Scope |
| --- | --- | --- |
| Compatibility | 30 passed, 79.72 s, exit 0 | New caller-proof class plus existing native-route, optional and correlated follow-up classes. Predates the final direct-native-field and dataclass-import restrictions. |
| Final source | 14 passed, 99.95 s, exit 0 | Final scanner source, caller-proof and native-route classes. Predates only the causal property's test-fixture correction below. |
| Corrected causal node | 1 passed, 6.00 s, exit 0 | Uses `if spec.evil != False` so the old native-reader rule admits its Compare parent; the new declared-field requirement rejects the side-effecting property. Rechecks the valid API tuples first. This node is part of the 14-case roster, not a fifteenth distinct test. |

Logs and XML are retained in `notes/native_n2_validation_2026-10-25/` as
`scanner-caller-compatibility.{log,xml}`, `scanner-caller-final.{log,xml}` and
`scanner-caller-causal.{log,xml}`. The original unit4 refusal log is preserved as
`scanner-caller-before.log`; the two failed development logs are retained as
`scanner-caller-development-{1,2}.log`.

No full scanner pass, final unit4 suite pass or 900-second runtime acceptance is
claimed by these focused results. The orchestrator owns those subsequent runs
after integrating this local repair; this note does not close a GitHub issue.
