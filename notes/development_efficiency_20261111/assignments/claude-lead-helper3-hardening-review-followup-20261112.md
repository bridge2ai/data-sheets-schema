# Assignment to Codex helper 3: the two review findings on your launch-sequence hardening

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file. This comes after your current assignment (`claude-lead-helper3-failure-record-and-retention-20261112.md`); if it reaches you while that is unfinished, finish Part 1 of that one first (issue #5967), do this, then return to its Part 2.

## Standing

An independent read-only Codex CLI review of your three hardening commits (`E/plans/reviews/native_hardening_c1ad9baa_codex_review_2026-11-12.md`, SHA-256 `bbb320bf088aaf55e8918a200ae764d1d8406c16744617769b4d466b3b49b36f`) says: acceptable after listed fixes. It confirms that packet path, working directory and fractional spellings of the same instant do not renew a claim while its state is intact; that the entry reads, compares, compiles and forwards one captured byte string; that every child receives inline digests and compares the bytes it consumes before any effect; and that guard v1 and every registered document's kind and version are unchanged. Two findings, both P1, filed:

## Part 1: issue #5992, replacing the claim directory renews a consumed direction

`src/data_sheets_schema/native_sequence_start.py`, about lines 44 to 66. After a delegated sequence has claimed its direction and capture refused, renaming `.native-sequence-starts/<registration-sha256>` and creating an empty directory at its former path lets a second invocation with the same direction create the same claim file again. The symlink check does not see a replaced physical directory, and validation, claim creation and directory sync resolve the path separately.

The lead's rulings:

1. **A missing claim state is not an empty one.** This machine has cleanup jobs and other sessions; a deleted or replaced state directory must refuse a delegated start, not admit it.
2. **Anchor the claim in state that already carries this run's one-use rules,** if there is such state and it is established before the launch: the registered capture and word state that enforces the three captures per word (D115) is the first place to look. If the claim can live under that state's lock and integrity rules, put it there; if not, say why and give the smallest alternative (state initialised once with an identity that the registration or the launch word pins, and refused when missing or different).
3. Create and sync the claim relative to held directory descriptors with identity checks, so that there is no check-to-use window on the ancestors.
4. An owner start is still repeatable, and a delegated start under a newly recorded direction is still admitted.

Tests: the replaced-directory case and a directory swap between validation and claim, each asserting zero further capture calls; the missing-state refusal; the two admitted cases above.

## Part 2: issue #5993, the imported sequence body bypasses the verified entry

`src/data_sheets_schema/native_launch_sequence.py`, about lines 135 to 174; `tests/test_native_launch_sequence.py`, lines 20 to 24. An imported caller can call `_run_verified(arguments, verified_script=B, entry_inputs={})` directly: the body retains B without verifying its pins or its relation to the code that is running, and empty `entry_inputs` makes the input comparison vacuous. That reopens the gap #5990 was to close.

Repair: an ordinary imported invocation of the body refuses before any packet is created; the body runs only in the namespace the verified entry establishes; every supported entry point goes through the entry. The unit tests that drive the body directly with fixture bytes need another route that does not leave a production bypass (for example an entry-level test seam that still verifies the fixture bytes against fixture pins). Tests: a direct-import refusal, and the loaded-A, retained-B witness through the import route.

If either repair cannot be made without changing a registered document's kind or version, stop and propose, as before.

## After both

Run every touched test file whole and the candidate's launch-sequence and review-bundle files, from saved output. One commit per issue on `codex/native-launch-sequence-hardening-20261112`. Your failure-record branch started from `c1ad9baa1`: say whether it needs these commits and how you will carry them (a merge or a cherry-pick into that branch, recorded), so that the lead can order the integration.

## Bounds

As before. Offline; no real-binary execution, no probe, no capture, no reservation; no provider or model call; nothing pushed; no GitHub write.

## Handoff

Update `R/notes/development_efficiency_20261111/handoffs/codex-h3-launch-sequence-hardening-20261112.md` and its JSON. Answer first: the two commits, where the claim now lives and what it trusts, what an imported call of the body now does, and the test counts.
