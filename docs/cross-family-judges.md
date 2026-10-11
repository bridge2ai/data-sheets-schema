# Offline paired support and fitness analysis

`d4d evaluate cross-family-judges` captures and checks two declared rating slots
for each registered target, then computes descriptive paired statistics. It does
not dispatch requests, choose raters or thresholds, manufacture missing ratings,
authenticate provider identities, or approve a study. Parent #3328 and the
support/fitness calibration and human review obligations remain separate.

The feature accepts the existing `nested_support_result_v1` and
`top_level_fitness_result_v1` descriptor/result contracts. Each original
acceptor reconstructs its captured record, provenance, source bundle, schema,
instrument, target and request. The new panel compares a fixed common subject:
logical generation identity, exact input pins, logical schema closure, axis,
kind, pointer, typed value and actual prompt/context. Only the original request's
top-level `model` and `max_tokens`, and fitness context's `model`, are excluded
from exposure equality. Their complete values remain evaluator settings. Original
path labels remain evidence; schema import keys and bytes remain exact. Paths
embedded in prompt/specification content are not removed.

Specification comparison is axis-specific: support reconstructs its nested
specification; fitness reconstructs its fitness specification and generation
digest. Only locator metadata is omitted from the comparison. Recapturing a
custom schema at another path can change its verified generation digest and
fitness context even when the fitness request text is identical; such fitness
pairs remain incompatible. Moving an already captured package preserves those
original context values and remains supported. Opposite-axis manifest
declarations remain preserved, not newly verified. The consumer does not demand
an uncaptured, unused opposite-axis artifact.

## Four portable packages

The Python entry points live in `cross_family_judge_panel` and
`cross_family_judge_analysis`:

1. `prepare_panel(declaration, output, root=...)` creates `panel.json`.
   `recheck_panel(directory)` reconstructs it.
2. `accept_panel_results(panel, submissions, output, root=...)` creates
   `results.json`. `recheck_panel_results(directory)` reconstructs it.
3. `prepare_analysis_spec(panel, declaration, output)` creates
   `specification.json`. `recheck_analysis_spec(directory)` reconstructs it.
4. `analyze_panel_results(specification, results, output)` creates
   `analysis.json`. `recheck_panel_analysis(directory)` reconstructs it.

Each package contains its needed content-addressed artifact closure and current
checker source pins. Rechecking after relocation uses those artifacts, without
original input paths or executing captured Python. It reconstructs outputs and
compares the complete saved document. An unsupported protocol, tampered artifact
or incompatible reconstructed contract refuses; hashes are not proof of human
review or preregistration timing. Historical execution implementation metadata
is retained separately from current checking authority.

The CLI exposes the same eight actions:

```sh
d4d evaluate cross-family-judges prepare --declaration panel.json --root evidence --output panel-package
d4d evaluate cross-family-judges recheck --panel panel-package
d4d evaluate cross-family-judges accept-results --panel panel-package --submissions submissions.json --root evidence --output results-package
d4d evaluate cross-family-judges recheck-results --results results-package
d4d evaluate cross-family-judges prepare-analysis --panel panel-package --declaration policy.json --output policy-package
d4d evaluate cross-family-judges recheck-analysis-spec --specification policy-package
d4d evaluate cross-family-judges analyze --specification policy-package --results results-package --output analysis-package
d4d evaluate cross-family-judges recheck-analysis --analysis analysis-package
```

A zero exit means the package was consistently created or rechecked, including
an honestly incomplete roster. It does not mean all expected ratings exist or
are scientifically eligible. Invalid input or publication failure exits nonzero.
Publication stages a complete package and installs it without replacing an
existing destination, including a concurrent empty directory. It checks source
bytes again before publication. This observed equality is not proof of continuous
source immutability.

## Declarations and missing evidence

Panel declarations use `cross_family_judge_panel_declaration_v1`, with all keys
explicit: `panel_id`, nullable `predecessor_sha256`, project/cohort `matrix`,
`descriptors`, `pairs`, and `decisions`. Descriptor entries name `descriptor_id`,
`protocol`, and a `source` containing a normalized relative directory `path` and
SHA256 of its exact `descriptor.json`. Every descriptor must be referenced.

A pair declares `pair_id`, `record_id`, a supported `anchor` descriptor/target,
`selection_stratum`, and exactly `same_family`/`cross_family` slots. The anchor
is required even when both slots are null. A non-null slot names its descriptor,
exact `target_id`/`attempt_id`, nullable declared `rater`/`route` identities, and
nullable `execution_registration` directory reference. Source-derived subjects
cannot be duplicated by assigning another pair or descriptor alias. Distinct
actual generation identities remain separate even with identical input bytes.

