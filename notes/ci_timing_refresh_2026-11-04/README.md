# BC1+G2 round-3 timing evidence, 2026-11-04 (#5485)

The task is the lead's `2026-11-04-codex-bc1-g2-ci-r3.md`, tasks 1–7.
The complete report and selected-tree search ledger are in the explicitly
requested sibling `plans/reviews/bc1_g2_ci_r3_2026-11-04.md`.

`input-manifest.json` pins 15 supplied JUnit XML files, nine CI metadata files,
the successful current collection, and the baseline weights at `decf0cab1`.
`measurement.json` gives every file's candidate coverage and selected source,
the largest 15 absolute changes, overhead calibration, full shard assignments,
and the G1/BC1+G2 admission-file comparison. G1 supplies no refreshed weights.
`verification.json` records exact reproduction, retained provenance, complete
collection unions, and refusal of a deliberately mismatched XML digest.
`validation.json` records the local tests with artifact hashes and commands.

Source precedence is latest BC1+G2 run 41735860489, earlier BC1+G2 run
41707437114, then current weight. A measurement is complete only when one shard
XML contains the exact current collected-case occurrence multiset for that file.
Failed/skipped completed cases remain measured timings, not evidence of success.
No cross-run or cross-shard joins fill an incomplete file. Previous source blocks
remain historical provenance; the new `bc1_g2_all_files_20261104` block governs
the refreshed snapshot.

The weights supply whole-file LPT assignment through the production sharder.
Estimated ordinary job seconds = assigned case-seconds / 4 + maximum positive
observed (job wall − JUnit case-seconds / 4), using the nine completed ordinary
shards from both BC1+G2 runs. This allowance includes worker imbalance as well as
setup/teardown. It is not a guarantee of future Linux runtime. All D75 limits and
CI workflow files remain unchanged.

## Reproduction

Run from this worktree with the already-installed dependency interpreter; no
installation, network, provider calls or Git synchronization is needed:

```bash
R3_PYTHON=/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python
"$R3_PYTHON" -B scripts/adhoc/refresh_ci_timings_r3_20261104.py refresh
"$R3_PYTHON" -B scripts/adhoc/refresh_ci_timings_r3_20261104.py verify
"$R3_PYTHON" -B scripts/adhoc/summarize_ci_r3_20261104.py validation
"$R3_PYTHON" -B scripts/adhoc/summarize_ci_r3_20261104.py profiles
```

`refresh` recomputes evidence and a scratch candidate; `--apply` additionally
writes the weights only when they equal the pinned baseline or exact candidate.
`pin` creates the input manifest once and refuses to overwrite it. Saved inputs
under sibling `scratch-bc1g2-timing/` are read-only evidence for reproduction.

The existing `refresh_ci_timings_bc1g2_20261103.py run` supervisor ran the
failing-first case, repaired canary, all six fixture modules, full collection,
and timing contracts. It enforces a 3600-second process-group deadline, uses
serial outer pytest, caps nested xdist at two, disables dependency `.pth`
execution, strips credentials, and installs an offline socket audit hook.
The exact invocation and environment are retained in each scratch evidence folder.

`profile_admission_r3_20261104.py run g1` and then `run bc1g2` run the same
slow admission case at exact source commits in fresh, isolated scratch archives.
The first run is the end-to-end canary. Each retains the source archive and its
SHA256, every included file's hash, imported-module origins, environment, JUnit,
process result, cProfile data and normalized per-function statistics. Source
snapshots include only the listed code/resources in `snapshot.json`; historical
run directories and `data/ATTIC/` are not copied. Snapshot directories have no
Git metadata. The test uses explicit fake clients and both source versions use
the same already-installed dependencies. No profiling patch enters production.

The paired profiles are sequential single-case observations with cProfile
overhead, on macOS/Python 3.13 rather than Linux/Python 3.12. Module self times
are additive; cumulative function times overlap and must not be summed. They
can identify executed work but cannot alone separate CI-host contention from
a source regression. Raw evidence stays in scratch; the compact comparison is
`profile-summary.json` and `profile-tables.md`.
