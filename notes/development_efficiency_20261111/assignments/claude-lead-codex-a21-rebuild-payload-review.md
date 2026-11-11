# Codex helper assignment from the Claude lead: payload review of the rebuilt A21 registration

Track: final generation (first priority). Offline, no spend, scratch-only.
One bounded task; report back to the lead and stop.

## State (owner decisions D130 and D131, 2026-11-11T16:12:28Z, in `data-sheets-schema/notes/coordination/STATUS.md`)

- PR 5808 is merged: main is `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`
  (parents `925d726d6…`, `6792947ea…`), schema 3.2.1.
- The owner released the D89/D93/D129 hold for the A21 rebuild. No launch
  word exists. The owner launches personally (D43).
- The lead moved `d4d-executions/launch-a21` to that commit (status
  `?? poetry.toml` only) and built, checked and dry-ran a new packet with
  `codex-development-efficiency-20261111/scripts/adhoc/a21_rebuild_on_merged_main_20261111.sh`.

New packet: `d4d-executions/plans/a21_registration_2026-11-11a_claude-opus-5-api-bc1-a21_rep1/`,
label `2026-11-11a_claude-opus-5-api-bc1-a21_rep1`.

| File | Bytes | sha256 |
|---|---:|---|
| roster | 447 | `d49cc3529a11e60716cde4affc6f5deec521b861576fcae6b961e2f74060dd63` |
| registration | 26,284 | `55691023e1d75c3bf5f9df09dcb524b4536870b93a4a3dde67306276f082aa1a` |
| sizing record | 32,182 | `0ae32356404e52d28acf0ff9ae8e39707947664df7506104a52fbab438465c87` |

Logs: `plans/a21_registration_2026-11-11a_claude-opus-5-api-bc1-a21_rep1.{preflight,builder,check,dryrun}.log`.

## What the lead has already established (do not repeat)

Leaf comparison against the M4 packet
(`codex-development-efficiency-20261111/tmp/a21-rebuild-review-20261111/leaf_diff_m4_vs_rebuild.json`):

- registration: 367 to 351 leaves, 335 equal. The changed leaves are the
  hashes of six files (two merged schemas, `api_runner.py`,
  `schema_digest.py`, `bc1_audit.py`, `bc1_context.py`), the two schema byte
  counts, the label, and `bounded_carry.contract.context` moving from
  `bc1_neutral_term_policy_v1` (hard-coded fallback and IRI prefixes) to
  `bc1_neutral_term_policy_v2` (`forms_annotation: d4d:termSourceIdentifierForms`).
- sizing record: every one of the sixteen typed-call rows grew by exactly
  4,453 wire bytes and about 1,626 estimated input tokens. Measured-escape
  aggregate 3,748,757 to 3,760,138 of 4,500,000.

AGY2 is doing an independent identity review of the same three files. That
leaves the part only the capture can show: **what changed in the bytes a model
would be sent.**

## Task

Using the existing capture and comparison tooling from the M4 review
(`d4d-executions/scratch-a21-precheck/scripts/adhoc/`, and the REAL run
recorded in
`plans/reviews/a21_registration_review_2026-11-05/capture-fix-20261105-r2/REAL.request.json`
with its capture in `.../capture2/`):

1. Capture the 20 model-facing payloads for the **new** packet, offline, once,
   after the tooling's own canary. Keep the same fixtures the M4 capture used
   (the 2026-10-31 run date, the 10-22a historical inputs, the empty future
   audit carry) so that the only differences are the ones the rebuild made.
2. Compare each new payload with its M4 counterpart in `capture2/captured/`.
   For every payload report old bytes, new bytes and the delta, and attribute
   **every differing byte** to a named cause: the label, or a specific change
   in the schema text between 3.1.0 and 3.2.1 (PR 5531's D98/D99 changes and
   PR 5808's `collection_type` wording), or the term-policy context v1 to v2.
   Show the actual differing text for one typed call and for each of `full`,
   `full_receipt_completion`, `reconcile_full` and `report`. A difference you
   cannot attribute is listed as unexplained; the count of those is the
   verdict.
3. Confirm the new sizing record's `wire_bytes` and `wire_sha256` for the
   typed rows equal your captured payloads.
4. Re-price with the existing spend helper: expected, at caps, at caps with
   cache writes, and the worst single in-flight call, beside the M4 figures
   ($31.66, $43.17, $44.25, $8.65). Say whether a $51 stop trigger still keeps
   the worst case under $60.

## Bounds

- Offline: provider keys and `D4D_MANIFEST` removed, the existing socket and
  remote-Git guards kept. No provider call, no `d4d api batch` without
  `--dry-run`, no pytest campaign.
- `launch-a21` and the two `plans/a21_registration_*` directories are
  read-only. Prove it the way the M4 review did (HEAD, status and a tree hash
  before and after).
- Write only under a new directory
  `d4d-executions/plans/reviews/a21_registration_review_2026-11-11/` and, for
  helpers you must change, new files beside the old ones in
  `scratch-a21-precheck/scripts/adhoc/` (keep the originals byte-identical).
  Nothing under `/tmp`.
- No commit, push, PR, issue, comment or STATUS edit. No at-sign handles.
- Do not direct other workers. If the tooling cannot capture the new packet
  without a production change, stop and report that instead.

Report: `d4d-executions/plans/reviews/a21_registration_review_2026-11-11/codex_payload_review.md`
with the verdict first, then the per-payload table, the attribution, the
re-pricing, evidence paths with SHA-256, and what stays unverified. Print its
path and SHA-256 and stop.
