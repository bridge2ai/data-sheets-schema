# Assignment to Codex helper 2: the observer's model-alias defect and three test repairs

From the Claude lead, 2026-11-12. You are a fresh session: first read `claude-lead-helper-context-20261112.md` beside this file (short names `P`, `E`, `R`, and the rules), then the section "Findings and remaining gates" of `R/notes/development_efficiency_20261111/handoffs/codex-native-packets-g07-20261112.md`. Your work is its findings G07-F6, G07-F4 and G07-F5. Helper 1 found them and is busy with something else; do not edit helper 1's worktree.

## Where you work

Create your own worktree and branch from the candidate's head:

```sh
git -C /Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema worktree add \
  -b codex/native-observer-alias-20261112 \
  /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-observer-alias-20261112 \
  5d63d0a77dc43c064cfc2b376355f98009dd5b6e
```

Scratch and test outputs go under `E/scratch-h2-observer-alias-20261112/`.

## Part A: G07-F6, the requested-versus-returned model label (production code)

**The defect, as helper 1 found it.** The native runtime declares two model labels: the one requested (and shown at init and in the terminal accounting) and the one the assistant's messages return. The owner fixed this pair in decision D116: requested, init and `modelUsage` are `claude-opus-5[1m]`; returned assistant messages are `claude-opus-5`. `native_shared_observations.py` (about lines 129 to 131, class `Trace`) compares the assistant frame's label with the requested model, so a correctly declared returned label is rejected. The public completion test fails on the first assistant tool-use frame: `tests/test_native_shared_execution.py::test_actual_public_correction_three_workers_and_saved_completion`. No native run can complete until this is fixed.

**What to do.**

1. Confirm the reading in the source: where the alias pair is defined (`native_model_aliases`), every place a frame's model label is checked, and which frame types carry which label.
2. Fix `Trace` so that each frame type is checked against the label that frame type must carry, using the existing alias helper. Keep the requested-model initialisation. Do not accept either label everywhere, and do not change the test peer to hide the defect.
3. Tests: a correctly declared returned label on assistant frames passes; a wrong or missing label on an assistant frame is refused; the requested label on a frame that must carry the returned one is refused, and the reverse; the historical case where both labels are identical still behaves as before.
4. Check what else pins this module's bytes (a source manifest, a scanner pin, a closure hash). If changing the file moves a pin, list every pin that moves and stop before updating any of them: report it. Helper 1's handoff names the observer's SHA-256 as `41459563575a0c9e0c396c488cb25afbd0f8421896b904ecfc290972ca1b3ae2`.
5. Re-run the single public completion test, and the public-paths cohort helper 1 ran (61 tests, 60 passed before). Report exactly how far the public completion test now gets. If it fails later for another reason, that is a new finding: describe it and stop; do not chase it.

## Part B: G07-F4, two test assertions (tests only)

`tests/test_native_subscription_capture.py`, the assertions at about lines 315 and 371, fail on the candidate and failed in CI with the same messages. Helper 1's reading: the direct-read tracer labels the claims step `outer-claims`, not `inner-claims`; and a changed review document is correctly refused in `validate_bundle` before the later recheck hook the test expected. Verify that reading against the production code. If it holds, repair the two assertions so that they assert what the code is meant to do: the exact trace for the direct read, and the exact pinned-review refusal with the earlier trace. Keep the other mutations' recheck assertions. If the reading does not hold, the production code may be wrong: report that instead.

## Part C: G07-F5, a missing test (tests only)

The current `prepare-subscription-guard-v2` command has only parser coverage. Add one focused offline test of its routing and publication: that it reads the capture it is given, refuses a capture that is not the last one claimed under the word (helper 1's commit `5d63d0a77`), writes the guard once and reports its sha256. No real capture, no binary.

## Commits and handoff

Three commits on your branch, one per part, in the order A, B, C. Handoff: `R/notes/development_efficiency_20261111/handoffs/codex-h2-observer-alias-20261112.md`, answer first: what was wrong, what you changed, the test counts from saved output, how far the public completion test now gets, any pin that moves, and anything you could not verify.
