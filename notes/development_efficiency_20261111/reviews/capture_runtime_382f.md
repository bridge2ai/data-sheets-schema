# Independent review of the S382f capture result

Reviewed 2026-11-11, from 05:47:58 through 05:49:49 UTC, by the lead's independent exchange-review agent. Read-only inspection of saved JSON/XML, source and fixture files; no tests, project imports, diagnostic execution or native evidence mutations. Terminal records were present at the 05:48:41 UTC poll.

**Disposition: the fixed software capture canary passed and its owned cleanup is certified by the retained supervisors. No missing required witness or capture blocker was found. Ready for the lead to release one existing `cpu-monitoring` diagnostic against this unchanged composition, with its existing 900-second cap.** This review does not release runtime itself. Reservation within 210 seconds, native generation, and quiet-host performance remain unverified.

## Exact invocation and identity

Evidence root:
`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-capture-recheck-capture-ast-20261111`.

- Source: `382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b`; source worktree still clean at that HEAD when checked.
- WP1 contract: `df9eb421572b3a9ca578adfe1664cd23b372c61f315d6c191d3eba4e57eeda4e`, independently hashed from `wp1-contract-382f0dfd1ce8.json`.
- Composition manifest: `fe782d98b04ce7d35e244cd396c7a341b690a4943962db65d96a627bfdcf3a89`, independently hashed and matching the contract and harness.
- Composed test commit: `78723931aaa803f7a706d565da76953c1e9baad4`, with composition parent equal to the source above. The different test commit in `plan.json` and `source-stability.json` is therefore expected.
- Exact singleton: `tests/test_native_subscription_capture.py::test_genuine_registration_read_capture_for_event_rechecks_live_selection_and_stage_root`. JUnit contains one testcase with this name and classname, zero failures/errors/skips. Suite time is 300.431 seconds; testcase time is 286.671 seconds. The final harness repeats the exact node, source, contract, `capture-recheck` kind, 900-second limit and `source_unchanged: true`.
- Source test SHA256 `5c07a3858e74adbc73d504a9caa68381bcbf93816a410584de57d0715fa23639` matches the harness. The once-only capture claim contains the same source, contract, output and node.

## Normal completion, isolation and prerequisite

The outer record reports 318.631411 seconds; its independent supervisor reports 318.684200 seconds. Both returned zero and report verified cleanup without forced cleanup. The outer reports no timeout, observation errors, observed survivors or post-observer cleanup PIDs, and `observer_joined: true`. The supervisor reports no errors or cleanup errors; its sandbox handoff was admitted and has no errors or observed survivors. The inner outcome likewise returned zero with verified cleanup, no forced cleanup, observation errors or observed survivors. The cutoff record has no events. These are normal completion certificates for the observed owned process tree; the supervisor explicitly excludes never-observed escaped descendants from its claim.

Source stability has equal before/after clean composed HEAD and wrapper/dependency identities. Before/after and nested-child package paths resolve to the exact composed test tree. Safe-path, no-user-site and no-bytecode flags are true, with no editable finders. The only before/after origin-record difference is an extra occurrence of the same composed repository root in `sys_path`; package and FAIRSCAPE origins are unchanged. Both direct and nested sandbox network-bind witnesses report denial. The saved sandbox denies network access and native executable paths, and restricts writes to the invocation output plus the listed device exceptions. Child Git global/system configuration is `/dev/null`, HOME is the fresh invocation directory, and the planned environment has no API-key entry.

The same-contract equivalence prerequisite also has its exact singleton pass: JUnit suite 3.416 seconds; outer 19.526704 seconds and supervisor 19.549595 seconds, normal certified cleanup with no observed survivors/errors. Its recorder remains functional, open call rows and thread stacks are zero, and all guard cases report restoration. Profile hook, monitoring slots and future-thread default are restored. `general_replacement_equivalence` remains false.

## Genuine software path and retained side effects

The reviewed test at source lines 375–450 uses the real registration verifier and real recheck. A first event lookup must match the public capture readback and its expected verifier/claim/recheck trace. The second lookup creates a regular file at the selected stage root between outer claim discovery and the inner recheck, then requires refusal. It also requires both full verification and the narrowed recheck to refuse that resulting state.

The retained fixture agrees with these assertions:

