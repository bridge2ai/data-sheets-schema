# Offline paired semantic analysis

The #4962 software slice under #3328 computes descriptive exact agreement,
unweighted Cohen's kappa, signed score differences, and paired cluster
percentile intervals from captured rubric10/rubric20 ratings. It does not run
raters, authenticate declarations, approve context, establish scientific
eligibility, or complete #3328's canary, actual second ratings, or separate
fitness/support panels.

## Capture, analyze, recheck

```sh
d4d evaluate cross-family-panel prepare-analysis \
  --panel /path/to/panel --declaration analysis-policy.json --output /path/to/new-spec

d4d evaluate cross-family-panel recheck-analysis-spec --specification /path/to/new-spec

d4d evaluate cross-family-panel analyze \
  --specification /path/to/new-spec --results /path/to/accepted-results \
  --output /path/to/new-analysis

d4d evaluate cross-family-panel recheck-analysis --analysis /path/to/new-analysis
```

Preparation captures a specification and the exact registered panel. Analysis
reconstructs existing saved-result acceptance from its captured artifacts,
checks the same panel bytes, and captures the specification, all result inputs
(including rejected submissions), and the computed report. Recheck reconstructs
all decisions and draws after relocation, without following original corpus or
rating paths. Captured Python is never executed. The supported imported
acceptor and analysis source identities must still match; a changed authority
needs a reviewed successor, not reinterpretation of an old report.

Captured instrument YAML uses a separate bounded safe loader because rubric
score descriptions have numeric mapping keys. It preserves scalar key types,
refuses duplicate keys (including equal numeric/Boolean keys), aliases, unsafe
tags and nonfinite values, and checks byte, node and collection-depth bounds
before construction. Manifest and record parsers retain their string-key rules.

Every output is a new directory. The publisher bounds and serializes the
report first, stages all artifacts and the manifest beside the destination,
fsyncs them, and installs the complete directory with an atomic no-replace
rename. An occupied destination, including a concurrently created one, is
preserved. Artifact-write failure exposes no partial destination. Only the
owned unpublished staging directory is cleaned up. This uses Darwin
`renamex_np(RENAME_EXCL)` or Linux `renameat2(RENAME_NOREPLACE)`; other platforms
refuse rather than use a replacing rename. A post-install directory-fsync
failure can report an error with a complete package already present; there is
no claim of rollback after installation or recovery from power loss.
Output paths containing a NUL character refuse before input capture or staging;
the native rename boundary independently checks both encoded path arguments.

## Explicit declaration

All keys below are mandatory; unknown keys refuse. These are **synthetic example
choices**, not defaults or an adopted study policy. Replace the digest and IDs
with those from the selected panel.

```json
{
  "format": "cross_family_panel_analysis_declaration_v1",
  "analysis_id": "synthetic-example",
  "panel_sha256": "<SHA256 of exact panel.json bytes including newline>",
  "record_ids": ["record1", "record2"],
  "instruments": [{"rubric": "rubric10", "version": "3.0"}],
  "agreement": {"unit": "record_item", "weighting": "equal_observation"},
  "gap": {"scale": "fixed_percentage_points", "weighting": "equal_record"},
  "grouping": "instrument_domain_ordered_rater_pair",
  "uncertainty": {
    "method": "paired_cluster_percentile_v1",
    "confidence": 0.9,
    "resamples": 20,
    "seed": 7,
    "quantile": "linear_n_minus_one",
    "blocks": [
      {"block_id": "b1", "record_ids": ["record1"]},
      {"block_id": "b2", "record_ids": ["record2"]}
    ],
    "strata": [{"stratum_id": "all", "record_ids": ["record1", "record2"]}]
  }
}
```

`record_ids` is a unique explicit subset of the panel, possibly empty; instrument
selections are a nonempty unique subset of its exact rubric/version choices.
The full original pair/slot roster is retained, including records not selected
for this analysis. Each non-null block or stratum mapping must partition
exactly the selected records. Known byte-identical selected records cannot be
split across blocks. They remain separate records; there is no deduplication
or assertion that different hashes imply independence.

Every field *inside* `agreement`, `gap`, and `uncertainty` may explicitly be null
while its policy is pending. No missing field receives a default. Pending
agreement does not suppress a complete gap policy, pending gap does not
suppress agreement, and pending uncertainty does not suppress point estimates.
Preparing a policy before results is possible, but timestamps or hashes do not
prove it was chosen before outcomes or scientifically preregistered.

## Pairing, categories and score bases

Analysis joins the exact registered record/rubric/version and common
input/context/scope/instrument binding, retaining both attempts and each
model/family/rater/route identity. `score_pair_complete` requires two accepted
ratings after reconstruction. `attributed_role_pair` additionally requires
fully declared identities, recognized generator/evaluator families, and exactly
one evaluator matching the generator family in the registered same-family
role. Missing attribution does not rewrite an accepted rating. Complete but
unattributed raw score pairs remain visible; they do not enter the primary
attributed agreement or signed-gap groups.