The ten explicit decision keys are `selection_policy`, `rater_policy`, `route`,
`budget`, `scientific_review`, `context_review`, `calibration`,
`private_control_handling`, `canary`, and `execution_authorization`. Each is
`{status: pending|declared, reference: null|{path,sha256}}`; a declared decision
requires a captured reference. Selection strata use the same status/reference
with a nullable `label`: support's `supported|unsupported` or fitness's
`fit|unfit`. These labels are reviewer declarations, never derived from scores.

Submissions use `cross_family_judge_submissions_v1`, `panel_sha256`, and `slots`.
Every submitted row contains `pair_id`, `role`, nullable `saved_result` directory
reference (hash of `result.json`), and nullable `execution` containing relative
run `path` and `registration_sha256`. Omitted rows stay missing; foreign,
duplicate or completely empty submitted rows refuse.

A panel-pinned execution registration fixes the evidence basis. A missing or
failed run cannot be downgraded to caller-saved evidence. Existing ledger
reconstruction checks the full descriptor/request order and durable frontier.
If both a saved result and run are submitted, the result must equal the ledger's
actual saved result, including envelope and response pins. A valid response in a
failed HTTP/usage-limit dispatch remains visible but ineligible. Slot state,
assessment state, dispatch state, spent status, evidence basis, problems and raw
artifacts are retained separately. Unselected descriptor targets remain declared
scope, not additional panel observations.

## Explicit statistical policy

Analysis declarations use `cross_family_judge_analysis_declaration_v1`, an
`analysis_id`, exact `panel_sha256`, explicit `pair_ids`, and:

- `agreement: {weighting: equal_target|null}` and
  `gap: {weighting: equal_record|null}`;
- `support_indicator: {favorable_verdicts: null|[...]}` from the seven existing
  support verdicts, with empty/full sets allowed as explicit constant policies;
- `fitness_threshold: null|{cutoff: number, boundary: ge|gt}`, cutoff in [0,1];
- `grouping: instrument_context_kind_ordered_rater_configuration_and_evidence_basis`;
- `uncertainty`, with every key explicit: `method`, `confidence`, `resamples`,
  `seed`, `quantile`, `blocks`, and `strata`.

A null choice is pending and only suppresses dependent metrics. Confidence,
resample count and seed have no defaults. The supported method is
`paired_cluster_percentile_v1`, quantile `linear_n_minus_one`; confidence lies
strictly between zero and one, resamples are 2–100000, and seed is an unsigned
64-bit integer. Blocks and strata each partition exactly the selected records,
using `{block_id,record_ids}` and `{stratum_id,record_ids}`. Identical record-byte
hashes must share one block; different bytes do not establish independence.

Agreement uses all compatible accepted pairs, including unknown-family pairs,
with declared slot A/B orientation. Support has a seven-category nominal matrix
and unweighted Cohen kappa. Fitness reports exact accepted numeric equality,
separate four-category failure-label agreement, and optional threshold agreement.
There is no kappa over arbitrary continuous scores or rounded prompt anchors.
Matrices retain zero categories, marginal counts, observed/expected agreement and
explicit undefined reasons at n=0 or Pe=1.

Directional gaps additionally require known generator and rater families,
exactly one matching family, correct declared role assignment and non-null rater
and route identities. Otherwise the raw pair remains but its directional gap is
unavailable. Positive same-minus-cross values do not isolate a causal family
effect from evaluator severity or route differences. Within each record, both
sides average over the **same eligible paired targets**; those record differences
then receive equal weight. Records without an eligible pair are not zero gaps.

Groups preserve instrument, schema, context policy, target kind and ordered
rater settings/evidence basis. Target-specific request hashes are row evidence,
not grouping keys. Anonymous raters retain descriptor identity. The report keeps
the whole original roster, selected flags, exclusions, missing slots and groups
with zero eligible observations.

Fitness int/float operands retain their accepted JSON types and raw response
bytes. Arithmetic uses exact integer or binary64 rational values; 1 and 1.0 are
equal scores, and signed zero remains in source evidence. No extra precision
from the original decimal token is claimed. Boundaries and degeneracy are tested
before deterministic floating-point export.

Bootstrap resamples whole declared blocks with paired roles/targets intact,
retaining multiplicity. Original target proportions weight agreement strata;
original eligible record proportions weight gaps. The existing semantic kernel's
`sha256_counter_rejection_v1` draw schedule is reused without changing its source.
Draw statistics and linear quantiles are recomputed from original exact
contributions, not rounded helper outputs. Every declared stratum is required:
zero or one contributing block, a block crossing strata, pending uncertainty or
undefined point statistics makes the corresponding interval unavailable while
preserving point estimates/counts. No empty stratum or undefined draw is dropped.

Capture is bounded to 512 MB, each output to 64 MB, and panel size to 10000
records/100000 pairs. Computational/output budgets cover group projection,
resampling and exact recomputation before admitted loops; excessive work refuses
instead of truncating. These are engineering bounds, not study-size advice.
