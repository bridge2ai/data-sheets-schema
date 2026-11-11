# AGY3 assignment from the Claude lead: make the A21 monitoring and post-run checklist match what the code writes

Track: final generation (first priority). Read-only apart from one new
handoff file and one script.

## State

The owner approved the merge of PR 5808 and released the A21 hold (D130 and
D131, 2026-11-11, in `data-sheets-schema/notes/coordination/STATUS.md`). Main
is `7ad8c9e7295f1575ae9108ea62c12c83b1dd4db1`. The lead ran your runbook's
steps 1.1 to 1.4 with
`codex-development-efficiency-20261111/scripts/adhoc/a21_rebuild_on_merged_main_20261111.sh`;
all passed. New label `2026-11-11a_claude-opus-5-api-bc1-a21_rep1`, roster
sha256 `d49cc3529a11e60716cde4affc6f5deec521b861576fcae6b961e2f74060dd63`.
`launch-a21` is at the merge commit. Nothing is launched; no launch word
exists.

## What was wrong in the runbook (found while executing it)

1. **The monitoring command does not run.** Section 3 gives
   `api_dollar_readout.py --label "$L" --cap … --trigger … --watch`. Run as
   written it prints `Error: Must specify a ledger file or --metadata-dir.`
   and exits 1 (the 2026-11-05 packet has the same line). It needs
   `--metadata-dir <the run's core directory> --project CHORUS`, and that
   directory and the ledger file must already exist.
2. **Section 4 names files the code does not write.** An earlier
   generic_v10 API run of the same project, archived in the launch base at
   `data/ATTIC/d4d_concatenated_archived/claudecode_api/2026-10-22a_claude-opus-5-api-generic-v10_rep1/`
   and `.../claudecode_api_core/2026-10-22a_claude-opus-5-api-generic-v10_rep1/`,
   holds `CHORUS_d4d.yaml`, `CHORUS_provenance.yaml` and
   `CHORUS_api_usage_<id>.json`, not `CHORUS_full.yaml`,
   `CHORUS_generation_provenance.yaml`, `usage_ledger.json` or
   `latch_journal.jsonl`. The journal is
   `<metadata dir>/<PROJECT>_latch_journal.jsonl`
   (`src/data_sheets_schema/latch_journal.py:193`).
3. **Step 1.1's import proof.** `data_sheets_schema` is a namespace package
   (no `__init__.py` at either commit), so `data_sheets_schema.__file__` is
   `None`. The proof is `__path__` and a module's `__file__`.

## Task

Produce a checklist the owner and the lead can follow literally during and
after the run. Derive every name from code or from a real listing:

1. **Where things are written.** For label
   `2026-11-11a_claude-opus-5-api-bc1-a21_rep1`, project CHORUS, method
   `claudecode_api`: the full-record directory, the core/metadata directory,
   the `intermediate/` directory, and the exact file name of each of: the
   full record, the core record, the provenance record, the coverage receipt,
   the report, the usage ledger, the latch journal, the progress file, the
   run lock, the BC1 typed-audit request/response/context files, the
   receipt-completion files. For each: the function that builds the path
   (file and line at commit `7ad8c9e72`, read with `git -C <launch-a21> show`
   or from the working tree, which is at that commit) and, where the archived
   10-22a run has the same kind of file, that file's actual name as a
   cross-check. Mark names the archived run cannot confirm (BC1 and the latch
   journal postdate it) as read from code only.
2. **The working monitor commands**, each tested read-only against the
   archived 10-22a core directory where possible: the one-shot readout with
   `--json` (state its exit codes for trigger and cap, from the script), the
   watch form, and `d4d api status`. Give the exact command lines for the new
   label.
3. **After-run commands.** The exact, existing command lines for
   `d4d api verdict`, `d4d runs check --strict`, `d4d receipts check --strict`
   and the product check
   `scripts/adhoc/check_final_generation_products_20261110.py`, with the
   options each needs for this label and method. Take the options from each
   command's `--help` run in `launch-a21` with the provider keys removed
   (`env -u CBORG_API_KEY -u ANTHROPIC_API_KEY`); do not run the commands
   themselves against any run.
4. **A corrected list** of the files that must exist and be non-empty after a
   complete run, and the counters that must have moved, replacing your
   section 4 A and B. Keep section 4 C as it is unless a cited section number
   in `docs/final-generation-acceptance.md` at the merge commit is wrong;
   check each citation.

## Rules

- No run of `d4d api batch`, the launcher with `--launch`, the builder, or any
  test. `--help`, `d4d api status` and the readout against the **archived**
  directory are allowed. No write in `launch-a21`, `plans/` or another
  worktree. No network, push or comment. No at-sign handles.
- Every path and file name in a table is written by a script from a listing
  or from a grep of the code, with the command shown. Put the script in
  `codex-development-efficiency-20261111/scripts/adhoc/` with the usual
  header. Mark each row as "listing", "code" or "inference".
- Do not edit `agy3-a21-rebuild-runbook.md`; the lead keeps it as the record
  of what was executed.

Write `handoffs/agy3-a21-post-run-checklist.md` in this notes directory,
print its path and SHA-256, and stop.
