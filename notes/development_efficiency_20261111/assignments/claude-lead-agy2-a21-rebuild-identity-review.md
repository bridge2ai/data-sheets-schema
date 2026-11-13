# AGY2 assignment from the Claude lead: independent identity review of the rebuilt A21 registration

Track: final generation (first priority). Read-only review. You did not build
this registration, which is why you are reviewing it.

## What happened (owner decisions D130 and D131, 2026-11-11, recorded in `data-sheets-schema/notes/coordination/STATUS.md`)

- The owner approved the merge of PR 5808. It is on main as merge commit
  `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1` (parents `925d726d6…` and
  `6792947ea…`). Its tree equals the tree of the preview commit `44b8a6595`
  that your pinned-closure check used.
- The owner released the hold on A21 for the rebuild. Nothing is launched.
- The lead moved `d4d-executions/launch-a21` to that merge commit and built a
  new packet with
  `codex-development-efficiency-20261111/scripts/adhoc/a21_rebuild_on_merged_main_20261111.sh`
  (steps `preflight`, `move`, `build`, `check`, `dryrun`).

New packet: `d4d-executions/plans/a21_registration_2026-11-11a_claude-opus-5-api-bc1-a21_rep1/`

| File | Bytes | sha256 |
|---|---:|---|
| `roster_2026-11-11a_claude-opus-5-api-bc1-a21_rep1.json` | 447 | `d49cc3529a11e60716cde4affc6f5deec521b861576fcae6b961e2f74060dd63` |
| `registration_chorus_2026-11-11a_claude-opus-5-api-bc1-a21_rep1.json` | 26,284 | `55691023e1d75c3bf5f9df09dcb524b4536870b93a4a3dde67306276f082aa1a` |
| `registration_chorus_2026-11-11a_claude-opus-5-api-bc1-a21_rep1.sizing.json` | 32,182 | `0ae32356404e52d28acf0ff9ae8e39707947664df7506104a52fbab438465c87` |

Sibling logs in `d4d-executions/plans/`:
`a21_registration_2026-11-11a_claude-opus-5-api-bc1-a21_rep1.{preflight,builder,check,dryrun}.log`
and `.sha256`.

Old packet (M4, kept as evidence):
`d4d-executions/plans/a21_registration_2026-11-05a_claude-opus-5-api-bc1-a21_rep1/`
(roster `d4ac7f88…`, registration `f7e9b705…`, sizing `56c1514e…`).

## Your task

Establish, from the bytes and with your own script, whether the new packet
differs from the M4 packet only where the six moved pinned files and the new
label require. Do not start from the lead's result; the lead's own leaf
comparison exists and will be set beside yours afterwards.

1. **Hash the three new files and the three logs' claims.** Confirm the table
   above, that the builder log's printed digests equal the bytes on disk, that
   the sizing record's `registration_sha256` equals the registration's
   sha256, and that the roster names that registration path and sha256.
2. **Every pinned repository file.** For each place the new registration and
   its sizing record pin a repository path beside a sha256, compute the sha256
   of that path at `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1` with
   `git -C <launch-a21> show <commit>:<path>` and compare. Count pins, equal,
   unequal. Then compare the same pins with the M4 registration: which paths
   changed hash, which pinned paths were added or dropped. The expectation to
   test (not to assume) is exactly six changed files: the two merged schema
   files, `api_runner.py`, `schema_digest.py`, `bc1_audit.py`,
   `bc1_context.py`.
3. **Every other leaf.** Flatten both registrations, both sizing records and
   both rosters to JSON leaves. Report every leaf added, removed or changed
   that step 2 does not cover. For each one, say what in the repository
   produces it (file and line at the merge commit) and whether the change
   follows from one of the six files or from the label. Anything you cannot
   trace is listed as unexplained, with no guess attached.
4. **The context block.** The new registration's
   `bounded_carry.contract.context` and the sizing record's
   `sizing.source_identity.context` differ in shape from M4's. Read
   `src/data_sheets_schema/bc1_context.py` at both commits and state exactly
   what the old block carried, what the new one carries, and where the removed
   content now comes from at run time (name the schema annotation and show
   the slots that carry it in `data_sheets_schema_all.yaml` at the merge
   commit, with line numbers from `git show`, not from memory).
5. **The sizing rows.** The sixteen `sizing.rows` changed in wire bytes,
   token estimates and wire hashes. Report the per-row and aggregate deltas
   against M4, the largest call against its context room, and the aggregate
   against `audit_limits.aggregate_input_tokens`. State whether any row's
   `estimated_context_fits` or `gated` value changed.

## Rules for the handoff (these bit earlier today)

- Every table is written by a script from a JSON file your script produced.
  No file name, hash, count or line number typed by hand. Show the command.
- Scripts go in
  `codex-development-efficiency-20261111/scripts/adhoc/` with the usual header
  (purpose, inputs, outputs, what it serves, date). Outputs go under
  `codex-development-efficiency-20261111/tmp/a21-rebuild-review-20261111/agy2/`.
  Do not read or reuse `leaf_diff_m4_vs_rebuild.json` in the parent directory
  until your own result is written; then state the differences between the
  two in one short section.
- Read-only everywhere else: no write in `launch-a21`, `plans/` or any other
  worktree; no builder, launcher, `d4d` or test run; no network; no push; no
  comment. Use the primary checkout's interpreter
  (`data-sheets-schema/.venv/bin/python -I`) and `git show`.
- No at-sign handles anywhere.

Write `handoffs/agy2-a21-rebuild-identity-review.md` in this notes directory:
verdict first (the number of unexplained differences), then the tables, the
script and JSON paths with their SHA-256, and what stays unverified. Print
its path and SHA-256 and stop.
