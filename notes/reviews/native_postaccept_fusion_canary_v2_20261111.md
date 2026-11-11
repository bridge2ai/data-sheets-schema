# Corrected fusion canary v2: scripted-peer execution denied

2026-11-11. Exactly one corrected offline singleton was released and executed
at clean `254071e053e7879f543b31d1ea84e8b3ea7dfb78`, helper SHA
`bece6bfc40bcfbfe040f5d1e9d6ebb740f8be215c586327bcf20f90f227c807c` and fixture SHA
`eb0522c4da33b24040cb2e10657b7e97b09a43a51fbf86d19b4c8af043899f96`.
Production/tests equal2fe49f. **The singleton failed.** Git setup succeeded, but
the sandbox denied execution of the fixture's ordinary-Python `durable-copy`.
No launch/reservation acceptance, real native execution or provider call occurred.
No retry, affected group, source/configuration edit or repair was performed.

## Executed command and result

The invocation was the same documented `env -i` command, existing `.venv` Python
with `-S -P -B`, `run_postaccept_fusion_checks_20261111.py canary`, using the fresh
exclusive `d4d-executions/scratch-native-postaccept-fusion-v2-20261111/canary/`.
That output and the quiet-window lock were absent before invocation. The older
failed canary under `scratch-native-postaccept-fusion-20261111/canary` was not
modified; its result, JUnit and process-sample hashes were rechecked unchanged.

| Observation | Result |
|---|---|
| Exact JUnit node | tests.test_native_u4b_a3_reservation.test_deferred_capture_acceptance_exact_order_to_real_reservation |
| JUnit | 1 failure, 0 errors, 0 skips; suite2.144s, testcase0.558s |
| Helper elapsed | **2.8475439170142636s** of30s acceptance budget |
| Deadline owner elapsed/work allowance | 2.8264474580064416s / 9.981620999984443s |
| Owner result | return1, expired=false, signals=[], termination_verified=true |
| Actual external exit | exec session73067, terminal tool chunk `9dbea2`, **exit_code1** |
| Helper acceptance | passed=false, exact_cases=true, peer_checks=false |
| Known process group | PID/PGID1593 absent in retained final process sample |

The external terminal is a directly observed fact; it is not inferred from the
helper's JSON. The30s bound is an acceptance criterion, not an independent hard
alarm. No deadline or forced-cleanup path was taken.

## Failed capture evidence

The failure occurred in `reservation_case` at its initial `capture_subscription`
call, before the actual launch-order test. `_supervise` attempted `Popen` of:

`cases/test_deferred_capture_acceptan0/durable-copy`

and received `PermissionError: [Errno 1] Operation not permitted`. The saved
script's shebang names the already permitted primary `.venv/bin/python`. The
retained sandbox includes the fixed Git literals, Python entry/target literals,
and the generated case-directory peer regex. The precise policy/serialization
or interpreter-resolution cause of this denial is not established by these
artifacts alone. No additional sandbox probe or execution was run to diagnose it.

The failed slot is retained under:

`cases/test_deferred_capture_acceptan0/one-capture/captures/d37b639efb5a47f3840332c04e6d55eebd2191a662ffc93b9df387c6bd1b48ea/capture-1/`

The manifest records `status=failed`, `spawn_count=0`, `returncode=null`,
`child_started=false`, `leader_reaped=true`, `group_absent=true`, and the original
PermissionError. It contains no selected event or terminal result. Its separate
terminal error reports the absent final terminal result. This is a failed
spawn record, **not successful peer cleanup or capture evidence**.

Direct hashes agree with the manifest's file pins: stdout and stderr are empty
(SHA `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`),
observations is the2-byte empty array
(SHA `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`),
and the durable claim hash is
`7ee6d55bb38e01c883078e8d4e2d7912daed46809c4d786e42d30957775b2079`.
The claim and failed slot are preserved; they must not be overwritten or reused.

The final read-only process sample has no PID/PGID1593. It verifies the known
owner group's absence at that time, not universal never-observed descendant
absence. Popen reported failed execution; no successfully started peer was
recorded. Source remained clean at254071 after the test.

## Artifact SHA-256

Paths below are relative to the v2 canary output except the slot manifest.

| Artifact | SHA-256 |
|---|---|
| result.json | `a961122eb43f263d1291ce5cc8e63ee382d02494a581a59e3eeac030ab5c3f30` |
| pytest.xml | `c2f16e8c4570993a9e49b14896ec0e65d46790eaa8e797a2571bd499c634da51` |
| pytest.log | `632a775fe6439773a768e34cce5b51830768296e53bd054507ab8816f9772919` |
| deadline/deadline.json | `43b07de3e27ed73ecbcf03a636758e4991bbe9b7fbcc1660e71695958859cdca` |
| deadline/controller.json | `caa05d543d57e3ff4189c55d5d819f60574c160b3b03893c16d12b272090671e` |
| offline.sb | `9210fa8b002c9ffc2c47851d3b0664b6f8ef627ed959e9e0daea14aca5a7ea5c` |
| plan.json | `fb3eb6961c252236123bcbc47979c1e4f8fdd8030d293617446a5551f57ccad8` |
| slot capture.json | `4a84cd2f45efdc08a10e4a75814ff3a25a243cdbb5227528415b9e2f6e762fae` |
| post-canary-processes.txt | `c52999aca87d18e9b209993b78f88240a97c03786b42a91c300e44a3172c1c9a` |

## Stop boundary

The one corrected singleton release is exhausted. Failure evidence is retained;
there is no passing v2 canary and no affected-group permission. The lead was
notified of the observed peer-execution refusal for issue filing before repair.
No source/helper/configuration changes, new runtime, push or merge follow from
this report. Existing genuine producer, freshness/reservation, acceptance and
owner decision gates remain unresolved and unchanged.
