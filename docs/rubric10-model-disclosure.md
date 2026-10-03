# Optional model disclosure for legacy rubric10 summaries

The rubric10 summary command can produce a separate report set with declared
model identities. Its existing no-argument command and writer APIs preserve
their historical output and aggregation:

```bash
PYTHONPATH=src python scripts/summarize_rubric10_results.py
```

Select disclosure explicitly and name a directory that does not exist:

```bash
PYTHONPATH=src python scripts/summarize_rubric10_results.py \
  --model-disclosure declared-v1 \
  --evaluation-root data/evaluation_llm/rubric10 \
  --output-dir /tmp/rubric10-declared-models
```

The new directory contains `all_scores.csv`, `summary_table.md` and
`summary_report.md`. The CSV retains its nine existing columns and all their
values and ordering. Added columns identify each evaluation file, resolved
path, SHA256 and disclosure index, plus declared evaluator, evaluator family,
generator, generator family, same-family status, binding status, policy and
limitations. The raw evaluation's identity is kept outside the dictionaries
used for scoring, grouping and stable tie ordering.

Both Markdown files retain the existing score sections and append complete
per-rating evidence. The paired membership table explicitly distinguishes:

- The first rating selected for each legacy concatenated table row, repeated
  ratings unshown there, and unlisted projects or methods.
- Ratings included in an individual project/method average and unlisted ones.
- Ratings selected in the existing top20, qualifying ratings beyond that
  limit, and ratings below its threshold.
- Inclusion in the existing executive, method and project summaries.

The appendix lists every selected input, even if a legacy table omits it.
`csv_row` counts data rows after the header. The disclosure index follows the
original loader enumeration order and joins the CSV, membership and evidence
sections; it is not a ranking. The independent discrimination helper retains
its existing cohort and duplicate policy. No aggregate gets one member's
same-family label.

**This mode preserves legacy aggregation; it does not certify comparability.**
The existing tables use fixed project/method lists, choose the first
concatenated rating per group, pool individual scores, and rank on the reported
percentage. Project/method groups are not thereby comparable scoring
instruments. Changing those measurements or replacing historical published
reports requires separate review. Family disclosure does not make the old
aggregates an independence or calibration measurement.

The input boundary also stays unchanged: recursive
`individual/**/*_evaluation.json` and direct undated
`concatenated/*_evaluation.json` children, in the old loader order. Dated
concatenated subdirectories are excluded. Exact repeated content at different
paths remains distinct occurrences. Symlink bindings follow the shared
authority's resolved-path identity; sharing a hardlink inode does not transfer
a generation binding to a different declared evaluation path.

Without supplied generation evidence the generator and same-family status
remain unknown. Repeat this option for each selected rating to bind evidence:

```bash
  --generation-binding path/to/rating_evaluation.json \
      path/to/generated_record.yaml path/to/provenance.yaml
```

`--disclosure-root PATH` sets the root for relative paths recorded inside the
evidence, defaulting to the working directory; command-line paths retain
ordinary working-directory semantics. The unchanged shared
`data_sheets_schema.model_disclosure` authority (`model-disclosure-v1`)
checks supplied hashes, paths, sizes and run identities. It reads original
evaluation bytes before the loader adds a record-kind `evaluation_type`, so
that presentation tag cannot manufacture an evaluator-type conflict.
Score and disclosure captures must agree on resolved path and SHA256.
The report identifies captured bytes, without claiming later immutability or
provider authentication. Missing evidence remains unknown; generator identity
is never guessed from a method or filename.

All three report contents are prepared before exclusive directory and file
creation. Existing destinations, including input aliases, are refused.
Contradictory or malformed evidence refuses publication. A failure during
publication retains partial outputs as evidence; rerun into a different new
directory. The opt-in mode never replaces an input, provenance file, old
summary or registered archive. Disclosure options require the selector.

No model calls are made. Declared same-family status does not measure
self-preference, calibration or evaluator independence. This is the rubric10
consumer in #4317; #3327's remaining consumer/output decisions and #3328's
empirical requirements remain separate.
