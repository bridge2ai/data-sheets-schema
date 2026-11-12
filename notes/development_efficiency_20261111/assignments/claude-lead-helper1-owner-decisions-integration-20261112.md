# Assignment to Codex helper 1: the owner's decisions of 2026-11-12, and what they change on the candidate

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file. This replaces the open end of `claude-lead-helper1-ci-triage-20261112.md`: read "What happens to the CI triage" first.

## What the owner decided (coordination record, D138 to D145, 2026-11-12T22:23Z)

- **D138:** amendment N1, draft v12, is ratified with all 34 items (file sha256 `de1f4a1386d2a5b05feba13f4bd6f7518c9768e73fb1f0e4d16c5a79a2f11c18`). Item (u): the pre-reservation margin is 300 s. Item (o): the age is 1200 s.
- **D139:** the `api_runner.py` post-image `830eec1e12e96f807fa76ea26e066a1923b60380013c424cfa99f0012af0a881` is approved. With D127's three, all four protected post-images may be on the branch.
- **D140:** the native production floor is measured on the at-receipt basis of D37. Your basis branch is taken.
- **D141:** rejected and stopped runs keep their records (helper 3's retention branch, after its review fix).
- **D142:** the pending-floor sentence of the model-facing receipt policy becomes, exactly: "A pending floor remains a diagnostic pilot: no coverage fraction is registered, and the measured coverage is recorded as a diagnostic reading."
- **D143:** two registered sets of run limits, the canary's ($90, 21,600 s) and one production set ($400, 43,200 s); helper 2 writes the source change.

## What the lead has already done

The four approved post-images are applied and published: commit `6561dac3c3af50cbfce1ba3c8b6ad21d9cd4b834`, one commit on top of your `ba1f56e4a9460fe87c1e0ea3cb35ed2d7405cfa0`, made in the lead's worktree `E/claude-native-candidate-20261112` and pushed to `codex/native-main-integration-20261112` (draft PR #5968). Each file was copied from your verified packet composition after checking the pre-image and the approved sha256. A real CI run on that head is in progress.

**First step for you:** in your worktree, `git fetch origin` and fast-forward your local branch to `6561dac3c` (`git merge --ff-only`). If you have local commits after `ba1f56e4a`, do not merge or rebase by guesswork: list them and stop for the lead's order.

## What happens to the CI triage

The question of that assignment ("would CI be green with the post-images applied") is now being answered by CI itself. Write down what your CI-equivalent run has established so far (your finding that the 78 recorder ids are the same protected-file gap is accepted), then stop extending it. When the real run finishes the lead will send its inventory; what is left after that is the triage that remains.

## Part 1: the margin (D138, item (u))

`pre_reservation_margin_seconds` becomes 300 in the registered admission terms of `native_u4b_policy.py` and wherever the v2 guard and its tests carry the value. Guard v1 stays byte-identical. One commit with its tests. Say whether the six test files the earlier freshness change touched are the same ones, and whether anything computes the latest admissible capture age from the two values (1200 − 300 = 900 s) in a way that needs a new test.

## Part 2: the basis (D140)

Bring `codex/native-floor-basis-d37-20261112` onto the candidate, with one ruling that changes your proposal: **for a registered (numeric) native floor the basis is mandatory and must be `receipted_part`.** A registration with a numeric floor and no basis refuses; it does not fall back to the final-record fraction. A pending registration is unchanged and may carry the at-receipt counters as a diagnostic reading. The API evaluator stays untouched. Tests for the refusal and for the deletion case (removing unreceipted leaves does not raise the fraction).

## Part 3: the policy asset, prepared as a successor packet for the owner (D142, D140)

Do not change the asset or `canonical_hashes.yaml` on the branch yet: the new post-image hash of `canonical_hashes.yaml` has to be approved by the owner as a number first.

Prepare, in scratch, the asset `src/download/prompts/native_shared_receipt_policy_v1.md` with exactly these two changes in its last paragraph, keeping the file's line wrapping style and changing nothing else:

- replace the sentence "The registered production floor is the exact integer fraction with_receipt / receiptable on the final record, using the unchanged receipt counters." by: "The registered production floor is the exact integer fraction with_receipt_at_receipt / receiptable_at_receipt: the coverage of the sealed phase-1 record under the completed effective receipt (basis receipted_part). Later edits of the record cannot change it."
- replace the sentence "A pending floor remains a diagnostic pilot and cannot satisfy strict completion." by the owner's sentence of D142, exactly as quoted above.

The first replacement is the lead's wording and goes to the owner with the hash; the second is the owner's.

Report: the full new last paragraph as it will read; the asset's whole-file sha256, prompt-body sha256 and byte count; the successor `canonical_hashes.yaml` post-image (built by the same packet tooling as the approved one, on top of the approved post-image `543e5cd6dc0da0f622ba2cd11a16a90732e9302a1ed0a4700efb61971299d252` now on the branch) with its sha256 and its diff against the approved post-image; and every other pin or constant in source that names the asset's hash and must move in the same commit (`native_shared_selection.RECEIPT_POLICY_SHA256`, `ASSET_HASHES`, and whatever else your inventory found). Then run the affected test files in a scratch composition with the successor applied and report from saved output.

## Part 4: integration, when the lead names the commits

Still not yet. Waiting for review or repair: helper 2's cache repair `e079e2f3a` (#5966) and its run-limits change (D143); helper 3's hardening (after #5992 and #5993), failure record (after #6015) and retention (after #6016). The lead sends each when it is reviewed.

## Then

Refresh the scanner pin and the D128-form comparison at the head that carries Parts 1 and 2.

## Bounds

As before. Offline; no provider, model or native-binary execution; nothing pushed (the lead pushes); no GitHub write. Apart from the four approved post-images already on the branch, no protected file changes without the owner's approval of its new hash.

## Handoff

`R/notes/development_efficiency_20261111/handoffs/codex-h1-owner-decisions-integration-20261112.md` with its JSON. Answer first: your branch head after the fast-forward and each part's commit; the successor packet's numbers (Part 3) in a block the lead can show the owner; the tests from saved output. Write a first version when Part 3's numbers exist, since the owner's approval waits on them.
