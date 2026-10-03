# Optional model disclosure in semantic comparisons

The active `scripts/report_semantic_comparison.py` report can show declared
generator/evaluator families alongside each rating, using the existing
`model-disclosure-v1` authority. Select the `declared-v1` policy explicitly:

```sh
PYTHONPATH=src python scripts/report_semantic_comparison.py rating.json \
  --model-disclosure declared-v1 \
  --generation-binding rating.json generated.yaml provenance.yaml \
  --disclosure-root /path/to/recorded/tree \
  --output new-comparison.md
```

The normal command and `report(paths, cohort, ...)` API keep their existing
output. Neither the current reference-rescore controller nor completed CBORG
conditions opt in automatically. The latter continue to read their verified
archived report helper. Historical reports, registrations, ratings, scoring
instruments and source records are not rewritten.

The Python API adds keyword-only `disclosure_policy="declared-v1"`,
`generation_bindings=[GenerationBinding(evaluation, input, provenance)]`, and
`disclosure_root=Path(...)` to `report`. Import `GenerationBinding` from
`data_sheets_schema.model_disclosure`. Bindings and a root require an explicit
policy; an unknown policy is refused. The root anchors paths recorded inside
the evidence files and defaults to the current directory. It does not discover
inputs or guess the original study tree. File arguments retain normal caller
filesystem meaning. Existing semantic `evidence_inputs`/`evidence_contexts` and
CLI flags keep their separate purposes.

The added columns are evaluator family, generator identifier, generator
family, same-family status and generation-binding status. The existing
evaluator display/key column is retained. An appended disclosure section lists
every rating's declared evaluator key/type, paths, captured hashes, binding
checks, unknown reasons and limitations. Repeated ratings remain separate
rows; the appendix's rating order is the table's order. A supplied binding
applies to each occurrence of that exact resolved evaluation path. A shared
basename does not establish a shared rating or binding.

The comparison and disclosure must identify the same evaluation path and exact
SHA256. The reporter checks these before scoring each captured evaluation;
changed bytes or a changed symlink target between the captures refuse output.
The detailed disclosure preserves the bytes' identities rather than claiming
that all source files stayed immutable afterward.

Without a binding, generator/family and same-family status are explicitly
unknown. A binding that contradicts a supplied hash, path, byte count or run
identity is refused; it is not silently downgraded to unknown. All the shared
[model-disclosure rules](model-disclosure.md) apply, including non-LLM and
conflicting evaluator-type handling, explicit model identifier precedence,
and no generator inference from method names, filenames or current defaults.
Old output size mismatches are not ignored to make a historical association.

With this policy, `--output` must name a new file. Existing files and direct,
symlink or hardlink aliases of evaluations, semantic evidence/context,
generation inputs and provenance are refused. Exclusive creation also refuses
an output alias created after rendering. No separate sidecar is needed: the
Markdown appendix contains the complete shared per-rating disclosure fields.

Disclosure does not change points, fixed or adjusted denominators, applicability,
cohorts, repeated-rating exclusions, evaluator grouping or discrimination. It
does not make a family label a comparability criterion. These are associated
local declarations, not authenticated provider identities; same-family status
does not measure self-preference, calibration or evaluator independence.

Hybrid/legacy summary writers and any decision to replace historical summary
outputs remain separate work under #3327. Cross-family rating design, route,
budget, paid canaries and empirical calibration remain under #3328. No model
execution is performed by this report.
