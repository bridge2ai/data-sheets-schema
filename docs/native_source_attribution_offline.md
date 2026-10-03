# Native attribution draft preflight: offline condition

The optional `native_source_attribution_version=1` supplements Claude Code native renderers
16–23 with a source-attribution draft check before the final evidence check.
Its policy and exact command are part of the request identity. Historical
requests omit the axis; their prompt, render-spec and assembly bytes remain
unchanged. Renderer 24, API runtimes and Codex CLI cannot select this v1 supplement;
its offline event adapter uses the Claude Code Read/Write/Bash event contract.

This delivery prepares and verifies **offline registrations only**. Execution
is unsupported pending independently reviewed controller integration. The old
direct launcher rejects these registrations; neither the registration nor a
passing verification authorizes a canary, another paid turn or a stopped
attempt's continuation. #2427 remains open for those steps.

## Prepare a new offline registration

Use the same Python environment and checkout for preparation and verification:

```bash
python -m data_sheets_schema.native_attribution_registration prepare \
  --project EXAMPLE --method claudecode_direct --label neutral_preflight_example \
  --bundle /absolute/path/bundle.txt \
  --chunk-manifest /absolute/path/chunks.yaml \
  --source-manifest /absolute/path/sources.yaml \
  --render-version 16 --run-date 2026-10-02 --max-draft-checks 3 \
  --output-directory /absolute/path/selected-output \
  --out /absolute/path/new-offline-registration.json
```

The example's limit is an explicit selection, not a recommended experimental
setting or a paid budget. Omit `--source-manifest` when none is selected. The
command requires a new output file; it never overwrites an existing one. It
renders the instruction and stores the complete selected spec, policy and
assembly identities, command spelling, working directory, code commit,
checker source-tree hashes and selected input hashes in one registration.
Inputs and checker/prompt drift refuse verification. Registrations can also be
prepared from a saved v1 `--render-spec` with the same explicit date and limit.

The new command uses the selected interpreter and exact full/report/bundle/
chunk-manifest paths. Source-manifest authority is included only when the
selected spec uses it. Source-review attribution lists document filenames;
source IDs belong in source-manifest provenance assertions. The checker gives
diagnostics, never automatic evidence translation or semantic approval.

## Verify a saved native trace offline

```bash
python -m data_sheets_schema.native_attribution_registration verify-history \
  --registration /absolute/path/new-offline-registration.json \
  --events /absolute/path/ordered-native-events.json
```

`events` is a JSON array of captured native message events, with unique
`tool_use`/`tool_result` pairs. A draft result needs an explicit integer exit
code, consistent boolean `is_error`, and the actual checker JSON. Verification
recomputes the checker on the current saved files and binds the selected last
pass to those exact bytes. Model prose is not a checker result. Offline trace
verification does not authenticate the provenance of an event file; the
future controller must capture and preserve the actual events.

A failed draft (exit 1) can precede a report-only correction and another check
within the registered limit. Exit 2, missing/interrupted results, wrong command
arguments, overlapping calls, changed inputs and prior terminal failure cannot
satisfy the gate. Writing and restoring identical report bytes still
invalidates an old pass; a new settled check is required. A delayed older pass
cannot replace a newer failure. Frozen originals, audits, source inputs and
final record files cannot be rewritten as draft corrections.

`draft_gate_passed` verifies only this additional draft obligation. It does not
claim a complete native run, grant command permissions or replace historical
phase, receipt, accounting, removal, schema or terminal evidence checks. The
existing `evidence_assertions` and `source_review` terminal stop rules remain in
force. No controller, registration, prompt asset or old record is backfilled.
