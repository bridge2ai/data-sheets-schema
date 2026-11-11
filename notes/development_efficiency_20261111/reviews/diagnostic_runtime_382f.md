# Independent review of the S382f monitoring diagnostic

Reviewed read-only on 2026-11-11 from 05:54:08 through 06:09:27 UTC, with approximately 45-second waits between terminal-artifact checks. No test, diagnostic retry, project import, provider call or native evidence mutation was performed by this reviewer.

**Disposition: HOLD. The diagnostic hit its inner deadline and did not produce a functional freshness result. Normal cleanup certification is false. Private Git configuration was separately restored to its original bytes and mode.** This run does not establish reservation within 210 seconds, a genuine stale/margin refusal, native acceptance, or a performance improvement.

Evidence root:
`/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-post-capture-ast-20261111`.

## Actual terminal result

| Layer | Return code | Recorded seconds | Result |
| --- | ---: | ---: | --- |
| Inner outcome | 124 | 881.374580 | `interrupted: deadline`, `forced_cleanup: true`, `cleanup_verified: false`, worker return code -15 |
| Outer | 125 | 894.469324 | `cleanup_verified: false`; observer joined; no observation errors or observed survivors |
| Independent supervisor | 125 | 894.533025 | `cleanup_verified: false`; no errors/cleanup errors; admitted sandbox handoff with no errors or observed survivors |

The outer's `timed_out: false` and `forced_cleanup: false` do not erase the inner deadline and forced cleanup. The cutoff record's empty event list likewise does not certify normal completion. The supervisors finished before the fixed 900-second limit, but the requested diagnostic did not finish. No observed surviving process was reported; the records explicitly exclude never-observed escaped descendants from their ownership claim.

An ignored-file-inclusive inventory of this invocation found no `pytest.xml`, diagnostic JSON, measurement JSON or `origins-after.json`; the existing `phase-metrics` directory is empty and `pytest.log` has zero bytes. Therefore there is no singleton pytest pass, reservation boundary, capture-age-at-check, final freshness return, observer restoration, forbidden-call census, or open-row/thread-stack result to certify. Do not relabel this as `genuine_refusal`: that is a diagnostic result value that was not saved here.

## Identity, policy and retained effects

The final harness records the exact fixed node `tests/test_native_u3k_profile.py::test_neutral_pre_reservation_diagnostic`, `cpu-monitoring`, monitoring consumer observer, control profiling and a 900-second cap. Source is `382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b`. Independently hashed WP1 contract remains `df9eb421572b3a9ca578adfe1664cd23b372c61f315d6c191d3eba4e57eeda4e`; composition manifest remains `fe782d98b04ce7d35e244cd396c7a341b690a4943962db65d96a627bfdcf3a89`. Source worktree remains clean at that HEAD. The harness reports source unchanged, and the source-stability record has equal clean before/after composed HEAD `78723931aaa803f7a706d565da76953c1e9baad4` and dependency identities.

Initial and nested-child package origins match the composed tree, with safe-path/no-user-site/no-bytecode enabled and no editable finders. Direct and nested network-bind witnesses report denial. The saved plan uses isolated HOME and `/dev/null` global/system Git configuration. The missing final origin record prevents a complete before/after origin certification.

The retained synthetic capture and subscription guard agree on timestamp `2026-11-11T06:00:49.992598Z`. The guard still has `max_age_seconds: 300` and `pre_reservation_margin_seconds: 90`. No boundary was saved against which to evaluate the resulting 210-second target. Total invocation elapsed time does not identify the time or cause of a particular freshness check.

The exact paths declared inside the saved registration end in `native-attempt` and `native-evidence`, both beneath `cases/popen-gw0/test_neutral_pre_reservation_d0/u3k-neutral/` in this invocation. Direct `ls -ld` checks found neither path, including no dangling symlink. This confirms their absence after the interruption, not a complete successful no-effects assertion. The preserved fixture is synthetic and supplies no native provider/authenticated-quota evidence.

Classification remains `unqualified_contended_cpu_diagnostic`, with host, wall-time freshness and accepted quiet-host qualification flags all false. No comparison with previous elapsed times or causal speed claim is supported.

## Separate configuration restoration

The reviewed cleanup wrapper recorded `config_restoration_observed`, `timeout: false`, elapsed 2.687280 seconds, exact source/manifest, and helper SHA256 `4a5a483d8260a28713f6eea1ae49708a3c258a3944dbc0a4cf1579a3829a5446`. The composer's `config-restored.json` is dated `2026-11-11T06:08:07.023771+00:00` and records the exact source/manifest, retained worktree and expected helper.

Independent current reads confirm both private config and its backup hash to `95a1f7d19be439847af9384dfe1a1f7678aa0902b1601b24c56cc60d783388b1`, with mode 0644 on both. The restoration record's own hash matches the wrapper's pinned report hash. This directly establishes restored bytes/mode. The wrapper intentionally also requires an externally observed zero exit; its result file alone is not that exit certificate. The owner must retain the command's exit observation. Restoration does not repair the failed diagnostic or certify its descendants.

Stop with these artifacts retained. No retry, capture rearm, new source identity, timing campaign or generation release follows from this result.

## Artifact hashes

Paths are relative to the diagnostic evidence root except sibling certificates and restoration files.

| Artifact | SHA256 |
| --- | --- |
| `outcome.json` | `dd0e2023ffca28468af91f5a080d92f96e6063e3bdf2992b0d9ddc965dfde9ed` |
| `wp1-harness.json` | `72405e1b268a1c92adc0211b188fcba0511c65b58366563b8712cbae3b0a0ebd` |
| `source-stability.json` | `aa6dbf5691f75623606b11779a848c61ff4c9fb4086f857440572247c02b52c9` |
| `origins-before.json` | `3392b49d015f88fcf82fd358c34440cbbd5737c51d5c8e7bc86f7ebaa67bb195` |
| `subprocess-origins.json` | `478f35cb4411af67dca18a1674f52270c8d44e4e9a372bbefcb11f6c23a32c1c` |
| `wp1-cutoff.json` | `7946d24440ac0f7ed026025522bbce400df336880e95778559b02aade1a369e8` |
| Sibling diagnostic `.outer.json` | `6219de74a444d3f054ddf20abd5bc9d5d6dea73d66dd412d262ae07bc28bde15` |
| Sibling diagnostic `.supervisor.json` | `bca0c15bdd444723fcb087b11063b769ac58ff93b97d313969f74d3719880897` |
| Composition `config-restored.json` | `6fe0aadd244ddafef9d1dd900739cf3106f8482fdcfaedacff1186845ed649a5` |
| Cleanup wrapper `result.json` | `8b8908388e5f87c020b927bc513ca11f55b9f71fdf622a29393e1a14db42a28c` |
