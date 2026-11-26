# Repeat scorings on `2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6`

Scorings 2 and 3 of the 15 records of `2026-11-25c_claude-fable-5-2-claudecode-generic-v9`,
30 files each, in `scoring_rep2/` and `scoring_rep3/` by rubric family. Scoring 1 is in
`data/evaluation_llm/{rubric10,rubric20}_semantic/label_aware/2026-11-25_codex-gpt-6-astra-ultra-fast_root-scope-v6/` and is not copied
here. Existing readers of `data/evaluation_llm` do not look in this directory, so no
scoring is counted twice.

- Every file here was written by the same measured scorer, prompt and inputs as
  scoring 1, validated by the strict exact-file validator, and published byte for byte
  from the validated copy.
- `scorings.tsv` lists all 90 cells: state, published attempt, points, maximum, sha256
  and path, and for a replaced cell the reason attempt 1 was refused. It is written by
  `scripts/adhoc/root_scope_triplicate_manifest_20261126.py` from the result of
  `scripts/adhoc/verify_root_scope_repeats_20261126.py`.
- Three scoring-3 cells are replacements (attempt 2) of refused runs. See
  `notes/root_scope_v6_scoring_variation_2026-11-26.md`, which also reports the
  run-to-run variation.
- The repeat and replacement paths are described in
  `notes/root_scope_repeat_scoring_20261126.md`.
- The launch wrappers bind machine-local paths and are kept with the run evidence, not
  in this repository; the commands they run are those of
  `scripts/adhoc/repeat_root_scope_scoring_20261126.py`.
