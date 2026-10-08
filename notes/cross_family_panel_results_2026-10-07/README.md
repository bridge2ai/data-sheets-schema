# Captured semantic panel rating acceptance

This implements the saved-rating engineering slice [#4651](https://github.com/bridge2ai/data-sheets-schema/issues/4651)
under #3328. It checks caller-supplied ratings against the registered panel's
exact selected record, rubric/version, role, attempt, model, family, rater,
route and common input binding. It does not run a rater or calculate agreement.

```sh
d4d evaluate cross-family-panel accept-results \
  --panel /path/to/captured-panel \
  --submissions /path/to/submissions.json \
  --root /path/to/saved-ratings \
  --output /path/to/new-results

d4d evaluate cross-family-panel recheck-results --results /path/to/new-results
```

Both commands report the saved decisions as JSON. A successful command means
the package was prepared or reconstructed; inspect `counts` and `rows` for
accepted, rejected, missing and unsupported ratings. A partial or rejected
panel is still a valid evidence package. Existing output directories are never
replaced, and all final manifest bytes are bounded before creating a directory.

## Closed submission declaration

The declaration contains exactly `format: cross_family_panel_submissions_v1`,
`panel_sha256` (the exact `panel.json` bytes, including its newline), and
`submissions`. Each submission has these fields:

| Field | Required association |
|---|---|
| `record_id`, `rubric`, `role` | One selected panel slot; rubric is `rubric10` or `rubric20`. |
| `version` | That slot's selected semantic version. |
| `attempt_id`, `model`, `family`, `rater`, `route` | Exact registered declarations, including null where declared. |
| `binding_sha256` | Exact registered common record/context/instrument binding. |
| `result` | `{path, sha256}` for the exact saved JSON bytes under the explicit root. |

Unknown slots, duplicate slot submissions, duplicate attempt declarations,
wrong panel digests, missing declared files and file/hash conflicts refuse the
operation before publication. A known slot with conflicting associations is
retained as rejected; it cannot select an alternative attempt. The payload's
model and any evaluator identity must also agree, so a correct sidecar cannot
relabel another model's output. Present identity/hash aliases are checked
independently. No association authenticates provider execution.

`results.json` pins the exact panel and submission declaration, captures all
referenced artifacts under their SHA-256 names, and records one row for every
required panel slot. An omitted submission stays missing; an unregistered slot
stays missing even if bytes are offered for it. Malformed or inconsistent
ratings stay rejected. Historical semantic v2 ratings remain unsupported.
There is no retry discovery or selection based on score. The package is one
explicit declaration, not a global registry preventing a caller from creating
another contradictory package.

## Captured resources and compatibility

The existing semantic schema, scope, applicability, arithmetic, quotation,
absence, count and issue-link checks are reused. The explicit `resource_reader`
seam reaches both classification and input-checked validation, including rubric
and evidence-name authority reads. It leaves default validator callers
unchanged. Captured validation rejects external JSON Schema references and
uses a resolver with no network retrieval; it does not execute captured Python.

The original context bytes and normalized context are both retained. Acceptance
uses the original caller context, never a rating's own declaration to fill a
missing predicate. False and missing context remain different. The selected
v4 definition and predecessor remain exactly those in the captured panel;
installed instrument resources are not substituted during recheck.

Only panels whose `validator_authority` source pins match the currently
supported implementation can accept new saved ratings. Adding the resource
seam changes those source bytes, so **pre-#4651 panels remain recheckable as
registrations but their submitted ratings are unsupported here**. No old
validator is executed or assumed equivalent. Prepare a new registration with
the previous `panel.json` SHA-256 in `predecessor_sha256`, preserving the explicit
selection and pending decisions. This records a successor; it does not migrate
ratings automatically, perform a campaign, or authorize changed context.
Tests cover coherent older-code packages and a fresh successor declaration.

Result recheck reads the copied artifacts and the supported imported
implementation's source identities. It does not follow original corpus/rating
paths or resolve ambient instrument files. A changed implementation requires
review; it cannot silently reinterpret a previously saved acceptance report.
Hash consistency does not authenticate a caller who can replace an entire
package and all of its declarations.

## Holds and validation

Acceptance means offline structural and internal consistency. A cited value
may still fail to justify a judgement. No scientific correctness, human
approval, provider authentication, independence or empirical calibration is
established. `execution_authorized` and `scientific_eligibility` remain false;
missing cells, missing attempts, duplicate input clusters and pending decisions
are carried forward. Null/unrecognized model-family declarations retain their
registration limitations; a null rating model cannot bind a submitted payload.

#3328 retains actual ratings, routes/budget/authorization, agreement statistics
and the separate fitness/support panels. #2911 and #2912 retain their scientific
and applicability review holds. Synthetic full-score test fixtures are software
controls, not approved scientific labels or empirical evaluation results.

Independent review found and fixed [#4652](https://github.com/bridge2ai/data-sheets-schema/issues/4652):
a draft resource-seam edit leaked an undefined variable into the historical
validator CLI. Focused regression cases cover both its existing schema routes.

Validation is pending the root agent's serialized test run. No tests, provider
calls, real ratings, replay or native applications were run while writing this
implementation. Planned checks include both new result modules, existing panel
registration/CLI controls, and existing semantic context/evidence/v4/default
validator tests. Exact source and JUnit evidence will be recorded after that run.
