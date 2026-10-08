# Captured support calibration evidence

This implements the offline evidence layer requested in #4599, under #3343,
#3342 and #2929. It registers expected labels against an existing nested-support
execution registration and reconstructs results from captured execution bytes.
These commands do not dispatch provider requests.

This is software infrastructure. Independently adjudicated original v10b–v10j
controls, the owner's decision on private-control handling, instrument/context
review, and explicit paid-run authorization remain pending. Synthetic fixtures
are not empirical calibration. Human reviews under #2912 and #2921 remain
pending independently.

## Workflow

Start with a nested-support descriptor from `d4d evaluate support-results
prepare` and an explicit registration from `d4d evaluate support-execution
prepare`. The registration selects a single attempt per target and fixes the
record, bundle, schema, prompt, model and effective request. A support-calibration
manifest must include exactly those selected attempts; it cannot silently drop
difficult controls or substitute another instrument.

```sh
d4d evaluate support-calibration prepare \
  --registration /path/to/registered \
  --controls /path/to/controls.json \
  --output /path/to/new-calibration

# Before a captured run exists, this reports missing observations.
d4d evaluate support-calibration report \
  --calibration /path/to/new-calibration

# Given a separately authorized, already captured execution:
d4d evaluate support-calibration report \
  --calibration /path/to/new-calibration \
  --run /path/to/captured-run \
  --output /path/to/new-portable-report

d4d evaluate support-calibration recheck \
  --calibration /path/to/new-portable-report
```

Both publication commands require a new output directory. Reports capture the
evidence necessary to reconstruct them after relocation, without consulting
the original source locations or dispatching another request.

## Control manifest

The closed JSON format is `support_calibration_controls_v1`. Top-level keys are
`format`, `calibration_id`, `registration_sha256` and `controls`.
`registration_sha256` hashes the exact `registration.json` bytes, including its
trailing newline. Each control has these fields:

| Field | Meaning |
|---|---|
| `control_id` | Unique, nonblank identifier within this manifest. |
| `target_id`, `attempt_id` | Exact selected target and attempt. |
| `kind` | `relationship_edge` or `attribute_value`; facets remain separate. |
| `pointer` | Exact selected JSON pointer into the captured record. |
| `binding_sha256` | SHA-256 of `support_plan.canonical(selection["binding"])` from the captured descriptor. |
| `review_status` | `pending`, `reviewed` or `synthetic`. |
| `expected_verdict` | One of the seven registered verdicts; pending controls may leave it null. |
| `defect_class` | Explicit caller-declared stratum; pending controls may leave it null. |
| `finding` | `{ "reference": "...", "sha256": "..." }` declaration identifying the source finding. |
| `review` | Review declaration in the same form, or null. Required for reviewed controls. |

Finding and review references are declarations, not authenticated approvals or
evidence that private originals were inspected. They are not dereferenced.
Preparing a manifest does not adjudicate its labels. Synthetic labels do not
claim a human review. A registration declared `local_fixture` always yields
software-only results, even if someone declares its labels reviewed.

The verdict vocabulary is `supported`, `partially_supported`, `unsupported`,
`contradicted`, `status_shifted`, `relationship_unsupported` and `wrong_document`.
A defect class is a reporting stratum, not an additional model-predicted class.

## Interpreting the report

The report reconstructs the registered executor's admission, response and
settlement evidence. A syntactically accepted verdict inside an HTTP failure
does not count as an accepted observation. Missing runs, failed calls,
unstarted attempts and admitted calls without a returned response remain
distinct; the last case is `spent_unknown`.

Reviewed controls and synthetic controls are reported separately, as are
relationship edges and attribute values. Pending labels are unscored and stay
in unresolved counts. Detection means an expected non-`supported` control
received a non-`supported` verdict; exact verdict agreement is reported
separately. A false positive is a supported control receiving any other verdict.

Headline recall, supported-negative false-positive rate and verdict agreement
are undefined when required controls are unresolved. A zero denominator also
gives an undefined rate. Conditional rates over available observations are
explicitly labeled and retain their denominators; they do not replace the
complete-control measures. No numeric result grants campaign authorization or
scientific eligibility. Original readiness blockers are retained.

After independently reviewed controls and explicit run authorization are
available, empirical calibration acceptance must precede project canaries,
the reference cohort and figure joins. The parent issues remain open until
those obligations are fulfilled.

## Review and validation

Two implementation review rounds addressed #4600 (returned metadata aliasing)
and #4601 (publishing a document larger than its own reader accepts). The second
round tightened the size regression to require the publication-specific error;
calibration now applies its own consistent document limit without changing
external plan or executor limits. Independent final review found no remaining
blocker.

All 419 selected tests passed across the final runs, including all 51 calibration
tests. The broad sandbox run passed 355; 64 existing loopback transport fixtures
could not bind their local sockets. Those same 64 passed when local binding was
allowed. There were no provider calls, skipped tests or unresolved failures.
`validation.json` records counts, JUnit hashes and the tested source hashes.

The selection comprises support judge/targets/planning, nested support
planning/results/execution, calibration core/adversarial/CLI, top-level fitness
results, fitness execution/index, and evaluation CLI/runtime-option tests. The
test commands used `PYTHONDONTWRITEBYTECODE=1`,
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, the isolated checkout's `src` and repository
root on `PYTHONPATH`, and `python -B -m pytest -q -p no:cacheprovider`, with test
temporary directories and JUnit output outside the checkout.
