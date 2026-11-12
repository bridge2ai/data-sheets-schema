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

**First step for you:** fast-forward your local branch to the lead's local head `a23ebf753` (see Part 3), which contains `6561dac3c`. If you have local commits after `ba1f56e4a`, do not merge or rebase by guesswork: list them and stop for the lead's order.

## What happens to the CI triage: CI has answered, five tests are left

Real CI ran on `6561dac3c` with the four post-images applied (run 43319698046; inventory `R/notes/development_efficiency_20261111/handoffs/lead-ci-run-43319698046-failures-20261112.json`). **593 failing ids became 5.** Your finding that the recorder class was the protected-file gap is confirmed. Stop the offline triage; write down what it established, and take these five instead, one commit per cause:

1. `tests/test_wave7_5213_d76_round4_inventory.py::test_every_public_runspec_boundary_has_an_explicit_contract`: "src/data_sheets_schema/native_shared_capture_orchestration.py:528 … recorded_receipt_assessment: needs exactly one RunSpec boundary declaration". Your #5994 repair added a public function that takes a RunSpec boundary. The contracts live in `tests/utils/run_spec_boundary_contracts.json`, which is a protected file. **First choice: change the repair so that it adds no new public RunSpec boundary** (for example by reaching the recorded assessment through a boundary that is already declared, or by keeping the new function out of the public boundary inventory in the way the inventory itself defines). Only if that is impossible, prepare the successor post-image of the contracts file in scratch with its sha256 and say why, and the lead takes it to the owner.
2. `tests/test_native_pending_public_completion.py::test_pending_floor_public_completion_retains_diagnostic_reading`: "native controller dependency imported from another origin: prepare_registration". Your new test needs the import-origin isolation the other native test files received in `f25230fe1`.
3. `tests/test_native_shared_owner_delivery.py::test_replay_owner_reuses_catalog_and_unknown_initialization_is_fresh[case0]`: `assert (None is None and None is not None)`. Not seen before; find the cause from the CI log, do not guess.
4. `tests/test_native_shared_execution_variant.py::test_actual_public_merged_omissions_and_all_chunk_statuses`: "subscription observation is stale or future-dated". In CI this public completion test stops on freshness before it reaches anything else. Helpers 2 and 3 saw the same on this machine. Helper 2 is asked for the fixture's slack; if you get there first, establish from the fixture how many seconds a slow host has before the synthetic observation goes stale, and propose the smallest fixture change that keeps the freshness check real. Do not change the production check.
5. `tests/test_native_d128_scanner_comparison.py::test_d128_final_composition_has_only_the_finite_approved_scanner_differences`: "D128 requires the exact approved scanner assets". Expected until the owner disposes of the new scanner comparison; produce that comparison in the D128 form at the integrated head so that the lead can put it to the owner, and say exactly which scanner assets differ from the approved ones.

**Shard time.** Shards 1 and 4 were cancelled at the 45-minute limit, and shards 5, 8 and 3 took 42.6, 42.3 and 39.9 minutes. The lead is asking the owner for more shards. Say which test files dominate shards 1 and 4, from the weights and from this run's logs.

You have a local commit `767eca31e` after `ba1f56e4a`, so your branch and the lead's have diverged. Do not rebase the lead's commits (the registry pin names `a23ebf753` by hash). List your local commits in the handoff; the lead will order the integration, most likely by cherry-picking yours onto its head.

## Part 1: the margin (D138, item (u))

`pre_reservation_margin_seconds` becomes 300 in the registered admission terms of `native_u4b_policy.py` and wherever the v2 guard and its tests carry the value. Guard v1 stays byte-identical. One commit with its tests. Say whether the six test files the earlier freshness change touched are the same ones, and whether anything computes the latest admissible capture age from the two values (1200 − 300 = 900 s) in a way that needs a new test.

## Part 2: the basis (D140)

