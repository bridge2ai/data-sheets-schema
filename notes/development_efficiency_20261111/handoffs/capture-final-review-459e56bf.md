# Capture A frozen source review

Recorded **2026-11-11 05:22:34 UTC**. Reviewed
`459e56bf896a29d854c5d250ce8632d7e2564427` against
`458887766effe38207a77fea2d8033f1f3e1c7f3` in
`agy-native-path-alias-parity-20261111`. HEAD matched the reviewed commit and
`git status --porcelain` was empty at the final read-only check.

| Frozen file | SHA-256 |
|---|---|
| `src/data_sheets_schema/native_shared_registration_orchestration.py` | `c674f2bea05d20d744871fe8839ee634527045e8fef23c027548afbc1b6ce233` |
| `src/data_sheets_schema/native_subscription_capture.py` | `b2e0f065a7a21b36bf015d558b8ca4e8aba15b01b8ffa8ab4359827b68cfad16` |
| `tests/test_native_subscription_capture.py` | `5c07a3858e74adbc73d504a9caa68381bcbf93816a410584de57d0715fa23639` |

## Source disposition

No additional concrete blocker found in this bounded final pass. The #5847
stage-root refusal is restored in source through genuine selection capture
(`native_shared_registration_orchestration.py:193–194`). The earlier live-state
checklist remains applicable. This is source clearance for the planned bounded
validation, not a passing test or proof of complete verifier equivalence.

The public `read_capture` signature and its full `_authority` verification remain
intact (`native_subscription_capture.py:685–701`). `read_capture_for_event` still
obtains full authority before discovering slots (`719–727`); only matching slots
use the new private `_read_capture_with_authority` route (`738–741`). That private
route obtains a fresh recheck before reading the unchanged saved-record logic
(`673–682`). It is supplied the initial tuple by this internal caller; it is not
a new public entry accepting caller-supplied verified authority. The recheck
compares the complete returned authority tuple with the initial tuple (`148–158`).

## Genuine test setup and scope

The new node at `tests/test_native_subscription_capture.py:375` uses the real
`make_case` builder with a fresh child of pytest's already-existing directory
(`388`). This corrects the earlier root-creation failure: the builder itself uses
`mkdir(exist_ok=False)` (`tests/native_shared_fixture.py:108–109`).

`make_case` obtains `value` through genuine `registration.verified`
(`tests/test_native_shared_execution.py:60–65`). Its runtime, reviews, permission
observations and saved capture are explicitly fabricated software-test evidence;
the readers and validation path are genuine. No live native capture is exercised.

The node reads the existing saved capture through public `read_capture` before
installing tracing wrappers (`397–399`). Each wrapper delegates to its original
implementation (`409–424`). It then requires successful matching-slot readback
and exact call order (`430–436`). Only on the second lookup does it write the
regular file at the stage root, after outer claims discovery (`420–423`). The
expected trace proves that this mutation occurs after initial full verification
and that the inner recheck refuses (`438–446`). The final assertions independently
require the same stage-root refusal from the full verifier and the recheck
(`447–450`). The mutation is confined to the newly created fixture directory.

The subprocess trap permits Git and rejects other subprocess commands (`381–387`).
The traced setup uses local Git, including a synthetic registration commit with
hooks disabled (`tests/utils/native_u4b_fixtures.py:19–45`). A configured local CI
repository URL/origin and readable committed workflow objects remain prerequisites
of `make_case` (`test_native_shared_execution.py:75–84`;
`native_execution_registration_v2.py:123–158`). The owner's private composition
must satisfy these existing prerequisites; the test does not waive them.

## Validation limit

No imports, tests, compile checks, provider calls or worker edits were performed
for this review. The lead reports two earlier attempts stopped before the target
behavior: the existing-directory setup error and then a sandbox Git-config
failure after 22.40 seconds. Those are setup failures, not passing or failing
evidence for the revised capture boundary. Their logs were not independently
replayed in this pass.

The exact node above is the outstanding positive/differential acceptance check.
It does not test generation dispatch, reservation, provider performance or native
acceptance. No broad test cohort is justified by source review alone.
