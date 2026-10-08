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

The integration tests use invented responses through a real localhost HTTP
endpoint. Independent adversarial tests supply invented bytes in-process under
a fixture that forbids network and provider access. They cover both-axis
reconstruction, failed HTTP with a valid verdict, malformed/truncated responses,
interrupted publication, unstarted selections, explicit false/zero values,
no-repurchase behavior, matching/contradictory/duplicate standalone results,
exact plan and selected-record joins, rehashed evidence tampering, portable
rereading and unchanged v1 output. These are software fixtures, not calibration
measurements.

## Validation

The serialized eight-module suite passed **221 tests**, with zero failures,
errors or skips, at commit
`af75e9f326dea67a0104411b954caa0be7d898b7` (tree
`fb9197a139cfca3675509716e4289838c1efd005`). This includes 9 new integration
cases, 19 independent adversarial cases and 193 existing fitness, nested support
and ledger regressions. JUnit records 254.734 seconds. Its SHA-256 is
`771cb2f741ac50662105757e3f509f6ed0e10c3d38f6c9b4cd906bcd88eb82b8`.
[validation.json](validation.json) records the exact source/test hashes, JUnit
identity and per-module counts. Independent checks confirmed those files match
the tested commit; the evidence update changes documentation only.

Independent adversarial source review found no confirmed production defects.
These results complete only the engineering slice in #4619. They do not close
#2929, #3342 or #3343, authenticate decision references, produce scientific
scores, or change human review, paid-run, readiness or audit28 holds.