- The registration document is 1,230,391 bytes; its SHA256 is `6213bb26bacadc590fa06b55743cdebf6f302ba91a0043af713b5cddfb085544`, matching its filename and capture binding.
- The sole saved `capture.json` is 2,565 bytes, status `captured`. Its observations are 442 bytes and stdout is 615 bytes, with hashes matching the capture's file manifest. Empty stderr is intentional and matches its recorded zero-byte SHA256.
- `authority/selection.json` names the exact retained `case/fresh-attempt/stages` path. That path is a regular file containing exactly `regular file blocking stage root` followed by a newline: 33 bytes, SHA256 `405979ca545f44c8408dc39bbe50788536dbccb3da5f2bd33702650f1679d565`.

These are genuine software verification/readback calls over a synthetic fixture. The fixture's invented review/subscription/runtime and capture lifecycle records do not prove a native provider call, authenticated quota, execution reservation or completed D4D.

There is intentionally no capture `phase-metrics` directory. An ignored-file-inclusive inventory confirmed its absence. `u3k_metrics_plugin_20261109.py:317–320` selects three other test modules, excluding `test_native_subscription_capture.py`; `native_wp1_validation_20261110.py:269–284` requires the pinned capture harness and exact singleton JUnit, not a measurement file. This does not invalidate the capture result. The draft separate acceptance-summary helper's unconditional measurement requirement was reported to the lead for correction; no capture rerun is warranted for that reporting mismatch.

## Configuration and next check

The private Git config still has its configured hash `8a96cf34356a4adffb3c4cf8f07358fcde3857c9a2ed57a1c15cb9822f329b76`; its original backup remains `95a1f7d19be439847af9384dfe1a1f7678aa0902b1601b24c56cc60d783388b1`. This is the authorized brief hold for lead review, not completed restoration. Keep the source/contract/composition unchanged. If separately released, run only the existing monitoring diagnostic, then the reviewed bounded restoration; otherwise restore and stop. Do not rearm the capture claim or rerun this passing capture.

The next diagnostic must report `reached_reservation_without_effect` and a real non-null reservation boundary within 210 seconds of capture, with the existing 300-second limit and 90-second margin. A passing pytest diagnostic that records `genuine_refusal` does not meet that target. Preserve `unqualified_contended_cpu_diagnostic` and false host/freshness/quiet-host qualification flags even if the functional boundary passes. Detailed artifact checks remain in `native_capture_ast_integration.md`.

## Selected artifact hashes

Hashes below were read directly with `shasum -a 256`; paths are relative to the capture evidence root except the two sibling certificates.

| Artifact | SHA256 |
| --- | --- |
| `pytest.xml` | `6ef0289620dd5c7eb2e4ef2790c720167e69a12b1376b4cc7b284e4dbb68c0ee` |
| `wp1-harness.json` | `29bfae9272ea0395d8cf5ba0a55677a4c7abe0a2f5a6d6de12814f0987d91b71` |
| `outcome.json` | `cc26154ebdb1cb5fd49e6064bd9d1a460a35695ec26bc8ce2f5f676a81594094` |
| `source-stability.json` | `aa6dbf5691f75623606b11779a848c61ff4c9fb4086f857440572247c02b52c9` |
| `origins-before.json` | `d850e70b6fa2321810be734a8bb6eee5ff6dba2b02e50a386ea91254ac3b20d5` |
| `origins-after.json` | `be65c4634e8ac0540254a09b7d20ac1483dba0f72074a1ca0376716adeafaa3b` |
| `subprocess-origins.json` | `5a9325c00a1b906bef2849f736615ff47a88a526a0a645dba51b3860b3cae004` |
| `network.json` | `1a2331680725decdbd9d69efbe5d893d68d58a615b87c34c9cfffb20b6d0621f` |
| `wp1-cutoff.json` | `cdca964db5238b792c32d8f4c2818181045728c72dee854e082e1ff289e0b6b2` |
| Sibling capture `.outer.json` | `88c6cdd5562d165b80085b65179a22d6325ca8da71ea8b201fad6b3b6185249f` |
| Sibling capture `.supervisor.json` | `287991de62da57d8d28dd3e455427dd7833f4a1bffd725568aaf5b4e3e37df9b` |
| Sole fixture `capture.json` | `0b512ee9b41091d5bdd354d2b68500d08bb134fd7bc7097cff745dbbe838c4db` |
