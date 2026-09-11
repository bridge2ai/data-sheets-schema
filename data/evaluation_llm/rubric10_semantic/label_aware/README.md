# Label-aware rubric10 evaluations

## Historical invalid output retained for #833

On 2026-09-11, the disposition of
`AI_READI_2026-08-28dapi_rep1_evaluation.json` is to preserve the evaluator's
original output and annotate its structural invalidity. Its two `severity:
info` values are outside the semantic schema's `low`, `medium`, `high`
vocabulary. The score block is unaffected; this annotation does not certify
the file as schema-valid or reinterpret the evaluator's judgements.

SHA-256 of the unchanged JSON: `bf62f3893e8b7af07d71e90c7c15437d7273a842baf34059274f98514fab4dfb`.

The whole-corpus validator continues to report and fail on this artifact.
It is retained at its original path so historical comparisons and links
remain reproducible. New evaluations must pass the strict `--file` check
before completion. A future rescore must be written beside the prior
evaluation under a named instrument, never overwrite these bytes.