Bring `codex/native-floor-basis-d37-20261112` onto the candidate, with one ruling that changes your proposal: **for a registered (numeric) native floor the basis is mandatory and must be `receipted_part`.** A registration with a numeric floor and no basis refuses; it does not fall back to the final-record fraction. A pending registration is unchanged and may carry the at-receipt counters as a diagnostic reading. The API evaluator stays untouched. Tests for the refusal and for the deletion case (removing unreceipted leaves does not raise the fraction).

## Part 3: the policy asset: the lead has prepared it; you validate it (D142, D140)

Changed by the lead before this file was delivered. The lead made the asset change itself, so that the owner could be asked for the new hash today.

- Local commit `a23ebf75391170de924cf023727ae103d60fc13d` on the lead's branch `claude/native-candidate-20261112`, one commit on top of `6561dac3c`, **not pushed**: the asset `src/download/prompts/native_shared_receipt_policy_v1.md` with its last paragraph's two sentences changed (the owner's sentence of D142, and the lead's sentence for the at-receipt basis), and `native_shared_selection.RECEIPT_POLICY_SHA256` moved to the asset's new sha256 `8b0695212d94380949ddc523963021b1edcb3ebb9b6a52291d36238a92779f1c` (2,510 bytes).
- The successor post-image of the protected `canonical_hashes.yaml`, made by `d4d api prompts pin` at that commit and kept in `E/scratch-lead-policy-packet-20261112/` (`canonical_hashes.postimage`, sha256 `d0de85f3da4bfa29a4bfc7ad6158abad5b3373a937a4e7e3b360217fa4eaf57f`; its `README.md` says how it was made). One registry entry changes. `d4d api prompts check --strict` reports 28 prompt files, 0 not at their pin, with it applied. It is **not** on any branch: the owner has to approve that sha256 first.

Your first step therefore becomes: fast-forward your local branch to `a23ebf753` (the lead's local branch is visible from your worktree; `git merge --ff-only claude/native-candidate-20261112`).

Then validate, in a scratch composition with the successor post-image applied (copy its exact bytes; do not re-run the pin command, which writes the day's date):

1. every other pin or derived identity that names the asset and must move in the same change. The lead found one in source (`RECEIPT_POLICY_SHA256`) and one stale copy in `scripts/adhoc/native_u1_packets/canonical_hashes.patch`, which is historical. Your earlier inventory named more (the receipt registration and selection identities, the render and execution authority, scanner evidence): say for each whether it is a stored value that must be edited or a value derived at run time;
2. the test files that read the asset, its hash or a registration built from it: run them whole and report from saved output. Fix fixtures that embed the old identity, in their own commit, without weakening what they assert;
3. whether the asset's new sentence on the basis says exactly what Part 2's code does. If the code and the sentence differ in any case, say which and propose the smallest change to the code, not to the sentence (a change to the sentence changes the hash the owner is approving).

## Part 4: integration, when the lead names the commits

Still not yet. Waiting for review or repair: helper 2's cache repair `e079e2f3a` (#5966) and its run-limits change (D143); helper 3's hardening (after #5992 and #5993), failure record (after #6015) and retention (after #6016). The lead sends each when it is reviewed.

## Then

Refresh the scanner pin and the D128-form comparison at the head that carries Parts 1 and 2.

## Bounds

As before. Offline; no provider, model or native-binary execution; nothing pushed (the lead pushes); no GitHub write. Apart from the four approved post-images already on the branch, no protected file changes without the owner's approval of its new hash.

## Handoff

`R/notes/development_efficiency_20261111/handoffs/codex-h1-owner-decisions-integration-20261112.md` with its JSON. Answer first: your branch head after the fast-forward and each part's commit; the successor packet's numbers (Part 3) in a block the lead can show the owner; the tests from saved output. Write a first version when Part 3's validation is done, since the lead applies the successor post-image as soon as the owner approves its hash.
