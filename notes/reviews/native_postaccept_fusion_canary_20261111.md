# Post-acceptance fusion canary: fixture setup failure; helper repair unexecuted

2026-11-11. Exactly one released offline canary ran at clean
`2fe49f143c9bd171b90760b9f4e380c277d05da3`. It **failed during fixture setup**,
before capture, launch or reservation. The sandbox denied `/usr/bin/git` while
`registration_commit_for` attempted to initialize its synthetic evidence repo.
This is #5869, a helper/fixture dependency failure. It is not a production
refusal, successful acceptance, performance result or native/provider run.

## Executed unit and outcome

The exact documented `env -i` invocation used the existing dependency Python
with `-S -P -B` and only helper mode `canary`. Source production hashes were
`13573951995c5e7d27b164feaab1b328dad09b33c8dce9ff53afa50ec360a89b` and
`c77d692deafafb483e8ccf0781cad9434f1aee14aa4585fec4a2269d081025e5`;
fixture `eb0522c4da33b24040cb2e10657b7e97b09a43a51fbf86d19b4c8af043899f96`;
executed helper `7975260d7299f2f3f6dee0dfeb98c3f055f7a756050ac63c0bbb2b252894132c`.
The quiet-window lock and fixed output path were absent before invocation.

- Exact JUnit node: `tests.test_native_u4b_a3_reservation.test_deferred_capture_acceptance_exact_order_to_real_reservation`.
- **1 failure, 0 errors, 0 skips**; JUnit suite1.855s, testcase0.038s.
- Helper elapsed **2.6705842920055147s**, acceptance budget30s.
- Deadline owner elapsed **2.6465247079904657s**, work allowance9.978113374992972s.
- Child return1, unexpired, no signals, termination_verified=true; no forced cleanup.
- Actual external tool invocation: exec session66834, terminal chunk `e7f1ba`, **exit_code1**. This is direct terminal evidence, not an inference from result.json.
- `exact_cases=true`, `passed=false`, `peer_checks=false`, empty peer list.

Failure stack: reservation_case -> component -> bundle_for ->
registration_commit_for -> `/usr/bin/git ... init -b synthetic-evidence` ->
`PermissionError: [Errno 1] Operation not permitted`.

The helper preserved JUnit/logs, plan, sandbox and deadline files under
`d4d-executions/scratch-native-postaccept-fusion-20261111/canary/`.
An ignore-independent file search including hidden files found no `capture.json`
or `claim.json`. The fixture had written invented runtime/observation inputs;
those are not observed provider or executable evidence. Capture lifecycle
validation was not exercised because capture was never reached.

The known owner PID/process group was90758. A saved read-only process sample
contains no PID or PGID90758. This verifies absence of that known group at the
sample time, not every never-observed descendant. No separately sessioned
capture peer was started on this path. Independent artifact review agrees with
the failure classification and evidence limits. No retry or affected group ran.

## Retained evidence hashes

All paths in this table are relative to the failed canary directory.

| Artifact | SHA-256 |
|---|---|
| result.json | `1698c24dcbf153a6f8d50bb0e3745f1bbb1e5b4a89d6d89771b2fcd3c51737e3` |
| pytest.xml | `d83957f3f6b3fb854ad2f50b37edea0f795aebbc64d24d507127dafe63777def` |
| pytest.log | `7d01b33e18bd6a3b245343641068a4bb30dd4857bfa9097c31b7627a94227960` |
| deadline/deadline.json | `b0609df1ee80f794e9fdd00742303c1378750eebec6156a954348a58358cda66` |
| deadline/controller.json | `c144b13f6eef1cc8eebc48bacefe5b0b15bac075771a68da98962f46770c4fd7` |
| offline.sb | `7a98384efd4481dfcfb4210a9c62fd1ec94b40f00fd9c2c5cef1d9b3ceb5bf7c` |
| plan.json | `50906942aca9184b2d210ba45878f580242672333b6c565ad210a9350eeab9bf` |
| post-canary-processes.txt | `0bfe0617e3ef113a8f313a2ecf97531b439c11a3e1ce7e40ffa8f7b880b07d8d` |

