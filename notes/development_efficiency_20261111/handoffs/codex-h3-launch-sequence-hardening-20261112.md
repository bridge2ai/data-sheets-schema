# Launch re-check follow-up: helper 3

Issue 6048: 48cb2d1f494add9903851af3c3babce31213af79, a22c51a9d082cad64eccb64c2de900b32e8e2630.
Issue 6047: ef193e4eabc65a1c7ab39ecc64ad2945889f3416, a22c51a9d082cad64eccb64c2de900b32e8e2630.

A sequence-dispatched capture now requires the existing current word journal and the exact parent-pinned, current sequence_start event under the capture lock. It opens with create=False and never activates a word on that route. The body now calls data_sheets_schema.native_launch_entry._require_invocation through an absolute local import; no callback or validator is accepted from the sequence namespace.

Saved test counts (overlapping cohorts, not a unique-test total):

| Cohort | Cases | Failures | Errors | Skipped | Exit |
|---|---:|---:|---:|---:|---:|
| recheck-6048-02 | 141 | 0 | 0 | 0 | 0 |
| recheck-6048-plumbing | 16 | 0 | 0 | 0 | 0 |
| recheck-6047-01 | 156 | 0 | 0 | 0 | 0 |
| recheck-6047-final | 345 | 1 | 0 | 0 | 1 |
| recheck-composed-final | 345 | 0 | 0 | 0 | 0 |
| recheck-unspent-before | 2 | 2 | 0 | 0 | 1 |
| recheck-unspent-after | 158 | 0 | 0 | 0 | 0 |
| recheck-composed-unspent | 26 | 0 | 0 | 0 | 0 |

The 345-case candidate cohort predates the extra under-lock unspent correction. The two new reservation-race cases fail before that correction; afterward all 158 focused worktree tests and all 26 candidate-composition capture/CLI tests pass. These are separate saved cohorts, not a claim that the entire 345-case cohort was repeated after the one-line correction.

## Issue 6048

The sequence adds its durable start-event path and digest to the capture child's closed invocation pin roster. The child checks those bytes during pin preflight and passes the pin to capture_subscription. Under the existing journal lock, Journal.require_start rechecks current format, current word, validity, refusal state, the event's type and word, and the exact current event path/digest before any capture-slot reservation or execution. A word-only journal, absent start, incorrect pin or later start refuses.

The regression moves the journal aside after the start is durable but immediately before the child acquires the lock. Missing and empty replacement cases refuse, leave retained state byte-identical, and never reach capture reservation or execution. The positive synthetic test verifies that the journal lock remains held through capture dispatch. CLI tests verify that sequence dispatch passes the pin and standalone dispatch omits it.

Standalone explicit capture is unchanged: it may initialize current word state, activates the presented word, and retains the existing three-slot allowance, chronology, validity, unspent-reservation and limits-refusal checks. The owner word-recording step remains the initializer for the sequence route. Tests use invented state and fake peers only.

Read-only review finding H3-LR1: bypassing activation on the new sequence route also bypassed activation's under-lock unspent-generation check. The prepared correction explicitly repeats require_unspent inside the journal lock before either route can reserve a capture. Regression cases create the attempt directory or evidence directory after preflight but before lock acquisition and assert refusal before capture reservation/execution. This finding is recorded locally because GitHub writes are prohibited.

## Issue 6047

The entry no longer injects a validator callback. The body's absolute local import ignores an assigned no-op _entry_invocation, a same-named global validator, and caller-changed package metadata. The trusted entry still consumes the one-use namespace/argument/source/input binding before packet creation or journal access. Tests cover ordinary imports, no-op injection, loaded-A/retained-B and supplied input maps, with zero packet and zero journal effects. The documented module-execution route dispatches through the canonical trusted entry instance so it shares the same invocation registry; both supported module routes pass with fabricated commands.

Rewriting the trusted entry itself or the interpreter remains out of scope, stated in the sequence module documentation string.

## Integration, failures and known limit

The first runner attempt could not start its child sandbox or enumerate macOS processes under the outer tool sandbox. Its saved log says sandbox_apply: Operation not permitted. The approved rerun used the existing network/native-denying child sandbox and process-cleanup monitor.

The first private-tree invocation refused before tests because its composition manifest lacked the runner's ready status, commit field and protected-file hash roster. Those fields were supplied only after checking the private HEAD, clean source diff and all four protected bytes against the published candidate. The initial manifest remains saved beside the completed manifest; no source or assertion was changed for this correction.

The uncomposed hardening branch retains the four protected main-file bytes. Its genuine-registration fixture needs the candidate's approved protected post-images; that setup refusal is retained in the uncomposed cohort above. The private rehearsal first applies the two repair commits onto published candidate 8760de5efe88b5af62e9d77e6335fa7e248017b6, which already contains those approved files, then adds the prepared H3-LR1 correction for the focused rerun. Both patches applied cleanly. All changed source/test files match the current hardening worktree byte for byte. The private tree has no remote, and its temporary CI configuration was restored byte-exactly. This is a scratch test composition, not a carry onto either previously merged branch.

Optional Part 3 was not implemented: no optional branch or tip-format commit was created. Issue 6049 remains the lead-accepted nonblocking limit. Deleting a valid journal suffix or restoring a consistent older state is not detected by the current unanchored journal; no new crash-safety claim is made for a count/tip protocol.

The source remains on codex/native-launch-sequence-hardening-20261112 for lead integration and independent review. The other two branches were not changed. The four protected files and guard v1 are byte-identical to the accepted hardening head. Nothing was pushed or published; no real native binary, probe, capture, reservation, provider or model was called. Synthetic word state stayed in this helper's scratch.
