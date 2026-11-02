# T7: startup guard refusals lack a configured evidence path

Local review issue draft for PR #5213, D76 round 3, 2026-11-02. No GitHub issue
has been created. Status: failing-before evidence captured; minimal observer
repair prepared; after-repair validation pending. Existing evidence remains
unchanged.

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

The repair initializes the absolute, process-specific denial path at import,
before installing the audit hook, and removes its redundant assignment during
pytest configuration. It retains the existing captured opener, on-demand
creation, late-denial persistence, fatal write errors, and unchanged runner
acceptance rules. It creates no empty final denial file on clean startup.

## Captured baseline and remaining validation

At tests-only commit `13128650c586e1d0de46d71c84d6bd30b697b991`, the validation
owner ran the ten contracts against unchanged observer bytes
`50109df46a128456cb0eda3e356b91b6394c747ecee4508c79392c743f13e2b2`:
**9 passed, 1 error**, reported runtime 0.082 seconds. The new startup-denial
case errors at observer line 79 with
`TypeError: expected str, bytes or os.PathLike object, not NoneType`.
The clean-startup control and eight existing contracts pass.

Evidence: `d4d-executions/plans/reviews/pr5213_d76_round3_2026-11-02/observer-contracts-before-t7/unittest.log`,
SHA-256 `943922a9dc129f789e0a2fd48ad0c48640c1a4bbecfff9ba201829bf7c7cdaa2`.
The frozen contract file SHA-256 is
`46805b3fe1e65ad1160cf350c21f7a960c5f478517b83e83ce7227fb2bd02b71`.

The validation owner will run the unchanged contracts after independent review
of the repair. This draft makes no passing-after, full-suite, merge-readiness,
or issue-closure claim. No production behavior or runner acceptance rule was
modified.
