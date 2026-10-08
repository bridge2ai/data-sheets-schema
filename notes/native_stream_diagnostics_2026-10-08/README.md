# First live-stream refusal diagnostics

Issue [#4682](https://github.com/bridge2ai/data-sheets-schema/issues/4682) adds diagnostic context to the existing native stream refusal. It does not repair or establish the cause of [#4680](https://github.com/bridge2ai/data-sheets-schema/issues/4680). The candidate lineage contains the native implementation; this change is not an integration of that implementation into main.

`read_live_stream` retains its existing physical identity, single-link, extent, append, two-pass byte equality and prior-prefix guards. Every metadata acquisition and byte-read call remains in its original position. A refusal from `_progress` may now carry a private `ValueError` subclass whose arguments are the original error's arguments. The adapter continues to report the original `ValueError: ...` first-stop text.

The optional `stream_diagnostic` object contains only observations already available when that guard failed:

- `kind: native_live_stream_refusal`, `version: 1`;
- stream `role`, exact selected `path`, and `max_bytes`;
- `stage` (`opened`, `before_read`, `after_read`, `final_fd`, or `final_path`), `pass_number` (1 or 2 for read stages, otherwise null), and byte `offset`;
- accepted `opened_extent`, or null if the opening metadata comparison itself refused;
- complete `earlier` and `later` metadata dictionaries already sampled by the reader;
- `previous_prefix` containing its byte count and SHA256, or null when none was supplied.

The exception and adapter retain canonical bytes bounded to 16 KiB. Each report decodes a detached object. There are no raw stream contents, extra observations, retries, sleeps, new writes, altered admission, or changed deadlines. Small context dictionaries are assembled at existing samples; diagnostic serialization runs only after a guard refuses. The exact selected path is retained in the local failure report and should be considered when sharing that report.

Diagnostic serialization or decoding failure falls back to the original refusal or the existing report without this optional field. Only the first failure can supply a diagnostic; a later callback still refuses immediately. Cursor behavior is unchanged: endpoint-acquisition failure advances neither cursor, while a later live recapture failure preserves the cursor updates already completed by endpoint acquisition. Success and unrelated failures do not acquire an invented diagnostic.

The deterministic tests inject metadata schedules into real stream reads, including an equal-size/changed-mtime pair at every sampled stage and a split-field ambiguity. These are synthetic observation controls, not reproductions or explanations of the hosted failure. Existing stream tests retain append success, same-size rewriting, truncation, replacement, hardlink/symlink, prior-prefix and byte-bound controls. Adapter tests exercise the real failure latch, endpoint cursor updates and report path without a native process, controller helper, or provider.

Validation is pending coordinator execution after independent source review. The proposed focused suite is:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. \
  "$PYTHON" -B -m pytest \
  tests/test_native_shared_stream_diagnostics.py \
  tests/test_native_shared_stream_diagnostics_adversarial.py \
  tests/test_native_shared_streams.py \
  tests/test_native_shared_stream_bindings.py \
  tests/test_native_shared_controller.py \
  -q -p no:cacheprovider \
  --basetemp="$EVIDENCE/native-stream-diagnostics-pytest-01" \
  --junitxml="$EVIDENCE/native-stream-diagnostics-tests-01.xml"
```

No native workload, hosted-race reproduction or performance comparison is included. The frozen controller source manifest and its dependencies are unchanged. Issues #4680, #4537 and #4354 remain open for their separate cause, performance and acceptance obligations.
