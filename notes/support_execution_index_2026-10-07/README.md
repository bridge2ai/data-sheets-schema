# Captured support execution in the common index

Issue #4619 closes an offline reporting gap under #2929 and #4459. The original
fitness index reconstructs fitness dispatch, but nested support supplied as
standalone result files describes strict response acceptance only. It cannot
recover missing selections or distinguish a valid verdict body inside a failed
HTTP response. The new opt-in index preserves that dispatch evidence.

```sh
d4d evaluate fitness-results index \
  --descriptor /path/to/fitness-descriptor \
  --execution /path/to/captured-fitness-run \
  --support-execution /path/to/captured-support-run \
  --output /path/to/new-index

d4d evaluate fitness-results recheck-index --index /path/to/new-index
```

`--support-execution` selects `top_level_fitness_index_v2`. Omitting it retains
the v1 format and behavior, including its explicit supplied-attempts-only
support count basis. Fitness execution remains optional; its existing state,
mode and declaration fields describe the fitness axis. Support execution has
separate `support_mode`, `support_approval_basis`, decision references and
original readiness. A support execution never promotes caller-saved fitness
responses into observed calls.

V2 independently reconstructs one registered nested-support execution and its
descriptor. Every selected support target must belong to the exact same plan
and a record selected in the fitness descriptor. Matching record names or
values alone are insufficient. Top-level fitness target links are associations,
not propagated fitness verdicts on nested values.

There is one support row for every registered support selection. The
`dispatch_state` is `accepted`, `failed`, `spent_unknown` or `not_started`.
The separate row `state` is accepted only when dispatch and strict response
acceptance both succeed; failed dispatch is rejected, and unknown/unstarted
work is missing. Raw assessments remain available without counting their
verdicts as accepted observations. `spent` records whether admission occurred,
not whether a provider billed a call. Per-kind counts retain selected, missing,
rejected and accepted attempts, with additional dispatch counts. These are
registered-selection denominators, not a claim that the entire plan or cohort
was executed.

Standalone support results may be included, but each must match the exact
registered descriptor, attempt and reconstructed result. Duplicates and
contradictions are refused. A matching accepted body cannot override failed
dispatch. The index captures both execution ledgers and any saved reports;
rereading reconstructs them from content-addressed bytes after the original
directories are unavailable. No calls, retries or reads from original generation
input paths are part of index construction or rereading. Construction reads the
explicitly supplied descriptor and captured run directories. Publication
requires a new directory.

This remains mechanical evidence integration. Decision references are caller
declarations, not authenticated scientific approvals. Scientific eligibility
stays false, and original readiness blockers remain unchanged. Human controls,
instrument/context decisions, empirical calibration, paid-run authorization,
project canaries, the reference cohort and rubric/receipt/figure joins remain
under #2929, #3342 and #3343.

The focused tests use invented responses through a real local HTTP endpoint.
They cover both-axis reconstruction, failed HTTP with a valid verdict,
malformed/truncated responses, interrupted publication, unstarted selections,
no-repurchase behavior, matching and contradictory standalone support evidence,
portable rereading and unchanged v1 output. These are software fixtures, not
calibration measurements. Validation results will be recorded after the
serialized test run and independent review.
