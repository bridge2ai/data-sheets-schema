# Native input rejection review, 2026-09-18

## Problem and scope

[#2084](https://github.com/bridge2ai/data-sheets-schema/issues/2084) was reproduced from a native `Read` whose numeric offset was supplied as a string. The pinned runtime returned a typed input-validation error before requesting a permission callback. The controller could not represent that unexecuted call and treated its missing callback as incomplete evidence.

The change recognizes only the evidenced `Read` numeric-string rejection for `offset` or `limit`. It requires the original invalid argument, matching typed error and error-only wrapper, a unique call/result pair, prior native session initialization, and no callback or conflicting execution evidence. An explicit `input_rejected_before_callback` record preserves event positions and hashes. Live completion and retrospective review independently check that record. No permission decision is fabricated, and the recognizer does not access a file.

This is a fix for future conditions. [v10y's actual stop](../native_canary_v10y_outcome_2026-09-17.md) was a receipt-helper argument mismatch. Its measured controller, outputs, accounting and verdict remain frozen. The scientific acceptance issues remain open. No model request or paid canary was needed to implement or test this change.

## Independent review

Round 1 produced two findings, filed as [#2086](https://github.com/bridge2ai/data-sheets-schema/issues/2086).

- Live rejection evidence used physical JSONL positions, while three retrospective loaders discarded blank lines. The shared loader now preserves blank positions explicitly and reports such history as uncheckable. Malformed, non-object, oversized and unterminated nonblank frames are rejected. Unicode separators within JSON strings retain their existing behavior.
- Rejection recognition could use a session initialized after the call. It now requires a matching session already established when the call occurred, with control initialization before the call and the result before termination. The outer runner already rejected entirely missing native initialization; this correction also closes the ordering gap.

Original counterexamples and review evidence are retained separately from the corrected results. Review does not waive missing callbacks for other errors or ambiguous execution.

Both round-2 reviewers found no remaining defect in the corrected patch. Independent replays confirmed the initialization failures and replayed the original saved blank-line fixture through the production loader: event positions and hashes now match while the blank-frame diagnostic still prevents acceptance. An independent run also passed all 101 focused tests. Merge remains subject to CI on the reviewed commit.

## Validation

The corrected patch passed 101 focused tests and all 318 tests in the eight native-control suites on Python 3.13.12. Loopback sockets were enabled for the transport fixtures; provider transports were mocked. CI verifies Python 3.12.

The real child-process fixture proves that an invalid read does not execute, has no permission callback or decision, and can be followed by a corrected read with ordinary complete evidence. Negative cases cover contradictory or extra content, duplicate identities/results, callbacks, altered arguments/errors/sessions and initialization ordering. Shared-loader checks cover physical blank positions, malformed and non-object frames, invalid UTF-8, frame limits, unfinished records and Unicode separators.

Five in-memory mutations were detected: removing rejection recognition, ignoring the original invalid argument, ignoring the error-only wrapper, allowing an unknown session, and restoring a loader that drops blank positions. The original round-1 evidence is preserved alongside the round-2 proof. No frozen canary file was changed.
