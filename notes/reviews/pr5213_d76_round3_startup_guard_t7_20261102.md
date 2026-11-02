# T7: startup guard refusals lack a configured evidence path

Local review issue draft for PR #5213, D76 round 3, 2026-11-02. No GitHub issue
has been created. Status: regression contracts prepared; before/after execution
and implementation are pending. Existing evidence remains unchanged.

## Finding

At reviewed source `fc055cc5742d99cee34017f7571e73de5ed0a4a5`,
`scripts/adhoc/run_d76_round3_validation_20261102.py:73` calls the observer's
`install_guard()` before importing/running pytest in the controller and before
executing the worker bootstrap. In
`scripts/adhoc/d76_round3_pytest_observer_20261102.py`, `_DENIAL_PATH` is initially
`None` and is assigned only by `pytest_configure`.

If the installed audit callback encounters a prohibited operation during that
startup interval, its captured opener receives `None` instead of a path. It
raises an incidental `TypeError` before writing the denial row, rather than
persisting the refusal and raising the intended offline-guard exception.
The operation still fails; this finding concerns missing denial evidence and
the diagnostic contract, not a demonstrated network bypass or an invalidation
of every prior run. No live operation was attempted for this review.

## Contracts and bounded repair

The eight existing observer I/O contracts configure pytest before triggering
their audit callbacks. Two new contracts in
`scripts/adhoc/test_d76_round3_observer_io_20261102.py` cover the actual earlier
installation order without contacting a provider or network:

- A synthetic prohibited socket audit event before `pytest_configure` must
  persist its exact event/detail row and raise the intended guard refusal,
  without manufacturing phase evidence.
- Allowed local startup events must create neither a denial artifact nor a
  phase journal before configuration.

The proposed repair is to initialize the process-specific denial path before
installing the audit hook. Retain the existing captured opener, on-demand
creation, late-denial persistence, fatal write errors, and unchanged runner
acceptance rules. Do not create an empty final denial file on clean startup.

The validation owner will capture failing-before and passing-after evidence.
This draft makes no test-pass, full-suite, merge-readiness, or issue-closure
claim. The source implementation has not been changed as part of this draft.
