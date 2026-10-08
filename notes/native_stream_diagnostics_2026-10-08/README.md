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

The independently reviewed implementation passed all **105 focused tests**, with no failures, errors or skips, at commit `d01ef23c37e22137be367a73f252cc74d4a58d73` (tree `b072f25cbcec36306ab8de421beecb3c3f6af21a`). JUnit records 141.224 seconds; the coordinator recorded 141.32 seconds at the console and one dateutil deprecation warning. The recorded interpreter was the existing primary-checkout virtual environment using CPython 3.13.12. These invocation and console observations are coordinator provenance; JUnit does not independently attest the interpreter or tested commit.

| Test module | Passed |
| --- | ---: |
| `test_native_shared_stream_diagnostics.py` | 26 |
| `test_native_shared_stream_diagnostics_adversarial.py` | 15 |
| `test_native_shared_streams.py` | 31 |
| `test_native_shared_stream_bindings.py` | 7 |
| `test_native_shared_controller.py` | 26 |

[validation.json](validation.json) records the complete tested change list, eight selected source pins, five test-module pins, dependency declarations, and the unchanged frozen controller manifest plus all 12 dependency pins. Each selected working file was checked against its tested Git blob. The manifest and its dependencies also match their declared hashes and parent bytes. This is selected source evidence, not a complete installed-environment or import-cache snapshot.

The external JUnit artifact, `native-stream-diagnostic-tests-01.xml`, is 17,180 bytes with SHA256 `7d36cd9da496dad8b3cc60b43ca9f2679a346d13e34f211cb9af69012da1c394`. The coordinator executed the following command from the candidate checkout; `$PYTHON` and `$EVIDENCE` stand for the selected interpreter and external evidence directory:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. \
  "$PYTHON" -B -m pytest \
  tests/test_native_shared_stream_diagnostics.py \
  tests/test_native_shared_stream_diagnostics_adversarial.py \
  tests/test_native_shared_streams.py \
  tests/test_native_shared_stream_bindings.py \
  tests/test_native_shared_controller.py \
  -q -p no:cacheprovider \
  --basetemp="$EVIDENCE/native-stream-diagnostic-pytest-01" \
  --junitxml="$EVIDENCE/native-stream-diagnostic-tests-01.xml"
```

The original retained CI evidence and reviewed verifier remain separately preserved in [PR #4683](https://github.com/bridge2ai/data-sheets-schema/pull/4683). These diagnostics do not alter or reinterpret those historical artifacts. No native workload, hosted-race reproduction or performance comparison is included. Issues #4680, #4537 and #4354 remain open for their separate cause, performance and acceptance obligations; native execution acceptance and scientific eligibility are not established here.
