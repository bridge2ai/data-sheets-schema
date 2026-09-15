# Codex Adversarial Review

Target: working tree diff
Verdict: needs-attention

Renderer v8 introduces unpinned request-setting dependencies that break historical verification after configuration changes. No scientific acceptance is inferred.

Findings:
- [high] Pin renderer v8's request settings in the render spec (src/data_sheets_schema/api_runner.py:1085-1086)
  The new transformation reads temperature, temperature applicability, and reasoning effort from live `_model_settings()`, but `render_spec()` stores none of them and `from_render_spec()` does not restore them. Changing only configured effort or an applicable temperature therefore changes a historical v8 instruction's hash. `runs.verify_request()` re-renders using that live configuration and can report `mismatch` against unchanged prompt files; backfill-spec likewise cannot recover the original hash. The new replay test keeps the same monkeypatched settings throughout, so it misses this failure.
  Recommendation: Freeze the header-producing settings from the execution settings, serialize them in v8 render specs, and restore them during replay. Add a synthetic regression that changes live temperature and effort after recording the spec and verifies identical replay bytes.

Next steps:
- Fix settings persistence and verify replay under changed live configuration using synthetic fixtures.
