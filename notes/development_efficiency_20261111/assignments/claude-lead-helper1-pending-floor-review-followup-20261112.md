# Assignment to Codex helper 1: the two review findings on the pending-floor repair, then the integration of the reviewed branches

From the Claude lead, 2026-11-12. Short names and rules are in `claude-lead-helper-context-20261112.md` beside this file.

## Standing

Your work so far is accepted as work done: Part 1 integrated (published by the lead as draft PR #5968 at `0fc003a86081891abbe8e130ac760c01da06423e`, for a CI run only); the pending-floor repair `e5fe279a3a685985c51589c867632424e8c110c4` with its tests; the scanner test revisions; the basis proposal on its separate branch, which waits for the owner. The lead read the repair's source: the exception is taken from the captured selection's registration, the structural floors keep gating, the API path is untouched.

An independent read-only Codex CLI review of the repair (`E/plans/reviews/native_pending_floor_e5fe279a_codex_review_2026-11-12.md`, SHA-256 `8dd74193bc9e2be730f53f9ff5fb462801b2d021fa2c130a7d2195b738e8b8fd`) says: acceptable after listed fixes. It confirms the structural floors at all three places, the constrained exception, fail-closed exceptions and the pending reading kept as `passed: False`. Two findings, filed:

## Part 1: issue #5994 (P1), the recorded-run path still fails a pending floor

A completed native run can be checked from its saved provenance without `--native-shared-selection` (`receipts.block_for()` through `recorded_receipt_block()`, `receipts.py` about lines 2694 to 2709). On that path `native_capture` stays `None`, so `cli/receipts.py` (about lines 306 to 330) skips `final_receipt_floors()` and falls back to `strict_failure()`, which counts pending coverage as a failure. So `d4d receipts check --method M --label L --project P --strict` still exits non-zero for a clean diagnostic pilot, and the outcome depends on a flag although the saved run already carries its selection.

1. Confirm it with a test first.
2. Repair: the validated selection from the recorded native reconstruction is carried into the final-floor decision, and the native helper is used for both the live and the recorded native assessment. Permission is never inferred from a pending marker in the receipt block. A recorded run whose saved selection cannot be validated refuses; it does not fall back to the generic predicate as if it were an API record, and it does not pass.
3. Say what distinguishes a recorded native run from an API record on this path, and show with a test that an API record cannot reach the native helper and a native record cannot reach the API fallback.

## Part 2: issue #5995 (P2), the tests the review found missing

CLI regression cases, asserting exit status and the retained coverage fields: a recorded native run with a pending floor, with and without the selection flag; a pending floor with a structural failure; a registered numeric floor that passes and one that fails; the API route under pending, pass and fail, unchanged from the base; and the rejection of a native selection flag on an API record.

## Part 3: integrate the reviewed branches when the lead names them

Not yet. Helper 3's launch-sequence hardening (`codex/native-launch-sequence-hardening-20261112`) has two review findings to repair first (issues #5992, #5993), and helper 2's HOME cache repair (#5966) and helper 3's failure-record repair (#5967) are in progress. When each is reviewed the lead will send you its commits. Until then do not take them.

After Parts 1 and 2: refresh the scanner pin and the D128-form comparison only if a source file under the scanner's authority changed since your last comparison; say which did.

## Bounds

As before. Offline; nothing pushed; no GitHub write; protected files equal to main on the branch; the policy asset `src/download/prompts/native_shared_receipt_policy_v1.md` is not edited (its wording goes to the owner; restate in your handoff the exact sentence, your smallest rewording, and every pin that would move, if you have not already).

## Handoff

Update `R/notes/development_efficiency_20261111/handoffs/codex-h1-integration-and-pending-floor-20261112.md` and its JSON. Answer first: the #5994 commit and what the recorded path now does; the #5995 test list with results from saved output; the candidate's head.
