# Isolated, gated N2 public-completion driver

Refs #4354. Branch `codex/n2-public-driver-20261027` starts from
`9ea9b70a3b333554bc132f00af7ef22a8cea6094` in the separate worktree
`/private/tmp/d4d-codex-n2-public-driver-20261027`. The active final-restack
worktree was not modified.

Implementation commit `b97265959a2f3727ff83319c84892481bee0252c` changes only
the ad-hoc validation driver and adds its mocked test module. Test correction
`97edbf4b065143baee04b557a66d079b9e1cfd67` changes only the source-drift mock.
**15 mocked tests pass**, zero failures/errors/skips, **0.10 s**, at the latter
head. No public-completion fixture, provider call or native process was run by
this task. This verifies driver sequencing, not actual runtime completion.

The `--group positive` parent now starts two separate existing `-S -P -B`
children, each with exactly one named public test. Their identities are checked
against the unchanged `utils.native_shared_acceptance.NODES` roster:

1. `tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion`
2. `tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses`

Before the omission child is admitted, neutral must exit zero, preserve the
original source snapshot, supply completed before/after project-origin evidence
and disabled-site/.pth bootstrap markers, and produce exactly one matching JUnit
classname/name with no failure/error/skip. The parent also rechecks actual source
state between children and at finalization. Missing evidence, a failed case or
source drift leaves omission explicitly pending with an `omission_not_run`
reason. An actual omission failure remains failed, not pending. Aggregate
`runtime_gates_passed` becomes true only when both gates and final source checks
pass; scientific acceptance remains `not_assessed`.

Each child retains its own `-S -P -B` dependency/bootstrap metadata, source
inventories, origin records, command, logs/JUnit and outcome under `neutral/` or
`omission/`. The parent retains its original/final source and gate outcome.
Credential removal is retained and is not represented as a network sandbox.
The original acceptance utility, production code, fixtures and 180/900-second
limits are unchanged. The native and legacy group rosters and execution body
retain their previous behavior; added conditionals select only the positive path.

## Causal tests and retained first failure

The first frozen run at `b97265959` returned **14 passed / 1 failed**, 0.12 s.
Its source-drift mock replaced `utils.source` after the parent had captured the
function locally, so it did not change any state observed by that function.
The failure is retained and is not claimed as a passing run.

The correction installs one source function before execution and returns a
fresh `deepcopy(state['snapshot'])` on every call. The fake neutral child then
changes the underlying snapshot to a new object. The captured verifier sees
the drift, while the original baseline cannot change by alias. The driver code
was unchanged by this test correction.

The final 15 tests cover neutral nonzero exit, changed source evidence, missing
or foreign origins, missing XML, wrong testcase class/name, failed/skipped/extra
cases, real parent-observed source drift, successful exact two-stage sequencing,
omission failure after neutral success, closed child flags/credential stripping,
and refusal of arbitrary node labels. All runtime subprocess calls are mocked.
Independent internal static review found no blocker in the driver or the narrow
mock correction; this is not a scientific review.

| Evidence | SHA256 |
| --- | --- |
| [Initial log](native_n2_public_driver_20261027/d4d-n2-public-driver-tests-20261027.log) | `b19b000ce22f12701db451ebaeba6ab36e6e03402e23b3dff72997fda9d6b932` |
| [Initial JUnit](native_n2_public_driver_20261027/d4d-n2-public-driver-tests-20261027.xml) | `6e2b33cecd83cd903138a01fb3b7cca810c996f4e29fc2552d7ab3fb6a490187` |
| [Final log](native_n2_public_driver_20261027/d4d-n2-public-driver-tests-fixed-20261027.log) | `2745f28704e6c6bd394f3ef9a8079c19bc4242bf2122dbb6538ef5d7a1f96e4e` |
| [Final JUnit](native_n2_public_driver_20261027/d4d-n2-public-driver-tests-fixed-20261027.xml) | `698338faeea041e6f63cee33e242d4ea38cbb470b11a31aa6419a033dc1ce812` |

The original files remain in `/private/tmp/`; retained copies match byte-for-byte.
The driver SHA256 is
`d6f5be9c04c5b9a1c6ce4755669425d3df3d18c6c6241096caf9c46edf46770b`;
the corrected test SHA256 is
`215c6785e445453da094f9e33ae93391d7ad05b2c16961f33ff12622f1c3ea2d`.
Post-test Git checks confirmed clean tracked/untracked state before evidence
was added, and empty differences against the base for `src/`, `utils/`, both
native fixtures and all three public execution test modules. Comparing the
driver with implementation commit `b97265959` also produced no differences.

## Invocation

The mocked verification used the primary checkout's absolute `.venv/bin/python`,
standard Python startup, `PYTHONDONTWRITEBYTECODE=1`,
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, and this worktree's `src` and root on
`PYTHONPATH`, with the three provider-key variables unset. It does not itself
claim the closed-child import proof; it tests the command and gate logic.

```sh
env -u ANTHROPIC_API_KEY -u CBORG_API_KEY -u OPENAI_API_KEY \
  PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH=/private/tmp/d4d-codex-n2-public-driver-20261027/src:/private/tmp/d4d-codex-n2-public-driver-20261027 \
  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python \
  -m pytest -q -p no:cacheprovider \
  --basetemp=/private/tmp/d4d-n2-public-driver-tests-fixed-20261027 \
  --junitxml=/private/tmp/d4d-n2-public-driver-tests-fixed-20261027.xml \
  tests/test_native_n2_public_driver_20261027.py \
  > /private/tmp/d4d-n2-public-driver-tests-fixed-20261027.log 2>&1
```

After integration into the frozen final restack, the public software gate can be
invoked with `validate_n2_restack_20261026.py --group positive --expected-head`
followed by that exact final SHA, plus `--output` naming a fresh external evidence
directory. No native/legacy rerun is implied by this driver-only change; their
separately pinned results retain their original tested heads. Actual positive
completion remains pending until the gated invocation runs successfully.