Groups remain separate by instrument identity/version and actual ordered rater
pair. Agreement additionally separates captured domains `{0,1}` and
`{0,3,5}`. Selected groups with no eligible observations still have denominator
rows and null estimates with reasons. The report retains all required matrix
cells, accepted/rejected/missing/unsupported slot states, selection flags,
unknown context, original applicability review status and all pending decisions.

`record_item` uses one score for each captured item ID and record. The existing
instrument defines it as the minimum of that item's resource scores. The
alternative `resource_item` uses each exact resource pointer/item pair; larger
collections then contribute more observations. Both use explicit
`equal_observation` weighting. Neither joins by array position or display name.
N/A remains null and outside the score categories; zero is a scored failure.
Both accepted ratings already obey the same captured applicability, so this
feature does not present that invariant as empirical applicability agreement.

For each agreement group, the report contains its full confusion matrix, row
and column marginals, agreeing count and n. With `Po = agreeing/n` and
`Pe = sum(row_total[c] * column_total[c]) / n²`, kappa is
`(Po-Pe)/(1-Pe)`. n=0 and Pe=1 are explicitly undefined, not zero or perfect
kappa. Exact rational arithmetic establishes degeneracy; there is no tolerance
that collapses a legitimate near-degenerate result. Values are converted to
unrounded floating outputs only for JSON reporting. No weighted kappa,
category recoding, interpretation thresholds, p-values, or significance labels
are introduced. See [Cohen (1960)](https://doi.org/10.1177/001316446002000104).

Gap scales are `raw_total_points`, `fixed_percentage_points`, and
`adjusted_percentage_points`. The declared one is averaged with `equal_record`
weighting within each compatible instrument/rater group. Every pair retains
canonical totals, full/applicable maxima, both percentages and excluded item
IDs. Percentages are derived from canonical scores and exact maxima; rounded
payload percentages are not subtracted. A zero applicable denominator is
unavailable, not zero. Positive differences mean the same-family rating was
higher; they do not distinguish family preference from severity or route.
Different rubrics are never pooled.

## Declared paired cluster uncertainty

For each metric group, every declared stratum is reported, including zero
contribution. Eligible records project onto original whole blocks; both raters
and all observations of a record stay together. In each stratum with G
contributing blocks, draw exactly G blocks with replacement for each replicate,
retaining repeated-block multiplicity. Original members stay in the captured
policy even when some members have unavailable ratings. There is no resampling
of individual items, permutation of roles, silent removal of required strata,
or retry of a degenerate statistic.

The original stratum weights are fixed before any draw: `N_h/N` eligible
records for gaps, `n_h/n` eligible observations for agreement. Each resampled
stratum mean or contingency proportion is combined using those original
weights; unequal sampled block sizes cannot change between-stratum allocation.
Within strata the declared equal-record/equal-observation estimand remains.
Contingency proportions and Pe=1 checks use exact fractions. The report emits
original counts, rational weights, every draw's block IDs and statistics,
undefined causes, and a schedule digest.

The interval is unavailable if the policy is pending, any whole block crosses
strata, any required stratum has fewer than two contributing blocks, the
observed statistic is undefined, or any requested replicate for that statistic
is undefined. Undefined draws are counted, never discarded or redrawn.
Constant finite replicate distributions can yield equal endpoints; that is
not evidence of verified precision. For confidence c, sort all B finite values
and interpolate at `(1-c)/2` and `(1+c)/2` using `h=(B-1)*p`, the adjacent order
statistics and h's fractional part. These are conditional resampling intervals,
not claims of representative sampling, independence, or verified population
coverage. A one-record canary can have point results and no interval.
[Field and Welsh (2007)](https://doi.org/10.1111/j.1467-9868.2007.00593.x)
discuss how cluster-bootstrap validity depends on the dependence model.

The RNG is the runtime-independent `sha256_counter_rejection_v1`, fully defined
as follows. For every group start counter zero; the prefix is ASCII
`cross-family-analysis-index-v1`, one NUL byte, then the unsigned 64-bit seed in
big-endian bytes. A candidate is the big-endian integer from
`SHA256(prefix || counter_as_8_big_endian_bytes)`. Increment the counter even
on rejection. For range G, accept only values below
`floor(2^256/G)*G`, and return value modulo G. At most 128 candidates are allowed
per index; exhausting this engineering bound refuses, without a biased fallback.
Process strata and block IDs in lexical order and replicates in ascending
zero-based order. Reset the same explicit seed per group; resamples across
groups are not asserted independent. Hash each canonical JSON object
`{"index": i, "strata": drawn_strata}` followed by one newline into the
schedule SHA256. No Python-version-specific PRNG state is required.

The implementation bounds manifest bytes, observations, resamples, worst-case
block-expansion/matrix work and emitted draw size before the corresponding
loops/publication. Bounds refuse rather than truncate results; they are
engineering limits, not recommended sample sizes or study defaults.

The Python APIs are `prepare_analysis_spec`, `recheck_analysis_spec`,
`analyze_panel_results`, `recheck_panel_analysis`, and the pure
`agreement_statistics(score_pairs, categories)` algebra function, all in
`data_sheets_schema.cross_family_panel_analysis`. Software tests use explicitly
synthetic ratings and cannot establish human approval or empirical calibration.
