# One-call schema admission attribution

This is an unexecuted external diagnostic. It calls the current real `_schema` exactly once, with the actual merged `FULL_SCHEMA_PATH` and a genuine captured snapshot. Imports and the initial capture run before measurement. No catalog cache is passed. No function wrappers, synthetic schemas, ontology calls, pytest fixtures or full pipeline runs are used.

The target is confirmed from the literal API constant and pinned before/after. The long node selects it through `tests/test_shared_generation_runtime.py:45`, `tests/test_evidence_generation_gate.py:18`, `tests/test_shared_generation_selection.py:41`, and `typed_audit_runtime.prepare_packet`. The merged source is 1,442,513 bytes in this freeze.

Root-only invocation, after review and with no other project runtime:

```sh
/private/tmp/d4d-performance-implementation-20261012/.venv/bin/python /private/tmp/d4d-agent-performance-20261012-vq8rgbu9/implementation/schema-admission-profile01/profile_schema_once.py --output /private/tmp/d4d-agent-performance-20261012-vq8rgbu9/implementation/schema-admission-profile01-results
```

Output must be new and external. The driver disables bytecode writes and verifies loaded project origins. It saves raw `schema.prof`, cumulative/top and module-filtered `functions.txt`, all function/caller rows in `functions.json`, plus `summary.json` with source/schema pins, package metadata, output catalog digest and wall/thread CPU. cProfile function times use its default elapsed timer and overlap; profiling overhead makes this attribution, not an uninstrumented speed comparison. A call exception is saved and produces exit 1. Initial import/capture failure terminates before the measured-call summary.

The key question is admission versus catalog work. `_read` currently performs a pure SafeLoader event pass through `nesting_exceeds`, a second pure `_UniqueLoader` parse/construction and graph validation. The profile should distinguish those from closure replay and `_build_schema_catalog`/`captured_view`/`version_document`. Do not sum nested cumulative times or infer the entire `_schema` exclusive duration is removable catalog work.

Next implementation is conditional on that evidence. A broad CSafeLoader replacement is not equivalent: `duplicate_keys.py` documents real tab/BOM/grammar and depth/error differences. A one-call checked-event replay into the existing composer/constructor may remove the second parser pass while keeping depth-before-composition error ordering; that remains an unimplemented candidate requiring malformed/deep/duplicate-anchor/alias/merge/duplicate-key and value-type controls. The existing catalog patch remains frozen and uncommitted; no additional cache or admission weakening is proposed.
