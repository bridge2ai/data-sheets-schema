# Post-acceptance fusion v4: singleton pass, stopped

2026-11-11. Exactly one separately released invocation at frozen clean
`64c612133b5b8fa0972ec2b10dc821f4d81e65c6`. Primary `.venv/bin/python -S -P -B`,
`env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=/var/empty`, fixed helper `canary`.
Helper SHA `8a5f5c3877e0674d3817e3c39660d3475a9848ca56015587eea876fc839954d7`;
test SHA `2880785a41a075ea2e955ae372fbfa8db364ad6bd5ef9d5c0d39ccb3e10fd478`.
Quiet lock/output absent at 06:53:43 UTC. No source/config edits or commits.

External owner session **56361**, terminal **b8897c**, exited **0**.
Exactly **1 passing JUnit case**, no failures/errors/skips. Helper elapsed
**6.7215348329918925 s**; child **6.702092334016925 s** against
**9.983432167005958 s** work; JUnit suite5.995s/test4.405s. No expiration/signals;
termination verified. Existing10s work/20s cleanup/30s acceptance criterion
unchanged; this is not a new hard alarm.

One ordinary-Python scripted capture, status captured, spawn1/exit0,
child_started/leader_reaped/group_absent all true. Verified stdout1480bytes,
observations463bytes, empty stderr and matching manifest hashes; claim and
claim-1 match, reserve.json matches the referenced digest. Empty generation
reservation persists with mode0700. Independent read-only review confirms all
of these and all11 recorded source/helper hashes match the frozen checkout.
Known controller PID/PGID12745 is absent from the saved read-only process sample.
Group observation is not a global claim about unrecorded descendants.

Evidence: `d4d-executions/scratch-native-postaccept-fusion-v4-20261111/canary/`.
The result.json names the exact capture slot and includes all source/lifecycle
witnesses. Its helper, test and production identities remain unchanged afterward.

| Artifact | SHA-256 |
|---|---|
| result.json | `b065600592e0c1ada7a4916c69f10bf0a2ec076e605c06df688cc6e348181870` |
| pytest.xml | `9c86483214cf67a617a6da8227d464f43f02203eb43f22f653fbdafddb6b6e4d` |
| pytest.log | `48d366b1475df79ccd1c13a1a899d13b6c5244bf7cb60733ec2c206e44d68c46` |
| deadline/deadline.json | `aad659bcd714fd272a206c9f2165c334fd7a910b9f121a9b87d3746a8f64f8b1` |
| deadline/controller.json | `6ef694d4763a4ce57ea28f348ecc66d47ad6d5b1505e86011874c5bc03465613` |
| offline.sb | `f0a98c7a8ee208c8e38616a9fc1708b084d420d24229ea861ac162a697b792cc` |
| plan.json | `1fbd290f243d3add66deae3cfd55eb6384bad6c014fb69ab6cdb7cd151c9aac3` |
| post-canary-processes.txt | `66a1e2ff6ee9033639ba4c28fd045c5e2d97bdb3da958eb271553c8db6f9f615` |
| capture.json | `fb0174f15afc62bbb69e24aa87ac8528fae6945ac904a86025c33a1f63c2c1e1` |
| claim.json | `1035e29e1d954ce497f8c27f125c63578680331deb3d3b68443f9802299ff173` |
| reserve.json | `e59a9280ffcfddc185ab7ae45aafb3e05ee0a2c7e4836d06e665dd126310152c` |
| stdout.jsonl | `25120025e2f4aa159070fa49d138be9101618607db0a46d7fd328e2002319496` |
| stderr.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| observations.json | `f9171003676d806a9b9c585a5da0cef9dbd40dde6a6c8af47c36d9282a9b807e` |

Stopped before all18 affected cases. V1/V2 failures and V3 pass preserved.
This proves isolated component ordering/persistence, not genuine producer,
native execution, real-clock freshness, quiet-host/performance or interruption
acceptance. Existing completion/failure-path gates remain; protected API packet
postimage and D128 scanner differences still require owner decisions. No new
cohort, provider/native call, private config/packet change, push or merge.
