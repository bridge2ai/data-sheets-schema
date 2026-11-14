# Fixed capture-recheck supervisor adapter

2026-11-11. Local implementation for independent review. Branch `codex/native-capture-recheck-adapter-20261111`, worktree `d4d-executions/codex-native-capture-recheck-adapter-20261111`, base `458887766effe38207a77fea2d8033f1f3e1c7f3`. Sparse local checkout; no environment/corpus copy. Native458887 and tools7043 are unchanged. No integration, private preparation, genuine capture, provider/native execution, push or GitHub action.

## Change and limits

The existing WP1 supervisor admits fixed kind `capture-recheck`, selecting only `tests/test_native_subscription_capture.py::test_genuine_registration_read_capture_for_event_rechecks_live_selection_and_stage_root`, one worker, 900-second ceiling. No arbitrary selector or cap override. Its software-correctness classification keeps every timing/freshness/native-acceptance flag false, even with an otherwise passed qualification witness. It belongs to the no-lease roster, not timing/CPU-comparison arms.

Both outer and supervised entries require the same-manifest certified equivalence canary. The target test file joins the implementation closure. Exclusive source+manifest keyed claims bind the output and fixed node, refusing relabelled retries. This is once per source/manifest, not globally across new identities. Final certification additionally requires matching source/manifest/node/cap/unchanged-source evidence and exactly one JUnit case with the fixed name and module, without failure/error/skip.

Supervisor process ownership, detached child handoff, signal/deadline cleanup, 10/5-second reserves, environment and sandbox algorithms are unchanged. Production driver and all `src/`/protected files are unchanged. `monitoring` remains an environment selection; this target does not exercise the consumer-observer arm. Result refusal sets existing certification false; `cleanup_verified=False` can mean rejected test evidence, not necessarily survivors. Preserve separate process/error witnesses.

## Validation

The committed unit runner reuses `d76_process_deadline_20261102.py`, existing dependency Python, `env -i`, `-S -P -B`, external basetemp, credential allowlist, network denial and write confinement. Fixed synthetic unit selections only; no `make_case`, private composition or native subprocess. Evidence is retained under `d4d-executions/scratch-native-capture-adapter-20261111/`.

| Invocation | Result | Elapsed seconds |
|---|---|---:|
| `canary` | 1 passed | 1.125901 |
| `affected` | 29 passed, 3 failed, 1 deselected | 1.488697 |
| `entry-repair` | 6 passed | 0.837971 |

The three failures were in new outer-entry unit fixtures: their mocked contract returned a manifest path without creating the file needed by final-report hashing. A test-only correction writes that mock file; both entry layers then passed matching/missing/wrong-manifest cases. Original failure evidence is unchanged. All **33 distinct unit cases have passing coverage across invocations**, not a claimed single final 33-pass run. No broad unchanged rerun. Every recorded invocation was under 30 seconds, with normal owned-group termination, no timeout or signals. Separately sessioned descendants were not exercised by these unit checks. `git diff --check` passed.

Commands: `env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python -S -P -B scripts/adhoc/run_capture_adapter_unit_checks_20261111.py` followed by `canary`, `affected`, then `entry-repair`.

## Review finding CAP-UNIT-1 — unit timeout cleanup reserve

Independent read-only review found the new unit runner reserved 10 seconds although existing D76 cleanup allows 5 seconds TERM grace plus 10 seconds reap. This was a helper-budget defect; the short completed runs did not exercise it. Corrected to at most 10 seconds child work with a 20-second reserve and explicit wording: a 30-second acceptance budget, **not an independent outer hard alarm**. The final reserve-only correction was source-reviewed, not rerun. The actual genuine-route 900-second outer hard deadline is unchanged. GitHub filing is pending the lead's publication workflow; this local issue preserves the finding without an unauthorized GitHub write.

Exact reserve correction from the executed helper SHA `c1f99b39e88a2d92d98c0056ac645ea50330e4756d70b0fc366accbe37c153ef`:

```diff
-        limit_seconds=30, cleanup_reserve_seconds=10), indent=2) + '\n')
+        limit_seconds=30, cleanup_reserve_seconds=20,
+        scope='30s acceptance budget; existing D76 cleanup, no independent outer hard alarm'), indent=2) + '\n')
-                           stream=stream, seconds=max(0.1, 20 - (time.monotonic() - began)))
+                           stream=stream, seconds=max(0.1, 10 - (time.monotonic() - began)))
```

Independent review found no additional adapter/entry-wiring blocker. Native runtime acceptance remains untested.

## Artifact SHA-256

| File | SHA-256 |
|---|---|
| `scripts/adhoc/native_wp1_validation_20261110.py` | `a995dba963a2a83d183dbb3fd523462d1fdd51b5a7132be7841c4b90557c0c6e` |
| `scripts/adhoc/native_wp1_quiet_fixture_20261110.py` | `6e2c3575f14d26af0b386a59b33c5f70fd9f19cef1f1e151f57e50df1ee912da` |
| final unit runner | `c6dcb342ccc050472efca914698d9972ffd4737e1b63fcb7b9aee94cb7ad1d52` |
| `tests/test_native_wp1_capture_recheck.py` | `0d3ee39f987b927131af9e8b3296a1e2491de056e35ea7efe9b57dca4f766408` |
| evidence `canary/result.json` | `9e00b6c479936eecd959aae5d7a2d13ce1fb6de225b73f60eaa8b96c4e5b898d` |
| evidence `canary/pytest.xml` | `587eab3ddb1106c4ac4f1f008b6a31b7b08a9cd2de46563b01c51ab6585dbdd8` |
| evidence `affected/result.json` | `43d9ad3e1b383d888bb898a14ed8119c91b5933534d429fe37cb25d158e66f6f` |
| evidence `affected/pytest.xml` | `6066f573ac6dd6ced895f703d876b090b7b414508e45f568c532ddd0f729cd43` |
| evidence `entry-repair/result.json` | `5753404c5b2b77cce4d4e2bf046855238a092c8ac4ac0f5548933946c4e18e21` |
| evidence `entry-repair/pytest.xml` | `1ee70afce6154ce35d4dc450524da481bbfccce0feff59dff3fef6fa475ad761` |

## Stop and handoff

Stop before integrating capture-A `459e56bf896a29d854c5d250ce8632d7e2564427` or AST `89975411d65e42aae5baa2bb92276ad5f9fabf1a`, before private preparation and before the genuine test. The target function is absent at this base; it arrives with capture A. Final integrated source/contract do not yet exist. Same-private-byte packet permission persists; runtime still awaits independent adapter review and final-source release. The genuine 900-second ceiling does not change capture-age or reservation-margin policy.

The attempted direct lead-thread coordination send was rejected by automatic approval review for lack of per-action messaging permission. No message was delivered or relayed through another channel. The specific permission question remains pending; requested local report/STATUS artifacts retain the handoff.
