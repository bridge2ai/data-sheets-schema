# Optional model disclosure for legacy rubric20 summaries

The rubric20 summary producer can append declared evaluator and generator
identities to a **new** set of reports. The existing no-argument command and
its historical outputs keep their prior behavior:

```bash
PYTHONPATH=src python scripts/summarize_rubric20_results.py
```

Select disclosure explicitly and name a directory that does not yet exist:

```bash
PYTHONPATH=src python scripts/summarize_rubric20_results.py \
  --model-disclosure declared-v1 \
  --evaluation-root data/evaluation_llm/rubric20 \
  --output-dir /tmp/rubric20-declared-models
```

This writes `all_scores.csv`, `summary_table.md`, and `summary_report.md`.
The CSV retains every existing column and value and appends the disclosure
policy, rating index, declared evaluator, evaluator family, generator,
generator family, same-family label, generation-binding status, exact resolved
evaluation path and SHA256, and limitations. Both Markdown files retain their
existing score sections, then append every rating's exact cohort membership
and the complete shared model-disclosure evidence. Disclosure indices join the
CSV, cohort membership table, and per-rating evidence within this report set.

Selection remains recursive `individual/**/*_evaluation.json` and direct
`concatenated/*_evaluation.json` children. Dated concatenated subdirectories are
excluded. Repeated ratings remain separate rows; existing cohort splits,
fixed and adjusted score bases, undefined percentages, exclusion identities,
top-performer order, and duplicate handling in discrimination are unchanged.
No aggregate row acquires a member's generator or same-family label.

Generator identity remains unknown unless explicitly supplied generation
evidence binds to a selected rating. Repeat the following option for each
binding:

```bash
  --generation-binding path/to/rating_evaluation.json \
      path/to/generated_record.yaml path/to/provenance.yaml
```

`--disclosure-root PATH` sets the root for relative paths recorded **inside**
that evidence; command-line file paths keep their usual working-directory
meaning. The default recorded-path root is the working directory. Binding,
hash, path, size, and run-identity checks use the shared
`data_sheets_schema.model_disclosure` authority (`model-disclosure-v1`), also
used by the standalone disclosure report. Duplicate or outside-selection
bindings and contradictory evidence refuse publication. Missing evidence is
reported as unknown rather than inferred from methods or filenames.

The shared authority reads the original evaluation bytes. Summary-only
`evaluation_type` record-kind tags are kept separate from the evaluator's
original type declarations, so they cannot manufacture evaluator-type
conflicts. Score and disclosure captures must have identical resolved paths
and SHA256 values. The appendix names those captured bytes; it does not claim
the files remain unchanged after capture or authenticate the provider.

All inputs and all three report contents are checked before creating the new
directory. Existing directories, files, or symlinks are refused, and each file
is created exclusively. If publication fails after it starts, any partial
outputs remain as failure evidence; rerun with a different new directory.
Inputs, provenance, old summaries, and registered archives are never replaced
by this mode. Options for disclosure require its explicit selector.

These are declared families associated with supplied local evidence.
Same-family status does not measure self-preference, calibration, or evaluator
independence. No scores are recomputed under a new instrument, and no provider
calls are made. This completes the rubric20 consumer in #4314; the remaining
consumers in #3327 and the empirical work in #3328 remain separate.
