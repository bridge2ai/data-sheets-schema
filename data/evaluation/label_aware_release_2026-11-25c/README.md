# Presence evaluation of release series 2026-11-25c

Made with `scripts/adhoc/run_presence_evaluation_release_series_20261126.sh` (field presence,
deterministic, no model call) over the full and core records of
`2026-11-25c_claude-fable-5-2-claudecode-generic-v9`.

- **28 of 30 records are scored.** The evaluator skipped the full records of CM4AI replicate 1
  and replicate 3: they list component `resources`, the evaluator validates them as a
  collection, and that validation fails (#6377). The skips were reported on the run's output
  stream and are in no file of the run directory, which is why they are written here.
- The run directory's name is the evaluator's: a local-time stamp (2026-11-25 19:12 Pacific,
  which is 2026-11-26 03:12 UTC) and two hashes.
- These scores are not comparable with the semantic rubric scores of the series.
