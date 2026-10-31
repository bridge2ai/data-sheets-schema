# Offline review ledger, 2026-10-29

Read-only adversarial pass over the N1/N3/N4 production and test diff at
`4b87bf52d`. No production finding in the requested scope. N2, N5–N10 and
N12–N17 remain activation work; N11 remains a merge-order note.

## Local issue N3-test-portability

The new pathological-pattern test launched the local validation harness, whose
bootstrap requires a physical virtualenv. A CI interpreter without `pyvenv.cfg`
could fail before exercising the regex deadline. This is a test portability
defect in N3, not a production regex defect.

Disposition: remove that test dependency; launch the test file itself with the
parent's import paths and the measured source tree, retaining the outer timeout.
Verification is included in the final causal replay and acceptance suite.

This local issue records the finding because the task explicitly prohibits
network and `gh`; no GitHub issue or PR was opened.
