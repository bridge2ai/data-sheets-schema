# AGY2 assignment from the Claude lead: check the A21 re-review scope mechanically

Track: final generation (first priority). Read-only. Deliverable is one file
and one small script.

## Your shard-count sizing: accepted

`handoffs/agy2-shard-count-option.md` is read and accepted. The three points
that change the picture, which the lead is taking to the owner as they stand:
the runner pool the repository's own notes record is about 20 jobs, so ten
shards plus a split lane would queue; the replay at other counts was diluted
by mixing files from fast and slow runners, so ten shards is nearer 28
minutes than 26; and twelve shards buys nothing because one file fills a
shard alone. No shard-count change is being proposed on this evidence. One
item I could not confirm: `notes/reviews/ci_queue_checkpoint_2026-11-10.md`
is not in the primary checkout. Say in your handoff which tree you read it
from.

## New task

AGY3's runbook (`handoffs/agy3-a21-rebuild-runbook.md`, section 2) says that
between the M4 registration's base `673838c51547278cfd79254670ec95421c7bcaf7`
and current main plus PR 5808, exactly six pinned items moved: the two merged
schema files, `api_runner.py`, `schema_digest.py`, `bc1_audit.py` and
`bc1_context.py`; and that the other 46 pinned Python files, the nine prompt
and command assets, the instruction hashes and the non-schema inputs did not.
That table is the scope of the registration re-review, and nobody has
checked it against the bytes. Check it.

1. Read the M4 registration
   `d4d-executions/plans/a21_registration_2026-11-05a_claude-opus-5-api-bc1-a21_rep1/registration_chorus_2026-11-05a_claude-opus-5-api-bc1-a21_rep1.json`
   (and its roster and sizing record beside it). Enumerate every place it
   pins a repository file by path with a sha256: inputs, runtime
   configuration, selection assets, the request-code and bounded-carry code
   lists, contract and instruction hashes that name a file. Record the JSON
   pointer of each.
2. For each pinned repository path, compute the sha256 of that path's bytes
   at the merge preview commit `44b8a6595c2abc3b91effe4b50cf0e7f9dad19c9`
   (main `925d726d` plus the PR head `6792947e`) with `git show
   <commit>:<path>` in the primary repository, read-only. A path that does
   not exist at that commit is a result, not an error. Inputs that live
   outside git at the launch base (`launch-a21/data/...`) are hashed from the
   file on disk; say so per row.
3. Compare. Report every pinned item whose bytes differ from the M4 pin,
   every one that is equal, and any pinned hash you could not map to a file
   (name it and say what it hashes if the code tells you).
4. Set your result beside AGY3's table: which of its six are confirmed,
   whether anything else moved that it does not list, and whether any of its
   "did not move" claims is wrong. For each file that moved, name the merged
   PRs that touched it between the two commits (`git log --oneline
   673838c51..44b8a6595 -- <path>`).

Write the comparison as a script, not by hand:
`scripts/adhoc/check_a21_pinned_closure_20261111.py` in the report worktree
(`codex-development-efficiency-20261111`), with the usual header (purpose,
inputs, outputs, what it serves, date). It reads the registration and calls
`git show`; it writes one JSON file under that worktree's
`tmp/a21-pinned-closure-20261111/` and nothing else. Run it once with the
primary checkout's interpreter.

## Bounds and handoff

- Read-only apart from that script and its JSON output. No edits to the
  runbook (report disagreements; AGY3 owns the file). No registration
  builds, no dry-runs, no network, no tests, no pushes, no comments.
- Do not write in `launch-a21`, `plans/`, or any other worktree.
- Write `handoffs/agy2-a21-pinned-closure-check.md` in this notes directory:
  the counts, the table of moved items with old and new sha256 and the PRs
  responsible, the disagreements with the runbook if any, the script's path
  and SHA-256 and the JSON's path and SHA-256, and what stays unverified. No
  at-sign handles. Print its path and SHA-256 and stop.
