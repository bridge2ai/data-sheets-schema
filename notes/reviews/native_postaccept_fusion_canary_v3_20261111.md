# Post-acceptance fusion: v3 singleton canary

2026-11-11. Exactly one released invocation at clean
`5a14c6de8cc80099053448e46e76788f225a58e2`, helper SHA-256
`b175549261aa28cd5681b23824b51757fbe7fb7c33a8905f6cdc54e123e29227`.
The retained v1 and v2 failures were not overwritten or reclassified.

Command: primary `.venv/bin/python -S -P -B` running
`scripts/adhoc/run_postaccept_fusion_checks_20261111.py canary`, under
`env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=/var/empty`.
The helper launched its unchanged network-denied sandbox, credential-free child,
10-second work budget and 20-second cleanup reserve. The 30-second limit is an
acceptance criterion, not a new hard alarm. Precheck at 06:47:43 UTC found the
quiet lock and v3 output absent. No native executable or provider was called.

## Result and persisted evidence

External owner tool session **35804**, terminal chunk **1d9c16**, exited **0**.
This exit was observed outside the helper; it is not inferred from result.json.
Result: **1 passed, 0 failures, 0 errors, 0 skips**, exact expected node
`tests/test_native_u4b_a3_reservation.py::test_deferred_capture_acceptance_exact_order_to_real_reservation`.
Helper elapsed **6.87306174999685 s**; supervisor **6.852562750020297 s** against
**9.982611624989659 s** available child work; JUnit test **4.647 s**, suite **6.145 s**.
No deadline expiration or signals; termination_verified=true. One unrelated
existing dateutil UTC deprecation warning is retained in the log.

The actual ordinary-Python scripted peer spawned once and exited 0. Capture
status is `captured`; child_started, leader_reaped and group_absent are all true.
stdout.jsonl is 1480 bytes, observations.json 463 bytes, stderr.txt 0 bytes;
all hashes and lengths match the capture manifest. claim.json and the retained
claim-1.json agree; the referenced reservation digest matches reserve.json.
The generation-attempt directory persists empty with mode 0700. The passing test
asserts the exact acceptance-to-lock-to-fsync order and that no generation
child/evidence directory is reached. Independent read-only artifact review
confirmed these findings without rerunning any test or importing the source.

Controller PID/PGID **5672** is absent from the separately saved read-only
post-canary process sample. The supervisor covers its owned group; peer cleanup
is evidenced separately by the retained capture lifecycle. This is not a claim
that every possible unrelated or unrecorded descendant was enumerated.

Evidence root:
`d4d-executions/scratch-native-postaccept-fusion-v3-20261111/canary/`.
Capture slot relative to it:
`cases/test_deferred_capture_acceptan0/one-capture/captures/e2e2f922220580e4f8bb0abcb524c6c304208837643376282192a40a73f65b5b/capture-1/`.

| Artifact | SHA-256 |
|---|---|
| result.json | `392ad510cf1ca9382e32cc87257945fe18a903183ad599c01ac4ead8eeb3af3b` |
| pytest.xml | `34dc053fcbfab48fe55968c50dfeb0ce93f18dc64b20fb40c9786920a51338e8` |
| pytest.log | `a74dcc96438be578c5d04219c3bf6d8eb03a3036a1dff8dc5b1de2cab691cd70` |
| deadline/deadline.json | `f859dbadb2e2bef58ecc5c3517798cf637ddc244bf2e30b449a06bfa0a4c8761` |
| deadline/controller.json | `896753eb97d2cbb3a8db3ef9952ab26654e88af12fe86c613967f3426420adff` |
| offline.sb | `259fbd6296eb399f279e7095c55237c31af3279a7899dd762021ee555f89e096` |
| plan.json | `1fb62ef8e721b5a4774b875f57df370bf2c60575553141b34d2595b845f4d1c6` |
| post-canary-processes.txt | `2217546ce46d4a6db82add99b2a681f7ec70071318a1819acec93671d0400820` |
| capture.json | `f48a56bc7b13ca3d1e57cf65f8193e12f8ac46904a24a6834bf353eebaf1076a` |
| claim.json | `23d7d8f26b4e30d47ff0808795d3e6de6484649620cdb11fd32c380542a96f49` |
| stdout.jsonl | `a31be709f3eff98874b5f2583ca5fbff1d3a5698d93cc93f2ee4f3259a54ff29` |
| stderr.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| observations.json | `750aa918fd5b0f627c58028c1384f2b03e0f110d3bfa8ffe53ac31cf14a567bf` |

## Limits and next boundary

The registration, producer and source-capability prerequisites remain explicitly
isolated. This establishes component capture/reservation ordering, not genuine
producer reconstruction, real-clock freshness, native execution, performance,
quiet-host qualification or interruption acceptance. The source-refusal and
mutation cases have not yet run. No affected group was started.

The lead held the old 2–4-case groups because this successful singleton does not
justify fitting them inside the unchanged 10-second work budget. A separate
preparation-only release permits fixed singleton selectors and stable parameter
IDs, retaining all 19 cases and the poison cases' two captures/one failed capture.
That identity change requires a fresh v4 canary; the v3 success cannot authorize
it or any affected run. No retry, new cohort or genuine diagnostic is inferred.

Remaining native gates are genuine freshness/reservation success, two public
completion checks, the 17 failure-path cases/eight deferred groups, independent
quiet-host/interruption acceptance and later native probe/canary acceptance.
The post-acceptance fusion removes one cascade; U3K-F1 is not closed. Owner
approval remains required for the changed protected API packet postimage and
D128 exact scanner differences. No packet/config/protected-byte change, push,
merge or new API-only final-D4D prerequisite follows from this result.
