# Offline semantic cross-family panel registration

This is the registration engineering slice #4606 under #3328. It fixes the
selected records, instrument identities and rating attempts before any results
are consumed. It does not ingest scores, calculate agreement or preference,
select a provider route, or execute requests.

Use an explicit declaration and source directory:

```sh
d4d evaluate cross-family-panel prepare \
  --declaration /path/to/panel-declaration.json \
  --root /path/to/source-evidence \
  --output /path/to/new-panel

d4d evaluate cross-family-panel recheck --panel /path/to/new-panel
```

Preparation publishes a new captured package. Rechecking reconstructs its
derived identities, declared coverage and pending decisions from captured
bytes after relocation. Existing packages and historical rating files are
preserved. A changed selection needs a new package, with its predecessor
identified explicitly when supplied.

The required project-by-cohort matrix remains visible even when selected
records do not fill it. Both semantic rubrics use the same selected records.
Each planned rating has a fixed attempt and a declared same-family or
cross-family role for that record and instrument. Missing attempts remain
missing; this registration cannot choose a replacement retry or select ratings
because their outcomes are favorable.

Generation and rater identities are declarations. Known family relationships
must agree with the existing family classifier; an unknown model is not proof
of a cross-family comparison. Byte-identical records are reported as shared
content rather than silently treated as independent evidence.

The registration preserves original applicability context and its normalized
meaning. Missing context remains unknown. Supplied values and review status
are separate: a pending context is not approved scoring context. Instrument
selection reuses the versioned semantic rubric contracts; choosing the draft
rubric20 v4 does not provide its pending scientific review.

Structural completeness never authorizes execution or establishes scientific
eligibility. Policy/reviewer references remain declarations rather than
authenticated approvals. The #2911/#2912 scientific/context decisions and
#3328's actual rater, route, limits/budget and paid authorization remain pending.

#3328 also retains paired saved-result acceptance, exact agreement, Cohen's
kappa, descriptive same-family minus cross-family score differences with
appropriate uncertainty, separate fitness/support panels, the canary and
actual second ratings. Two raters alone do not separate family preference from
general rater severity or route effects. No empirical result is claimed by
this package or its synthetic tests.

## Declaration fields

The closed JSON declaration uses `format: cross_family_panel_declaration_v1`.
Unknown fields are errors. Paths in evidence references are relative to the
explicit `--root`; each reference also supplies the exact file's SHA-256.

| Top-level field | Value |
|---|---|
| `panel_id` | Nonblank identity for this panel. |
| `predecessor_sha256` | Previous package digest declaration, or null. |
| `matrix` | `projects` and `cohorts` lists defining the full required Cartesian product. |
| `records` | Explicit selected record declarations described below. |
| `instruments` | Exactly one `{rubric, version}` for `rubric10` and one for `rubric20`; only existing supported semantic versions. |
| `slots` | Fixed planned rating attempts described below. |
| `decisions` | `selection_policy`, `rater_policy`, `route`, `budget`, `scientific_review`, and `execution_authorization`; each has `status` (`pending` or `declared`) and `reference` (text or null). |

Each record names `record_id`, `project`, `cohort`, `label`, `method` and a positive
integer `replicate`, plus `input: {path, sha256}`. `provenance` is an optional
`{path, sha256}` or null; it is captured as an unverified artifact declaration,
without inferring a generation model or output association from its contents.
`generator` supplies `model` and `family`, each text or null.

The record's `context` has `source` (a `{path, sha256}` reference or null),
`review_status` (`pending` or `declared_reviewed`) and `review_reference` (text
or null). A review declaration about absent context can describe only the
unknown-context declaration; it does not introduce reviewed predicate values.

Each slot names `record_id`, `rubric`, `role` (`same_family` or `cross_family`),
`attempt_id`, `model`, `family`, `rater` and `route`. Pending model/rater/route
values are null. A slot derives its record, context, scope and instrument
binding from the registration; the two roles cannot silently use different
inputs. Omitted slots are reported against the complete expected roster.

Instrument resources are selected by the existing version selector and read
from the imported package. The evidence directory need not contain these
resources; any copy at the corresponding authority path must match the
package bytes exactly. Captured resources include the selected definition,
output schema, evidence authority, validator helpers and rubric20 v4's actual
predecessor when that draft is explicitly selected. Recheck uses only captured
bytes and establishes internal consistency, not authenticated origin.

Semantic version 2.0 remains available for historical classification. Its
`acceptance_contract` is `historical_classification_only`, and registration
always records a pending new-output acceptance blocker for that instrument.
Versions 3.0 and 4.0 use the current new-output validator contract. Registration
does not itself accept an output under any of these versions.

## Validation

255 tests passed: 61 new panel and CLI tests plus 194 existing context, scope,
instrument and model-disclosure controls. The synthetic adversarial controls
cover duplicate identities and attempts, missing denominators, unknown versus
false context, unknown families, unverified provenance, resource substitution,
relocation, altered captured bytes, forged readiness and preserved outputs.

Independent review identified #4607 (historical-v2 acceptance) and #4608
(caller-substituted authority). Both are fixed and covered by regressions;
follow-up source review found no further confirmed issue. Source and external
JUnit digests are recorded in `validation.json`. No provider calls, real
ratings, human approvals or scientific measurements were produced.
