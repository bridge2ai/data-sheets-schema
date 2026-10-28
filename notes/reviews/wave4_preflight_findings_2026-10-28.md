# Preflight review follow-up — 2026-10-28

Reviewed upstream #5095 head `af86168305ceb92c78fbcaaca4ab7571842264d4`.
This branch repairs the remaining #5122 and #5124 findings. It does not
authorize generation or scientific scoring. No provider calls are needed.

## #5122 — schema closure and selected worktree

The original Wave 4 independent suite passed 80 cases and failed three:
both full/core schema roots could change after registration while `--check`
reported success, and `build_registration(worktree=...)` captured schemas from
the caller's tree instead of the requested tree. The later generation capture
has separate guards; these failures demonstrate false-green preparatory checks,
not a demonstrated paid-generation bypass.

Repair must check every pinned schema source, including imported sources and
closure identity, and consistently resolve manifest, context, schemas,
vocabulary, runtime config and prompt assets from the selected worktree.
Explicit worktree selection must also work when invoking a copied script.
Missing selected resources must not silently fall back to another checkout.

Existing open issue: https://github.com/bridge2ai/data-sheets-schema/issues/5122

## #5124 — attributable appended launch logs

The current header records the command and worktree, but omits the time and
approval digest requested by F13. Return the normalized digest(s) from the
actual command validator, write an aware UTC timestamp and those digests, and
flush before spawning. A command without registration approval must say `none`.
Record the approved roster digest when that was the approved object; do not
mislabel it as an individual registration's digest. Quote command arguments
containing spaces. Do not record credential values.

Existing open issue: https://github.com/bridge2ai/data-sheets-schema/issues/5124

## CI failure — nested detached-launch test virtualenv loses dependencies

Filed as https://github.com/bridge2ai/data-sheets-schema/issues/5228.

The completed Python 3.12 / shard 5 job for #5095 failed one test; the other
3,147 cases in that job passed:
https://github.com/bridge2ai/data-sheets-schema/actions/runs/40615881436/job/122578130439

`TestLauncherCLI.test_background_launch_redirects_stdin_and_survives_closed_fd0`
failed before its stdin assertion: the production import-isolation guard
could not import `data_sheets_schema.api_runner` because `yaml` was missing.
The fixture symlinks the base virtualenv's interpreter and `lib`, but does not
copy `pyvenv.cfg`. Linux then discovers the base interpreter instead of the
intended virtualenv and loses its installed dependencies.

Copy the base virtualenv's configuration into this synthetic test environment.
Keep the production import-isolation check, detached child, closed fd 0,
`stdin=DEVNULL` assertion, and actual prompt-pin check unchanged. The supplied
CI failure is the baseline evidence; a local macOS pass alone cannot prove
the repaired fixture works on Linux. The updated PR must pass that CI shard.

## Merge prerequisites

#5095 targets #5094, which targets #5093. Merge commits and base/CI verification
are required in that order to preserve the canary ancestors `723c8ac20` and
`77b94e457`. Local owner worktrees and evidence must be preserved. The exact
PR scope for the user's merge/deletion request is awaiting clarification.

The live #5093 description still describes pre-D38 pins and says the spelling
decision is pending despite head `f73764e06`. Its description needs correction
under existing #5100 before claiming that prerequisite is review-complete.
