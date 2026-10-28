# Recovered original progress backup (#5233 / #5096)

`CHORUS_api_progress.json` is the byte-identical existing original from the
read-only preserved AGY scratch snapshot. It records pre-edit progress for
10-20a, the assisted canary that remains invalid and archived as evidence only.
Its source, digest, size and the bounded credential scan are in `manifest.json`.

The #5096 archive README already lists this original among eight backups, but
the reviewed commit `ada98b56b73b60217ccacf02fef2af4393d6ecae` tracks only seven.
The global `*_api_progress.json` ignore pattern omitted this eighth file.
This new location preserves it without changing ATTIC or an existing run directory.
No output, hash pin, failure state, registration, or provenance has been rewritten.

Recovery is reproducible with
`scripts/adhoc/recover_5096_progress_backup_20261028.py`; it refuses a changed source
and refuses to overwrite either output. The file must be explicitly force-added
by exact path because the global ignore rule still applies.
Use `--output-dir /private/tmp/new-5096-recovery-check` to reproduce into a fresh
directory without touching the tracked recovery copy. The manifest's
`artifact_sha256_recorded_in_original_readme` hashes the recovered artifact, not
the README itself.

The independent review is on `codex/wave4-5096-review-20261028` at
`8973c375bc0bcae5dae8300ac16faeb3afe5d89d`. Its recorded comparison shows the other
seven originals match the preserved scratch bytes and all 98 original run artifacts
were archived unchanged. This recovery completes the eight available backups;
it does not recover the separately documented lost receipt-completion originals.

Claude retains ownership of any decision-record correction or authority erratum
under D50. This recovery does not ratify the false D43/D47 archive-maintenance claim,
approve a generation launch, or admit these canaries to scientific scoring.