The process sample was saved during authorized outcome verification. After
that, the lead required the failed directory to remain exact; no further file
was added, changed or removed there. Subsequent repair work is only in the
branch/helper and these review reports.

## #5869 helper-only repair prepared for review

The fixture at `tests/utils/native_u4b_fixtures.py:20–45` uses only fixed
`/usr/bin/git -c core.hooksPath=/dev/null -C <fresh synthetic repo>` commands:
`init -b synthetic-evidence`, `add -- <registration>`, `commit -m <fixed message>`,
and `log -1 --format=%H -- <registration>`.
The real review validator also invokes this fixed Git entry for local
`rev-parse`, `cat-file`, `ls-tree` and registration-object readback. It disables
hooks, filesystem monitoring, protocol transport, replacements and prompts.
The fixture uses an explicit synthetic identity, null global/no-system config,
no interactive prompts and no lazy fetch. No remote is involved.

Read-only local platform inspection established:

- `/usr/bin/git` is a regular Mach-O selector, not a symlink.
- `otool -L /usr/bin/git` shows `/usr/lib/libxcselect.dylib`; `nm -u` shows
  `_xcselect_invoke_xcrun` on both architectures.
- `xcode-select -p` returns `/Library/Developer/CommandLineTools`;
  `xcrun --find git` returns `/Library/Developer/CommandLineTools/usr/bin/git`.
- The selected Git target is a separate Mach-O executable. Git selector SHA
  `179301dcb41ea78accc3fa0048a7e6f6710d891945a751a34addd622020c1818`;
  selected target SHA `3121e7e4d16059539731c58d94888709c12904abe922acde8e37caef4607c1d1`;
  `/usr/bin/xcrun` SHA `a439970aea2b4e435eac6518ff62c97fd1c57d8c731974027ad211b515c7a7b8`.

The lead explicitly ruled that this evidence supports three literal exec
allowances: `/usr/bin/git`, the selected CommandLineTools Git, and
`/usr/bin/xcrun` as the bounded Apple selector helper. The failed canary only
observed denial at the first entry. **No claim is made that all three were
actually executed, or that an additional helper was dynamically observed.**
No runtime probe or binary-execution tracing was performed to extend that claim.

The corrected helper adds exactly those literals to the previously reviewed
Python/fixture exec set. There is no executable-directory wildcard, shell,
Git remote/upload/receive helper, or general process-exec allowance. `xcrun`
cannot broaden the allowed target set. Network denial, output-only writes,
credential-free environment, null Git configs, original deadline helper,
10s-work/20s-cleanup/<=30s acceptance budget and all fixed selections are intact.
This is still an acceptance budget, not an independent hard alarm.

A new exclusive root,
`d4d-executions/scratch-native-postaccept-fusion-v2-20261111/`, holds the corrected
recipe's future canary and later same-source gate. It was checked absent and
has not been created. The old failed canary cannot serve as that gate and
cannot be overwritten by the new recipe. No automatic retry or fanout exists.

Prepared helper SHA:
`bece6bfc40bcfbfe040f5d1e9d6ebb740f8be215c586327bcf20f90f227c807c`.
Exact helper delta: `notes/reviews/native_postaccept_fusion_git_allowance_20261111.diff`,
SHA `0551a6bcc633623c11836cb89f6de7da4bdac7de2731d269d2f187f492c512d1`.
Production/tests remain byte-identical to2fe49f; no protected edits or config
rearm. The helper repair has **not been imported, compiled or run**.

## Stop

The failed canary release is exhausted. The separate helper-repair release
allows preparation only. Freeze this delta for review before any new explicit
singleton release. No affected group, genuine producer diagnostic, native or
provider call, push or merge has occurred. Existing native acceptance gates
and owner packet/scanner decisions remain unchanged.
