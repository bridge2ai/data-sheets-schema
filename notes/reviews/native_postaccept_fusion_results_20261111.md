# #5867 post-acceptance fusion: 19 component cases passed

2026-11-11. Tested clean, frozen head
`64c612133b5b8fa0972ec2b10dc821f4d81e65c6` throughout. One reviewed v4 canary,
then the 18 expressly released fixed singleton keys in insertion order, each
started only after the preceding case's external exit, exact JUnit, source pins,
deadline and peer evidence passed. No retry, concurrent case, new runner,
profile, budget increase or source/config change occurred.

Each invocation used primary `.venv/bin/python -S -P -B` under
`env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=/var/empty`, calling the existing
`scripts/adhoc/run_postaccept_fusion_checks_20261111.py KEY` directly. Existing
network-denied, credential-free child,10s work plus20s cleanup reserve and30s
acceptance criterion remained unchanged; this is not a new hard alarm.

## Frozen identities and raw evidence

| File | SHA-256 |
|---|---|
| helper: scripts/adhoc/run_postaccept_fusion_checks_20261111.py | `8a5f5c3877e0674d3817e3c39660d3475a9848ca56015587eea876fc839954d7` |
| tests/test_native_u4b_a3_reservation.py | `2880785a41a075ea2e955ae372fbfa8db364ad6bd5ef9d5c0d39ccb3e10fd478` |
| tests/test_native_u4b_a3_captures.py | `afdfc8205c652aee1b8dcd685271b3150f2d1c36dbec7ba3269b6320055a5aca` |
| native_execution_orchestration.py | `13573951995c5e7d27b164feaab1b328dad09b33c8dce9ff53afa50ec360a89b` |
| native_shared_execution_orchestration.py | `c77d692deafafb483e8ccf0781cad9434f1aee14aa4585fec4a2269d081025e5` |
| tests/utils/subprocess_deadline.py | `876c91d211f4870c5622e7403310200b37028a3287c2b94e468a4c9d084b01b7` |

Raw root: `d4d-executions/scratch-native-postaccept-fusion-v4-20261111/`.
For each KEY below, raw result/JUnit/deadline paths are `KEY/result.json`,
`KEY/pytest.xml`, `KEY/deadline/deadline.json`, with controller, plan, sandbox and
pytest log alongside. Each result names its exact capture manifests, stream
hash/length witnesses and all11 source/helper pins. The same-source canary gate
checked these pins before each affected invocation; `shasum -c` verified all11
again after each. Final checkout stayed clean at the tested head.

`singleton_evidence.sha256` in that root (identical archived copy
`notes/reviews/native_postaccept_fusion_v4_evidence_20261111.sha256`) freezes the
raw results, JUnit, deadline/controller, plans, sandbox/logs, capture manifests,
streams, claim/reservation chains and existing process/source-check samples.
Manifest SHA-256: **`46ce69b33ea44da93eac41a38ae5373a638d56357a263a3c4f40094079b43c88`**.
Its415 path entries include pytest case aliases; they are not415 tests/captures.

## Outcomes

Every row is **one JUnit pass, zero failures/errors/skips**, external exit0,
result.passed=true, exact_cases=true, source11/11 unchanged, unexpired deadline,
no signals, termination_verified=true and peer_checks=true. Thus JUnit,
cleanup and source columns are P/P/P for every row. Captures shows total/failed;
the two failed captures are intentional poison refusals with successful scripted
peer exit. Times are helper elapsed seconds, rounded here; exact floats persist
in the results. External refs are owner-tool terminal chunks (session shown when
execution yielded), independently observed rather than inferred from JSON.

| KEY | Seconds | Captures total/failed | JUnit/cleanup/source | External exit0 witness |
|---|---:|---:|---|---|
| canary | 6.721535 | 1/0 | P/P/P | 56361 / b8897c |
| values-current | 6.410404 | 1/0 | P/P/P | 4827 / cc64dc |
| values-fresh | 6.338269 | 1/0 | P/P/P | 28799 / a5081b |
| values-both | 6.609405 | 1/0 | P/P/P | 81942 / 52b708 |
| values-during-read | 6.343222 | 1/0 | P/P/P | d75797 |
| inputs-changed-bytes | 6.017972 | 1/0 | P/P/P | 41e77d |
| inputs-read-failure | 6.098350 | 1/0 | P/P/P | 85aada |
| inputs-platform | 5.981616 | 1/0 | P/P/P | b6627b |
| direct-90 | 5.341934 | 1/0 | P/P/P | 13aaf9 |
| direct-89 | 5.583180 | 1/0 | P/P/P | 70fcd6 |
| direct-recapture-90 | 5.601923 | 1/0 | P/P/P | 90b79b |
| direct-recapture-91 | 5.561048 | 1/0 | P/P/P | 2d46f4 |
| margin-90 | 6.388989 | 1/0 | P/P/P | a68d0e |
| margin-91 | 6.247152 | 1/0 | P/P/P | 3bfaf9 |
| admission-direct-superseded | 5.162813 | 1/0 | P/P/P | de5bf2 |
| admission-direct-poison | 5.448646 | 2/1 | P/P/P | b75687 |
| admission-deferred-superseded | 5.184223 | 1/0 | P/P/P | 0fb5b9 |
| admission-deferred-poison | 5.327619 | 2/1 | P/P/P | 83d8f0 |
| lease | 3.184710 | 0/0 | P/P/P | 3fafb8 |

Total19 passing cases,20 scripted captures, including two intentional failed
capture records. Each actual peer has spawn_count1/returncode0 and
child_started/leader_reaped/group_absent=true. Lease has no peer. Canary and
first two affected cases also have separate read-only process samples; later
cases use the lead-approved supervisor termination and peer cleanup certificates.
This establishes known owned-group/peer retirement, not arbitrary descendant
or global-process absence. The evidence was checked before each successor;
no extra test was run solely to obtain another review.

## Preserved history, scope and remaining gates

Preserved: v1 failed at Git exec before capture; v2 failed at peer exec with
spawn0; v3 passed its one component canary. Their directories and reports remain
intact. V4's separately recorded canary pass remains in
`native_postaccept_fusion_canary_v4_20261111.md` (SHA
`959a5e458208d4f0bb9d2c31d89d723bc22041d3f7be5a10597c746f5ef9c1ba`); its initial
18-case hold was superseded only by the explicit conditional serial release.

These are isolated registration/controller/source-capability components. They
exercise actual shared input checks, mutation refusals, lease/current-word
locking, reservation persistence and order, synthetic-clock margin boundaries
and intentional admission refusal. They do not establish genuine producer or
projection reconstruction, real-clock freshness, quiet-host performance,
native execution, interruption acceptance, a speedup or U3K-F1 closure.

Still pending: genuine fresh capture-to-reservation success; two public-completion
checks; the previously deferred17 failure-path cases/eight cohorts; quiet-host
and interruption acceptance; subsequent native probe/canary acceptance. Owner
decisions remain for the changed protected API packet postimage and exact D128
scanner differences. This component roster does not replace those acceptance
cohorts. No packet/config/protected byte, provider/native executable, push, PR or
merge was authorized or performed by this sequence. Stop after the report-only
commit; separate evidence review precedes any publication or further runtime.
