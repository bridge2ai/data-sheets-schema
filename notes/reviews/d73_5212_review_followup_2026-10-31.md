# D73 follow-up to the 4cde66d2d implementation review

Work is in progress; this is not a completed-validation report.

## Required PR merge strategy

**#5212 must land as a merge commit. Do not squash or rebase it.** The positive
D41 ancestry boundary is `8ab03fda923d2c8caa9a2e65e558be73e92500e9`.
The explicit ancestry regression fails in a full repository if that commit is
not an ancestor of HEAD; a shallow repository skips with the stated reason
that the ancestry cannot be established from its incomplete graph.

## Completed initial checks

- Finding 1: all four prefix-sibling controls failed on unchanged production
  source at `4cde66d2d`. The same flat-layout canary passed after the fix, then
  all 214 legacy/refusal/verifier regressions passed. Raw reports and artifacts
  are under the authorized `scratch-5212fix/f1-*` basetemps.
- D73(a): 17 targeted age/reporting checks passed. Unknown age is eligible and
  reported separately from quality rows and the registered-evaluation plan hash.
- D73(b): the verifier remains limited to generic_v6 API records with a
  structured request specification. Other API conditions and agentic records
  are unsupported; the lead will file the extension issue.
- D73(c): all four additional accepted flips are disclosed individually in
  `tests/fixtures/pre_d41/README.md`.

The stopped earlier gate is evidence of `4cde66d2d` only. The revised validation
will use external basetemps, the requested broad set and one ordinary shard
out of four with up to four xdist workers. Main will be merged only after those
checks, with no hand resolution of production conflicts.
